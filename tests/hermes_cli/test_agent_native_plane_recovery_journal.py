"""Protected request preparation must survive interruption without leaking to receipts."""
from dataclasses import replace
import json
import sqlite3
from uuid import uuid4

import pytest

from agent_native.identity import OWNER, create_root, revise_soul
from agent_native.plane_access import grant_project
from agent_native.plane_write_access import WriteAuthority, grant_writes, revoke_writes
from agent_native.plane_write_journal import MutationJournal, ReplayError
from hermes_cli.kanban_db_connect import connect_closing


@pytest.fixture
def setup(tmp_path):
    path = tmp_path / 'control.db'
    with connect_closing(path) as conn:
        root = create_root(conn, actor=OWNER, request_id='builder', name='Builder', purpose='Build')
        binding = grant_project(conn, actor=OWNER, agent_id=root['id'], workspace_slug='build',
                                workspace_id=str(uuid4()), project_id=str(uuid4()))
        grant_writes(conn, actor=OWNER, binding_id=binding['id'], operations=['item.create'])
        authority = WriteAuthority(conn)
        scope = authority.resolve(authority.issue_context(actor=OWNER, binding_id=binding['id']))
        journal, operation_id = MutationJournal(conn), str(uuid4())
        arguments = {'name': 'Private task', 'description': 'private body', 'priority': 'none'}
        prepared = {'method': 'POST', 'suffix': 'work-items/', 'payload': {
            'name': arguments['name'], 'description_html': '<p>private body</p>',
            'priority': 'none', 'state': str(uuid4()), 'external_id': operation_id,
            'external_source': 'agent-native',
        }, 'expected': 201, 'kind': 'item', 'resource_id': None}
        journal.begin(scope, operation_id, 'item.create', arguments)
        yield conn, journal, scope, operation_id, arguments, prepared, path


def test_preparation_is_durable_private_and_returns_independent_objects(setup):
    conn, journal, scope, operation_id, arguments, prepared, path = setup
    receipt = journal.get(operation_id, actor=OWNER)
    saved = journal.prepare(scope, operation_id, arguments, prepared)
    assert saved == {'arguments': arguments, 'prepared': prepared, 'attempted': False}
    saved['prepared']['payload']['name'] = 'Caller mutated its returned copy'
    assert journal.preparation(operation_id, actor=OWNER)['prepared'] == prepared
    assert journal.get(operation_id, actor=OWNER) == receipt
    assert 'Private task' not in json.dumps(journal.get(operation_id, actor=OWNER))
    assert 'private body' not in json.dumps(journal.events(actor=OWNER))
    with connect_closing(path) as reader:
        assert MutationJournal(reader).preparation(operation_id, actor=OWNER)['prepared'] == prepared


def test_preparation_is_immutable_but_identical_repeat_is_idempotent(setup):
    _, journal, scope, operation_id, arguments, prepared, _ = setup
    first = journal.prepare(scope, operation_id, arguments, prepared)
    assert journal.prepare(scope, operation_id, dict(arguments), dict(prepared)) == first
    changed = {**prepared, 'payload': {**prepared['payload'], 'name': 'Changed delivery'}}
    with pytest.raises(ReplayError):
        journal.prepare(scope, operation_id, arguments, changed)
    assert journal.preparation(operation_id, actor=OWNER) == first


def test_arguments_must_match_the_original_intent_hash(setup):
    _, journal, scope, operation_id, arguments, prepared, _ = setup
    with pytest.raises(ValueError):
        journal.prepare(scope, operation_id, {**arguments, 'name': 'Different'}, prepared)
    with pytest.raises(KeyError):
        journal.preparation(operation_id, actor=OWNER)


@pytest.mark.parametrize('actor', [None, 'owner', {}, object()])
def test_protected_preparation_is_available_only_to_owner_capability(setup, actor):
    _, journal, scope, operation_id, arguments, prepared, _ = setup
    journal.prepare(scope, operation_id, arguments, prepared)
    with pytest.raises(PermissionError):
        journal.preparation(operation_id, actor=actor)


def test_missing_preparation_is_explicit_for_legacy_or_unprepared_intent(setup):
    _, journal, _, operation_id, _, _, _ = setup
    with pytest.raises(KeyError):
        journal.preparation(operation_id, actor=OWNER)


