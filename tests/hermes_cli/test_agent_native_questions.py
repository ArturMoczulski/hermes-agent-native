import pytest
from agent_native.identity import OWNER, ConflictError
from tests.hermes_cli.test_agent_native_work_effects import broker, effect  # noqa: F401
from tests.hermes_cli.test_agent_native_work_focus import select


def ask(s, call='ask'):
    return s.run._effect(s.conn,s.planning,effect(s,call,'work_question',{
        'item_id':s.setup['discovery_item_id'],'topic':'ending','question':'Should the ending be hopeful?'}))


def test_question_deduplicates_and_answer_does_not_resume_owner_paused_work(broker):
    from agent_native import questions
    s=broker
    select(s)
    q=ask(s)
    assert ask(s,'ask-again')['id']==q['id']
    assert q['answer'] is None
    s.run.stop()
    args=dict(actor=OWNER,agent_id=s.root['id'],question_id=q['id'],expected_revision=1,answer='Yes, hopeful.')
    assert questions.answer(s.conn,**args)['answer']=='Yes, hopeful.'
    assert questions.answer(s.conn,**args)['answer']=='Yes, hopeful.'
    with pytest.raises(ConflictError):
        questions.answer(s.conn,**{**args,'answer':'No'})
    assert s.conn.execute('SELECT state FROM agent_native_work_runs WHERE id=?',(s.work['id'],)).fetchone()[0]=='paused'
    with pytest.raises(PermissionError):
        s.run._effect(s.conn,s.planning,effect(s,'read-paused','work_question',{'question_id':q['id']}))


def test_question_answer_is_read_only_for_current_item_criteria(broker):
    from agent_native import questions
    s=broker
    select(s)
    q=ask(s)
    questions.answer(s.conn,actor=OWNER,agent_id=s.root['id'],question_id=q['id'],expected_revision=1,answer='Yes')
    read=lambda call: s.run._effect(s.conn,s.planning,effect(s,call,'work_question',{'question_id':q['id']}))
    assert read('read')['answer']=='Yes'
    s.plane.items[s.setup['discovery_item_id']]['description_html']='<p>Changed requirements</p>'
    stale=read('changed-read')
    assert stale['applicable'] is False and stale['answer'] is None
    assert stale['has_recorded_answer'] is True
    assert questions.recent(s.conn,s.root['id'])[0]['answer']=='Yes'
    assert read('changed-read-again')['applicable'] is False


def test_question_owner_scope_and_chat_share_the_same_answer(broker):
    from agent_native import questions, identity
    from agent_native.chat import issue_binding
    from agent_native.chat_context import snapshot
    s=broker
    select(s)
    q=ask(s)
    args=dict(actor=OWNER,agent_id=s.root['id'],question_id=q['id'],expected_revision=1,answer='A hopeful ending')
    with pytest.raises(PermissionError):
        questions.answer(s.conn,**{**args,'actor':'owner'})
    with pytest.raises(KeyError):
        questions.answer(s.conn,**{**args,'agent_id':'another-agent'})
    questions.answer(s.conn,**args)
    binding=issue_binding(actor=OWNER,agent_id=s.root['id'],db_path=s.db_path,storage_root=s.home/'agents')
    observed=snapshot(binding)['questions'][0]
    assert observed['id']==q['id'] and observed['answer']==args['answer']
    s.run.stop()
    identity.revise_soul(s.conn,actor=OWNER,agent_id=s.root['id'],expected_revision=1,purpose='New purpose')
    assert questions.recent(s.conn,s.root['id'])[0]['applicable'] is False
    with pytest.raises(ConflictError):
        questions.answer(s.conn,**{**args,'expected_revision':2})


from tests.hermes_cli.test_agent_native_chat_api import client  # noqa: E402,F401


def test_question_api_requires_owner_and_scopes_missing_records(client):
    c,token=client
    root=c.post('/api/agent-native/agents',json={'request_id':'question-api','name':'Writer','purpose':'Write'}).json()
    path='/api/agent-native/agents/'+root['id']+'/questions'
    assert c.get(path).json()==[]
    args={'expected_revision':1,'answer':'Yes'}
    assert c.post(path+'/missing/answer',json=args).status_code==404
    c.headers.pop('X-Hermes-Session-Token')
    assert c.get(path).status_code in (401,403)
    assert c.post(path+'/missing/answer',json=args).status_code in (401,403)


def test_question_is_posted_once_in_plane_even_when_acknowledgement_is_lost(broker):
    from agent_native import progress
    s=broker
    select(s)
    progress.change_settings(s.conn,actor=OWNER,agent_id=s.root['id'],verbosity='concise',expected_revision=1)
    path=f"/api/v1/workspaces/{s.setup['workspace_slug']}/projects/{s.setup['project_id']}/work-items/{s.setup['discovery_item_id']}/comments/"
    s.plane.lose.add(('POST',path))
    q=ask(s)
    comments=[c for c in s.plane.comments.values() if q['id'] in c['comment_html']]
    assert len(comments)==1
    assert q['question'] in comments[0]['comment_html']
    assert ask(s,'repeat-question')['id']==q['id']
    assert len([c for c in s.plane.comments.values() if q['id'] in c['comment_html']])==1
    report=s.conn.execute('SELECT status FROM agent_native_progress WHERE source_id=?',('question:'+q['id'],)).fetchone()
    assert report[0]=='unknown'


def test_question_and_plane_intent_commit_together(broker):
    import sqlite3
    s=broker
    select(s)
    s.conn.execute("CREATE TRIGGER reject_question_report BEFORE INSERT ON agent_native_progress WHEN NEW.source_id LIKE 'question:%' BEGIN SELECT RAISE(ABORT,'report unavailable'); END")
    before=len(s.plane.comments)
    with pytest.raises(sqlite3.IntegrityError):
        ask(s)
    assert s.conn.execute('SELECT count(*) FROM agent_native_questions').fetchone()[0]==0
    assert len(s.plane.comments)==before
