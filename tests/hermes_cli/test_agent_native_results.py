"""Shared results through the host broker, real Plane HTTP and durable SQLite."""
import hashlib
from uuid import uuid4

import pytest

from agent_native import work_state
from hermes_cli.kanban_db_connect import connect_closing, write_txn
from tests.hermes_cli.test_agent_native_work_effects import broker, effect  # noqa: F401


def record(s, call_id='result-one', **changes):
    args = {'item_id': s.setup['discovery_item_id'], 'summary': 'The supplied figures increased by 25%.',
            'outcome': 'discovery', 'evaluation': 'Compared 80 to 100; no external research performed.',
            'outputs': [], 'references': []}
    return s.run._effect(s.conn, s.planning, effect(s, call_id, 'result_record', {**args, **changes}))


def test_useful_result_without_file_finishes_attempt_but_does_not_accept_task(broker):
    s = broker
    observed = s.planning.inspect({'kind': 'item', 'resource_id': s.setup['discovery_item_id']})
    before = len(s.plane.requests)
    result = record(s)
    assert result['agent_id'] == s.root['id'] and result['run_id'] == s.work['id']
    assert result['item_id'] == observed['resource']['id']
    assert result['soul_revision'] == 1 and result['purpose'] == s.root['purpose']
    assert result['criteria_snapshot'] == observed['resource']['description_html']
    assert result['criteria_revision'] == hashlib.sha256(result['criteria_snapshot'].encode()).hexdigest()
    assert result['assignment_fingerprint'] == observed['fingerprint']
    assert result['outcome'] == 'discovery' and result['acceptance'] == 'not_evaluated'
    assert result['review'] == {'required': False, 'source': 'autonomy', 'reason': None}
    assert result['outputs'] == [] and result['references'] == []
    s.run.finish(s.conn, {'type': 'turn.end'})
    with connect_closing(s.db_path) as reopened:
        work = work_state.read_work(reopened, s.root['id'])
    assert work['state'] == 'completed'
    assert work['outputs'] == [] and work['results'] == [result]
    # No terminal Plane state mutation was issued by recording or finishing.
    assert not any(r['method'] == 'PATCH' for r in s.plane.requests[before:])


@pytest.mark.parametrize('outcome', ['waiting', 'blocked'])
def test_wait_and_blocker_are_preserved_as_results_without_artifacts(broker, outcome):
    s = broker
    result = record(s, outcome=outcome, summary='Owner needs to supply the missing figures.')
    s.run.finish(s.conn, {'type': 'turn.end'})
    work = work_state.read_work(s.conn, s.root['id'])
    assert work['state'] == 'completed'
    assert work['results'][0]['outcome'] == outcome
    assert work['summary'] == result['summary']
    assert work['results'][0]['acceptance'] == 'not_evaluated'


def test_replay_is_idempotent_and_changed_arguments_cannot_reuse_call(broker):
    s = broker
    first = record(s)
    assert record(s) == first
    with pytest.raises(PermissionError):
        record(s, summary='A different claim')
    assert work_state.read_work(s.conn, s.root['id'])['results'] == [first]
    second = record(s, 'second-result', summary='An additional finding')
    assert second['id'] != first['id']
    assert len(work_state.read_work(s.conn, s.root['id'])['results']) == 2


@pytest.mark.parametrize('frame,expected', [({'type': 'turn.error'}, 'failed'), ({'type': 'turn.end'}, 'completed')])
def test_report_never_overrides_worker_outcome(broker, frame, expected):
    s = broker
    record(s, outcome='submitted')
    s.run.finish(s.conn, frame)
    work = work_state.read_work(s.conn, s.root['id'])
    assert work['state'] == expected
    assert work['results'][0]['acceptance'] == 'not_evaluated'


def test_unknown_effect_cannot_be_overridden_by_existing_result(broker):
    s = broker
    record(s)
    with write_txn(s.conn):
        s.conn.execute("UPDATE agent_native_work_runs SET state='unknown',stop_requested=1 WHERE id=?", (s.work['id'],))
    s.run.finish(s.conn, {'type': 'turn.end'})
    assert work_state.read_work(s.conn, s.root['id'])['state'] == 'unknown'
    with pytest.raises(PermissionError):
        record(s, 'after-unknown')


def test_a_file_alone_does_not_substitute_for_evaluation_and_result(broker):
    s = broker
    output = s.run._effect(s.conn, s.planning, effect(s, 'report', 'output_publish', {
        'title': 'Analysis', 'content': '100 / 80 - 1 = 25%', 'format': 'markdown',
        'item_id': s.setup['discovery_item_id']}))
    s.run.finish(s.conn, {'type': 'turn.end'})
    work = work_state.read_work(s.conn, s.root['id'])
    assert work['state'] == 'failed' and work['results'] == []
    assert work['outputs'][0]['output_id'] == output['output_id']