@pytest.mark.parametrize('change', ['scope', 'revoked', 'purpose'])
def test_preparation_cannot_attach_to_a_different_or_obsolete_scope(setup, change):
    conn, journal, scope, operation_id, arguments, prepared, _ = setup
    if change == 'scope':
        scope = replace(scope, agent_id=str(uuid4()))
    elif change == 'revoked':
        revoke_writes(conn, actor=OWNER, binding_id=scope.binding_id)
    else:
        revise_soul(conn, actor=OWNER, agent_id=scope.agent_id, expected_revision=1, purpose='Different work')
    with pytest.raises(PermissionError):
        journal.prepare(scope, operation_id, arguments, prepared)
    with pytest.raises(KeyError):
        journal.preparation(operation_id, actor=OWNER)


def test_preparation_requires_an_existing_pending_intent(setup):
    _, journal, scope, operation_id, arguments, prepared, _ = setup
    with pytest.raises(KeyError):
        journal.prepare(scope, str(uuid4()), arguments, prepared)
    journal.finish(operation_id, 'unknown')
    with pytest.raises(ReplayError):
        journal.prepare(scope, operation_id, arguments, prepared)


def test_attempt_marker_is_durable_and_cannot_authorize_second_delivery(setup):
    _, journal, scope, operation_id, arguments, prepared, path = setup
    journal.prepare(scope, operation_id, arguments, prepared)
    saved = journal.mark_attempted(scope, operation_id)
    assert saved['attempted'] is True
    with connect_closing(path) as reader:
        assert MutationJournal(reader).preparation(operation_id, actor=OWNER)['attempted'] is True
    with pytest.raises(ReplayError):
        journal.mark_attempted(scope, operation_id)
    assert journal.get(operation_id, actor=OWNER)['status'] == 'pending'


def test_attempt_marker_requires_current_scope_preparation_and_pending_status(setup):
    conn, journal, scope, operation_id, arguments, prepared, _ = setup
    with pytest.raises(KeyError):
        journal.mark_attempted(scope, operation_id)
    journal.prepare(scope, operation_id, arguments, prepared)
    revoke_writes(conn, actor=OWNER, binding_id=scope.binding_id)
    with pytest.raises(PermissionError):
        journal.mark_attempted(scope, operation_id)
    assert journal.preparation(operation_id, actor=OWNER)['attempted'] is False


@pytest.mark.parametrize('initial_status', ['pending', 'unknown'])
def test_reconciliation_confirms_prepared_operation_once_with_redacted_event(setup, initial_status):
    _, journal, scope, operation_id, arguments, prepared, _ = setup
    journal.prepare(scope, operation_id, arguments, prepared)
    journal.mark_attempted(scope, operation_id)
    if initial_status == 'unknown':
        journal.finish(operation_id, 'unknown')
    resource_id = str(uuid4())
    resolved = journal.reconcile(scope, operation_id, status='confirmed', resource_id=resource_id)
    assert resolved['status'] == 'confirmed' and resolved['resource_id'] == resource_id
    assert journal.reconcile(scope, operation_id, status='confirmed', resource_id=resource_id) == resolved
    events = journal.events(actor=OWNER, operation_id=operation_id)
    assert [event['status'] for event in events].count('confirmed') == 1
    assert 'private body' not in json.dumps(events)
    with pytest.raises(ReplayError):
        journal.reconcile(scope, operation_id, status='confirmed', resource_id=str(uuid4()))
    with pytest.raises(ReplayError):
        journal.reconcile(scope, operation_id, status='rejected')


@pytest.mark.parametrize('initial_status', ['pending', 'unknown'])
def test_only_durable_unattempted_operations_can_be_reconciled_as_rejected(setup, initial_status):
    _, journal, scope, operation_id, arguments, prepared, _ = setup
    journal.prepare(scope, operation_id, arguments, prepared)
    if initial_status == 'unknown':
        journal.finish(operation_id, 'unknown')
    resolved = journal.reconcile(scope, operation_id, status='rejected')
    assert resolved['status'] == 'rejected'
    assert journal.reconcile(scope, operation_id, status='rejected') == resolved


def test_attempted_unknown_write_cannot_be_mislabeled_rejected(setup):
    _, journal, scope, operation_id, arguments, prepared, _ = setup
    journal.prepare(scope, operation_id, arguments, prepared)
    journal.mark_attempted(scope, operation_id)
    journal.finish(operation_id, 'unknown')
    with pytest.raises(ReplayError):
        journal.reconcile(scope, operation_id, status='rejected')
    assert journal.get(operation_id, actor=OWNER)['status'] == 'unknown'


