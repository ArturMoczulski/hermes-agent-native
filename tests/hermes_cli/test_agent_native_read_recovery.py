"""Rejected observations cannot strand an otherwise recoverable work attempt."""
from uuid import uuid4

import pytest

from agent_native import cadence, work_state
from agent_native.identity import OWNER
from tests.hermes_cli.test_agent_native_work_effects import broker, effect  # noqa: F401


def test_missing_selection_settles_before_corrected_selection_and_cadence(broker):
    s = broker
    cadence.configure(s.conn, actor=OWNER, agent_id=s.root['id'], expected_revision=1,
                      interval_seconds=1, enabled=True)
    missing_id = str(uuid4())
    rejected = s.run._effect(s.conn, s.planning, effect(
        s, 'missing-item', 'work_item_select', {'item_id': missing_id}))
    assert rejected['status'] == 'rejected'
    assert rejected['error'] == 'PlaneReadError'
    assert 'No work selection or write' in rejected['message']
    assert work_state.read_work(s.conn, s.root['id'])['focus'] is None
    before = len(s.plane.requests)
    # Exact replay returns its receipt without inspecting again.
    assert s.run._effect(s.conn, s.planning, effect(
        s, 'missing-item', 'work_item_select',
        {'item_id': missing_id})) == rejected
    assert len(s.plane.requests) == before
    selected = s.run._effect(s.conn, s.planning, effect(
        s, 'corrected-item', 'work_item_select', {'item_id': s.setup['discovery_item_id']}))
    assert selected['item_id'] == s.setup['discovery_item_id']
    s.run.finish(s.conn, {'type': 'turn.end'})
    assert work_state.read_work(s.conn, s.root['id'])['state'] == 'retryable_failure'
    assert len(cadence.queue_due(s.conn, now='2099-01-01T00:00:00+00:00')) == 1


@pytest.mark.parametrize('unsettled', [False, True])
def test_model_step_exhaustion_continues_only_after_effects_are_settled(broker, unsettled):
    s = broker
    cadence.configure(s.conn, actor=OWNER, agent_id=s.root['id'], expected_revision=1,
                      interval_seconds=1, enabled=True)
    if unsettled:
        s.conn.execute('INSERT INTO agent_native_work_effects '
                       '(run_id,call_id,operation_id,fingerprint,tool) VALUES(?,?,?,?,?)',
                       (s.work['id'], 'lost-write', 'lost-write', 'hash', 'plane_operation_execute'))
    s.conn.execute('UPDATE agent_native_work_runs SET model_calls=? WHERE id=?',
                   (s.work['limits']['max_iterations'], s.work['id']))
    s.run.finish(s.conn, {'type': 'turn.end', 'limit_reached': 'model_steps'})
    work = work_state.read_work(s.conn, s.root['id'])
    assert work['state'] == ('unknown' if unsettled else 'limit_reached')
    assert 'model-step limit' in work['summary']
    assert work['results'] == []  # A bounded stop does not fabricate accepted work.
    assert len(cadence.queue_due(s.conn, now='2099-01-01T00:00:00+00:00')) == (0 if unsettled else 1)
