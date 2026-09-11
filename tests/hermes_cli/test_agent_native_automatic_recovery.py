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


def test_step_limit_unknown_run_is_reconcilable(broker):
    """The step-limit ``unknown`` path must flag the run for read-back.

    Every other transition to ``unknown`` sets ``stop_requested``; the
    model-step-limit branch in ``finish`` did not, while
    ``_reconcile_unknown_run.validate`` requires it. A genuine lost Plane write
    at the step limit therefore could never be read back and the agent stayed
    at ``framework_reconciliation`` with no way forward.
    """
    from agent_native import work_state
    from hermes_cli.kanban_db_connect import write_txn

    s = broker
    operation_id, before = _lost_item_effect(s)
    with write_txn(s.conn):
        s.conn.execute(
            "UPDATE agent_native_work_runs SET state='running',stop_requested=0,"
            "model_calls=json_extract(limits,'$.max_iterations') WHERE id=?",
            (s.work['id'],),
        )

    s.run.finish(s.conn, {'type': 'turn.end', 'limit_reached': 'model_steps'})

    assert tuple(s.conn.execute(
        'SELECT state,stop_requested FROM agent_native_work_runs WHERE id=?',
        (s.work['id'],),
    ).fetchone()) == ('unknown', 1)
    s.run.service.reconcile_unknown_runs()
    assert work_state.read_work(s.conn, s.root['id'])['state'] == 'interrupted'
    assert len([r for r in s.plane.requests if r['method'] == 'POST']) == before


def test_retryable_failure_waits_for_bounded_backoff_without_spending_tokens(broker):
    from agent_native import cadence

    s = broker
    cadence.configure(
        s.conn,
        actor=OWNER,
        agent_id=s.root['id'],
        expected_revision=1,
        interval_seconds=1,
        enabled=True,
    )
    s.conn.execute(
        "UPDATE agent_native_work_runs SET state='retryable_failure',"
        "created_at='2099-01-01T00:00:00+00:00',"
        "finished_at='2099-01-01T00:00:01+00:00',"
        "summary='Temporary provider failure' WHERE id=?",
        (s.work['id'],),
    )
    s.conn.execute(
        "UPDATE agent_native_cadence SET next_due='2099-01-01T00:00:01+00:00' "
        "WHERE agent_id=?", (s.root['id'],),
    )

    assert cadence.queue_due(s.conn, now='2099-01-01T00:00:02+00:00') == []
    assert s.conn.execute(
        'SELECT count(*) FROM agent_native_work_runs WHERE agent_id=?',
        (s.root['id'],),
    ).fetchone()[0] == 1
    assert cadence.read(s.conn, s.root['id'])['next_due'] == '2099-01-01T00:00:06+00:00'

    queued = cadence.queue_due(s.conn, now='2099-01-01T00:00:06+00:00')
    assert len(queued) == 1
    assert queued[0] == cadence.recovery_identity(s.root['id'], s.work['id'])


def test_retry_backoff_is_an_explicit_readiness_state_not_ready(broker):
    """A retryable failure inside its backoff window is waiting, not ready."""
    from agent_native import cadence
    from agent_native.readiness import automatic_work

    s = broker
    cadence.configure(
        s.conn,
        actor=OWNER,
        agent_id=s.root['id'],
        expected_revision=1,
        interval_seconds=1,
        enabled=True,
    )
    s.conn.execute(
        "UPDATE agent_native_work_runs SET state='retryable_failure',"
        "created_at='2099-01-01T00:00:00+00:00',"
        "finished_at='2099-01-01T00:00:01+00:00' WHERE id=?",
        (s.work['id'],),
    )
    s.conn.execute(
        "UPDATE agent_native_cadence SET next_due='2099-01-01T00:00:01+00:00' "
        "WHERE agent_id=?", (s.root['id'],),
    )

    decision = automatic_work(s.conn, s.root['id'], now='2099-01-01T00:00:02+00:00')
    assert decision == {
        'state': 'waiting_retry', 'may_start': False,
        'blocker': 'Waiting for the automatic retry backoff to elapse.',
        'release_condition': (
            'The next automatic retry becomes eligible at 2099-01-01T00:00:06+00:00.'
        ),
        'responsible_actor': 'framework',
    }
    # The scheduler skip and the API decision agree, before and after the due
    # row is evaluated (which extends next_due to the retry-eligible time).
    assert cadence.queue_due(s.conn, now='2099-01-01T00:00:02+00:00') == []
    assert automatic_work(s.conn, s.root['id'], now='2099-01-01T00:00:02+00:00') == decision
    assert automatic_work(
        s.conn, s.root['id'], now='2099-01-01T00:00:06+00:00')['state'] == 'ready'


