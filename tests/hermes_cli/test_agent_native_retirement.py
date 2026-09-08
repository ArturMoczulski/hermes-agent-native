"""Guarded agent-initiated retirement through managed work authority."""
import sqlite3

import pytest

from agent_native.identity import OWNER, get_root, list_roots
from tests.hermes_cli.test_agent_native_purpose_evaluation import broker, effect  # noqa: F401


def test_existing_retirement_records_migrate_to_subtree_provenance():
    from agent_native.retirement import migrate_subtrees
    conn = sqlite3.connect(':memory:')
    conn.execute('PRAGMA foreign_keys=ON')
    conn.executescript('''
        CREATE TABLE agent_native_agents(id TEXT PRIMARY KEY);
        CREATE TABLE agent_native_purpose_evaluations(id TEXT PRIMARY KEY);
        CREATE TABLE agent_native_retirements (
          agent_id TEXT PRIMARY KEY REFERENCES agent_native_agents(id),
          evaluation_id TEXT NOT NULL UNIQUE REFERENCES agent_native_purpose_evaluations(id),
          source TEXT NOT NULL CHECK(source IN ('agent','parent','owner')),
          retired_at TEXT NOT NULL
        );
        INSERT INTO agent_native_agents VALUES('root');
        INSERT INTO agent_native_purpose_evaluations VALUES('evaluation');
        INSERT INTO agent_native_retirements VALUES('root','evaluation','agent','then');
    ''')

    migrate_subtrees(conn)

    assert conn.execute(
        'SELECT agent_id,evaluation_id,replacement_id,source,decision_agent_id,retired_at '
        'FROM agent_native_retirements'
    ).fetchone() == ('root', 'evaluation', None, 'agent', 'root', 'then')


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


def test_retirement_atomically_retires_the_active_descendant_subtree(broker):
    from agent_native import cadence
    from agent_native.identity import create_root
    s = broker
    child = create_root(s.conn, actor=OWNER, request_id='retirement-child', name='Child',
                        purpose='Continue delegated work.', parent_id=s.root['id'],
                        work={'timeout_seconds': 60, 'max_iterations': 4})
    grandchild = create_root(
        s.conn, actor=OWNER, request_id='retirement-grandchild', name='Grandchild',
        purpose='Continue deeper delegated work.', parent_id=child['id'],
        work={'timeout_seconds': 60, 'max_iterations': 4},
    )
    for descendant in (child, grandchild):
        cadence.configure(
            s.conn, actor=OWNER, agent_id=descendant['id'], expected_revision=1,
            interval_seconds=60, enabled=True,
        )

    result = retire(s, evaluate(s))

    assert result['affected_agent_ids'] == [s.root['id'], child['id'], grandchild['id']]
    for index, agent_id in enumerate(result['affected_agent_ids']):
        retired = get_root(s.conn, actor=OWNER, agent_id=agent_id)['retirement']
        assert retired['evaluation_id'] == result['evaluation_id']
        assert retired['decision_agent_id'] == s.root['id']
        assert retired['source'] == ('agent' if index == 0 else 'parent')
        current = get_root(s.conn, actor=OWNER, agent_id=agent_id)
        assert current['cadence']['enabled'] is False
        assert current['work']['state'] == ('stopping' if index == 0 else 'paused')


def test_descendant_unanswered_question_blocks_the_entire_retirement(broker):
    from agent_native.identity import create_root
    s = broker
    child = create_root(s.conn, actor=OWNER, request_id='question-child', name='Child',
                        purpose='Continue delegated work.', parent_id=s.root['id'])
    s.conn.execute(
        'INSERT INTO agent_native_questions '
        '(id,agent_id,soul_revision,run_id,item_id,fingerprint,topic,question,created_at) '
        'VALUES(?,?,?,?,?,?,?,?,?)',
        ('child-question', child['id'], 1, 'child-run', 'child-item', 'fingerprint',
         'scope', 'Should this delegated work be abandoned?', child['created_at']),
    )

    with pytest.raises(ValueError, match='descendant has an unanswered question'):
        retire(s, evaluate(s))

    assert get_root(s.conn, actor=OWNER, agent_id=s.root['id'])['retirement'] is None
    assert get_root(s.conn, actor=OWNER, agent_id=child['id'])['retirement'] is None
