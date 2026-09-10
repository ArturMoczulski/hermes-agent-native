"""Owner decisions bind to immutable result records and deliver revision feedback."""
import hashlib
import json
from uuid import uuid4

import pytest

from tests.hermes_cli.test_agent_native_model_settings import configured, client, URL, BODY  # noqa: F401


def _result(c):
    root = c.post(URL, json={**BODY, 'work': {'timeout_seconds': 60, 'max_iterations': 2}}).json()
    result_id = str(uuid4())
    record = {'id': result_id, 'agent_id': root['id'], 'run_id': root['work']['id'], 'item_id': 'item-one',
              'soul_revision': 1, 'purpose': root['purpose'], 'criteria_snapshot': '', 'criteria_revision': 'criteria',
              'assignment_fingerprint': 'fingerprint', 'criteria_observed_at': root['created_at'],
              'summary': 'Draft ready', 'outcome': 'submitted', 'evaluation': {'report': 'Meets criteria', 'source': 'agent'},
              'acceptance': 'not_evaluated', 'outputs': [{'output_id': str(uuid4()), 'version': 3}],
              'review': {'required': True, 'source': 'autonomy', 'reason': 'Approval-driven autonomy requires owner review of submitted deliverables.'},
              'references': [], 'observed_effects': [], 'observed_effect_scope': 'attempt', 'created_at': root['created_at']}
    encoded = json.dumps(record, sort_keys=True, ensure_ascii=False, allow_nan=False)
    from hermes_cli.kanban_db_connect import connect_closing
    with connect_closing(board='default') as conn:
        conn.execute('INSERT INTO agent_native_work_results VALUES(?,?,?,?,?,?,?,?,?)',
                     (result_id, root['id'], root['work']['id'], 'item-one', 'call-one', 'request', encoded,
                      hashlib.sha256(encoded.encode()).hexdigest(), root['created_at']))
    return root, result_id


def test_accept_exact_result_is_idempotent_and_immutable(configured):
    root, result_id = _result(configured)
    path = f'{URL}/{root["id"]}/results/{result_id}/decision'
    body = {'request_id': 'accept-one', 'decision': 'accepted',
            'expected_criteria_revision': 'criteria'}
    assert configured.post(path, json=body).status_code == 200
    again = configured.post(path, json=body)
    assert again.status_code == 200
    accepted = next(r for r in again.json()['work']['results'] if r['id'] == result_id)
    assert accepted['acceptance'] == 'accepted'
    assert accepted['outputs'][0]['version'] == 3
    assert configured.post(path, json={**body, 'decision': 'revision_requested', 'note': 'Change it'}).status_code == 409


def test_revision_request_requires_note_and_becomes_pending_feedback(configured):
    root, result_id = _result(configured)
    path = f'{URL}/{root["id"]}/results/{result_id}/decision'
    assert configured.post(path, json={'request_id': 'rev-empty', 'decision': 'revision_requested',
                                       'expected_criteria_revision': 'criteria'}).status_code == 422
    response = configured.post(path, json={'request_id': 'rev-one', 'decision': 'revision_requested',
                                            'expected_criteria_revision': 'criteria',
                                            'note': 'Strengthen the ending.'})
    assert response.status_code == 200
    result = next(r for r in response.json()['work']['results'] if r['id'] == result_id)
    assert result['acceptance'] == 'revision_requested'
    feedback = configured.get(f'{URL}/{root["id"]}/feedback').json()
    assert feedback[0]['status'] == 'pending'
    assert feedback[0]['intent'] == 'revision_request'
    assert 'Strengthen the ending.' in feedback[0]['text']


def test_owner_cannot_accept_result_without_a_review_gate(configured):
    root, result_id = _result(configured)
    from hermes_cli.kanban_db_connect import connect_closing
    with connect_closing(board='default') as conn:
        row = conn.execute('SELECT record_json FROM agent_native_work_results WHERE id=?', (result_id,)).fetchone()
        record = json.loads(row[0])
        record['review'] = {'required': False, 'source': 'autonomy', 'reason': None}
        encoded = json.dumps(record, sort_keys=True, ensure_ascii=False, allow_nan=False)
        conn.execute('UPDATE agent_native_work_results SET record_json=?,record_sha256=? WHERE id=?',
                     (encoded, hashlib.sha256(encoded.encode()).hexdigest(), result_id))
    response = configured.post(f'{URL}/{root["id"]}/results/{result_id}/decision', json={
        'request_id': 'accept-optional', 'decision': 'accepted',
        'expected_criteria_revision': 'criteria'})
    assert response.status_code == 422
    assert response.json()['detail'] == 'This result does not require an owner decision'


@pytest.mark.parametrize('decision,note',[
    ('accepted',None),('revision_requested','Continue with a stronger ending.'),
])
def test_required_review_stops_cadence_until_owner_decides(configured,decision,note):
    root, result_id = _result(configured)
    from agent_native import cadence
    from agent_native.identity import OWNER
    from hermes_cli.kanban_db_connect import connect_closing
    with connect_closing(board='default') as conn:
        cadence.configure(conn,actor=OWNER,agent_id=root['id'],expected_revision=1,
                          interval_seconds=1,enabled=True)
        conn.execute("UPDATE agent_native_setup SET status='ready',message='Ready' WHERE agent_id=?",
                     (root['id'],))
        conn.execute("UPDATE agent_native_work_runs SET state='completed',"
                     "finished_at='2000-01-01T00:00:00+00:00' WHERE id=?",
                     (root['work']['id'],))
        from agent_native.readiness import automatic_work
        assert automatic_work(conn, root['id'], now='2099-01-01T00:00:00+00:00') == {
            'state': 'waiting_owner_review', 'may_start': False,
            'blocker': 'A required output review is unanswered.',
            'release_condition': 'Accept the output or request a revision.',
            'responsible_actor': 'owner',
        }
        assert cadence.queue_due(conn,now='2099-01-01T00:00:00+00:00')==[]

    path = f'{URL}/{root["id"]}/results/{result_id}/decision'
    assert configured.post(path,json={
        'request_id':'resolve-cadence-gate','decision':decision,
        'expected_criteria_revision':'criteria',**({'note':note} if note else {})
    }).status_code==200
    with connect_closing(board='default') as conn:
        assert len(cadence.queue_due(conn,now='2099-01-01T00:00:01+00:00'))==1


def test_owner_decision_rejects_a_stale_criteria_revision(configured):
    root, result_id = _result(configured)
    response = configured.post(f'{URL}/{root["id"]}/results/{result_id}/decision', json={
        'request_id': 'stale-criteria', 'decision': 'accepted',
        'expected_criteria_revision': 'older-screen-revision',
    })

    assert response.status_code == 409
    assert response.json()['detail'] == 'Result criteria changed; reload before deciding'
