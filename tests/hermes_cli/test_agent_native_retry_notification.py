"""Failed-attempt status delivery cannot impersonate uncertain task effects."""
import pytest
from agent_native import progress
from agent_native.identity import OWNER, ConflictError
from agent_native.plane_write_journal import MutationJournal
from agent_native.work_retry import retry_failed
from hermes_cli.kanban_db_connect import write_txn
from tests.hermes_cli.test_agent_native_work_effects import broker  # noqa: F401
from tests.hermes_cli.test_agent_native_work_focus import select


def lost_terminal(s):
    select(s)
    s.conn.execute("UPDATE agent_native_work_runs SET state='failed' WHERE id=?", (s.work['id'],))
    with write_txn(s.conn):
        progress.terminal(s.conn, s.work['id'])
    path = f"/api/v1/workspaces/{s.setup['workspace_slug']}/projects/{s.setup['project_id']}/work-items/{s.setup['discovery_item_id']}/comments/"
    s.plane.lose.add(('POST', path))
    # Authorize the fixture's already-failed host reporting path, independently
    # of execution authority; no model or work attempt is started here.
    s.conn.execute("UPDATE agent_native_work_runs SET state='running' WHERE id=?", (s.work['id'],))
    progress.deliver(s.conn, s.planning, s.run.validate, 'terminal:'+s.work['id'])
    s.conn.execute("UPDATE agent_native_work_runs SET state='failed' WHERE id=?", (s.work['id'],))
    operation_id = s.conn.execute('SELECT operation_id FROM agent_native_progress WHERE source_id=?',('terminal:'+s.work['id'],)).fetchone()[0]
    assert MutationJournal(s.conn).get(operation_id,actor=OWNER)['status'] == 'unknown'
    return operation_id


def test_owner_retry_preserves_unknown_terminal_notice_without_resending(broker):
    s = broker
    operation_id = lost_terminal(s)
    before = len(s.plane.requests)
    args = dict(actor=OWNER,agent_id=s.root['id'],expected_revision=1,expected_run_id=s.work['id'])
    new = retry_failed(s.conn, **args)
    assert new['state'] == 'queued'
    assert retry_failed(s.conn, **args) == new
    assert len(s.plane.requests) == before
    assert MutationJournal(s.conn).get(operation_id,actor=OWNER)['status'] == 'unknown'
    assert s.conn.execute('SELECT status FROM agent_native_progress WHERE operation_id=?',(operation_id,)).fetchone()[0] == 'unknown'
    events = s.conn.execute("SELECT summary FROM agent_native_work_events WHERE run_id=? AND kind='work.notification_unresolved'",(new['id'],)).fetchall()
    assert len(events) == 1 and operation_id in events[0][0]


@pytest.mark.parametrize('change', ['source', 'text', 'pending', 'linked'])
def test_retry_blocks_notifications_without_exact_terminal_provenance(broker, change):
    s = broker
    operation_id = lost_terminal(s)
    fields = {'source':("source_id",'question:other'), 'text':('text','Modified text'),
              'pending':('status','pending'), 'linked':('link_url','https://example.test')}
    field,value = fields[change]
    s.conn.execute(f'UPDATE agent_native_progress SET {field}=? WHERE operation_id=?',(value,operation_id))
    with pytest.raises(ConflictError,match='delivery'):
        retry_failed(s.conn,actor=OWNER,agent_id=s.root['id'],expected_revision=1,expected_run_id=s.work['id'])


def test_cadence_after_owner_recovery_keeps_terminal_notification_unknown(broker):
    from agent_native import cadence
    s = broker
    cadence.configure(s.conn,actor=OWNER,agent_id=s.root['id'],expected_revision=1,interval_seconds=60,enabled=True)
    operation_id = lost_terminal(s)
    assert cadence.queue_due(s.conn,now='2099-01-01T00:00:00+00:00') == []
    new = retry_failed(s.conn,actor=OWNER,agent_id=s.root['id'],expected_revision=1,expected_run_id=s.work['id'])
    s.conn.execute("UPDATE agent_native_work_runs SET state='completed',finished_at='2000-01-01T00:00:00+00:00' WHERE id=?",(new['id'],))
    queued = cadence.queue_due(s.conn,now='2099-01-01T00:00:00+00:00')
    assert len(queued) == 1
    assert MutationJournal(s.conn).get(operation_id,actor=OWNER)['status'] == 'unknown'


def test_cadence_continues_past_pending_normal_limit_notice(broker):
    from agent_native import cadence
    s = broker
    cadence.configure(s.conn,actor=OWNER,agent_id=s.root['id'],expected_revision=1,
                      interval_seconds=60,enabled=True)
    select(s)
    s.conn.execute("UPDATE agent_native_work_runs SET state='limit_reached',stop_requested=1,"
                   "summary='Work reached its time limit.',finished_at='2000-01-01T00:00:00+00:00' WHERE id=?",
                   (s.work['id'],))
    with write_txn(s.conn):
        progress.terminal(s.conn,s.work['id'])
    notice=s.conn.execute("SELECT operation_id,status FROM agent_native_progress WHERE source_id=?",
                          ('terminal:'+s.work['id'],)).fetchone()
    assert tuple(notice)[1]=='pending'

    queued=cadence.queue_due(s.conn,now='2099-01-01T00:00:00+00:00')

    assert len(queued)==1
    event=s.conn.execute("SELECT summary FROM agent_native_work_events WHERE run_id=? "
                         "AND kind='work.notification_unresolved'",(queued[0],)).fetchone()
    assert notice[0] in event[0]


def test_cadence_continues_past_pending_pause_notice_after_owner_resume(broker):
    """A recorded pause is informational once owner resume restored cadence."""
    from agent_native import cadence
    s = broker
    cadence.configure(s.conn, actor=OWNER, agent_id=s.root['id'], expected_revision=1,
                      interval_seconds=60, enabled=True)
    select(s)
    s.conn.execute(
        "UPDATE agent_native_work_runs SET state='paused',stop_requested=1,"
        "summary='Work paused or its execution authority ended.',"
        "finished_at='2000-01-01T00:00:00+00:00' WHERE id=?",
        (s.work['id'],),
    )
    with write_txn(s.conn):
        progress.terminal(s.conn, s.work['id'])
    notice = s.conn.execute(
        "SELECT operation_id,status FROM agent_native_progress WHERE source_id=?",
        ('terminal:' + s.work['id'],),
    ).fetchone()
    assert tuple(notice)[1] == 'pending'

    from agent_native.readiness import automatic_work
    readiness = automatic_work(s.conn, s.root['id'], now='2099-01-01T00:00:00+00:00')
    assert readiness == {
        'state': 'ready',
        'may_start': True,
        'blocker': None,
        'release_condition': None,
        'responsible_actor': None,
    }

    queued = cadence.queue_due(s.conn, now='2099-01-01T00:00:00+00:00')

    assert len(queued) == 1
    event = s.conn.execute(
        "SELECT summary FROM agent_native_work_events WHERE run_id=? "
        "AND kind='work.notification_unresolved'",
        (queued[0],),
    ).fetchone()
    assert notice[0] in event[0]
