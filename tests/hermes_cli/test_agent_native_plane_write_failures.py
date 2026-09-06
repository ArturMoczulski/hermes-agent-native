"""Real HTTP/storage failures must never claim an unconfirmed planning write."""
import sqlite3

import pytest

from agent_native.identity import OWNER, revise_soul
from agent_native.plane_reads import MAX_BODY_BYTES, PlaneReadError
from agent_native.plane_write_access import allow_resource, revoke_writes
from agent_native.plane_write_contracts import fingerprint
from agent_native.plane_write_journal import ReplayError
from hermes_cli.kanban_db_connect import connect_closing
from tests.hermes_cli import test_agent_native_plane_writes as fixtures

setup = fixtures.setup
upstream = fixtures.upstream


def _writes(upstream):
    return [request for request in upstream.requests if request['method'] != 'GET']


def _receipt(s, operation_id):
    return s.journal.get(operation_id, actor=OWNER)


def _events(s, operation_id):
    return s.journal.events(actor=OWNER, operation_id=operation_id)


def _create_route(s, upstream, *, changed=None):
    created_id = fixtures.uid()

    def create(request):
        result = {**fixtures.record(s, id=created_id, created_by=s.user), **request['body']}
        if changed:
            result.update(changed)
        return 201, {}, result

    upstream.routes['POST', s.path + 'work-items/'] = create
    return created_id


@pytest.mark.parametrize('change', ['fields', 'write_grant', 'purpose'])
def test_revocation_during_preflight_blocks_delivery_and_records_scope_change(setup, upstream, change):
    s = setup
    fixtures.allow(s, 'project', s.project, {'description'})
    operation_id = fixtures.uid()

    def observed_project(_):
        with connect_closing(s.db_path) as owner:
            if change == 'fields':
                allow_resource(owner, actor=OWNER, binding_id=s.binding['id'], kind='project',
                               resource_id=s.project, fields=[])
            elif change == 'write_grant':
                revoke_writes(owner, actor=OWNER, binding_id=s.binding['id'])
            else:
                revise_soul(owner, actor=OWNER, agent_id=s.root['id'], expected_revision=1,
                            purpose='The owner changed the purpose')
        return 200, {}, s.project_record

    upstream.routes['GET', s.path] = observed_project
    with pytest.raises(PermissionError):
        s.service.execute(s.context, operation_id, 'project.update', {
            'description': 'No longer authorized', 'expected_fingerprint': fingerprint(s.project_record),
        })
    assert _writes(upstream) == []
    assert _receipt(s, operation_id)['status'] == 'rejected'
    assert [event['status'] for event in _events(s, operation_id)] == ['pending', 'rejected', 'denied']
    assert _events(s, operation_id)[-1]['reason'] == 'scope_changed'


def test_revocation_after_post_leaves_unknown_receipt_and_does_not_grant_new_resource(setup, upstream):
    s = setup
    operation_id, created_id = fixtures.uid(), fixtures.uid()

    def posted(request):
        with connect_closing(s.db_path) as owner:
            revoke_writes(owner, actor=OWNER, binding_id=s.binding['id'])
        return 201, {}, {**fixtures.record(s, id=created_id, created_by=s.user), **request['body']}

    upstream.routes['POST', s.path + 'work-items/'] = posted
    with pytest.raises(PermissionError):
        s.service.execute(s.context, operation_id, 'item.create', {'name': 'Pending authorization'})
    assert len(_writes(upstream)) == 1
    assert _receipt(s, operation_id)['status'] == 'unknown'
    assert _events(s, operation_id)[-1]['reason'] == 'scope_changed'
    assert s.conn.execute('SELECT 1 FROM agent_native_plane_resource_access WHERE resource_id = ?',
                          (created_id,)).fetchone() is None


def test_confirmed_operation_replay_never_sends_another_request(setup, upstream):
    s = setup
    operation_id = fixtures.uid()
    _create_route(s, upstream)
    assert s.service.execute(s.context, operation_id, 'item.create', {'name': 'Once'})['status'] == 'confirmed'
    sent = list(upstream.requests)
    with pytest.raises(ReplayError):
        s.service.execute(s.context, operation_id, 'item.create', {'name': 'Once'})
    assert upstream.requests == sent
    assert _receipt(s, operation_id)['status'] == 'confirmed'