def test_result_can_link_multiple_outputs_and_unverified_external_reference(broker):
    s = broker
    outputs = []
    for n, format in enumerate(('markdown', 'text')):
        value = s.run._effect(s.conn, s.planning, effect(s, 'output-'+str(n), 'output_publish', {
            'title': 'Analysis '+str(n), 'content': 'Supplied data only.', 'format': format,
            'item_id': s.setup['discovery_item_id']}))
        outputs.append({'output_id': value['output_id'], 'version': value['version']})
    result = record(s, outputs=outputs, references=[{'label': 'External report', 'url': 'https://example.com/report'}])
    assert result['outputs'] == outputs
    assert result['references'] == [{'label': 'External report', 'url': 'https://example.com/report', 'verified': False}]
    assert result['observed_effects'] == []
    assert result['evaluation'] == {'report': 'Compared 80 to 100; no external research performed.', 'source': 'agent'}


def test_owner_review_policy_gates_submitted_output_at_balanced_autonomy(broker):
    from agent_native import autonomy
    from agent_native.identity import OWNER
    s=broker
    autonomy.change_settings(s.conn,actor=OWNER,agent_id=s.root['id'],level=3,
                             require_owner_review=True,expected_revision=1)
    output=s.run._effect(s.conn,s.planning,effect(s,'policy-output','output_publish',{
        'title':'Policy draft','content':'A complete draft.','format':'markdown',
        'item_id':s.setup['discovery_item_id']}))

    result=record(s,'policy-result',outcome='submitted',outputs=[{
        'output_id':output['output_id'],'version':output['version']}])

    assert result['review']=={
        'required':True,'source':'owner_policy',
        'reason':'Owner policy requires review of every submitted deliverable.',
    }


def test_assignment_review_gate_binds_to_observed_item_revision(broker):
    from agent_native.assignment_review import configure_current
    from agent_native.identity import ConflictError, OWNER
    from tests.hermes_cli.test_agent_native_work_focus import select
    s=broker
    focus=select(s)
    policy=configure_current(s.conn,actor=OWNER,agent_id=s.root['id'],run_id=s.work['id'],
                             required=True,expected_revision=0)
    assert policy['assignment_fingerprint']==focus['assignment_fingerprint']
    output=s.run._effect(s.conn,s.planning,effect(s,'assignment-output','output_publish',{
        'title':'Assignment draft','content':'A complete draft.','format':'markdown',
        'item_id':s.setup['discovery_item_id']}))
    result=record(s,'assignment-result',outcome='submitted',outputs=[{
        'output_id':output['output_id'],'version':output['version']}])
    assert result['review']['source']=='assignment_policy'

    s.plane.items[s.setup['discovery_item_id']]['description_html']='<p>Changed criteria</p>'
    with pytest.raises(ConflictError,match='Assignment changed'):
        record(s,'stale-assignment-result',outcome='submitted',outputs=[{
            'output_id':output['output_id'],'version':output['version']}])


def test_approval_driven_attempt_requires_review_for_submitted_output(broker):
    s = broker
    with write_txn(s.conn):
        s.conn.execute('UPDATE agent_native_autonomy_settings SET level=1 WHERE agent_id=?', (s.root['id'],))
    output = s.run._effect(s.conn, s.planning, effect(s, 'gated-output', 'output_publish', {
        'title': 'Gated draft', 'content': 'Review me.', 'format': 'markdown',
        'item_id': s.setup['discovery_item_id']}))
    result = record(s, outcome='submitted', outputs=[{'output_id': output['output_id'], 'version': output['version']}])
    assert result['review'] == {
        'required': True,
        'source': 'autonomy',
        'reason': 'Approval-driven autonomy requires owner review of submitted deliverables.',
    }


@pytest.mark.parametrize('changes', [
    {'outcome': 'accepted'}, {'soul_revision': 999}, {'acceptance': 'accepted'},
    {'observed_effects': [{'claim': 'paid'}]},
    {'outputs': [{'output_id': str(uuid4()), 'version': 1}]},
    {'references': [{'label': 'script', 'url': 'javascript:alert(1)'}]},
    {'evaluation': ''}, {'summary': ''},
])
def test_result_rejects_forged_authority_unknown_outputs_and_unsafe_references(broker, changes):
    with pytest.raises((PermissionError, ValueError, LookupError)):
        record(broker, **changes)
    assert work_state.read_work(broker.conn, broker.root['id'])['results'] == []


@pytest.mark.parametrize('cause', ['purpose', 'deadline'])
def test_late_completion_cannot_override_revoked_run_authority(broker, cause):
    import time
    from agent_native.identity import OWNER, revise_soul
    s = broker
    original = record(s)
    if cause == 'purpose':
        revise_soul(s.conn, actor=OWNER, agent_id=s.root['id'], expected_revision=1,
                    purpose='A new purpose invalidates the old admitted work.')
    else:
        s.run.deadline = time.monotonic() - 1
    s.run.finish(s.conn, {'type': 'turn.end'})
    work = work_state.read_work(s.conn, s.root['id'])
    assert work['state'] == 'paused'
    assert work['results'] == [original]
    assert original['soul_revision'] == 1 and original['acceptance'] == 'not_evaluated'
