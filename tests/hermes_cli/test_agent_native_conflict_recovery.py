from tests.hermes_cli.test_agent_native_work_effects import broker, effect  # noqa: F401


def test_rejected_conflict_is_retained_and_fresh_inspection_can_continue(broker):
    s=broker
    item=s.setup['discovery_item_id']
    cycle=s.run._effect(s.conn,s.planning,effect(s,'cycle',arguments={'operation':'cycle.create','arguments':{'name':'First cycle'}}))['resource']['id']
    seen=s.planning.inspect({'kind':'item','resource_id':item})
    s.plane.items[item]['description_html']='<p class="editor-paragraph-block" data-id="new">Changed criteria</p>'
    stale=effect(s,'stale',arguments={'operation':'cycle.assign','arguments':{'item_id':item,'cycle_id':cycle,'expected_cycle_id':None,'expected_item_fingerprint':seen['fingerprint']}})
    result=s.run._effect(s.conn,s.planning,stale)
    assert result['status']=='conflict' and result['write_attempted'] is False
    assert item not in s.plane.memberships
    assert s.run._effect(s.conn,s.planning,stale)==result
    fresh=s.run._effect(s.conn,s.planning,effect(s,'inspect','plane_resource_inspect',{'kind':'item','resource_id':item}))
    assert 'Changed criteria' in fresh['resource']['description_html']
    stale['tool_call_id']='fresh'
    stale['arguments']['arguments']['expected_item_fingerprint']=fresh['fingerprint']
    assert s.run._effect(s.conn,s.planning,stale)['status']=='confirmed'
    assert s.plane.memberships[item]['cycle']==cycle
