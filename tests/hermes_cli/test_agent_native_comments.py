from uuid import uuid4
import pytest
from tests.hermes_cli.test_agent_native_work_effects import broker, effect  # noqa: F401
from tests.hermes_cli.test_agent_native_work_focus import select


def invoke(s, call, args):
    return s.run._effect(s.conn,s.planning,effect(s,call,'work_comments',args))


def external(s):
    c={'id':str(uuid4()),'workspace':s.setup['workspace_id'],'project':s.setup['project_id'],
       'issue':s.setup['discovery_item_id'],'actor':s.plane.user,'comment_html':'<p>Please make the ending hopeful.</p>'}
    s.plane.comments[c['id']]=c
    return c


def test_comments_review_reply_deduplicates_and_detects_edits(broker):
    s=broker
    select(s)
    c=external(s)
    args={'item_id':c['issue']}
    pending=invoke(s,'read',args)['pending']
    assert len(pending)==1 and pending[0]['comment_id']==c['id']
    reply={**args,'review_id':pending[0]['id'],'response':'I will revise the ending.','reply':True}
    assert invoke(s,'reply',reply)['status']=='confirmed'
    assert invoke(s,'reply-again',reply)['status']=='confirmed'
    assert invoke(s,'read-again',args)['pending']==[]
    assert len([v for v in s.plane.comments.values() if 'I will revise' in v['comment_html']])==1
    c['comment_html']='<p>Actually, keep the ending ambiguous.</p>'
    updated=invoke(s,'edited',args)['pending']
    assert len(updated)==1 and updated[0]['id']!=pending[0]['id']
    s.run.stop()
    with pytest.raises(PermissionError):
        invoke(s,'paused',args)


def test_comment_reply_unknown_is_not_resent(broker):
    s=broker
    select(s)
    c=external(s)
    args={'item_id':c['issue']}
    r=invoke(s,'read',args)['pending'][0]
    path=f"/api/v1/workspaces/{s.setup['workspace_slug']}/projects/{s.setup['project_id']}/work-items/{c['issue']}/comments/"
    s.plane.lose.add(('POST',path))
    reply={**args,'review_id':r['id'],'response':'I will consider this feedback.','reply':True}
    assert invoke(s,'reply',reply)['status']=='unknown'
    assert invoke(s,'repeat',reply)['status']=='unknown'
    assert len([v for v in s.plane.comments.values() if 'consider this' in v['comment_html']])==1
    assert invoke(s,'read-again',args)['pending']==[]


def test_review_rejects_stale_comment_and_can_record_no_reply(broker):
    from agent_native.identity import ConflictError
    s=broker
    select(s)
    c=external(s)
    args={'item_id':c['issue']}
    r=invoke(s,'read',args)['pending'][0]
    c['comment_html']='<p>Additional context only.</p>'
    stale=invoke(s,'stale',{**args,'review_id':r['id'],'response':'Thanks','reply':True})
    assert stale['status']=='rejected' and stale['error']==ConflictError.__name__
    r=invoke(s,'fresh',args)['pending'][0]
    before=len(s.plane.comments)
    assert invoke(s,'no-reply',{**args,'review_id':r['id'],'response':'Informational context retained; no reply needed.','reply':False})['status']=='reviewed_without_reply'
    assert len(s.plane.comments)==before
    assert invoke(s,'again',args)['pending']==[]
    from agent_native.plane_reads import PlaneReadError
    with pytest.raises(PlaneReadError):
        invoke(s,'wrong-item',{'item_id':str(uuid4())})


def test_other_agent_shared_account_is_reviewed_but_reply_loops_are_blocked(broker):
    from agent_native.identity import OWNER, create_root
    from agent_native.plane_access import grant_project
    from agent_native.plane_write_access import WriteAuthority, grant_writes
    from agent_native.plane_writes import PlaneWrites
    from agent_native.plane_write_journal import MutationJournal
    s=broker
    select(s)
    other=create_root(s.conn,actor=OWNER,request_id='other-commenter',name='Reviewer',purpose='Review')
    grant=grant_project(s.conn,actor=OWNER,agent_id=other['id'],workspace_slug=s.setup['workspace_slug'],workspace_id=s.setup['workspace_id'],project_id=s.setup['project_id'])
    grant_writes(s.conn,actor=OWNER,binding_id=grant['id'],operations={'comment.create'})
    authority=WriteAuthority(s.conn)
    context=authority.issue_context(actor=OWNER,binding_id=grant['id'])
    writer=PlaneWrites(authority,MutationJournal(s.conn),base_url=s.plane.config['base_url'],api_key=s.plane.config['api_key'],service_user_id=s.plane.user)
    operation=str(uuid4())
    writer.execute(context,operation,'comment.create',{'item_id':s.setup['discovery_item_id'],'text':'Consider a shorter draft.'})
    args={'item_id':s.setup['discovery_item_id']}
    pending=invoke(s,'read-other',args)['pending']
    assert len(pending)==1 and pending[0]['origin_agent_id']==other['id']
    # A protected reply intent identifies automation, not its shared actor or text.
    s.conn.execute("INSERT INTO agent_native_progress(operation_id,source_id,agent_id,run_id,item_id,summary,text,status,created_at) VALUES(?,?,?,?,?,?,?,'confirmed','now')",(operation,'comment-reply:other',other['id'],s.work['id'],args['item_id'],'reply','reply'))
    loop=invoke(s,'loop',{**args,'review_id':pending[0]['id'],'response':'Replying to your reply','reply':True})
    assert loop['status']=='rejected' and loop['error']=='PermissionError'


def test_related_item_discussion_does_not_change_current_assignment(broker):
    from agent_native.work_focus import read_focus
    s=broker
    related=external(s)
    new=s.run._effect(s.conn,s.planning,effect(s,'new-task'))['resource']['id']
    s.run._effect(s.conn,s.planning,effect(s,'select-new','work_item_select',{'item_id':new}))
    pending=invoke(s,'related',{'item_id':related['issue']})['pending']
    assert pending[0]['comment_id']==related['id']
    assert invoke(s,'reply-related',{'item_id':related['issue'],'review_id':pending[0]['id'],'response':'I will use this in the next story.','reply':True})['status']=='confirmed'
    assert read_focus(s.conn,s.work['id'])['item_id']==new
    reply=next(c for c in s.plane.comments.values() if 'I will use this' in c['comment_html'])
    assert reply['issue']==related['issue']


def test_related_discussion_cannot_read_another_project(broker):
    from agent_native.plane_reads import PlaneReadError
    s=broker
    select(s)
    foreign=str(uuid4())
    s.plane.items[foreign]={'id':foreign,'project':str(uuid4())}
    before=len(s.plane.requests)
    with pytest.raises(PlaneReadError):
        invoke(s,'foreign',{'item_id':foreign})
    assert not any('/comments/' in r['path'] for r in s.plane.requests[before:])
    assert s.conn.execute('SELECT count(*) FROM agent_native_comment_reviews').fetchone()[0]==0
