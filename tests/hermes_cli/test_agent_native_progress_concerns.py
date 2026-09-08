"""Repeated unproductive cadence failures suspend once and require owner resume."""
import pytest

from agent_native.identity import OWNER, ConflictError
from tests.hermes_cli.test_agent_native_work_effects import broker  # noqa: F401


def failed_attempts(s, count=3):
    ids=[]
    for index in range(count):
        run_id=s.work['id'] if index==0 else f'failed-{index}'
        if index:
            s.conn.execute(
                "INSERT INTO agent_native_work_runs "
                "(id,agent_id,activation_id,soul_revision,session_id,limits,state,created_at,finished_at) "
                "SELECT ?,agent_id,activation_id,soul_revision,?,limits,'retryable_failure',?,? "
                "FROM agent_native_work_runs WHERE id=?",
                (run_id,f'failed-session-{index}',f'2000-01-0{index+1}T00:00:00+00:00',
                 f'2000-01-0{index+1}T00:00:01+00:00',s.work['id']),
            )
        else:
            s.conn.execute(
                "UPDATE agent_native_work_runs SET state='retryable_failure',"
                "created_at='2000-01-01T00:00:00+00:00',"
                "finished_at='2000-01-01T00:00:01+00:00' WHERE id=?",(run_id,))
        ids.append(run_id)
    return ids


def test_three_unproductive_failures_create_one_concern_and_suspend_cadence(broker):
    from agent_native import cadence
    from agent_native.progress_concerns import list_concerns, resume
    s=broker
    cadence.configure(s.conn,actor=OWNER,agent_id=s.root['id'],expected_revision=1,
                      interval_seconds=60,enabled=True)
    attempts=failed_attempts(s)

    assert cadence.queue_due(s.conn,now='2099-01-01T00:00:00+00:00')==[]
    assert cadence.read(s.conn,s.root['id'])['enabled'] is False
    [concern]=list_concerns(s.conn,s.root['id'])
    assert concern['status']=='open' and concern['attempt_ids']==attempts
    assert '3 consecutive attempts' in concern['summary']
    with pytest.raises(ConflictError,match='progress concern'):
        cadence.configure(s.conn,actor=OWNER,agent_id=s.root['id'],expected_revision=1,
                          interval_seconds=60,enabled=True)
    assert cadence.queue_due(s.conn,now='2099-01-02T00:00:00+00:00')==[]
    assert len(list_concerns(s.conn,s.root['id']))==1

    args=dict(actor=OWNER,agent_id=s.root['id'],concern_id=concern['id'],
              expected_revision=1,request_id='resume-once')
    assert resume(s.conn,**args)['status']=='resolved'
    assert resume(s.conn,**args)['status']=='resolved'
    assert cadence.read(s.conn,s.root['id'])['enabled'] is True
    assert len(cadence.queue_due(s.conn,now='2099-01-03T00:00:00+00:00'))==1
    with pytest.raises(ConflictError,match='already resolved'):
        resume(s.conn,**{**args,'request_id':'different'})


def test_new_result_breaks_the_unproductive_failure_sequence(broker):
    from agent_native import cadence
    from agent_native.progress_concerns import list_concerns
    s=broker
    cadence.configure(s.conn,actor=OWNER,agent_id=s.root['id'],expected_revision=1,
                      interval_seconds=60,enabled=True)
    attempts=failed_attempts(s)
    s.conn.execute(
        'INSERT INTO agent_native_work_results '
        '(id,agent_id,run_id,item_id,call_id,request_sha256,record_json,record_sha256,created_at) '
        'VALUES(?,?,?,?,?,?,?,?,?)',
        ('result',s.root['id'],attempts[1],s.setup['discovery_item_id'],'call',
         'request','{}','record','2000-01-02T00:00:00+00:00'),
    )

    queued=cadence.queue_due(s.conn,now='2099-01-01T00:00:00+00:00')

    assert len(queued)==1
    assert cadence.read(s.conn,s.root['id'])['enabled'] is True
    assert list_concerns(s.conn,s.root['id'])==[]


def test_owner_can_configure_the_per_agent_failure_threshold(broker):
    from agent_native import cadence
    from agent_native.progress_concerns import configure, list_concerns, settings
    s=broker
    assert settings(s.conn,s.root['id'])=={'failure_threshold':3}
    with pytest.raises(PermissionError):
        configure(s.conn,actor='owner',agent_id=s.root['id'],failure_threshold=2)
    with pytest.raises(ValueError):
        configure(s.conn,actor=OWNER,agent_id=s.root['id'],failure_threshold=1)
    assert configure(s.conn,actor=OWNER,agent_id=s.root['id'],failure_threshold=2)=={
        'failure_threshold':2}
    cadence.configure(s.conn,actor=OWNER,agent_id=s.root['id'],expected_revision=1,
                      interval_seconds=60,enabled=True)
    attempts=failed_attempts(s,count=2)

    assert cadence.queue_due(s.conn,now='2099-01-01T00:00:00+00:00')==[]
    assert list_concerns(s.conn,s.root['id'])[0]['attempt_ids']==attempts
