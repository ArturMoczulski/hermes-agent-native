"""Authenticated HTTP boundary over real isolated control storage."""
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


def test_invalid_and_conflicting_requests(client):
    assert client.post(URL, json={**BODY, 'purpose': ' '}).status_code == 422
    assert client.post(URL, json={**BODY, 'actor': 'owner'}).status_code == 422
    assert client.post(URL, json=BODY).status_code == 201
    assert client.post(URL, json={**BODY, 'purpose': 'Different'}).status_code == 409
    assert client.get(URL + '/missing').status_code == 404


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