@pytest.mark.parametrize('failure', ['malformed_json', 'large_body', 'truncated_body', 'redirect', 'rate_limit', 'server_error', 'encoding'])
def test_unconfirmed_transport_response_is_unknown_redacted_and_never_retried(setup, upstream, failure):
    s = setup
    operation_id = fixtures.uid()
    secret_body = b'private-fixture-key secret upstream text'
    variants = {
        'malformed_json': (201, {}, secret_body),
        'large_body': (201, {}, b'x' * (MAX_BODY_BYTES + 1)),
        'truncated_body': (201, {'Content-Length': str(len(secret_body) + 10)}, secret_body),
        'redirect': (302, {'Location': upstream.url + '/must-not-follow'}, secret_body),
        'rate_limit': (429, {'Retry-After': '7'}, secret_body),
        'server_error': (503, {}, secret_body),
        'encoding': (201, {'Content-Encoding': 'gzip'}, secret_body),
    }
    upstream.routes['POST', s.path + 'work-items/'] = variants[failure]
    with pytest.raises(PlaneReadError) as raised:
        s.service.execute(s.context, operation_id, 'item.create', {'name': 'One attempt'})
    assert len(_writes(upstream)) == 1
    assert all(request['path'] != '/must-not-follow' for request in upstream.requests)
    assert _receipt(s, operation_id)['status'] == 'unknown'
    assert 'private-fixture-key' not in str(raised.value)
    assert 'secret upstream text' not in str(raised.value)
    if failure == 'rate_limit':
        assert raised.value.status == 429 and raised.value.retry_after == 7
    sent = list(upstream.requests)
    with pytest.raises(ReplayError):
        s.service.execute(s.context, operation_id, 'item.create', {'name': 'One attempt'})
    assert upstream.requests == sent


@pytest.mark.parametrize('table', ['agent_native_plane_mutations', 'agent_native_plane_mutation_events'])
def test_failed_intent_persistence_prevents_every_http_request(setup, upstream, table):
    s = setup
    operation_id = fixtures.uid()
    # Table comes from the fixed test parameter, never a request field.
    s.conn.execute(f"CREATE TRIGGER reject_intent BEFORE INSERT ON {table} "
                   "BEGIN SELECT RAISE(ABORT, 'storage unavailable'); END")
    with pytest.raises(sqlite3.IntegrityError):
        s.service.execute(s.context, operation_id, 'item.create', {'name': 'No durable intent'})
    assert upstream.requests == []
    with pytest.raises(KeyError):
        _receipt(s, operation_id)
    assert _events(s, operation_id) == []


def test_outcome_persistence_failure_never_returns_success_or_sends_again(setup, upstream):
    s = setup
    operation_id = fixtures.uid()
    _create_route(s, upstream)
    s.conn.execute("CREATE TRIGGER reject_outcome BEFORE INSERT ON agent_native_plane_mutation_events "
                   "WHEN NEW.status != 'pending' BEGIN SELECT RAISE(ABORT, 'storage unavailable'); END")
    with pytest.raises(sqlite3.IntegrityError):
        s.service.execute(s.context, operation_id, 'item.create', {'name': 'Effect with uncertain receipt'})
    assert len(_writes(upstream)) == 1
    assert _receipt(s, operation_id)['status'] == 'pending'
    assert [event['status'] for event in _events(s, operation_id)] == ['pending']
    sent = list(upstream.requests)
    with pytest.raises(ReplayError):
        s.service.execute(s.context, operation_id, 'item.create', {'name': 'Effect with uncertain receipt'})
    assert upstream.requests == sent


@pytest.mark.parametrize('field', ['workspace', 'project', 'created_by'])
def test_foreign_creation_scope_or_attribution_is_unknown_and_grants_no_rights(setup, upstream, field):
    s = setup
    operation_id = fixtures.uid()
    created_id = _create_route(s, upstream, changed={field: fixtures.uid()})
    with pytest.raises(PlaneReadError):
        s.service.execute(s.context, operation_id, 'item.create', {'name': 'Validate returned identity'})
    assert _receipt(s, operation_id)['status'] == 'unknown'
    assert len(_writes(upstream)) == 1
    with pytest.raises(PermissionError):
        s.authority.authorize(s.context, 'item.update', kind='item', resource_id=created_id, fields=['name'])


@pytest.mark.parametrize('context', [object(), {'agent_id': 'forged-owner'}])
def test_forged_context_has_no_network_effect_and_no_invented_attribution(setup, upstream, context):
    s = setup
    operation_id = fixtures.uid()
    with pytest.raises(PermissionError):
        s.service.execute(context, operation_id, 'item.create', {'name': 'Untrusted'})
    assert upstream.requests == []
    event, = _events(s, operation_id)
    assert event['status'] == 'denied' and event['agent_id'] is None and event['binding_id'] is None


def test_revocation_at_journal_boundary_records_denial_before_network(setup, upstream, monkeypatch):
    s = setup
    operation_id = fixtures.uid()
    begin = s.journal.begin

    def revoke_then_begin(*args, **kwargs):
        # Deterministically schedule an owner edit in the gap before the real
        # journal transaction; the authorization and persistence remain real.
        with connect_closing(s.db_path) as owner:
            revoke_writes(owner, actor=OWNER, binding_id=s.binding['id'])
        return begin(*args, **kwargs)

    monkeypatch.setattr(s.journal, 'begin', revoke_then_begin)
    with pytest.raises(PermissionError):
        s.service.execute(s.context, operation_id, 'item.create', {'name': 'No longer authorized'})
    assert upstream.requests == []
    with pytest.raises(KeyError):
        _receipt(s, operation_id)
    event, = _events(s, operation_id)
    assert event['status'] == 'denied' and event['reason'] == 'scope_changed'