def test_legacy_intent_and_obsolete_scope_are_not_silently_reconciled(setup):
    conn, journal, scope, operation_id, arguments, prepared, _ = setup
    with pytest.raises(KeyError):
        journal.reconcile(scope, operation_id, status='rejected')
    journal.prepare(scope, operation_id, arguments, prepared)
    revise_soul(conn, actor=OWNER, agent_id=scope.agent_id, expected_revision=1, purpose='Different purpose')
    with pytest.raises(PermissionError):
        journal.reconcile(scope, operation_id, status='confirmed', resource_id=str(uuid4()))
    assert journal.get(operation_id, actor=OWNER)['status'] == 'pending'


@pytest.mark.parametrize('changed', [
    {'method': 'GET'}, {'suffix': 'https://other.invalid/'}, {'suffix': '../other/'},
    {'expected': True}, {'kind': 'authority'}, {'resource_id': 'not-a-uuid'},
    {'api_key': 'never store credentials'}, {'payload': 'not a delivery object'},
])
def test_invalid_prepared_delivery_shape_is_rejected_before_storage(setup, changed):
    _, journal, scope, operation_id, arguments, prepared, _ = setup
    with pytest.raises(ValueError):
        journal.prepare(scope, operation_id, arguments, {**prepared, **changed})
    with pytest.raises(KeyError):
        journal.preparation(operation_id, actor=OWNER)


@pytest.mark.parametrize('column,new_value', [
    ('arguments_json', '{"name":"tampered private body"}'),
    ('prepared_json', '{"payload":{"name":"tampered private body"}}'),
    ('prepared_sha256', '0' * 64),
])
def test_protected_payload_or_hash_corruption_blocks_loading_and_delivery(setup, column, new_value):
    conn, journal, scope, operation_id, arguments, prepared, _ = setup
    journal.prepare(scope, operation_id, arguments, prepared)
    conn.execute(f'UPDATE agent_native_plane_preparations SET {column} = ? WHERE operation_id = ?',
                 (new_value, operation_id))
    with pytest.raises(ValueError, match='^Protected preparation is invalid$'):
        journal.preparation(operation_id, actor=OWNER)
    with pytest.raises(ValueError):
        journal.mark_attempted(scope, operation_id)


def test_reconciliation_and_outcome_event_fail_atomically(setup):
    conn, journal, scope, operation_id, arguments, prepared, _ = setup
    journal.prepare(scope, operation_id, arguments, prepared)
    journal.mark_attempted(scope, operation_id)
    journal.finish(operation_id, 'unknown')
    before = journal.get(operation_id, actor=OWNER)
    conn.execute("CREATE TRIGGER reject_reconciled_event BEFORE INSERT ON agent_native_plane_mutation_events "
                 "WHEN NEW.status = 'confirmed' BEGIN SELECT RAISE(ABORT, 'storage failure'); END")
    with pytest.raises(sqlite3.IntegrityError):
        journal.reconcile(scope, operation_id, status='confirmed', resource_id=str(uuid4()))
    assert journal.get(operation_id, actor=OWNER) == before
    assert [event['status'] for event in journal.events(actor=OWNER)] == ['pending', 'unknown']


@pytest.mark.parametrize('arguments', [
    {'name': 'x' * 256},
    {'name': 'Task', 'description': '\U0001f600' * 9000},
    {'name': 'Task', 'actor': 'caller-selected owner'},
])
def test_preparation_obeys_existing_operation_contract_bounds(setup, arguments):
    _, journal, scope, _, _, prepared, _ = setup
    operation_id = str(uuid4())
    # Legacy begin stores a hash of bounded JSON; preparation must additionally
    # enforce the operation contract before making content recoverable.
    journal.begin(scope, operation_id, 'item.create', arguments)
    with pytest.raises(ValueError):
        journal.prepare(scope, operation_id, arguments, prepared)
    with pytest.raises(KeyError):
        journal.preparation(operation_id, actor=OWNER)


