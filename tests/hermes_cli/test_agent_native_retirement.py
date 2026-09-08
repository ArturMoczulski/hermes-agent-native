"""Guarded agent-initiated retirement through managed work authority."""
import pytest

from agent_native.identity import OWNER, get_root, list_roots
from tests.hermes_cli.test_agent_native_purpose_evaluation import broker, effect  # noqa: F401


def evaluate(s, *, uncertainty=None):
    return s.run._effect(s.conn, s.planning, effect(s, 'retire-evaluation', 'purpose_evaluate', {
        'judgment': 'retire_candidate',
        'evidence': ['The protected purpose and its acceptance criteria are fulfilled.'],
        'remaining_obligations': [],
        'uncertainty': uncertainty,
        'next_action': 'Retire through the framework lifecycle operation.',
        'question_id': None,
    }))


def retire(s, evaluation):
    return s.run._effect(s.conn, s.planning, effect(s, 'retire-operation', 'purpose_retire', {
        'evaluation_id': evaluation['id'],
    }))


def test_agent_retires_from_current_clear_evaluation(broker):
    s = broker
    result = retire(s, evaluate(s))

    assert result['status'] == 'retired'
    assert result['evaluation_id']
    root = get_root(s.conn, actor=OWNER, agent_id=s.root['id'])
    assert root['removed_at'] is None
    assert root['retirement']['source'] == 'agent'
    assert root['cadence']['enabled'] is False
    assert all(agent['id'] != s.root['id'] for agent in list_roots(s.conn, actor=OWNER))
    retired = list_roots(s.conn, actor=OWNER, lifecycle='retired')
    assert [agent['id'] for agent in retired] == [s.root['id']]

    with pytest.raises(PermissionError):
        s.run._effect(s.conn, s.planning, effect(s, 'after-retirement', 'purpose_evaluate', {
            'judgment': 'continue', 'evidence': [], 'remaining_obligations': [],
            'uncertainty': None, 'next_action': 'Continue.', 'question_id': None,
        }))


def test_retirement_rejects_unresolved_uncertainty_without_ending_agent(broker):
    s = broker
    evaluation = evaluate(s, uncertainty='The owner may expect another deliverable.')

    with pytest.raises(ValueError, match='uncertainty'):
        retire(s, evaluation)

    assert get_root(s.conn, actor=OWNER, agent_id=s.root['id'])['removed_at'] is None


def test_retirement_rejects_an_unanswered_question(broker):
    from tests.hermes_cli.test_agent_native_questions import ask
    from tests.hermes_cli.test_agent_native_work_focus import select
    s = broker
    select(s)
    ask(s)

    with pytest.raises(ValueError, match='unanswered question'):
        retire(s, evaluate(s))

    assert get_root(s.conn, actor=OWNER, agent_id=s.root['id'])['removed_at'] is None


def test_retirement_rejects_a_required_owner_review(broker):
    from tests.hermes_cli.test_agent_native_results import record
    s = broker
    s.conn.execute(
        'UPDATE agent_native_autonomy_settings SET require_owner_review=1 WHERE agent_id=?',
        (s.root['id'],),
    )
    s.conn.execute(
        'UPDATE agent_native_autonomy_attempts SET require_owner_review=1 WHERE run_id=?',
        (s.work['id'],),
    )
    output = s.run._effect(s.conn, s.planning, effect(s, 'reviewed-output', 'output_publish', {
        'title': 'Final deliverable', 'content': 'Complete.', 'format': 'markdown',
        'item_id': s.setup['discovery_item_id'],
    }))
    record(s, 'reviewed-result', outcome='submitted', outputs=[{
        'output_id': output['output_id'], 'version': output['version'],
    }])

    with pytest.raises(ValueError, match='required owner review'):
        retire(s, evaluate(s))

    assert get_root(s.conn, actor=OWNER, agent_id=s.root['id'])['removed_at'] is None


def test_retirement_rejects_an_unresolved_effect_other_than_its_own(broker):
    s = broker
    evaluation = evaluate(s)
    s.conn.execute(
        'INSERT INTO agent_native_work_effects(run_id,call_id,operation_id,fingerprint) VALUES(?,?,?,?)',
        (s.work['id'], 'older-effect', 'older-operation', 'fingerprint'),
    )

    with pytest.raises(ValueError, match='unresolved effect'):
        retire(s, evaluation)

    assert get_root(s.conn, actor=OWNER, agent_id=s.root['id'])['removed_at'] is None
