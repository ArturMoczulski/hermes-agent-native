"""Parents observe descendant evidence and evaluate direct-child results."""
from datetime import datetime, timedelta
from pathlib import Path

from agent_native.identity import OWNER, create_root, get_root
from agent.work_policy import tool_schemas
from agent_native.output_store import publish
from agent_native.result_store import record
from tests.hermes_cli.test_agent_native_child_delegation import delegate, prepare_frozen_parent
from tests.hermes_cli.test_agent_native_work_effects import broker, effect  # noqa: F401


def child_result(s):
    prepare_frozen_parent(s)
    child_id = delegate(s)['child_id']
    child = get_root(s.conn, actor=OWNER, agent_id=child_id)
    child_workspace = Path(s.home) / 'agents' / child_id / 'workspace'
    child_workspace.mkdir(parents=True, mode=0o700)
    item_id = next(iter(s.plane.items))
    saved = publish(
        s.conn, validate=lambda conn: None, workspace=child_workspace,
        agent_id=child_id, run_id=child['work']['id'], call_id='child-output',
        item_id=item_id, title='Research dossier', content='Verified child evidence.',
        format='markdown',
    )
    observation = s.planning.inspect({'kind': 'item', 'resource_id': item_id})
    result = record(
        s.conn, validate=lambda conn: None, workspace=child_workspace,
        agent_id=child_id, run_id=child['work']['id'], call_id='child-result',
        observation=observation,
        arguments={
            'item_id': item_id,
            'summary': 'Completed the delegated lore research.',
            'outcome': 'submitted',
            'evaluation': 'The dossier addresses the assigned history questions.',
            'outputs': [{'output_id': saved['output_id'], 'version': 1}],
        },
    )
    return child, result, saved


def invoke(s, call_id, tool, arguments):
    params = effect(s, call_id, tool, arguments)
    params['arguments'] = arguments
    return s.run._effect(s.conn, s.planning, params)


def test_parent_inspects_descendant_work_and_reads_exact_output(broker):
    s = broker
    child, result, saved = child_result(s)

    roster = invoke(s, 'list-children', 'child_inspect', {})
    overview = invoke(s, 'inspect-child', 'child_inspect', {'child_id': child['id']})
    content = invoke(s, 'read-child-output', 'child_inspect', {
        'child_id': child['id'], 'output_id': saved['output_id'], 'version': 1,
    })

    assert roster['children'][0]['id'] == child['id']
    assert roster['children'][0]['unevaluated_result_count'] == 1
    assert overview['relationship'] == 'direct_child'
    assert overview['child']['id'] == child['id']
    assert overview['child']['work']['state'] == 'queued'
    assert overview['results'][0]['id'] == result['id']
    assert overview['outputs'][0]['output_id'] == saved['output_id']
    assert content['content'] == 'Verified child evidence.'
    assert content['next_offset'] is None


def test_new_child_result_wakes_parent_after_busy_work_without_waiting_full_cadence(broker):
    from agent_native import cadence

    s = broker
    _, result, _ = child_result(s)
    finished_at = result['created_at']
    reconsider_at = (datetime.fromisoformat(finished_at) + timedelta(seconds=1)).isoformat()
    s.conn.execute(
        "UPDATE agent_native_work_runs SET state='completed',finished_at=? WHERE id=?",
        (finished_at, s.work['id']),
    )

    [queued] = cadence.queue_due(s.conn, now=reconsider_at)

    assert queued != s.work['id']
    assert s.conn.execute(
        'SELECT count(*) FROM agent_native_cadence_wakes WHERE agent_id=?',
        (s.root['id'],),
    ).fetchone()[0] == 0
    summary = s.conn.execute(
        "SELECT summary FROM agent_native_work_events WHERE run_id=? AND kind='work.queued'",
        (queued,),
    ).fetchone()[0]
    assert 'child_result' in summary


def test_managed_worker_receives_child_supervision_tools():
    schemas = {tool['function']['name']: tool['function'] for tool in tool_schemas()}

    assert schemas['child_inspect']['parameters']['required'] == []
    assert schemas['child_result_evaluate']['parameters']['required'] == [
        'child_id', 'result_id', 'decision', 'evaluation', 'uncertainty',
    ]


