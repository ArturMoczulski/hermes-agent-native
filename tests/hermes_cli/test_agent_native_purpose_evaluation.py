"""Whole-purpose judgments remain separate from attempt and assignment results."""
import pytest

from tests.hermes_cli.test_agent_native_work_effects import broker, effect  # noqa: F401


def test_worker_records_durable_whole_purpose_evaluation(broker):
    s=broker
    evaluation=s.run._effect(s.conn,s.planning,effect(s,'purpose-one','purpose_evaluate',{
        'judgment':'continue','evidence':['The first setting chapter is saved.'],
        'remaining_obligations':['Complete geography and cultures.'],
        'uncertainty':'None material.','next_action':'Draft the geography chapter.'}))
    assert evaluation['purpose']==s.root['purpose']
    assert evaluation['soul_revision']==1
    assert evaluation['judgment']=='continue'
    assert evaluation['remaining_obligations']==['Complete geography and cultures.']
    assert s.run._effect(s.conn,s.planning,effect(s,'purpose-one','purpose_evaluate',{
        'judgment':'continue','evidence':['The first setting chapter is saved.'],
        'remaining_obligations':['Complete geography and cultures.'],
        'uncertainty':'None material.','next_action':'Draft the geography chapter.'}))==evaluation


def test_retirement_candidate_requires_no_remaining_obligations(broker):
    s=broker
    with pytest.raises(ValueError,match='remaining obligations'):
        s.run._effect(s.conn,s.planning,effect(s,'purpose-retire','purpose_evaluate',{
            'judgment':'retire_candidate','evidence':['One output exists.'],
            'remaining_obligations':['Owner review remains.'],'uncertainty':None,
            'next_action':'Retire.'}))
