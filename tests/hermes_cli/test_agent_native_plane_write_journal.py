"""Persistence, no-replay and redaction at the real control DB boundary."""
import hashlib
import json
import sqlite3
from uuid import uuid4

import pytest

from agent_native.identity import OWNER, create_root
from agent_native.plane_access import grant_project
from agent_native.plane_write_access import WriteAuthority, grant_writes
from agent_native.plane_write_journal import MutationJournal, ReplayError
from hermes_cli.kanban_db_connect import connect_closing


@pytest.fixture
def setup(tmp_path):
    with connect_closing(tmp_path / 'control.db') as conn:
        root = create_root(conn, actor=OWNER, request_id='builder', name='Builder', purpose='Build')
        grant = grant_project(conn, actor=OWNER, agent_id=root['id'], workspace_slug='build',
                              workspace_id=str(uuid4()), project_id=str(uuid4()))
        grant_writes(conn, actor=OWNER, binding_id=grant['id'], operations=['item.create'])
        authority = WriteAuthority(conn)
        scope = authority.resolve(authority.issue_context(actor=OWNER, binding_id=grant['id']))
        yield conn, scope


def test_pending_intent_persists_only_canonical_hash_and_scoped_evidence(setup):
    conn, scope = setup
    journal = MutationJournal(conn)
    operation_id, resource_id = str(uuid4()), str(uuid4())
    arguments = {'name': 'Private title', 'description': 'secret-marker', 'nested': {'b': 2, 'a': 1}}
    record = journal.begin(scope, operation_id, 'item.create', arguments, resource_ids=[resource_id])
    expected = hashlib.sha256(json.dumps(arguments, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                                         allow_nan=False).encode()).hexdigest()
    assert record['status'] == 'pending' and record['arguments_sha256'] == expected
    assert record['operation_id'] == operation_id and record['resource_ids'] == [resource_id]
    assert record['binding_id'] == scope.binding_id and record['agent_id'] == scope.agent_id
    assert record['project_id'] == scope.project_id and record['write_revision'] == scope.write_revision
    assert record['soul_revision'] == scope.soul_revision and record['revision'] == scope.revision
    assert MutationJournal(conn).get(operation_id, actor=OWNER) == record
    assert 'secret-marker' not in '\n'.join(conn.iterdump())
    assert 'Private title' not in '\n'.join(conn.iterdump())
    assert [e['status'] for e in journal.events(actor=OWNER, operation_id=operation_id)] == ['pending']


@pytest.mark.parametrize('status', ['pending', 'confirmed', 'rejected', 'unknown'])
def test_reused_operation_id_never_replays_even_identical_request(setup, status):
    conn, scope = setup
    journal = MutationJournal(conn)
    operation_id = str(uuid4())
    journal.begin(scope, operation_id, 'item.create', {'name': 'One'})
    if status != 'pending':
        journal.finish(operation_id, status)
    with pytest.raises(ReplayError):
        journal.begin(scope, operation_id, 'item.create', {'name': 'One'})
    with pytest.raises(ReplayError):
        journal.begin(scope, operation_id, 'item.create', {'name': 'Different'})
    assert journal.get(operation_id, actor=OWNER)['status'] == status


def test_terminal_transition_is_single_and_keeps_append_only_evidence(setup):
    conn, scope = setup
    journal = MutationJournal(conn)
    operation_id, created_id = str(uuid4()), str(uuid4())
    before = journal.begin(scope, operation_id, 'item.create', {'name': 'One'})
    after = journal.finish(operation_id, 'confirmed', resource_id=created_id)
    assert after['status'] == 'confirmed' and after['resource_id'] == created_id
    for key in ('arguments_sha256', 'agent_id', 'project_id', 'write_revision', 'soul_revision', 'created_at'):
        assert after[key] == before[key]
    with pytest.raises(ReplayError):
        journal.finish(operation_id, 'rejected')
    assert [e['status'] for e in journal.events(actor=OWNER)] == ['pending', 'confirmed']