def test_direct_parent_evaluates_result_and_revision_feedback_wakes_child(broker):
    s = broker
    child, result, _ = child_result(s)

    evaluation = invoke(s, 'evaluate-child', 'child_result_evaluate', {
        'child_id': child['id'], 'result_id': result['id'],
        'decision': 'revision_requested',
        'evaluation': 'The chronology is useful, but the source conflicts need resolution.',
        'uncertainty': 'Two dates remain weakly supported.',
    })

    assert evaluation['decision'] == 'revision_requested'
    assert evaluation['parent_id'] == s.root['id']
    feedback = s.conn.execute(
        'SELECT agent_id,soul_revision,text,status FROM agent_native_feedback '
        "WHERE request_id=?", ('parent-result:' + result['id'],),
    ).fetchone()
    assert tuple(feedback) == (
        child['id'], 1,
        'Parent requested revision of delegated result ' + result['id'] +
        ': The chronology is useful, but the source conflicts need resolution. '
        'Uncertainty: Two dates remain weakly supported.',
        'pending',
    )
    assert get_root(s.conn, actor=OWNER, agent_id=child['id'])['cadence']['enabled'] is True


def test_only_direct_parent_can_evaluate_and_one_result_has_one_decision(broker):
    s = broker
    child, result, _ = child_result(s)
    grandchild = create_root(
        s.conn, actor=OWNER, request_id='grandchild', name='Source checker',
        purpose='Check sources.', parent_id=child['id'],
    )
    arguments = {
        'child_id': child['id'], 'result_id': result['id'], 'decision': 'accepted',
        'evaluation': 'The result meets the delegated brief.', 'uncertainty': None,
    }

    accepted = invoke(s, 'accept-child', 'child_result_evaluate', arguments)
    assert accepted['decision'] == 'accepted'
    assert get_root(
        s.conn, actor=OWNER, agent_id=child['id'],
    )['cadence']['next_due'] == accepted['created_at']
    child_result_after = get_root(
        s.conn, actor=OWNER, agent_id=child['id'],
    )['work']['results'][0]
    assert child_result_after['parent_evaluation']['decision'] == 'accepted'
    assert invoke(s, 'accept-child', 'child_result_evaluate', arguments) == accepted
    repeat = invoke(s, 'reject-child', 'child_result_evaluate', {
        **arguments, 'decision': 'rejected', 'evaluation': 'Changed judgment.',
    })
    assert repeat['status'] == 'rejected' and repeat['error'] == 'ValueError'
    denied = invoke(s, 'evaluate-grandchild', 'child_result_evaluate', {
        **arguments, 'child_id': grandchild['id'],
    })
    assert denied['status'] == 'rejected' and denied['error'] == 'PermissionError'


def test_parent_cannot_inspect_unrelated_agent(broker):
    s = broker
    unrelated = create_root(
        s.conn, actor=OWNER, request_id='unrelated', name='Unrelated', purpose='Other work.',
    )

    denied = invoke(s, 'inspect-unrelated', 'child_inspect', {'child_id': unrelated['id']})
    assert denied['status'] == 'rejected' and denied['error'] == 'PermissionError'


def test_parent_evaluation_rejects_tampered_child_result(broker):
    s = broker
    child, result, _ = child_result(s)
    encoded = s.conn.execute(
        'SELECT record_json FROM agent_native_work_results WHERE id=?', (result['id'],),
    ).fetchone()[0]
    s.conn.execute(
        'UPDATE agent_native_work_results SET record_json=? WHERE id=?',
        (encoded.replace('Completed the delegated lore research.', 'Tampered report.'), result['id']),
    )

    denied = invoke(s, 'evaluate-tampered', 'child_result_evaluate', {
        'child_id': child['id'], 'result_id': result['id'], 'decision': 'accepted',
        'evaluation': 'Looks complete.', 'uncertainty': None,
    })
    assert denied['status'] == 'rejected' and denied['error'] == 'ValueError'
