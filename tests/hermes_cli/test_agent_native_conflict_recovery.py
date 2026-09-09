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
    assert result['operation']=='cycle.assign'
    assert result['fresh']['kind']=='item'
    assert result['fresh']['resource']['id']==item
    assert result['fresh']['fingerprint']!=seen['fingerprint']
    assert item not in s.plane.memberships
    assert s.run._effect(s.conn,s.planning,stale)==result
    fresh=s.run._effect(s.conn,s.planning,effect(s,'inspect','plane_resource_inspect',{'kind':'item','resource_id':item}))
    assert 'Changed criteria' in fresh['resource']['description_html']
    stale['tool_call_id']='fresh'
    stale['arguments']['arguments']['expected_item_fingerprint']=fresh['fingerprint']
    assert s.run._effect(s.conn,s.planning,stale)['status']=='confirmed'
    assert s.plane.memberships[item]['cycle']==cycle


def test_cycle_assignment_confirms_target_among_existing_cycle_members(broker):
    s=broker
    cycle=s.run._effect(s.conn,s.planning,effect(s,'cycle',arguments={'operation':'cycle.create','arguments':{'name':'Multiple tasks'}}))['resource']['id']
    other=s.run._effect(s.conn,s.planning,effect(s,'other'))['resource']['id']
    for index,item in enumerate((s.setup['discovery_item_id'],other)):
        seen=s.planning.inspect({'kind':'item','resource_id':item})
        result=s.run._effect(s.conn,s.planning,effect(s,f'assign-{index}',arguments={'operation':'cycle.assign','arguments':{'item_id':item,'cycle_id':cycle,'expected_cycle_id':None,'expected_item_fingerprint':seen['fingerprint']}}))
        assert result['status']=='confirmed'
        assert result['resource']['issue']==item
    assert len(s.plane.memberships)==2


def test_already_satisfied_cycle_and_dependency_ignore_stale_item_fingerprint(broker):
    s=broker
    item=s.setup['discovery_item_id']
    dependency=s.run._effect(s.conn,s.planning,effect(s,'dependency'))['resource']['id']
    cycle=s.run._effect(s.conn,s.planning,effect(s,'cycle',arguments={'operation':'cycle.create','arguments':{'name':'Current work'}}))['resource']['id']
    seen=s.planning.inspect({'kind':'item','resource_id':item})
    assign={'operation':'cycle.assign','arguments':{'item_id':item,'cycle_id':cycle,'expected_cycle_id':None,'expected_item_fingerprint':seen['fingerprint']}}
    link={'operation':'dependency.add','arguments':{'item_id':item,'dependency_id':dependency,'expected_fingerprint':seen['fingerprint']}}
    assert s.run._effect(s.conn,s.planning,effect(s,'assign',arguments=assign))['status']=='confirmed'
    fresh=s.planning.inspect({'kind':'item','resource_id':item})
    link['arguments']['expected_fingerprint']=fresh['fingerprint']
    assert s.run._effect(s.conn,s.planning,effect(s,'link',arguments=link))['status']=='confirmed'
    # Plane changes unrelated metadata after both relationships are already true.
    s.plane.items[item]['description_html']='<p>New criteria</p>'
    assign['arguments']['expected_item_fingerprint']=seen['fingerprint']
    link['arguments']['expected_fingerprint']=seen['fingerprint']
    assert s.run._effect(s.conn,s.planning,effect(s,'assign-again',arguments=assign))['status']=='confirmed'
    assert s.run._effect(s.conn,s.planning,effect(s,'link-again',arguments=link))['status']=='confirmed'


def test_invalid_plane_operation_returns_actionable_tool_result(broker):
    s=broker
    result=s.run._effect(s.conn,s.planning,effect(s,'invalid',arguments={
        'operation':'cycle.assign',
        'arguments':{'item_id':s.setup['discovery_item_id'],'cycle_id':'not-a-cycle'},
    }))
    assert result=={
        'status':'invalid_arguments',
        'operation':'cycle.assign',
        'write_attempted':False,
        'message':'cycle.assign arguments do not match the tool contract. Review its required fields and use IDs and fingerprints from current Plane observations.',
    }
    events=s.conn.execute("SELECT summary FROM agent_native_work_events WHERE run_id=?",(s.run.work['id'],)).fetchall()
    assert any(row[0]=='Plane rejected invalid cycle.assign arguments before execution.' for row in events)
