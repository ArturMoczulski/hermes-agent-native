"""Host-side Plane reconciliation releases safe cadence recovery."""

import pytest

from agent_native import work_state
from agent_native.plane_write_journal import MutationJournal
from agent_native.plane_writes import PlaneWriteError
from agent_native.identity import OWNER
from tests.hermes_cli.test_agent_native_work_effects import broker, effect  # noqa: F401


def _lost_item_effect(s):
    path = (
        f"/api/v1/workspaces/{s.setup['workspace_slug']}/projects/"
        f"{s.setup['project_id']}/work-items/"
    )
    s.plane.lose.add(('POST', path))
    with pytest.raises(PlaneWriteError) as failure:
        s.run._effect(s.conn, s.planning, effect(s, 'lost-create'))
    operation_id = failure.value.operation_id
    after_original = len([r for r in s.plane.requests if r['method'] == 'POST'])
    return operation_id, after_original


def test_service_reconciles_unknown_effect_before_cadence_retry(broker):
    from agent_native import cadence

    s = broker
    cadence.configure(
        s.conn,
        actor=OWNER,
        agent_id=s.root['id'],
        expected_revision=1,
        interval_seconds=60,
        enabled=True,
    )
    operation_id, before = _lost_item_effect(s)

    s.run.service.reconcile_unknown_runs()

    assert MutationJournal(s.conn).get(operation_id, actor=OWNER)['status'] == 'confirmed'
    assert work_state.read_work(s.conn, s.root['id'])['state'] == 'interrupted'
    assert len([r for r in s.plane.requests if r['method'] == 'POST']) == before

    queued = cadence.queue_due(s.conn, now='2099-01-01T00:00:00+00:00')
    assert len(queued) == 1
    assert work_state.read_work(s.conn, s.root['id'])['state'] == 'queued'


def test_unresolved_reconciliation_stays_framework_blocked_and_is_throttled(broker):
    s = broker
    operation_id, before = _lost_item_effect(s)
    path = (
        f"/api/v1/workspaces/{s.setup['workspace_slug']}/projects/"
        f"{s.setup['project_id']}/work-items/"
    )
    s.plane.overrides[('GET', path)] = lambda _request: (
        503,
        {'Retry-After': '2'},
        {'error': 'temporary fixture outage'},
    )

    s.run.service.reconcile_unknown_runs()
    reads_after_first = len([r for r in s.plane.requests if r['method'] == 'GET'])
    s.run.service.reconcile_unknown_runs()

    assert MutationJournal(s.conn).get(operation_id, actor=OWNER)['status'] == 'unknown'
    assert work_state.read_work(s.conn, s.root['id'])['state'] == 'unknown'
    assert len([r for r in s.plane.requests if r['method'] == 'POST']) == before
    assert len([r for r in s.plane.requests if r['method'] == 'GET']) == reads_after_first
    assert any(
        event['kind'] == 'work.recovery_unresolved'
        for event in work_state.read_work(s.conn, s.root['id'])['events']
    )
