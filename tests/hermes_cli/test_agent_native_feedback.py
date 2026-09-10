import pytest
from agent_native.identity import OWNER, ConflictError
from tests.hermes_cli.test_agent_native_work_effects import broker, effect  # noqa: F401


def test_feedback_receipt_replay_and_worker_handling_preserve_pause(broker):
    from agent_native import feedback
    s = broker
    args = dict(actor=OWNER, agent_id=s.root['id'], expected_revision=1, request_id='owner-feedback-1', text='Use a hopeful ending')
    row = feedback.submit(s.conn, **args)
    assert feedback.submit(s.conn, **args)['id'] == row['id']
    with pytest.raises(ConflictError):
        feedback.submit(s.conn, **{**args, 'text':'Different feedback'})
    offered = s.run._effect(s.conn,s.planning,{**effect(s,'feedback-read','work_feedback'), 'arguments':{}})
    assert offered['pending'][0]['text'] == args['text']
    s.run._effect(s.conn,s.planning,effect(s,'feedback-handle','work_feedback',{'feedback_id':row['id'],'response':'Revised the ending for review.'}))
    assert feedback.recent(s.conn,s.root['id'])[0]['status'] == 'handled'
    assert s.conn.execute("SELECT count(*) FROM agent_native_work_events WHERE kind='work.feedback_received'").fetchone()[0] == 1
    assert s.conn.execute("SELECT count(*) FROM agent_native_work_events WHERE kind='work.feedback_handled'").fetchone()[0] == 1
    s.run.stop()
    later = feedback.submit(s.conn, **{**args,'request_id':'later','text':'Please shorten the next draft'})
    assert later['status'] == 'pending'
    assert s.conn.execute('SELECT state FROM agent_native_work_runs WHERE id=?',(s.work['id'],)).fetchone()[0] == 'paused'
    with pytest.raises(PermissionError):
        s.run._effect(s.conn,s.planning,{**effect(s,'paused-read','work_feedback'), 'arguments':{}})


def test_feedback_requires_owner_and_current_purpose(broker):
    from agent_native import feedback
    s = broker
    args = dict(actor=OWNER,agent_id=s.root['id'],expected_revision=1,request_id='guard',text='A direction')
    with pytest.raises(PermissionError):
        feedback.submit(s.conn,**{**args,'actor':'owner'})
    with pytest.raises(ConflictError):
        feedback.submit(s.conn,**{**args,'expected_revision':2})


def test_feedback_records_revision_request_intent(broker):
    from agent_native import feedback
    s = broker
    row = feedback.submit(s.conn, actor=OWNER, agent_id=s.root['id'], expected_revision=1,
                          request_id='revision-intent', text='Make the map more readable.',
                          intent='revision_request')
    assert row['intent'] == 'revision_request'
    offered = s.run._effect(s.conn, s.planning, {**effect(s, 'revision-intent-read', 'work_feedback'), 'arguments': {}})
    assert offered['pending'][0]['intent'] == 'revision_request'
    with pytest.raises(ValueError):
        feedback.submit(s.conn, actor=OWNER, agent_id=s.root['id'], expected_revision=1,
                        request_id='invalid-intent', text='No.', intent='approval')


from tests.hermes_cli.test_agent_native_chat_api import client  # noqa: E402,F401


def test_feedback_api_requires_owner_and_does_not_start_work(client):
    c, token = client
    root = c.post('/api/agent-native/agents',json={'request_id':'feedback-api','name':'Writer','purpose':'Write drafts'}).json()
    path = '/api/agent-native/agents/'+root['id']+'/feedback'
    data = {'request_id':'direction','expected_revision':1,'text':'Keep it short'}
    assert c.post(path,json=data).status_code == 201
    assert c.post(path,json=data).status_code == 201
    assert len(c.get(path).json()) == 1
    assert c.get('/api/agent-native/agents/'+root['id']).json()['execution'] == 'not_started'
    c.headers.pop('X-Hermes-Session-Token')
    assert c.get(path).status_code in (401,403)
    assert c.post(path,json=data).status_code in (401,403)
