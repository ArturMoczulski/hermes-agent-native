"""Opt-in AN-19 proof against disposable data in an explicitly selected local Plane.

Creates two accounts, one workspace and two private projects, then exercises the
real trusted-host read adapter with an isolated control database. No managed
worker, model engine, owner account or Builder credential is used. Fixture IDs,
credentials and recovery state stay in the required new private output directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
from urllib.parse import urlsplit

import requests


class ProbeFailure(RuntimeError):
    """Only static labels/statuses may enter this exception's public message."""


def local_base(value):
    parsed = urlsplit(value)
    try:
        port = parsed.port
    except ValueError:
        raise argparse.ArgumentTypeError('Invalid local port') from None
    if (parsed.scheme != 'http' or parsed.hostname not in ('localhost', '127.0.0.1')
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in ('', '/') or port is None):
        raise argparse.ArgumentTypeError('Select an explicit http://localhost:PORT or http://127.0.0.1:PORT origin')
    return value.rstrip('/')


def session(base):
    result = requests.Session()
    result.trust_env = False
    result.headers.update({'Origin': base, 'Referer': base + '/'})
    return result


def call(sess, base, method, path, *, body=None, data=None, expected=(200, 201, 204)):
    try:
        response = sess.request(method, base + path, json=body, data=data,
                                allow_redirects=False, timeout=30)
    except requests.RequestException:
        raise ProbeFailure('Fixture transport failure; inspect the private recovery manifest') from None
    if response.status_code not in expected:
        raise ProbeFailure(f'Fixture request returned HTTP {response.status_code}')
    return response


def csrf(sess, base):
    sess.headers['X-CSRFToken'] = call(sess, base, 'GET', '/auth/get-csrf-token/').json()['csrf_token']


def require(condition, label):
    if not condition:
        raise ProbeFailure(label)


def results(response):
    payload = response.json()
    if isinstance(payload, list):
        return payload
    require(not payload.get('next_page_results'), 'Fixture setup response unexpectedly requires pagination')
    return payload['results']


def same_origin_upload(base, upload):
    parsed, origin = urlsplit(upload['url']), urlsplit(base)
    require((parsed.scheme, parsed.hostname, parsed.port) ==
            (origin.scheme, origin.hostname, origin.port)
            and not parsed.username and not parsed.password
            and not parsed.query and not parsed.fragment,
            'Attachment upload was not issued for the selected local origin')


# Credentials are read only inside the existing local API container. Each key is
# independently constrained and its contents verified before exact-key deletion.
ERASE_OBJECTS = r'''
import hashlib, json, os, re, sys
from urllib.parse import urlsplit
from uuid import UUID
import boto3
from botocore.exceptions import ClientError
payload = json.load(sys.stdin)
checks = []
try:
    endpoint = os.environ.get('AWS_S3_ENDPOINT_URL') or os.environ.get('MINIO_ENDPOINT_URL')
    parsed = urlsplit(endpoint or '')
    if os.environ.get('USE_MINIO') != '1' or parsed.scheme != 'http' or parsed.hostname != 'plane-minio':
        raise ValueError('Expected existing local MinIO endpoint')
    workspace = str(UUID(payload['workspace_id']))
    bucket = os.environ['AWS_S3_BUCKET_NAME']
    client = boto3.client('s3', endpoint_url=endpoint,
        aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
        region_name=os.environ.get('AWS_REGION') or 'us-east-1')
    for obj in payload['objects']:
        UUID(obj['asset_id'])
        key = obj['key']
        if not re.fullmatch(re.escape(workspace) + r'/[a-f0-9]{32}-' + re.escape(obj['name']), key):
            raise ValueError('Unrecognized fixture object key')
        try:
            body = client.get_object(Bucket=bucket, Key=key)['Body']
            try:
                content = body.read(4097)
            finally:
                body.close()
        except ClientError as exc:
            if exc.response.get('Error', {}).get('Code') in ('NoSuchKey', '404', 'NotFound'):
                checks.append('already absent')
                continue
            raise
        if len(content) > 4096 or hashlib.sha256(content).hexdigest() != obj['sha256']:
            raise ValueError('Fixture object contents do not match')
        client.delete_object(Bucket=bucket, Key=key)
        try:
            client.head_object(Bucket=bucket, Key=key)
        except ClientError as exc:
            if exc.response.get('Error', {}).get('Code') in ('NoSuchKey', '404', 'NotFound'):
                checks.append('erased and absence verified')
                continue
            raise
        raise ValueError('Object still exists after deletion')
    print(json.dumps({'ok': True, 'checks': checks}))
except Exception as exc:
    print(json.dumps({'ok': False, 'checks': checks, 'error_type': type(exc).__name__}))
    sys.exit(1)
'''


