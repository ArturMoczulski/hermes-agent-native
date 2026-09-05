"""Authenticated HTTP boundary over real isolated control storage."""
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv('HERMES_KANBAN_DB', str(tmp_path / 'control.db'))
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
    assert client.get(URL).json() == [agent]
    assert client.get(URL + '/' + agent['id']).json() == agent
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
