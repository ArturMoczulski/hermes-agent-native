"""Authenticated HTTP boundary over real isolated control storage."""
import hashlib
import json

import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv('HERMES_HOME', str(tmp_path / 'home'))
    monkeypatch.setenv('HERMES_KANBAN_DB', str(tmp_path / 'control.db'))
    home = tmp_path / 'home'
    home.mkdir()
    # Explicit isolated connection: admission tests never inherit a real model.
    (home / 'config.yaml').write_text(json.dumps({
        'model': {'provider': 'custom:api-fixture', 'default': 'api-fixture-model'},
        'custom_providers': [{'name': 'api-fixture', 'base_url': 'http://127.0.0.1:1/v1',
                              'api_key': 'test-only', 'models': ['api-fixture-model']}],
    }))
    from hermes_cli.web_server import app, _SESSION_TOKEN
    with TestClient(app, base_url='http://127.0.0.1') as client:
        client.headers['X-Hermes-Session-Token'] = _SESSION_TOKEN
        yield client

URL = '/api/agent-native/agents'
BODY = {'request_id': 'test-create', 'name': 'Artist', 'purpose': 'Make metal music'}

def test_create_list_and_read(client):
    response = client.post(URL, json=BODY)
    assert response.status_code == 201
    agent = response.json()
    assert client.post(URL, json=BODY).json()['id'] == agent['id']
    for current in (client.get(URL).json()[0], client.get(URL + '/' + agent['id']).json()):
        assert {key: value for key, value in current.items() if key != 'setup'} == {key: value for key, value in agent.items() if key != 'setup'}
    assert agent['execution'] == 'not_started'


def test_creation_with_work_enables_automatic_continuation_by_default(client):
    root = client.post(URL, json={
        **BODY, 'request_id': 'self-driven-create',
        'work': {'timeout_seconds': 180, 'max_iterations': 50},
    }).json()

    assert root['work']['state'] == 'queued'
    assert root['cadence']['enabled'] is True
    assert root['cadence']['interval_seconds'] == 60


def test_owner_creates_a_child_and_api_returns_tree_relationships(client):
    parent = client.post(URL, json=BODY).json()
    child = client.post(URL, json={**BODY, 'request_id': 'api-child', 'name': 'Composer',
                                  'purpose': 'Compose songs', 'parent_id': parent['id']})
    assert child.status_code == 201
    assert child.json()['parent_id'] == parent['id']
    assert client.get(f"{URL}/{parent['id']}").json()['child_ids'] == [child.json()['id']]
    assert {agent['id'] for agent in client.get(URL).json()} == {parent['id'], child.json()['id']}
    assert client.post(URL, json={**BODY, 'request_id': 'missing-parent',
                                 'parent_id': 'not-an-agent'}).status_code == 404


def test_invalid_and_conflicting_requests(client):
    assert client.post(URL, json={**BODY, 'purpose': ' '}).status_code == 422
    assert client.post(URL, json={**BODY, 'actor': 'owner'}).status_code == 422
    assert client.post(URL, json=BODY).status_code == 201
    assert client.post(URL, json={**BODY, 'purpose': 'Different'}).status_code == 409
    assert client.get(URL + '/missing').status_code == 404


def test_owner_revises_purpose_with_compare_and_swap_and_retains_identity(client):
    root = client.post(URL, json=BODY).json()
    path = URL + '/' + root['id'] + '/purpose'
    revised = client.patch(path, json={
        'expected_revision': 1,
        'purpose': 'Compose a progressive metal album',
    })
    assert revised.status_code == 200
    assert revised.json()['id'] == root['id']
    assert revised.json()['purpose'] == 'Compose a progressive metal album'
    assert revised.json()['soul_revision'] == 2
    assert client.patch(path, json={
        'expected_revision': 1,
        'purpose': 'Overwrite from a stale page',
    }).status_code == 409
    assert client.get(URL + '/' + root['id']).json()['purpose'] == 'Compose a progressive metal album'


def test_missing_auth_rejected_on_all_paths(client):
    client.headers.pop('X-Hermes-Session-Token')
    assert client.get(URL).status_code == 401
    assert client.post(URL, json=BODY).status_code == 401
    assert client.get(URL + '/missing').status_code == 401


def test_creation_response_contains_durable_initial_review(client):
    root = client.post(URL, json=BODY).json()
    assert root.get('startup') is not None, 'Owner creation must return its durable startup request'
    assert root['startup']['cause'] == 'creation'
    assert root['startup']['soul_revision'] == 1
    assert client.post(URL, json=BODY).json()['startup'] == root['startup']
    assert client.get(URL + '/' + root['id']).json()['startup'] == root['startup']
    assert client.post(URL, json={**BODY, 'startup': {'actor': 'owner'}}).status_code == 422