def test_denied_events_do_not_invent_actor_attribution_or_retain_arbitrary_content(setup):
    conn, scope = setup
    journal = MutationJournal(conn)
    operation_id = str(uuid4())
    journal.denied(operation_id, 'item.create')
    journal.denied(str(uuid4()), 'secret-operation', reason='secret-reason')
    journal.denied(str(uuid4()), 'item.create', scope=scope)
    events = journal.events(actor=OWNER)
    assert all(e['status'] == 'denied' for e in events)
    assert events[0]['agent_id'] is None and events[0]['binding_id'] is None
    assert events[-1]['agent_id'] == scope.agent_id
    assert 'secret-operation' not in '\n'.join(conn.iterdump())
    assert 'secret-reason' not in '\n'.join(conn.iterdump())
    with pytest.raises(PermissionError):
        journal.denied(str(uuid4()), 'item.create', scope={'agent_id': scope.agent_id})


@pytest.mark.parametrize('actor', [None, 'owner', {}, object()])
def test_journal_evidence_is_only_visible_to_trusted_owner(setup, actor):
    conn, scope = setup
    journal = MutationJournal(conn)
    operation_id = str(uuid4())
    journal.begin(scope, operation_id, 'item.create', {})
    with pytest.raises(PermissionError):
        journal.get(operation_id, actor=actor)
    with pytest.raises(PermissionError):
        journal.events(actor=actor)


def test_intent_and_event_persistence_fail_atomically(setup):
    conn, scope = setup
    journal = MutationJournal(conn)
    operation_id = str(uuid4())
    conn.execute("CREATE TRIGGER reject_mutation_event BEFORE INSERT ON agent_native_plane_mutation_events "
                 "BEGIN SELECT RAISE(ABORT, 'simulated event failure'); END")
    with pytest.raises(sqlite3.IntegrityError):
        journal.begin(scope, operation_id, 'item.create', {})
    with pytest.raises(KeyError):
        journal.get(operation_id, actor=OWNER)


def test_denied_operation_id_cannot_be_reused_for_delivery(setup):
    conn, scope = setup
    journal = MutationJournal(conn)
    operation_id = str(uuid4())
    journal.denied(operation_id, 'item.create')
    with pytest.raises(ReplayError):
        journal.begin(scope, operation_id, 'item.create', {})


def test_journal_revalidates_scope_before_committing_pending_intent(setup):
    from agent_native.plane_write_access import revoke_writes
    conn, scope = setup
    journal = MutationJournal(conn)
    revoke_writes(conn, actor=OWNER, binding_id=scope.binding_id)
    operation_id = str(uuid4())
    with pytest.raises(PermissionError):
        journal.begin(scope, operation_id, 'item.create', {})
    with pytest.raises(KeyError):
        journal.get(operation_id, actor=OWNER)


def test_outcome_and_event_roll_back_together_on_event_storage_failure(setup):
    conn, scope = setup
    journal = MutationJournal(conn)
    operation_id = str(uuid4())
    journal.begin(scope, operation_id, 'item.create', {})
    conn.execute("CREATE TRIGGER reject_mutation_outcome BEFORE INSERT ON agent_native_plane_mutation_events "
                 "BEGIN SELECT RAISE(ABORT, 'simulated event failure'); END")
    with pytest.raises(sqlite3.IntegrityError):
        journal.finish(operation_id, 'confirmed', resource_id=str(uuid4()))
    assert journal.get(operation_id, actor=OWNER)['status'] == 'pending'
    assert [e['status'] for e in journal.events(actor=OWNER)] == ['pending']


@pytest.mark.parametrize('arguments', [None, [], {'a': float('nan')}, {'a': object()}, {1: 'not-string-key'},
    {'a': 'x' * 262145}, {'a': [0] * 1025}])
def test_unbounded_or_non_json_arguments_leave_no_intent(setup, arguments):
    conn, scope = setup
    journal = MutationJournal(conn)
    operation_id = str(uuid4())
    with pytest.raises(ValueError):
        journal.begin(scope, operation_id, 'item.create', arguments)
    with pytest.raises(KeyError):
        journal.get(operation_id, actor=OWNER)


