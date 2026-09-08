"""Owner decisions bind to immutable result records and deliver revision feedback."""
import hashlib
import json
from uuid import uuid4

from tests.hermes_cli.test_agent_native_model_settings import configured, client, URL, BODY  # noqa: F401


def _result(c):
    root = c.post(URL, json={**BODY, 'work': {'timeout_seconds': 60, 'max_iterations': 2}}).json()
    result_id = str(uuid4())
    record = {'id': result_id, 'agent_id': root['id'], 'run_id': root['work']['id'], 'item_id': 'item-one',
              'soul_revision': 1, 'purpose': root['purpose'], 'criteria_snapshot': '', 'criteria_revision': 'criteria',
              'assignment_fingerprint': 'fingerprint', 'criteria_observed_at': root['created_at'],
              'summary': 'Draft ready', 'outcome': 'submitted', 'evaluation': {'report': 'Meets criteria', 'source': 'agent'},
              'acceptance': 'not_evaluated', 'outputs': [{'output_id': str(uuid4()), 'version': 3}],
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
    body = {'request_id': 'accept-one', 'decision': 'accepted'}
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
    assert configured.post(path, json={'request_id': 'rev-empty', 'decision': 'revision_requested'}).status_code == 422
    response = configured.post(path, json={'request_id': 'rev-one', 'decision': 'revision_requested', 'note': 'Strengthen the ending.'})
    assert response.status_code == 200
    result = next(r for r in response.json()['work']['results'] if r['id'] == result_id)
    assert result['acceptance'] == 'revision_requested'
    feedback = configured.get(f'{URL}/{root["id"]}/feedback').json()
    assert feedback[0]['status'] == 'pending'
    assert 'Strengthen the ending.' in feedback[0]['text']