def test_remove_retains_history_and_blocks_new_work(client):
    root = client.post(URL, json=BODY).json()
    path = URL + '/' + root['id']
    response = client.delete(path)
    assert response.status_code == 200
    assert response.json()['removed_at']
    assert client.get(URL).json() == []
    assert client.get(path).json()['purpose'] == BODY['purpose']
    assert client.delete(path).json()['removed_at'] == response.json()['removed_at']
    assert client.post(path + '/chat').status_code == 409
    assert client.post(path + '/work', json={'expected_revision': 1, 'timeout_seconds': 30, 'max_iterations': 2}).status_code == 409
    assert client.post(path + '/setup/retry').status_code == 409


def test_retired_roster_is_separate_from_active_and_removed_agents(client):
    from agent_native.identity import OWNER
    from hermes_cli.kanban_db_connect import connect_closing
    active = client.post(URL, json=BODY).json()
    retired = client.post(URL, json={**BODY, 'request_id': 'retired-create', 'name': 'Retired artist'}).json()
    removed = client.post(URL, json={**BODY, 'request_id': 'removed-create', 'name': 'Removed artist'}).json()
    with connect_closing(board='default') as conn:
        now = retired['created_at']
        run_id = 'retired-test-run'
        evaluation_id = 'retired-test-evaluation'
        conn.execute('INSERT INTO agent_native_work_runs '
                     '(id,agent_id,activation_id,soul_revision,session_id,limits,state,created_at) '
                     'VALUES(?,?,?,?,?,?,?,?)', (run_id, retired['id'], retired['startup']['id'], 1,
                     'retired-test-session', '{"max_iterations": 1, "timeout_seconds": 1}', 'completed', now))
        record = {'id': evaluation_id, 'agent_id': retired['id'], 'run_id': run_id,
                  'soul_revision': 1, 'purpose': retired['purpose'], 'judgment': 'retire_candidate',
                  'evidence': ['Purpose fulfilled.'], 'remaining_obligations': [], 'uncertainty': None,
                  'next_action': 'Retire.', 'question_id': None, 'created_at': now}
        encoded = json.dumps(record, sort_keys=True, ensure_ascii=False, allow_nan=False)
        conn.execute('INSERT INTO agent_native_purpose_evaluations VALUES(?,?,?,?,?,?,?)',
                     (evaluation_id, retired['id'], run_id, 'retired-test-call', encoded,
                      hashlib.sha256(encoded.encode()).hexdigest(), now))
        conn.execute('INSERT INTO agent_native_retirements(agent_id,evaluation_id,replacement_id,source,decision_agent_id,retired_at) VALUES(?,?,?,?,?,?)',
                     (retired['id'], evaluation_id, None, 'agent', retired['id'], now))
    client.delete(f"{URL}/{removed['id']}")

    assert [agent['id'] for agent in client.get(URL).json()] == [active['id']]
    retired_roster = client.get(URL + '?lifecycle=retired')
    assert retired_roster.status_code == 200
    assert [agent['id'] for agent in retired_roster.json()] == [retired['id']]
    assert retired_roster.json()[0]['retirement']['source'] == 'agent'
    assert client.get(URL + '?lifecycle=removed').status_code == 422


def test_removal_cancels_queued_work_and_cannot_be_revived(client):
    from hermes_cli.kanban_db_connect import connect_closing
    from agent_native.cadence import queue_due
    body = {**BODY, 'work': {'timeout_seconds': 30, 'max_iterations': 2}}
    root = client.post(URL, json=body).json()
    path = URL + '/' + root['id']
    assert client.post(path + '/cadence', json={'expected_revision': 1, 'interval_seconds': 1, 'enabled': True}).status_code == 200
    removed = client.delete(path).json()
    assert removed['work']['state'] == 'paused'
    assert not removed['cadence']['enabled']
    assert client.post(URL, json=body).json()['removed_at'] == removed['removed_at']
    assert client.post(path+'/cadence', json={'expected_revision': removed['soul_revision'], 'interval_seconds': 1, 'enabled': True}).status_code == 409
    with connect_closing(board='default') as conn:
        assert queue_due(conn, now='2099-01-01T00:00:00+00:00') == []
    client.headers.pop('X-Hermes-Session-Token')
    assert client.delete(path).status_code == 401