def test_journal_rejects_nested_transaction_before_any_external_delivery(setup):
    conn, scope = setup
    journal = MutationJournal(conn)
    conn.execute('BEGIN IMMEDIATE')
    try:
        with pytest.raises(RuntimeError, match='already inside a transaction'):
            journal.begin(scope, str(uuid4()), 'item.create', {})
    finally:
        conn.rollback()


def test_receipt_survives_database_reopen_and_unknown_operation_stays_unreplayable(tmp_path):
    path = tmp_path / 'control.db'
    operation_id = str(uuid4())
    with connect_closing(path) as conn:
        root = create_root(conn, actor=OWNER, request_id='builder', name='Builder', purpose='Build')
        grant = grant_project(conn, actor=OWNER, agent_id=root['id'], workspace_slug='build',
                              workspace_id=str(uuid4()), project_id=str(uuid4()))
        grant_writes(conn, actor=OWNER, binding_id=grant['id'], operations=['item.create'])
        authority = WriteAuthority(conn)
        scope = authority.resolve(authority.issue_context(actor=OWNER, binding_id=grant['id']))
        journal = MutationJournal(conn)
        journal.begin(scope, operation_id, 'item.create', {'name': 'One'})
        journal.finish(operation_id, 'unknown')
    with connect_closing(path) as conn:
        journal = MutationJournal(conn)
        assert journal.get(operation_id, actor=OWNER)['status'] == 'unknown'
        with pytest.raises(ReplayError):
            journal.begin(scope, operation_id, 'item.create', {'name': 'One'})
        assert [e['status'] for e in journal.events(actor=OWNER)] == ['pending', 'unknown']


def test_concurrent_operation_id_is_claimed_once_across_real_connections(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    path = tmp_path / 'control.db'
    operation_id = str(uuid4())
    with connect_closing(path) as conn:
        root = create_root(conn, actor=OWNER, request_id='builder', name='Builder', purpose='Build')
        grant = grant_project(conn, actor=OWNER, agent_id=root['id'], workspace_slug='build',
                              workspace_id=str(uuid4()), project_id=str(uuid4()))
        grant_writes(conn, actor=OWNER, binding_id=grant['id'], operations=['item.create'])
        authority = WriteAuthority(conn)
        scope = authority.resolve(authority.issue_context(actor=OWNER, binding_id=grant['id']))

    def claim(_):
        with connect_closing(path) as conn:
            try:
                MutationJournal(conn).begin(scope, operation_id, 'item.create', {'name': 'One'})
                return 'claimed'
            except ReplayError:
                return 'replay'

    with ThreadPoolExecutor(max_workers=4) as workers:
        outcomes = list(workers.map(claim, range(4)))
    assert outcomes.count('claimed') == 1 and outcomes.count('replay') == 3
    with connect_closing(path) as conn:
        assert [event['status'] for event in MutationJournal(conn).events(actor=OWNER)] == ['pending']


@pytest.mark.parametrize('operation_id', [None, '', '../mutations', str(uuid4()).upper(), str(uuid4()).replace('-', '')])
def test_operation_identifier_must_be_canonical(setup, operation_id):
    conn, scope = setup
    journal = MutationJournal(conn)
    with pytest.raises(ValueError):
        journal.begin(scope, operation_id, 'item.create', {})
    assert journal.events(actor=OWNER) == []


def test_changed_soul_and_forged_scope_cannot_be_recorded_as_current_authority(setup):
    from dataclasses import replace
    from agent_native.identity import revise_soul
    conn, scope = setup
    journal = MutationJournal(conn)
    with pytest.raises(PermissionError):
        journal.begin(replace(scope, agent_id=str(uuid4())), str(uuid4()), 'item.create', {})
    revise_soul(conn, actor=OWNER, agent_id=scope.agent_id, expected_revision=1, purpose='Different')
    with pytest.raises(PermissionError):
        journal.begin(scope, str(uuid4()), 'item.create', {})
    assert journal.events(actor=OWNER) == []
