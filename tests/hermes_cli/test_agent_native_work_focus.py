"""Explicit work focus through the real broker, scoped Plane HTTP and SQLite."""
import json

import pytest

from agent_native import work_state
from agent_native.identity import OWNER, create_root
from agent_native.plane_reads import PlaneReadError
from agent_native.startup import prepare, read_setup
from hermes_cli.kanban_db_connect import connect_closing, write_txn
from tests.hermes_cli.test_agent_native_work_effects import broker, effect  # noqa: F401


def select(s, call_id='select-one', item_id=None, **extra):
    return s.run._effect(s.conn, s.planning, effect(s, call_id, 'work_item_select', {
        'item_id': item_id or s.setup['discovery_item_id'], **extra}))


def test_work_has_no_implicit_focus_before_selection(broker):
    s = broker
    assert s.plane.items
    assert work_state.read_work(s.conn, s.root['id'])['focus'] is None
    with write_txn(s.conn):
        s.conn.execute("UPDATE agent_native_work_runs SET state='completed' WHERE id=?", (s.work['id'],))
    assert work_state.read_work(s.conn, s.root['id'])['focus'] is None


def test_select_records_scoped_item_criteria_and_host_identity_durably(broker):
    s = broker
    observation = s.planning.inspect({'kind': 'item', 'resource_id': s.setup['discovery_item_id']})
    selected = select(s)
    assert selected['selection_id']
    assert selected['run_id'] == s.work['id'] and selected['soul_revision'] == 1
    assert selected['item_id'] == observation['resource']['id']
    assert selected['name'] == observation['resource']['name']
    assert selected['description_html'] == observation['resource']['description_html']
    assert selected['assignment_fingerprint'] == observation['fingerprint']
    assert selected['cycle_id'] == observation['cycle_id'] and selected['selected_at']
    with connect_closing(s.db_path) as reopened:
        assert work_state.read_work(reopened, s.root['id'])['focus'] == selected
    assert any(e['kind'] == 'work.focus' for e in work_state.read_work(s.conn, s.root['id'])['events'])


def test_changing_focus_preserves_selection_history_and_exact_replay_cannot_rewind(broker):
    s = broker
    first = select(s)
    item = s.run._effect(s.conn, s.planning, effect(s, 'create-second', arguments={
        'operation': 'item.create', 'arguments': {'name': 'Next useful task', 'description': 'Keep the evidence.'}}))
    second_id = item['resource']['id']
    second = select(s, 'select-two', second_id)
    assert second['selection_id'] != first['selection_id'] and second['item_id'] == second_id
    assert select(s) == first
    assert work_state.read_work(s.conn, s.root['id'])['focus'] == second
    with pytest.raises(PermissionError):
        select(s, item_id=second_id)
    # Simulate losing only the broker receipt after committing a local selection.
    with write_txn(s.conn):
        s.conn.execute('UPDATE agent_native_work_effects SET result=NULL WHERE run_id=? AND call_id=?',
                       (s.work['id'], 'select-one'))
    requests = len(s.plane.requests)
    assert select(s) == first
    assert len(s.plane.requests) == requests
    with connect_closing(s.db_path) as reopened:
        assert work_state.read_work(reopened, s.root['id'])['focus'] == second
        rows = reopened.execute('SELECT record_json FROM agent_native_work_selections WHERE run_id=? ORDER BY sequence',
                                (s.work['id'],)).fetchall()
        assert [json.loads(row[0]) for row in rows] == [first, second]
    events = [e for e in work_state.read_work(s.conn, s.root['id'])['events'] if e['kind'] == 'work.focus']
    assert len(events) == 2


def test_selection_cannot_read_a_foreign_project_item(broker):
    s = broker
    other = create_root(s.conn, actor=OWNER, request_id='foreign-focus', name='Other', purpose='Other project.')
    prepare(s.conn, actor=OWNER, agent_id=other['id'], home=s.home)
    foreign = read_setup(s.conn, other['id'])
    with pytest.raises(PlaneReadError) as error:
        select(s, item_id=foreign['discovery_item_id'])
    assert error.value.status == 404
    assert work_state.read_work(s.conn, s.root['id'])['focus'] is None


