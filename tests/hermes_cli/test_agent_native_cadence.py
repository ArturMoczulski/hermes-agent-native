import pytest
from agent_native.identity import OWNER
from tests.hermes_cli.test_agent_native_work_effects import broker  # noqa: F401


def test_due_cadence_retains_attempts_and_never_overlaps_or_resumes_pause(broker):
    from agent_native import cadence, work_state
    s=broker
    cadence.configure(s.conn,actor=OWNER,agent_id=s.root['id'],expected_revision=1,interval_seconds=60,enabled=True)
    assert cadence.queue_due(s.conn,now='2099-01-01T00:00:00+00:00')==[]
    s.conn.execute("UPDATE agent_native_work_runs SET state='completed',finished_at='2000-01-01T00:00:00+00:00' WHERE id=?",(s.work['id'],))
    queued=cadence.queue_due(s.conn,now='2099-01-01T00:00:00+00:00')
    assert len(queued)==1 and queued[0]!=s.work['id']
    assert cadence.queue_due(s.conn,now='2099-01-02T00:00:00+00:00')==[]
    assert work_state.read_work(s.conn,s.root['id'])['id']==queued[0]
    assert s.conn.execute('SELECT count(*) FROM agent_native_work_runs WHERE agent_id=?',(s.root['id'],)).fetchone()[0]==2
    work_state.request_pause(s.conn,actor=OWNER,agent_id=s.root['id'])
    assert cadence.queue_due(s.conn,now='2099-01-03T00:00:00+00:00')==[]
    assert cadence.read(s.conn,s.root['id'])['enabled'] is False


def test_cadence_requires_owner_and_stops_on_unknown_or_changed_purpose(broker):
    from agent_native import cadence
    s=broker
    args=dict(agent_id=s.root['id'],expected_revision=1,interval_seconds=60,enabled=True)
    with pytest.raises(PermissionError):
        cadence.configure(s.conn,actor='owner',**args)
    cadence.configure(s.conn,actor=OWNER,**args)
    s.conn.execute("UPDATE agent_native_work_runs SET state='unknown' WHERE id=?",(s.work['id'],))
    assert cadence.queue_due(s.conn,now='2099-01-01T00:00:00+00:00')==[]
    s.conn.execute("UPDATE agent_native_work_runs SET state='completed' WHERE id=?",(s.work['id'],))
    s.conn.execute('UPDATE agent_native_agents SET soul_revision=2 WHERE id=?',(s.root['id'],))
    assert cadence.queue_due(s.conn,now='2099-01-01T00:00:00+00:00')==[]


def test_legacy_attempt_migration_preserves_foreign_key_history():
    import sqlite3
    from agent_native.cadence import migrate_runs
    c=sqlite3.connect(':memory:',isolation_level=None)
    c.execute('PRAGMA foreign_keys=ON')
    c.execute('CREATE TABLE agent_native_work_runs(id TEXT PRIMARY KEY,agent_id TEXT NOT NULL UNIQUE,activation_id TEXT NOT NULL UNIQUE)')
    c.execute('CREATE TABLE history(run_id TEXT REFERENCES agent_native_work_runs(id),summary TEXT)')
    c.execute("INSERT INTO agent_native_work_runs VALUES('first','agent','activation')")
    c.execute("INSERT INTO history VALUES('first','saved output')")
    migrate_runs(c)
    migrate_runs(c)
    c.execute("INSERT INTO agent_native_work_runs VALUES('second','agent','activation')")
    assert c.execute('SELECT * FROM history').fetchall()==[('first','saved output')]
    assert c.execute('PRAGMA foreign_key_check').fetchall()==[]
    assert c.execute('PRAGMA foreign_keys').fetchone()[0]==1


def test_service_restart_holds_interrupted_attempt_instead_of_replaying(broker):
    from agent_native import cadence
    from agent_native.work_service import WorkService
    from hermes_cli.kanban_db_connect import connect_closing
    s=broker
    cadence.configure(s.conn,actor=OWNER,agent_id=s.root['id'],expected_revision=1,interval_seconds=1,enabled=True)
    service=WorkService(s.db_path,s.home).start()
    try:
        with connect_closing(s.db_path) as reopened:
            assert reopened.execute('SELECT state FROM agent_native_work_runs WHERE id=?',(s.work['id'],)).fetchone()[0]=='unknown'
            assert cadence.queue_due(reopened,now='2099-01-01T00:00:00+00:00')==[]
            assert reopened.execute('SELECT count(*) FROM agent_native_work_runs').fetchone()[0]==1
    finally:
        service.stop()
