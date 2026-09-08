"""Whole-purpose judgments remain separate from attempt and assignment results."""
import pytest

from tests.hermes_cli.test_agent_native_work_effects import broker, effect  # noqa: F401


def test_worker_records_durable_whole_purpose_evaluation(broker):
    s=broker
    evaluation=s.run._effect(s.conn,s.planning,effect(s,'purpose-one','purpose_evaluate',{
        'judgment':'continue','evidence':['The first setting chapter is saved.'],
        'remaining_obligations':['Complete geography and cultures.'],
        'uncertainty':'None material.','next_action':'Draft the geography chapter.','question_id':None}))
    assert evaluation['purpose']==s.root['purpose']
    assert evaluation['soul_revision']==1
    assert evaluation['judgment']=='continue'
    assert evaluation['remaining_obligations']==['Complete geography and cultures.']
    assert s.run._effect(s.conn,s.planning,effect(s,'purpose-one','purpose_evaluate',{
        'judgment':'continue','evidence':['The first setting chapter is saved.'],
        'remaining_obligations':['Complete geography and cultures.'],
        'uncertainty':'None material.','next_action':'Draft the geography chapter.','question_id':None}))==evaluation


def test_retirement_candidate_requires_no_remaining_obligations(broker):
    s=broker
    with pytest.raises(ValueError,match='remaining obligations'):
        s.run._effect(s.conn,s.planning,effect(s,'purpose-retire','purpose_evaluate',{
            'judgment':'retire_candidate','evidence':['One output exists.'],
            'remaining_obligations':['Owner review remains.'],'uncertainty':None,
            'next_action':'Retire.','question_id':None}))


def test_clarification_blocks_cadence_until_the_linked_question_is_answered(broker):
    from agent_native import cadence, questions
    from agent_native.identity import OWNER
    from tests.hermes_cli.test_agent_native_questions import ask
    from tests.hermes_cli.test_agent_native_work_focus import select
    s=broker
    select(s); question=ask(s)
    cadence.configure(s.conn,actor=OWNER,agent_id=s.root['id'],expected_revision=1,
                      interval_seconds=1,enabled=True)
    s.run._effect(s.conn,s.planning,effect(s,'purpose-clarify','purpose_evaluate',{
        'judgment':'clarify','evidence':['Requirements leave the ending open.'],
        'remaining_obligations':['Finish the ending.'],'uncertainty':'Owner preference is required.',
        'next_action':'Use the owner answer.','question_id':question['id']}))
    s.conn.execute("UPDATE agent_native_work_runs SET state='completed',finished_at='2000-01-01T00:00:00+00:00' WHERE id=?",(s.work['id'],))
    assert cadence.queue_due(s.conn,now='2099-01-01T00:00:00+00:00')==[]
    questions.answer(s.conn,actor=OWNER,agent_id=s.root['id'],question_id=question['id'],
                     expected_revision=1,answer='Make it hopeful.')
    assert len(cadence.queue_due(s.conn,now='2099-01-01T00:00:01+00:00'))==1
