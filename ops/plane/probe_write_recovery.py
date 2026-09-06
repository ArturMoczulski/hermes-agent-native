"""Opt-in AN-22 lost-response proof against disposable local Plane data.

A loopback relay forwards one armed mutation to the pinned local Plane origin,
then discards its successful response. Recovery uses the real public read API
through a reopened control database and fresh host authority. No transport mocks,
automatic mutation retries, owner credentials, uploads or artifact fetches.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import socket
import sys
from threading import Lock, Thread
from urllib.parse import unquote, urlsplit
from uuid import UUID, uuid4

import requests

from probe_scoped_reads import ProbeFailure, call, local_base, require, results
from probe_scoped_writes import WriteProbe

MAX_RELAY_BODY = 1024 * 1024
MUTATIONS = frozenset({'POST', 'PATCH', 'DELETE'})


class LossRelay:
    """Real HTTP relay pinned to one local origin, fixture project and key."""
    def __init__(self, origin, prefix, api_key):
        self.origin, self.prefix, self.api_key = origin, prefix, api_key
        self.lock = Lock()
        self.armed = None
        self.attempts, self.forwarded = Counter(), Counter()
        self.losses, self.failures = [], []
        relay = self

        class Server(ThreadingHTTPServer):
            daemon_threads = True

            def handle_error(self, request, client_address):
                with relay.lock:
                    relay.failures.append('handler_error')

        class Handler(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'

            def log_message(self, *args):
                pass

            def reply(self, status, body=b'{}'):
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.send_header('Connection', 'close')
                self.end_headers()
                self.close_connection = True
                if body:
                    self.wfile.write(body)

            def handle_request(self):
                method = self.command
                with relay.lock:
                    relay.attempts[method] += 1
                parsed = urlsplit(self.path)
                path = unquote(parsed.path)
                if (method not in {'GET', *MUTATIONS} or parsed.scheme or parsed.netloc
                        or parsed.fragment or not path.startswith(relay.prefix)
                        or path != parsed.path or '..' in path.split('/') or '//' in path
                        or self.headers.get('X-API-Key') != relay.api_key
                        or self.headers.get('Transfer-Encoding')):
                    self.reply(403)
                    return
                length = self.headers.get('Content-Length', '0')
                if not length.isdigit() or int(length) > MAX_RELAY_BODY:
                    self.reply(413)
                    return
                body = self.rfile.read(int(length))
                with relay.lock:
                    rule = relay.armed if method in MUTATIONS else None
                    if method in MUTATIONS:
                        if rule is None or rule['method'] != method or rule['path'] != path:
                            relay.failures.append('unarmed_or_unexpected_mutation')
                            self.reply(409)
                            return
                        relay.armed = None
                upstream = requests.Session()
                upstream.trust_env = False
                try:
                    with upstream.request(method, relay.origin + self.path, data=body or None,
                            headers={'X-API-Key': relay.api_key, 'Content-Type': 'application/json',
                                     'Accept-Encoding': 'identity'},
                            allow_redirects=False, stream=True, timeout=15) as response:
                        output = bytearray()
                        for chunk in response.iter_content(16384):
                            output.extend(chunk)
                            if len(output) > MAX_RELAY_BODY:
                                raise ProbeFailure('Relay response exceeded its bound')
                        with relay.lock:
                            relay.forwarded[method] += 1
                        if rule is not None and response.status_code == rule['status']:
                            resource_id = None
                            try:
                                value = json.loads(output) if output else None
                                if isinstance(value, dict) and isinstance(value.get('id'), str):
                                    resource_id = str(UUID(value['id']))
                            except (ValueError, TypeError):
                                pass
                            with relay.lock:
                                relay.losses.append({'operation_id': rule['operation_id'],
                                    'method': method, 'status': response.status_code,
                                    'resource_id': resource_id})
                            self.close_connection = True
                            try:
                                self.connection.shutdown(socket.SHUT_RDWR)
                            except OSError:
                                pass
                            self.connection.close()
                            return
                        self.reply(response.status_code, bytes(output))
                except (requests.RequestException, ProbeFailure):
                    with relay.lock:
                        relay.failures.append('upstream_transport_failure')
                    self.reply(502)
                finally:
                    upstream.close()

            do_GET = do_POST = do_PATCH = do_DELETE = handle_request

        self.server = Server(('127.0.0.1', 0), Handler)
        self.url = f'http://127.0.0.1:{self.server.server_port}'
        self.thread = Thread(target=self.server.serve_forever,
                             kwargs={'poll_interval': 0.05}, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def arm(self, operation_id, method, suffix, status):
        with self.lock:
            require(self.armed is None, 'Relay still has an unconsumed loss boundary')
            self.armed = {'operation_id': operation_id, 'method': method,
                          'path': self.prefix + suffix, 'status': status}

    def snapshot(self):
        with self.lock:
            return {'attempts': dict(self.attempts), 'forwarded': dict(self.forwarded),
                    'losses': [dict(item) for item in self.losses],
                    'failures': list(self.failures), 'armed': self.armed is not None}

    def mutation_attempts(self):
        with self.lock:
            return sum(self.attempts[method] for method in MUTATIONS)


class RecoveryProbe(WriteProbe):
    def __init__(self, base, output):
        super().__init__(base, output)
        self.manifest['slug'] = 'write-recovery-probe-' + secrets.token_hex(5)
        self.report['limitations'] = [
            'Trusted-host recovery only; no managed workers or model engine.',
            'Recovery observes matching current effects; no automatic mutation resend.',
            'Mutable native metadata and offset pagination are not a transactional receipt.',
            'Missing, duplicated or changed evidence remains unresolved.',
            'Recovered creates grant no editing authority; later fixture edits use explicit owner grants.',
            'Logical Plane deletion/deactivation does not physically erase database history.',
        ]
        self.save()

    @contextmanager
    def host(self):
        from agent_native.identity import OWNER
        from agent_native.plane_write_access import WriteAuthority
        from agent_native.plane_write_journal import MutationJournal
        from agent_native.plane_writes import PlaneWrites
        from hermes_cli.kanban_db_connect import connect_closing

        with connect_closing(self.out / 'control.db') as conn:
            authority = WriteAuthority(conn)
            context = authority.issue_context(actor=OWNER, binding_id=self.manifest['bindings'][0])
            journal = MutationJournal(conn)
            writer = PlaneWrites(authority, journal, base_url=self.relay.url,
                                 api_key=self.manifest['accounts'][1]['tokens'][1]['api_key'],
                                 service_user_id=self.manifest['accounts'][1]['id'])
            try:
                yield writer, context, journal
            finally:
                if hasattr(writer, 'close'):
                    writer.close()

    def observe(self, kind, resource_id=None):
        self.report['stage'] = 'inspect_' + kind
        self.save()
        self.pace()
        with self.host() as (writer, context, _):
            return writer.inspect(context, kind, resource_id)

    def lose(self, operation, arguments, method, suffix, status):
        from agent_native.identity import OWNER
        from agent_native.plane_writes import PlaneWriteError

        operation_id = str(uuid4())
        intent = {'id': operation_id, 'operation': operation, 'status': 'attempted'}
        self.manifest['operations'].append(intent)
        self.report['stage'] = 'lose_' + operation
        self.save()
        self.pace()
        before = self.relay.mutation_attempts()
        self.relay.arm(operation_id, method, suffix, status)
        with self.host() as (writer, context, journal):
            try:
                writer.execute(context, operation_id, operation, arguments)
            except PlaneWriteError as exc:
                require(exc.outcome == 'unknown', 'Lost successful response was not recorded as unknown')
            else:
                raise ProbeFailure('Relay failed to discard the successful mutation response')
            record = journal.get(operation_id, actor=OWNER)
            require(record['status'] == 'unknown', 'Lost write journal was not durable unknown')
        snapshot = self.relay.snapshot()
        losses = [entry for entry in snapshot['losses'] if entry['operation_id'] == operation_id]
        require(len(losses) == 1 and losses[0]['status'] == status
                and self.relay.mutation_attempts() == before + 1,
                'Expected exactly one successful native effect and one dropped response')
        intent.update(status='unknown', resource_id=losses[0]['resource_id'])
        self.save()
        return operation_id, losses[0]['resource_id']

    def recover(self, operation_id, expected_id):
        from agent_native.identity import OWNER

        self.report['stage'] = 'recover_' + operation_id
        self.save()
        self.pace()
        before = self.relay.mutation_attempts()
        with self.host() as (writer, context, journal):
            result = writer.recover(context, operation_id)
            require(result['status'] == 'confirmed' and result['resource']['id'] == expected_id,
                    'Recovery did not confirm the original native resource')
            require(result.get('confirmation') == 'matching_effect',
                    'Recovery or journal read lost matching-effect provenance')
            require(journal.get(operation_id, actor=OWNER)['status'] == 'confirmed',
                    'Recovered outcome was not durably confirmed')
        require(self.relay.mutation_attempts() == before, 'Recovery attempted a mutation')
        for entry in self.manifest['operations']:
            if entry['id'] == operation_id:
                entry.update(status='confirmed', resource_id=expected_id, confirmation='matching_effect')
        self.save()
        return result

    def assert_no_created_resource_grants(self, kind, resource_id):
        from agent_native.plane_write_access import RESOURCE_FIELDS

        with self.host() as (writer, context, _):
            for field in RESOURCE_FIELDS[kind]:
                try:
                    writer.authority.authorize(context, kind + '.update', kind=kind,
                                               resource_id=resource_id, fields={field})
                except PermissionError:
                    pass
                else:
                    raise ProbeFailure('Recovery granted editing authority from mutable native evidence')

    def grant_fixture_resource(self, kind, resource_id, operation_id):
        """Explicit test-owner setup after proving recovery itself granted nothing.

        The relay retained the original successful native response ID before
        dropping it. This private fixture owner verifies that independent evidence
        and the live resource, then grants fields for subsequent mutation cases.
        This owner action is deliberately outside the recovery implementation.
        """
        from agent_native.identity import OWNER
        from agent_native.plane_write_access import RESOURCE_FIELDS, allow_resource
        from hermes_cli.kanban_db_connect import connect_closing

        self.assert_no_created_resource_grants(kind, resource_id)
        receipts = [entry for entry in self.relay.snapshot()['losses']
                    if entry['operation_id'] == operation_id]
        require(len(receipts) == 1 and receipts[0]['resource_id'] == resource_id
                and receipts[0]['method'] == 'POST' and receipts[0]['status'] == 201,
                'Fixture owner lacks the original native creation identity')
        suffix = ('work-items' if kind == 'item' else 'cycles') + '/' + resource_id + '/'
        native = call(self.api, self.base, 'GET', self.path + suffix).json()
        require(native['id'] == resource_id and native['project'] == self.manifest['projects'][0]['id']
                and native['workspace'] == self.manifest['workspace_id']
                and native['created_by'] == self.manifest['accounts'][1]['id']
                and native['external_source'] == 'agent-native' and native['external_id'] == operation_id,
                'Independent native fixture creation readback does not match')
        with connect_closing(self.out / 'control.db') as conn:
            allow_resource(conn, actor=OWNER, binding_id=self.manifest['bindings'][0],
                           kind=kind, resource_id=resource_id, fields=RESOURCE_FIELDS[kind])
        self.check(kind + '_recovery_granted_no_fields_before_explicit_fixture_owner_grant')

    def unresolved(self, operation_id, label):
        from agent_native.identity import OWNER
        from agent_native.plane_recovery import PlaneRecoveryUnresolved

        self.report['stage'] = 'unresolved_' + label
        self.save()
        self.pace()
        before = self.relay.mutation_attempts()
        with self.host() as (writer, context, journal):
            try:
                writer.recover(context, operation_id)
            except PlaneRecoveryUnresolved:
                pass
            else:
                raise ProbeFailure('Ambiguous recovery incorrectly confirmed the mutation')
            require(journal.get(operation_id, actor=OWNER)['status'] in ('unknown', 'pending'),
                    'Unresolved recovery incorrectly changed delivery to final success or failure')
        require(self.relay.mutation_attempts() == before, 'Unresolved recovery attempted a resend')
        self.check(label)

    def inventory(self):
        return results(call(self.api, self.base, 'GET', self.path + 'work-items/'))

    def project_inventory(self):
        # Plane may seed its own demo project during workspace setup. Preserve
        # the complete visible baseline, not only our two explicit fixtures.
        records = results(call(self.api, self.base, 'GET', self.v1))
        require(all(record.get('workspace') == self.manifest['workspace_id'] for record in records),
                'Project inventory escaped the disposable workspace')
        identities = {str(UUID(record['id'])) for record in records}
        require(len(identities) == len(records), 'Project inventory repeated an identity')
        return identities

    def verify(self):
        from agent_native.identity import OWNER, create_root
        from agent_native.plane_access import grant_project
        from agent_native.plane_write_access import OPERATIONS, allow_resource, grant_writes
        from agent_native.plane_write_journal import MutationJournal, ReplayError
        from hermes_cli.kanban_db_connect import connect_closing

        self.report['stage'] = 'setup_host'
        first, other = self.manifest['projects']
        self.path = self.v1 + first['id'] + '/'
        key = self.manifest['accounts'][1]['tokens'][1]['api_key']
        initial_items = {item['id'] for item in self.inventory()}
        initial_projects = self.project_inventory()
        require({first['id'], other['id']}.issubset(initial_projects),
                'Complete project baseline does not contain both explicit fixtures')
        self.manifest['project_inventory_before'] = sorted(initial_projects)
        self.save()
        other_before = results(call(self.api, self.base, 'GET', self.v1 + other['id'] + '/work-items/'))
        with connect_closing(self.out / 'control.db') as conn:
            roots, bindings = [], []
            for index, project in enumerate((first, other)):
                root = create_root(conn, actor=OWNER, request_id=f'recovery-root-{index}',
                                   name=f'Recovery root {index}', purpose=f'Plan fixture project {index}')
                binding = grant_project(conn, actor=OWNER, agent_id=root['id'],
                    workspace_slug=self.manifest['slug'], workspace_id=self.manifest['workspace_id'],
                    project_id=project['id'])
                roots.append(root['id'])
                bindings.append(binding['id'])
            grant_writes(conn, actor=OWNER, binding_id=bindings[0], operations=OPERATIONS)
            allow_resource(conn, actor=OWNER, binding_id=bindings[0], kind='project',
                           resource_id=first['id'], fields={'description'})
            self.manifest.update(roots=roots, bindings=bindings)
            self.save()
        with LossRelay(self.base, self.path, key) as relay:
            self.relay = relay
            try:
                create_args = {'name': 'Recovered work item', 'description': 'Original durable result'}
                create_op, item_id = self.lose('item.create', create_args, 'POST', 'work-items/', 201)
                require(item_id is not None, 'Lost item response had no native identity')
                self.recover(create_op, item_id)
                self.assert_no_created_resource_grants('item', item_id)
                before_inventory = {item['id'] for item in self.inventory()}
                self.recover(create_op, item_id)
                self.grant_fixture_resource('item', item_id, create_op)
                self.pace()
                before_attempts = relay.mutation_attempts()
                with self.host() as (writer, context, _):
                    try:
                        writer.execute(context, create_op, 'item.create', create_args)
                    except ReplayError:
                        pass
                    else:
                        raise ProbeFailure('Consumed operation UUID was accepted for another delivery')
                require(relay.mutation_attempts() == before_attempts
                        and {item['id'] for item in self.inventory()} == before_inventory,
                        'Repeated recovery or execute created another work item')
                self.check('lost_item_create_recovered_after_database_reopen_without_duplicate')

                cycle_op, cycle_id = self.lose('cycle.create', {'name': 'Undated recovered cycle'},
                                             'POST', 'cycles/', 201)
                self.recover(cycle_op, cycle_id)
                self.grant_fixture_resource('cycle', cycle_id, cycle_op)
                comment_op, comment_id = self.lose('comment.create', {'item_id': item_id, 'text': 'Recovered comment'},
                    'POST', f'work-items/{item_id}/comments/', 201)
                self.recover(comment_op, comment_id)
                artifact_op, artifact_id = self.lose('artifact.record', {'item_id': item_id,
                    'reference': 'urn:agent-native:recovery:unverified', 'description': 'Unverified reference'},
                    'POST', f'work-items/{item_id}/comments/', 201)
                self.recover(artifact_op, artifact_id)

                observed = self.observe('item', item_id)
                update_op, _ = self.lose('item.update', {'item_id': item_id,
                    'expected_fingerprint': observed['fingerprint'], 'name': 'Recovered updated item'},
                    'PATCH', f'work-items/{item_id}/', 200)
                self.recover(update_op, item_id)
                project = self.observe('project')
                project_op, _ = self.lose('project.update', {'description': 'Recovered project brief',
                    'expected_fingerprint': project['fingerprint']}, 'PATCH', '', 200)
                self.recover(project_op, first['id'])
                cycle = self.observe('cycle', cycle_id)
                cycle_update_op, _ = self.lose('cycle.update', {'cycle_id': cycle_id,
                    'expected_fingerprint': cycle['fingerprint'], 'description': 'Accepted recovery evidence'},
                    'PATCH', f'cycles/{cycle_id}/', 200)
                self.recover(cycle_update_op, cycle_id)
                observed = self.observe('item', item_id)
                dependency_op, _ = self.lose('dependency.add', {'item_id': item_id,
                    'dependency_id': first['items'][1], 'expected_fingerprint': observed['fingerprint']},
                    'POST', f'work-items/{item_id}/relations/', 201)
                self.recover(dependency_op, item_id)
                observed = self.observe('item', item_id)
                assign_op, _ = self.lose('cycle.assign', {'item_id': item_id, 'cycle_id': cycle_id,
                    'expected_item_fingerprint': observed['fingerprint'], 'expected_cycle_id': None},
                    'POST', f'cycles/{cycle_id}/cycle-issues/', 200)
                # Assignment returns a native membership identity, not the item ID.
                # Read that identity independently after the real lost response.
                member = call(self.api, self.base, 'GET', self.path + f'cycles/{cycle_id}/cycle-issues/{item_id}/').json()
                require(member['issue'] == item_id and member['cycle'] == cycle_id
                        and member['project'] == first['id'] and member['workspace'] == self.manifest['workspace_id'],
                        'Native cycle membership readback was outside the expected scope')
                membership_id = str(UUID(member['id']))
                recovered_member = self.recover(assign_op, membership_id)['resource']
                require(recovered_member == {key: member[key] for key in ('id', 'issue', 'cycle', 'project', 'workspace')},
                        'Recovered cycle assignment differs from independent native membership')
                observed = self.observe('item', item_id)
                remove_op, _ = self.lose('cycle.remove', {'item_id': item_id, 'cycle_id': cycle_id,
                    'expected_item_fingerprint': observed['fingerprint']},
                    'DELETE', f'cycles/{cycle_id}/cycle-issues/{item_id}/', 204)
                self.recover(remove_op, item_id)
                call(self.api, self.base, 'GET', self.path + f'cycles/{cycle_id}/cycle-issues/{item_id}/', expected=(404,))
                self.check('all_ten_operations_recovered_by_read_only_observation')

                duplicate_args = {'name': 'Duplicate evidence', 'description': 'Identical fixture content'}
                duplicate_op, duplicate_id = self.lose('item.create', duplicate_args, 'POST', 'work-items/', 201)
                extra = call(self.api, self.base, 'POST', self.path + 'work-items/', body={
                    'name': duplicate_args['name'], 'description_html': '<p>Identical fixture content</p>',
                    'external_source': self.manifest['slug'], 'external_id': duplicate_op}).json()
                self.manifest['duplicate_fixture_id'] = extra['id']
                self.save()
                call(self.api, self.base, 'PATCH', self.path + 'work-items/' + extra['id'] + '/',
                     body={'external_source': 'agent-native'})
                candidates = [record for record in self.inventory() if record.get('external_source') == 'agent-native'
                              and record.get('external_id') == duplicate_op]
                require({record['id'] for record in candidates} == {duplicate_id, extra['id']},
                        'Native fixture did not create two correlation candidates')
                duplicate_before = {record['id'] for record in self.inventory()}
                self.unresolved(duplicate_op, 'native_duplicate_markers_remain_unresolved')
                require({record['id'] for record in self.inventory()} == duplicate_before,
                        'Duplicate recovery changed native inventory')

                changed_op, changed_id = self.lose('item.create', {'name': 'Changed recovery candidate'},
                                                  'POST', 'work-items/', 201)
                call(self.api, self.base, 'PATCH', self.path + f'work-items/{changed_id}/',
                     body={'name': 'Native content changed after the lost response'})
                self.unresolved(changed_op, 'changed_candidate_remains_unresolved_without_resend')
                deleted_op, deleted_id = self.lose('item.create', {'name': 'Deleted recovery candidate'},
                                                  'POST', 'work-items/', 201)
                call(self.api, self.base, 'DELETE', self.path + f'work-items/{deleted_id}/', expected=(204,))
                self.unresolved(deleted_op, 'missing_deleted_candidate_remains_unresolved_without_resend')

                self.report['stage'] = 'final_native_inventory'
                self.save()
                final_items = self.inventory()
                require({record['id'] for record in final_items}
                        == initial_items | {item_id, duplicate_id, extra['id'], changed_id},
                        'Final work inventory indicates an unexpected create or removal')
                actual = next(record for record in final_items if record['id'] == item_id)
                require(actual['name'] == 'Recovered updated item', 'Recovered update lost its intended effect')
                actual_cycle = call(self.api, self.base, 'GET', self.path + f'cycles/{cycle_id}/').json()
                require(actual_cycle['start_date'] is None and actual_cycle['end_date'] is None
                        and actual_cycle['description'] == 'Accepted recovery evidence',
                        'Recovered cycle content or undated sequence changed')
                comments = results(call(self.api, self.base, 'GET', self.path + f'work-items/{item_id}/comments/'))
                require({record['id'] for record in comments} == {comment_id, artifact_id},
                        'Recovered comment operation duplicated or lost a record')
                relations = call(self.api, self.base, 'GET', self.path + f'work-items/{item_id}/relations/').json()
                require({record['issue_id'] for record in relations['blocked_by']} == {first['items'][1]},
                        'Recovered dependency effect missing')
                require(results(call(self.api, self.base, 'GET', self.path + f'work-items/{item_id}/links/')) == [],
                        'Recovery produced an artifact URL fetch')
                require(results(call(self.api, self.base, 'GET', self.v1 + other['id'] + '/work-items/')) == other_before,
                        'Other project changed during recovery')
                self.report['stage'] = 'final_project_inventory'
                self.save()
                final_projects = self.project_inventory()
                self.report['project_inventory'] = {
                    'before_ids': sorted(initial_projects), 'after_ids': sorted(final_projects),
                    'added_ids': sorted(final_projects - initial_projects),
                    'missing_ids': sorted(initial_projects - final_projects),
                }
                self.save()
                require(final_projects == initial_projects,
                        'Recovery changed the complete pre-existing planning project inventory')
                with connect_closing(self.out / 'control.db') as conn:
                    rows = conn.execute('SELECT id, project_id FROM agent_native_plane_access ORDER BY id').fetchall()
                    require(dict(rows) == dict(zip(self.manifest['bindings'], (first['id'], other['id']))),
                            'Recovery remapped existing host project bindings')
                    events = MutationJournal(conn).events(actor=OWNER)
                    encoded = json.dumps(events)
                    require(key not in encoded and create_args['description'] not in encoded,
                            'Recovery events exposed work text or credentials')
                snapshot = relay.snapshot()
                require(not snapshot['failures'] and not snapshot['armed'] and len(snapshot['losses']) == 13,
                        'Relay evidence contains an unexpected write or incomplete boundary')
                require(sum(snapshot['forwarded'].get(method, 0) for method in MUTATIONS) == 13
                        and relay.mutation_attempts() == 13, 'Unexpected proxy mutation attempt or resend')
                self.check('independent_native_inventory_and_project_bindings_preserved')
                self.check('exactly_thirteen_native_mutations_with_thirteen_lost_responses', {
                    'recovered_operations': 10, 'unresolved_operations': 3,
                    'native_duplicate_fixture_creates': 1, 'automatic_resends': 0})
            finally:
                self.report['proxy'] = relay.snapshot()
                self.save()
        self.check('no_models_workers_uploads_or_browser_started')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', required=True, type=local_base)
    parser.add_argument('--output-dir', required=True, type=Path,
                        help='New absolute private directory outside the repository')
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    out = args.output_dir
    if not out.is_absolute() or out.resolve().is_relative_to(repo):
        parser.error('Choose an absolute private output directory outside the repository')
    os.umask(0o077)
    out.mkdir(parents=True, exist_ok=False)
    out.chmod(0o700)
    sys.path.insert(0, str(repo))
    probe = RecoveryProbe(args.base_url, out)
    try:
        probe.setup()
        probe.verify()
        probe.report['result'] = 'completed'
    except BaseException as exc:
        probe.report['result'] = 'interrupted' if isinstance(exc, KeyboardInterrupt) else 'failed'
        probe.report['failure'] = {'stage': probe.report['stage'], 'error_type': type(exc).__name__}
        if type(getattr(exc, 'status', None)) is int:
            probe.report['failure']['http_status'] = exc.status
        if getattr(exc, 'outcome', None) in ('rejected', 'unknown'):
            probe.report['failure']['outcome'] = exc.outcome
        if isinstance(exc, ProbeFailure):
            probe.report['failure']['reason'] = str(exc)
    finally:
        probe.cleanup()
    proxy = probe.report.get('proxy', {})
    print(json.dumps({'result': probe.report['result'], 'checks': list(probe.report['checks']),
                      'cleanup': probe.report['cleanup'], 'proxy': {
                          'attempts': proxy.get('attempts', {}), 'forwarded': proxy.get('forwarded', {}),
                          'dropped_responses': len(proxy.get('losses', [])),
                          'failures': proxy.get('failures', []), 'armed': proxy.get('armed', False)}}, indent=2))
    return 0 if probe.report['result'] == 'completed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