def test_retryable_recovery_identity_is_idempotent_while_pending(broker):
    from agent_native import cadence

    s = broker
    cadence.configure(
        s.conn,
        actor=OWNER,
        agent_id=s.root['id'],
        expected_revision=1,
        interval_seconds=1,
        enabled=True,
    )
    s.conn.execute(
        "UPDATE agent_native_work_runs SET state='retryable_failure',"
        "created_at='2099-01-01T00:00:00+00:00',"
        "finished_at='2099-01-01T00:00:01+00:00' WHERE id=?",
        (s.work['id'],),
    )
    s.conn.execute(
        "UPDATE agent_native_cadence SET next_due='2099-01-01T00:00:06+00:00' "
        "WHERE agent_id=?", (s.root['id'],),
    )

    first = cadence.queue_due(s.conn, now='2099-01-01T00:00:06+00:00')
    second = cadence.queue_due(s.conn, now='2099-01-01T00:00:06+00:00')

    assert len(first) == 1 and second == []
    assert s.conn.execute(
        'SELECT count(*) FROM agent_native_work_runs WHERE agent_id=?',
        (s.root['id'],),
    ).fetchone()[0] == 2


def test_old_retryable_failures_do_not_consume_the_current_recovery_window(broker):
    from agent_native import cadence

    s = broker
    cadence.configure(
        s.conn,
        actor=OWNER,
        agent_id=s.root['id'],
        expected_revision=1,
        interval_seconds=1,
        enabled=True,
    )
    for index in range(3):
        run_id = s.work['id'] if index == 0 else f'old-retry-{index}'
        if index:
            s.conn.execute(
                "INSERT INTO agent_native_work_runs "
                "(id,agent_id,activation_id,soul_revision,session_id,limits,state,created_at,finished_at) "
                "SELECT ?,agent_id,activation_id,soul_revision,?,limits,'retryable_failure',?,? "
                "FROM agent_native_work_runs WHERE id=?",
                (run_id, f'old-retry-session-{index}',
                 '2099-01-01T00:00:00+00:00', '2099-01-01T00:00:01+00:00',
                 s.work['id']),
            )
        else:
            s.conn.execute(
                "UPDATE agent_native_work_runs SET state='retryable_failure',"
                "created_at='2099-01-01T00:00:00+00:00',"
                "finished_at='2099-01-01T00:00:01+00:00' WHERE id=?", (run_id,),
            )
    s.conn.execute(
        "UPDATE agent_native_cadence SET next_due='2099-01-01T01:00:00+00:00' "
        "WHERE agent_id=?", (s.root['id'],),
    )

    queued = cadence.queue_due(s.conn, now='2099-01-01T01:00:00+00:00')

    assert len(queued) == 1
    assert cadence.read(s.conn, s.root['id'])['enabled'] is True


def test_recent_retry_budget_caps_even_when_owner_threshold_is_more_permissive(broker):
    from agent_native import cadence
    from agent_native.progress_concerns import configure, list_concerns

    s = broker
    configure(s.conn, actor=OWNER, agent_id=s.root['id'], failure_threshold=10)
    cadence.configure(
        s.conn,
        actor=OWNER,
        agent_id=s.root['id'],
        expected_revision=1,
        interval_seconds=1,
        enabled=True,
    )
    for index in range(3):
        run_id = s.work['id'] if index == 0 else f'budget-retry-{index}'
        if index:
            s.conn.execute(
                "INSERT INTO agent_native_work_runs "
                "(id,agent_id,activation_id,soul_revision,session_id,limits,state,created_at,finished_at) "
                "SELECT ?,agent_id,activation_id,soul_revision,?,limits,'retryable_failure',?,? "
                "FROM agent_native_work_runs WHERE id=?",
                (run_id, f'budget-retry-session-{index}',
                 '2099-01-01T00:00:0' + str(index) + '+00:00',
                 '2099-01-01T00:00:1' + str(index) + '+00:00', s.work['id']),
            )
        else:
            s.conn.execute(
                "UPDATE agent_native_work_runs SET state='retryable_failure',"
                "created_at='2099-01-01T00:00:00+00:00',"
                "finished_at='2099-01-01T00:00:10+00:00' WHERE id=?", (run_id,),
            )
    s.conn.execute(
        "UPDATE agent_native_cadence SET next_due='2099-01-01T00:01:00+00:00' "
        "WHERE agent_id=?", (s.root['id'],),
    )

    assert cadence.queue_due(s.conn, now='2099-01-01T00:01:00+00:00') == []
    assert cadence.read(s.conn, s.root['id'])['enabled'] is False
    [concern] = list_concerns(s.conn, s.root['id'])
    assert concern['kind'] == 'repeated_unproductive_failure'
    assert '3 consecutive attempts' in concern['summary']
