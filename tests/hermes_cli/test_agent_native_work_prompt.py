"""Focused contract checks for managed-work instructions."""

from agent_native.work_service import _initial_context
from agent_native.work_service import _authority_revoked


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


def test_scoped_operation_denial_does_not_revoke_the_run():
    assert _authority_revoked(lambda: None, PermissionError('Wrong work item')) is False
    assert _authority_revoked(lambda: (_ for _ in ()).throw(PermissionError('Run stopped')),
                              PermissionError('Denied during revoked run')) is True
    assert _authority_revoked(lambda: (_ for _ in ()).throw(AssertionError('must not run')),
                              ValueError('Malformed arguments')) is False


def test_managed_prompt_explains_how_to_bootstrap_an_empty_project_workspace():
    prompt = _initial_context({}, {})

    assert 'A granted project workspace may initially be empty' in prompt
    assert 'expected_sha256="missing"' in prompt
    assert 'rg --files' in prompt
    assert 'does not mean the workspace grant is absent' in prompt
