from tests.hermes_cli.test_agent_native_work_effects import broker, effect  # noqa: F401


def test_cycle_assignment_accepts_timestamp_only_change_after_item_update(broker):
    s=broker
    item=s.setup['discovery_item_id']
    cycle=s.run._effect(s.conn,s.planning,effect(s,'cycle',arguments={'operation':'cycle.create','arguments':{'name':'Deliver the brief'}}))['resource']['id']
    seen=s.planning.inspect({'kind':'item','resource_id':item})
    changed=s.run._effect(s.conn,s.planning,effect(s,'rename',arguments={'operation':'item.update','arguments':{'item_id':item,'name':'Deliver brief','expected_fingerprint':seen['fingerprint']}}))
    s.plane.items[item]['updated_at']='2099-01-01T00:00:00Z'
    result=s.run._effect(s.conn,s.planning,effect(s,'assign',arguments={'operation':'cycle.assign','arguments':{'item_id':item,'cycle_id':cycle,'expected_cycle_id':None,'expected_item_fingerprint':changed['fingerprint']}}))
    assert result['status']=='confirmed'
    assert s.plane.memberships[item]['cycle']==cycle


def test_cycle_assignment_still_rejects_changed_task_content(broker):
    s=broker
    item=s.setup['discovery_item_id']
    cycle=s.run._effect(s.conn,s.planning,effect(s,'cycle',arguments={'operation':'cycle.create','arguments':{'name':'Deliver the brief'}}))['resource']['id']
    seen=s.planning.inspect({'kind':'item','resource_id':item})
    s.plane.items[item]['description_html']='<p>New acceptance criteria from owner</p>'
    result=s.run._effect(s.conn,s.planning,effect(s,'assign',arguments={'operation':'cycle.assign','arguments':{'item_id':item,'cycle_id':cycle,'expected_cycle_id':None,'expected_item_fingerprint':seen['fingerprint']}}))
    assert result['status']=='conflict'
    assert item not in s.plane.memberships
