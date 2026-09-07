"""Owner recovery preserves attempts and never replays uncertain external effects."""
import pytest
from agent_native.identity import OWNER, ConflictError
from tests.hermes_cli.test_agent_native_work_effects import broker  # noqa: F401


def test_failed_work_retry_creates_one_new_session_and_preserves_failure(broker):
    from agent_native.work_retry import retry_failed
    s = broker
    s.conn.execute("UPDATE agent_native_work_runs SET state='failed',error='tool rejected' WHERE id=?", (s.work['id'],))
    args = dict(actor=OWNER, agent_id=s.root['id'], expected_revision=1, expected_run_id=s.work['id'])
    new = retry_failed(s.conn, **args)
    assert new['id'] != s.work['id'] and new['session_id'] != s.work['session_id']
    assert new['state'] == 'queued' and new['limits'] == s.work['limits']
    assert retry_failed(s.conn, **args)['id'] == new['id']
    assert tuple(s.conn.execute('SELECT state,error FROM agent_native_work_runs WHERE id=?', (s.work['id'],)).fetchone()) == ('failed', 'tool rejected')
    assert s.conn.execute('SELECT count(*) FROM agent_native_work_runs').fetchone()[0] == 2


@pytest.mark.parametrize('state', ['unknown', 'paused', 'running', 'completed'])
def test_retry_refuses_non_failed_work(broker, state):
    from agent_native.work_retry import retry_failed
    s = broker
    s.conn.execute('UPDATE agent_native_work_runs SET state=? WHERE id=?', (state, s.work['id']))
    with pytest.raises(ConflictError):
        retry_failed(s.conn, actor=OWNER, agent_id=s.root['id'], expected_revision=1, expected_run_id=s.work['id'])
    assert s.conn.execute('SELECT count(*) FROM agent_native_work_runs').fetchone()[0] == 1


def test_retry_rejects_unresolved_progress_and_changed_authority(broker):
    from agent_native.work_retry import retry_failed
    s = broker
    s.conn.execute("UPDATE agent_native_work_runs SET state='failed' WHERE id=?", (s.work['id'],))
    args = dict(agent_id=s.root['id'], expected_revision=1, expected_run_id=s.work['id'])
    with pytest.raises(PermissionError):
        retry_failed(s.conn, actor='owner', **args)
    s.conn.execute("INSERT INTO agent_native_progress(operation_id,source_id,agent_id,run_id,item_id,summary,text,status,created_at) VALUES('pending','pending',?,?,?,'update','update','pending','now')", (s.root['id'], s.work['id'], s.setup['discovery_item_id']))
    with pytest.raises(ConflictError, match='delivery'):
        retry_failed(s.conn, actor=OWNER, **args)
    s.conn.execute('DELETE FROM agent_native_progress')
    s.conn.execute('UPDATE agent_native_agents SET soul_revision=2 WHERE id=?', (s.root['id'],))
    with pytest.raises(ConflictError, match='Purpose'):
        retry_failed(s.conn, actor=OWNER, **args)


def test_retry_blocks_unsettled_mutation_and_removed_agent(broker):
    from agent_native.work_retry import retry_failed
    from agent_native.identity import remove_root
    from tests.hermes_cli.test_agent_native_work_effects import effect
    s = broker
    s.run._effect(s.conn, s.planning, effect(s, 'create-before-failure'))
    s.conn.execute("UPDATE agent_native_plane_mutations SET status='unknown' WHERE agent_id=?", (s.root['id'],))
    s.conn.execute("UPDATE agent_native_work_runs SET state='failed' WHERE id=?", (s.work['id'],))
    args = dict(actor=OWNER, agent_id=s.root['id'], expected_revision=1, expected_run_id=s.work['id'])
    with pytest.raises(ConflictError, match='delivery'):
        retry_failed(s.conn, **args)
    s.conn.execute("UPDATE agent_native_plane_mutations SET status='confirmed' WHERE agent_id=?", (s.root['id'],))
    remove_root(s.conn, actor=OWNER, agent_id=s.root['id'])
    with pytest.raises(ConflictError, match='removed'):
        retry_failed(s.conn, **args)
    assert s.conn.execute('SELECT count(*) FROM agent_native_work_runs').fetchone()[0] == 1
