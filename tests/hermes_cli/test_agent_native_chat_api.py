"""Managed chat authenticates owner selection before creating a native transport."""
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv('HERMES_HOME', str(tmp_path / 'home'))
    monkeypatch.setenv('HERMES_KANBAN_DB', str(tmp_path / 'control.db'))
    from hermes_cli.web_server import app, _SESSION_TOKEN
    with TestClient(app, base_url='http://127.0.0.1') as client:
        client.headers['X-Hermes-Session-Token'] = _SESSION_TOKEN
        yield client, _SESSION_TOKEN


def test_managed_selection_rejects_unknown_agent_before_native_session(client):
    client, token = client
    for path in ('/api/pty', '/api/ws'):
        with pytest.raises(WebSocketDisconnect) as error:
            with client.websocket_connect(f'{path}?token={token}&agent=missing') as ws:
                ws.receive_text()
        assert error.value.code == 4404


def test_managed_chat_rejects_native_identity_overrides_and_missing_owner(client):
    client, token = client
    root = client.post('/api/agent-native/agents', json={
        'request_id': 'chat', 'name': 'Writer', 'purpose': 'Write fantasy',
    }).json()
    for path in ('/api/pty', '/api/ws'):
        with pytest.raises(WebSocketDisconnect) as error:
            with client.websocket_connect(f'{path}?agent={root["id"]}') as ws:
                ws.receive_text()
        assert error.value.code == 4401
        for override in ('profile=other', 'resume=unrelated', 'fresh=1'):
            with pytest.raises(WebSocketDisconnect) as error:
                with client.websocket_connect(f'{path}?token={token}&agent={root["id"]}&{override}') as ws:
                    ws.receive_text()
            assert error.value.code == 4400


def test_open_chat_is_owner_only_and_reuses_its_binding(client):
    client, _ = client
    root = client.post('/api/agent-native/agents', json={
        'request_id': 'open-chat', 'name': 'Writer', 'purpose': 'Write fantasy',
    }).json()
    url = '/api/agent-native/agents/' + root['id'] + '/chat'
    first = client.post(url)
    assert first.status_code == 200
    assert first.json()['mode'] == 'conversation_only'
    assert first.json()['agent']['purpose'] == root['purpose']
    assert client.post(url).json()['session_id'] == first.json()['session_id']
    client.headers.pop('X-Hermes-Session-Token')
    assert client.post(url).status_code == 401


def test_chat_connection_cannot_silently_change_the_displayed_purpose(client):
    from fastapi import HTTPException
    from hermes_cli.web_server_agent_chat import resolve_chat_binding
    client, _ = client
    root = client.post('/api/agent-native/agents', json={
        'request_id': 'revision-chat', 'name': 'Writer', 'purpose': 'Write fantasy',
    }).json()
    with pytest.raises(HTTPException) as error:
        resolve_chat_binding({'agent': root['id'], 'purpose_revision': '0'})
    assert error.value.status_code == 409
    assert resolve_chat_binding({'agent': root['id'], 'purpose_revision': '1'}).purpose == root['purpose']