@pytest.mark.parametrize('change', ['stop', 'revision'])
def test_stop_or_changed_purpose_prevents_selection_and_replay_before_network(broker, change):
    s = broker
    selected = select(s)
    with write_txn(s.conn):
        if change == 'stop':
            s.conn.execute('UPDATE agent_native_work_runs SET stop_requested=1 WHERE id=?', (s.work['id'],))
        else:
            s.conn.execute('UPDATE agent_native_agents SET soul_revision=2 WHERE id=?', (s.root['id'],))
    before = len(s.plane.requests)
    for call_id in ('select-one', 'select-new'):
        with pytest.raises(PermissionError):
            select(s, call_id)
    assert len(s.plane.requests) == before
    assert work_state.read_work(s.conn, s.root['id'])['focus'] == selected


def test_selection_rejects_model_supplied_host_fields(broker):
    s = broker
    with pytest.raises(ValueError):
        select(s, soul_revision=100)
    assert work_state.read_work(s.conn, s.root['id'])['focus'] is None


def test_local_selection_and_event_roll_back_if_final_admission_is_revoked(broker, monkeypatch):
    s = broker
    validate = s.run.validate
    def revoke_after_insert(conn):
        validate(conn)
        if conn.in_transaction and conn.execute('SELECT COUNT(*) FROM agent_native_work_selections').fetchone()[0]:
            raise PermissionError('Authority revoked before local commit')
    monkeypatch.setattr(s.run, 'validate', revoke_after_insert)
    with pytest.raises(PermissionError):
        select(s)
    work = work_state.read_work(s.conn, s.root['id'])
    assert work['focus'] is None
    assert not any(e['kind'] == 'work.focus' for e in work['events'])


def test_selecting_again_records_changed_criteria_and_cycle_without_rewriting_history(broker):
    s = broker
    first = select(s)
    s.run._effect(s.conn, s.planning, effect(s, 'update-criteria', arguments={
        'operation': 'item.update', 'arguments': {'item_id': first['item_id'],
            'description': 'Revised criteria: retain the original evidence.',
            'expected_fingerprint': first['assignment_fingerprint']}}))
    cycle = s.run._effect(s.conn, s.planning, effect(s, 'create-cycle', arguments={
        'operation': 'cycle.create', 'arguments': {'name': 'Evidence', 'description': 'Exit: retained findings.'}}))
    observed = s.planning.inspect({'kind': 'item', 'resource_id': first['item_id']})
    cycle_id = cycle['resource']['id']
    s.run._effect(s.conn, s.planning, effect(s, 'assign-cycle', arguments={
        'operation': 'cycle.assign', 'arguments': {'item_id': first['item_id'], 'cycle_id': cycle_id,
            'expected_item_fingerprint': observed['fingerprint'], 'expected_cycle_id': observed['cycle_id']}}))
    # Merely changing Plane never claims the agent has seen the new criteria.
    assert work_state.read_work(s.conn, s.root['id'])['focus'] == first
    selected = select(s, 'select-revised')
    assert selected['cycle_id'] == cycle_id
    assert 'Revised criteria' in selected['description_html']
    assert selected['description_html'] != first['description_html']
    assert selected['assignment_fingerprint'] != first['assignment_fingerprint']
    assert select(s) == first
    assert work_state.read_work(s.conn, s.root['id'])['focus'] == selected


def test_local_idempotence_rejects_changed_input_even_without_broker_receipt(broker):
    from agent_native.work_focus import select as select_local
    s = broker
    select(s)
    before = len(s.plane.requests)
    with pytest.raises(PermissionError):
        select_local(s.conn, validate=s.run.validate, inspect=s.planning.inspect,
                     agent_id=s.root['id'], run_id=s.work['id'], call_id='select-one',
                     arguments={'item_id': '11111111-1111-4111-8111-111111111111'})
    assert len(s.plane.requests) == before