def test_prepare_and_attempt_storage_failures_leave_no_partial_state(setup):
    conn, journal, scope, operation_id, arguments, prepared, _ = setup
    conn.execute("CREATE TRIGGER reject_preparation BEFORE INSERT ON agent_native_plane_preparations "
                 "BEGIN SELECT RAISE(ABORT, 'storage failure'); END")
    with pytest.raises(sqlite3.IntegrityError):
        journal.prepare(scope, operation_id, arguments, prepared)
    with pytest.raises(KeyError):
        journal.preparation(operation_id, actor=OWNER)
    conn.execute('DROP TRIGGER reject_preparation')
    journal.prepare(scope, operation_id, arguments, prepared)
    conn.execute("CREATE TRIGGER reject_attempt BEFORE UPDATE ON agent_native_plane_preparations "
                 "WHEN NEW.attempted = 1 BEGIN SELECT RAISE(ABORT, 'storage failure'); END")
    with pytest.raises(sqlite3.IntegrityError):
        journal.mark_attempted(scope, operation_id)
    assert journal.preparation(operation_id, actor=OWNER)['attempted'] is False
    assert journal.get(operation_id, actor=OWNER)['status'] == 'pending'


def test_concurrent_attempt_markers_allow_one_delivery_claim(setup):
    from concurrent.futures import ThreadPoolExecutor
    _, journal, scope, operation_id, arguments, prepared, path = setup
    journal.prepare(scope, operation_id, arguments, prepared)

    def mark(_):
        with connect_closing(path) as conn:
            try:
                MutationJournal(conn).mark_attempted(scope, operation_id)
                return 'claimed'
            except ReplayError:
                return 'replay'

    with ThreadPoolExecutor(max_workers=4) as workers:
        results = list(workers.map(mark, range(4)))
    assert results.count('claimed') == 1 and results.count('replay') == 3


def test_concurrent_identical_reconciliation_has_one_outcome_event(setup):
    from concurrent.futures import ThreadPoolExecutor
    _, journal, scope, operation_id, arguments, prepared, path = setup
    journal.prepare(scope, operation_id, arguments, prepared)
    journal.mark_attempted(scope, operation_id)
    journal.finish(operation_id, 'unknown')
    resource_id = str(uuid4())

    def confirm(_):
        with connect_closing(path) as conn:
            return MutationJournal(conn).reconcile(scope, operation_id, status='confirmed', resource_id=resource_id)

    with ThreadPoolExecutor(max_workers=4) as workers:
        results = list(workers.map(confirm, range(4)))
    assert all(result == results[0] for result in results)
    assert [event['status'] for event in journal.events(actor=OWNER)].count('confirmed') == 1


def test_noop_preparation_can_be_confirmed_without_network_attempt(setup):
    conn, journal, scope, _, _, _, _ = setup
    grant_writes(conn, actor=OWNER, binding_id=scope.binding_id, operations=['cycle.assign'])
    authority = WriteAuthority(conn)
    scope = authority.resolve(authority.issue_context(actor=OWNER, binding_id=scope.binding_id))
    operation_id, item_id, cycle_id = str(uuid4()), str(uuid4()), str(uuid4())
    arguments = {'item_id': item_id, 'cycle_id': cycle_id, 'expected_cycle_id': cycle_id,
                 'expected_item_fingerprint': 'a' * 64}
    prepared = {'method': None, 'suffix': '', 'payload': [{'id': str(uuid4()), 'issue': item_id,
                 'cycle': cycle_id, 'workspace': scope.workspace_id, 'project': scope.project_id}],
                'expected': None, 'kind': 'membership', 'resource_id': item_id}
    journal.begin(scope, operation_id, 'cycle.assign', arguments)
    journal.prepare(scope, operation_id, arguments, prepared)
    with pytest.raises(ValueError):
        journal.mark_attempted(scope, operation_id)
    assert journal.reconcile(scope, operation_id, status='confirmed', resource_id=item_id)['status'] == 'confirmed'
    assert journal.preparation(operation_id, actor=OWNER)['attempted'] is False


def test_protected_preparation_and_attempt_marker_survive_database_close_and_reopen(setup):
    conn, journal, scope, operation_id, arguments, prepared, path = setup
    journal.prepare(scope, operation_id, arguments, prepared)
    journal.mark_attempted(scope, operation_id)
    journal.finish(operation_id, 'unknown')
    conn.close()
    with connect_closing(path) as restarted:
        journal = MutationJournal(restarted)
        authority = WriteAuthority(restarted)
        context = authority.issue_context(actor=OWNER, binding_id=scope.binding_id)
        current = authority.resolve(context)
        assert journal.preparation(operation_id, actor=OWNER) == {
            'arguments': arguments, 'prepared': prepared, 'attempted': True,
        }
        with pytest.raises(ReplayError):
            journal.mark_attempted(current, operation_id)
        resolved = journal.reconcile(current, operation_id, status='confirmed', resource_id=str(uuid4()))
        assert resolved['status'] == 'confirmed'
