"""Focused contract checks for managed-work instructions."""

from agent_native.work_service import _initial_context


def test_planning_records_stay_in_plane_and_outputs_are_purpose_deliverables():
    prompt = _initial_context({'project': 'example'}, {'item.create': {'name': 'string'}})

    assert 'task descriptions, acceptance criteria, dependencies, planning notes and progress updates in Plane' in prompt
    assert 'They are not saved outputs unless the purpose or selected assignment explicitly requests a planning document' in prompt
    assert 'Use output_publish only for the actual purpose-level work product' in prompt
    assert 'A confirmed planning change is a valid result with an empty outputs list' in prompt
    assert 'Save any produced text or Markdown' not in prompt


def test_high_autonomy_does_not_invent_owner_acceptance_gate():
    from agent_native.autonomy import policy
    prompt = _initial_context({}, {}, policy(5))
    assert 'Continuously pursue the purpose across outputs and milestones' in prompt
    assert 'do not invent an owner-acceptance gate' in prompt
    assert 'Leave the task nonterminal for owner review' not in prompt
