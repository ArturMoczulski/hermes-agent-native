"""Recovery crosses the real owner HTTP and durable storage boundaries."""
from tests.hermes_cli.test_agent_native_api import client, URL, BODY  # noqa: F401
from hermes_cli.kanban_db_connect import connect_closing


def test_retry_api_requires_owner_and_keeps_replay_identity_after_completion(client):
    agent = client.post(URL, json={**BODY, 'work': {'timeout_seconds': 120, 'max_iterations': 16}}).json()
    prior = agent['work']['id']
    path = URL + '/' + agent['id'] + '/work/retry'
    body = {'expected_revision': 1, 'expected_run_id': prior}
    assert client.post(path, json=body).status_code == 409
    with connect_closing(board='default') as conn:
        conn.execute("UPDATE agent_native_work_runs SET state='failed' WHERE id=?", (prior,))
    result = client.post(path, json=body)
    assert result.status_code == 200, result.text
    recovery = result.json()['recovery_run_id']
    assert recovery != prior and result.json()['agent']['work']['id'] == recovery
    with connect_closing(board='default') as conn:
        conn.execute("UPDATE agent_native_work_runs SET state='completed' WHERE id=?", (recovery,))
    replay = client.post(path, json=body)
    assert replay.status_code == 200 and replay.json()['recovery_run_id'] == recovery
    assert replay.json()['agent']['work']['state'] == 'completed'
    client.headers.pop('X-Hermes-Session-Token')
    assert client.post(path, json=body).status_code == 401