class Probe:
    def __init__(self, base, output, api_container):
        self.base, self.out, self.api_container = base, output, api_container
        self.manifest = {'slug': 'scoped-read-probe-' + secrets.token_hex(5),
                         'accounts': [], 'projects': [], 'objects': []}
        self.report = {'result': 'started', 'stage': 'setup', 'checks': {}, 'cleanup': [],
                       'limitations': ['Trusted-host adapter only; no managed workers or model engine.',
                                       'Plane workspace/account deletion is logical deletion/deactivation, not database erasure.']}
        self.sessions = []
        self.api = None
        self.save()

    def save(self):
        for name, value in [('manifest.json', self.manifest), ('report.json', self.report)]:
            path = self.out / name
            path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
            path.chmod(0o600)

    def check(self, label, detail=True):
        self.report['checks'][label] = detail
        self.save()

    def setup(self):
        initial = session(self.base)
        try:
            config = call(initial, self.base, 'GET', '/api/instances/').json()['config']
            require(config.get('is_smtp_configured') is False,
                    'Disposable account setup requires explicitly unconfigured SMTP')
        finally:
            initial.close()
        for role in ('workspace-owner', 'service'):
            account = {'email': self.manifest['slug'] + '-' + role + '@agent-native.test',
                       'password': secrets.token_urlsafe(32), 'tokens': []}
            self.manifest['accounts'].append(account)
            sess = session(self.base)
            self.sessions.append(sess)
            self.save()
            csrf(sess, self.base)
            account['signup_attempted'] = True
            self.save()
            signed = call(sess, self.base, 'POST', '/auth/sign-up/', data={
                'email': account['email'], 'password': account['password']}, expected=(302,))
            require('error' not in signed.headers.get('Location', ''), 'Disposable account signup failed')
            csrf(sess, self.base)
            account['id'] = call(sess, self.base, 'GET', '/api/users/me/').json()['id']
            self.save()
        admin, service = self.sessions
        account = self.manifest['accounts'][1]
        for name in ('fixture-setup', 'scoped-reads'):
            token = call(service, self.base, 'POST', '/api/users/api-tokens/',
                         body={'label': self.manifest['slug'] + '-' + name}).json()
            account['tokens'].append({'id': token['id'], 'api_key': token.get('api_key') or token['token']})
            self.save()
        self.api = session(self.base)
        self.api.headers['X-API-Key'] = account['tokens'][0]['api_key']
        self.manifest['workspace_creation_attempted'] = True
        self.save()
        workspace = call(admin, self.base, 'POST', '/api/workspaces/', body={
            'name': self.manifest['slug'], 'slug': self.manifest['slug']}).json()
        self.manifest['workspace_id'] = workspace['id']
        self.save()
        wp = '/api/workspaces/' + self.manifest['slug'] + '/'
        call(admin, self.base, 'POST', wp + 'invitations/',
             body={'emails': [{'email': account['email'], 'role': 15}]})
        csrf(service, self.base)
        invitations = results(call(service, self.base, 'GET', '/api/users/me/workspaces/invitations/'))
        call(service, self.base, 'POST', '/api/users/me/workspaces/invitations/',
             body={'invitations': [item['id'] for item in invitations]})
        self.v1 = '/api/v1/workspaces/' + self.manifest['slug'] + '/projects/'
        for letter, count in (('A', 3), ('B', 1)):
            project = call(self.api, self.base, 'POST', self.v1, body={
                'name': 'Disposable scoped reads ' + letter, 'identifier': 'PROBE' + letter,
                'cycle_view': True}).json()
            fixture = {'id': project['id'], 'items': [], 'cycles': []}
            self.manifest['projects'].append(fixture)
            self.save()
            private = call(service, self.base, 'PATCH', wp + 'projects/' + project['id'] + '/',
                           body={'network': 0}).json()
            require(private['network'] == 0, 'Fixture project was not made private')
            path = self.v1 + project['id'] + '/'
            for number in range(count):
                item = call(self.api, self.base, 'POST', path + 'work-items/', body={
                    'name': f'Isolated {letter} item {number}',
                    'external_source': self.manifest['slug'], 'external_id': f'{letter}-{number}'}).json()
                fixture['items'].append(item['id'])
                self.save()
            detail = path + 'work-items/' + fixture['items'][0] + '/'
            comment = call(self.api, self.base, 'POST', detail + 'comments/',
                           body={'comment_html': '<p>Isolated evidence ' + letter + '</p>'}).json()
            fixture['comment_id'] = comment['id']
            for number in range(2 if letter == 'A' else 1):
                cycle = call(self.api, self.base, 'POST', path + 'cycles/', body={
                    'name': f'Outcome {letter} {number}', 'owned_by': account['id'],
                    'start_date': None, 'end_date': None}).json()
                fixture['cycles'].append(cycle['id'])
                self.save()
            fixture['states'] = [state['id'] for state in results(
                call(self.api, self.base, 'GET', path + 'states/'))]
            self.upload(fixture, letter, detail)
        self.check('isolated_fixture', {'private_projects': 2, 'accounts': 2, 'real_attachments': 2})

    def upload(self, fixture, letter, detail):
        name = self.manifest['slug'] + '-' + letter + '.txt'
        content = ('Disposable AN-19 attachment ' + name + '\n').encode()
        created = call(self.api, self.base, 'POST', detail + 'attachments/', body={
            'name': name, 'type': 'text/plain', 'size': len(content),
            'external_source': self.manifest['slug'], 'external_id': letter}).json()
        upload, attachment = created['upload_data'], created['attachment']
        obj = {'asset_id': created['asset_id'], 'project_id': fixture['id'],
               'item_id': fixture['items'][0], 'name': name,
               'sha256': hashlib.sha256(content).hexdigest(), 'size': len(content)}
        self.manifest['objects'].append(obj)
        fixture['attachment_id'] = obj['asset_id']
        self.save()
        require(attachment['id'] == obj['asset_id'] and attachment['workspace'] == self.manifest['workspace_id']
                and attachment['project'] == fixture['id'] and attachment['issue'] == fixture['items'][0],
                'Attachment response was outside fixture scope')
        key = upload['fields']['key']
        require(attachment['asset'] == key and re.fullmatch(
            re.escape(self.manifest['workspace_id']) + r'/[a-f0-9]{32}-' + re.escape(name), key) is not None,
            'Attachment storage key was outside fixture scope')
        same_origin_upload(self.base, upload)
        obj['key'] = key
        self.save()
        # Fresh unauthenticated session: never forward Plane cookies/API keys to storage.
        storage = requests.Session()
        storage.trust_env = False
        try:
            response = storage.post(upload['url'], data=upload['fields'],
                                    files={'file': (name, content, 'text/plain')},
                                    allow_redirects=False, timeout=30)
            require(response.status_code in (200, 201, 204), 'Local attachment upload failed')
        except requests.RequestException:
            raise ProbeFailure('Local attachment transport failed') from None
        finally:
            storage.close()
        obj['uploaded'] = True
        self.save()
        call(self.api, self.base, 'PATCH', detail + 'attachments/' + obj['asset_id'] + '/',
             body={'is_uploaded': True})
        obj['completed'] = True
        self.save()

    def verify(self):
        from agent_native.identity import OWNER, create_root, revise_soul
        from agent_native.plane_access import ReadAuthority, grant_project, revoke_project
        from agent_native.plane_reads import PlaneReads, PlaneReadError
        from hermes_cli.kanban_db_connect import connect_closing

        self.report['stage'] = 'adapter_reads'
        self.save()
        first, other = self.manifest['projects']
        key = self.manifest['accounts'][1]['tokens'][1]['api_key']
        raw = session(self.base)
        raw.headers['X-API-Key'] = key
        try:
            for fixture in (first, other):
                path = self.v1 + fixture['id'] + '/'
                require(call(raw, self.base, 'GET', path).json()['id'] == fixture['id'],
                        'Underlying service could not read both fixture projects')
            path = self.v1 + other['id'] + '/work-items/' + other['items'][0] + '/'
            require(call(raw, self.base, 'GET', path).json()['id'] == other['items'][0],
                    'Foreign fixture item missing from service control read')
            require(other['comment_id'] in {x['id'] for x in results(call(raw, self.base, 'GET', path + 'comments/'))},
                    'Foreign fixture comment missing from service control read')
            require(other['attachment_id'] in {x['id'] for x in results(call(raw, self.base, 'GET', path + 'attachments/'))},
                    'Foreign fixture attachment missing from service control read')
        finally:
            raw.close()
        self.check('service_credential_can_read_both_projects')
        with connect_closing(self.out / 'control.db') as conn:
            authority = ReadAuthority(conn)
            reader = PlaneReads(authority, base_url=self.base, api_key=key, page_size=1)
            contexts, bindings, roots = [], [], []
            for index, fixture in enumerate((first, other)):
                root = create_root(conn, actor=OWNER, request_id=f'probe-root-{index}',
                                   name=f'Isolated root {index}', purpose=f'Read only fixture project {index}')
                binding = grant_project(conn, actor=OWNER, agent_id=root['id'],
                    workspace_slug=self.manifest['slug'], workspace_id=self.manifest['workspace_id'],
                    project_id=fixture['id'])
                roots.append(root)
                bindings.append(binding)
                contexts.append(authority.issue_context(actor=OWNER, binding_id=binding['id']))
            self.manifest['roots'] = [root['id'] for root in roots]
            self.manifest['bindings'] = [binding['id'] for binding in bindings]
            self.save()
            context = contexts[0]
            require(reader.get_project(context)['id'] == first['id'], 'Allowed project mismatch')
            items = reader.list_work_items(context)
            require({x['id'] for x in items} == set(first['items']) and len(items) == 3,
                    'Allowed pagination lost, duplicated or leaked work items')
            require(reader.get_work_item(context, first['items'][0])['id'] == first['items'][0],
                    'Allowed item mismatch')
            comments = reader.list_comments(context, first['items'][0])
            require({x['id'] for x in comments} == {first['comment_id']}, 'Allowed comment mismatch')
            attachments = reader.list_attachments(context, first['items'][0])
            require({x['id'] for x in attachments} == {first['attachment_id']}, 'Allowed attachment mismatch')
            for attachment in attachments:
                require(not {'asset', 'asset_url', 'storage_metadata', 'upload_data', 'url'} & set(attachment),
                        'Attachment read exposed storage/download capability')
                require(set(attachment.get('attributes', {})) <= {'name', 'size', 'type'},
                        'Attachment attributes exposed non-metadata fields')
                require(attachment['attributes']['name'] == self.manifest['objects'][0]['name'],
                        'Allowed attachment name mismatch')
            require({x['id'] for x in reader.list_cycles(context)} == set(first['cycles']),
                    'Allowed cycle pagination mismatch')
            require({x['id'] for x in reader.list_states(context)} == set(first['states']),
                    'Allowed state pagination mismatch')
            self.check('allowed_scoped_reads', {'items': len(items), 'page_size': 1,
                       'comments': len(comments), 'attachments': len(attachments), 'cycles': 2,
                       'states': len(first['states'])})
            require(reader.get_work_item(contexts[1], other['items'][0])['id'] == other['items'][0],
                    'Second root did not retain its own project access')
            self.check('second_root_has_separate_access')

            def denied(label, operation, *, authority_only=False):
                try:
                    operation()
                except PermissionError:
                    self.check(label, {'denied_by': 'authority'})
                except PlaneReadError as exc:
                    require(not authority_only and exc.status in (403, 404),
                            'Read failed for a reason other than expected scope denial')
                    self.check(label, {'denied_by': 'scoped_resource', 'status': exc.status})
                else:
                    raise ProbeFailure('Unauthorized read returned instead of denying access')

            foreign = other['items'][0]
            denied('foreign_item_denied', lambda: reader.get_work_item(context, foreign))
            denied('foreign_comments_denied', lambda: reader.list_comments(context, foreign))
            denied('foreign_attachments_denied', lambda: reader.list_attachments(context, foreign))
            denied('forged_context_denied', lambda: reader.get_project({
                'actor': 'owner', 'agent_id': roots[1]['id'], 'project_id': other['id']}), authority_only=True)
            denied('fabricated_opaque_context_denied', lambda: reader.get_project(object()), authority_only=True)
            revoke_project(conn, actor=OWNER, binding_id=bindings[0]['id'])
            denied('revoked_context_denied', lambda: reader.get_project(context), authority_only=True)
            denied('revoked_binding_cannot_issue_context', lambda: authority.issue_context(
                actor=OWNER, binding_id=bindings[0]['id']), authority_only=True)
            renewed = grant_project(conn, actor=OWNER, agent_id=roots[0]['id'],
                workspace_slug=self.manifest['slug'], workspace_id=self.manifest['workspace_id'],
                project_id=first['id'])
            denied('regrant_does_not_revive_old_context', lambda: reader.get_project(context), authority_only=True)
            fresh = authority.issue_context(actor=OWNER, binding_id=renewed['id'])
            require(reader.get_project(fresh)['id'] == first['id'], 'Fresh regrant did not restore access')
            revise_soul(conn, actor=OWNER, agent_id=roots[0]['id'], expected_revision=1,
                        purpose='Revised isolated purpose requires a new context')
            denied('purpose_change_invalidates_context', lambda: reader.get_project(fresh), authority_only=True)
            if hasattr(reader, 'close'):
                reader.close()
        self.check('no_workers_or_model_engine_started')

    def cleanup(self):
        self.report['stage'] = 'cleanup'
        self.save()

        def attempt(label, action):
            try:
                action()
                self.report['cleanup'].append({'action': label, 'ok': True})
            except Exception as exc:
                self.report['cleanup'].append({'action': label, 'ok': False, 'error_type': type(exc).__name__})
            self.save()

        for obj in self.manifest['objects']:
            if self.api is not None:
                path = self.v1 + obj['project_id'] + '/work-items/' + obj['item_id'] + '/attachments/' + obj['asset_id'] + '/'
                attempt('fixture attachment soft-deleted', lambda path=path:
                        call(self.api, self.base, 'DELETE', path, expected=(204, 404)))
        objects = [obj for obj in self.manifest['objects'] if obj.get('key')]
        if objects:
            def erase():
                payload = {'workspace_id': self.manifest['workspace_id'], 'objects': objects}
                process = subprocess.run(['docker', 'exec', '-i', self.api_container, 'python', '-c', ERASE_OBJECTS],
                    input=json.dumps(payload), text=True, capture_output=True, timeout=60, check=False)
                require(process.returncode == 0, 'Exact fixture object erasure could not be verified')
                proof = json.loads(process.stdout)
                require(proof.get('ok') is True and len(proof['checks']) == len(objects),
                        'Incomplete exact-object cleanup proof')
                self.report['object_erasure'] = proof['checks']
            attempt('exact fixture objects erased and absence verified', erase)
        if self.manifest.get('workspace_creation_attempted') and self.sessions:
            def delete_workspace():
                csrf(self.sessions[0], self.base)
                call(self.sessions[0], self.base, 'DELETE',
                     '/api/workspaces/' + self.manifest['slug'] + '/', expected=(200, 204, 404))
            attempt('fixture workspace deleted', delete_workspace)
        for sess, account in zip(self.sessions, self.manifest['accounts']):
            if not account.get('signup_attempted'):
                continue
            def authenticate(sess=sess, account=account):
                csrf(sess, self.base)
                signed = call(sess, self.base, 'POST', '/auth/sign-in/', data={
                    'email': account['email'], 'password': account['password']}, expected=(302,))
                require('error' not in signed.headers.get('Location', ''), 'Fixture cleanup login failed')
                csrf(sess, self.base)
            attempt('fixture cleanup session authenticated', authenticate)
            for token in account['tokens']:
                attempt('fixture API token revoked', lambda sess=sess, token=token:
                        call(sess, self.base, 'DELETE', '/api/users/api-tokens/' + token['id'] + '/', expected=(204, 404)))
            attempt('fixture account deactivated', lambda sess=sess:
                    call(sess, self.base, 'DELETE', '/api/users/me/'))
            sess.close()
        if self.api is not None:
            self.api.close()
        if any(not entry['ok'] for entry in self.report['cleanup']):
            self.report['result'] = 'cleanup_incomplete'
        self.report['stage'] = 'finished'
        self.save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', required=True, type=local_base)
    parser.add_argument('--output-dir', required=True, type=Path,
                        help='New absolute private directory outside the repository')
    parser.add_argument('--api-container', default='agent-native-plane-api-1',
                        help='Existing local API container for exact fixture-object cleanup only')
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    out = args.output_dir
    if not out.is_absolute() or out.resolve().is_relative_to(repo):
        parser.error('Choose an absolute private output directory outside the repository')
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]+', args.api_container):
        parser.error('Invalid existing API container name')
    # A restrictive umask also covers SQLite, sidecars and initially written manifests.
    os.umask(0o077)
    out.mkdir(parents=True, exist_ok=False)
    out.chmod(0o700)
    sys.path.insert(0, str(repo))
    probe = Probe(args.base_url, out, args.api_container)
    try:
        probe.setup()
        probe.verify()
        probe.report['result'] = 'completed'
    except BaseException as exc:
        probe.report['result'] = 'interrupted' if isinstance(exc, KeyboardInterrupt) else 'failed'
        probe.report['failure'] = {'stage': probe.report['stage'], 'error_type': type(exc).__name__}
        if isinstance(exc, ProbeFailure):
            probe.report['failure']['reason'] = str(exc)
        # Deliberately omit request exception strings, response bodies and tracebacks.
    finally:
        probe.cleanup()
    print(json.dumps({'result': probe.report['result'], 'checks': list(probe.report['checks']),
                      'cleanup': probe.report['cleanup']}, indent=2))
    return 0 if probe.report['result'] == 'completed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
