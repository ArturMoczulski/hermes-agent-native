"""Agent model settings through owner HTTP and real isolated control storage."""
import os
from pathlib import Path

import pytest
import yaml

from tests.hermes_cli.test_agent_native_api import client, URL, BODY  # noqa: F401

DEFAULT = '/api/agent-native/models/default'
A = {'provider': 'custom:unit-a', 'model': 'stub-a'}
B = {'provider': 'custom:unit-b', 'model': 'stub-b'}


@pytest.fixture
def configured(client):
    home = Path(os.environ['HERMES_HOME'])
    home.mkdir(parents=True, exist_ok=True)
    (home / 'config.yaml').write_text(yaml.safe_dump({
        'model': {'provider': A['provider'], 'default': A['model']},
        'custom_providers': [
            {'name': 'unit-a', 'base_url': 'http://127.0.0.1:18881/v1', 'api_key': 'fixture-only'},
            {'name': 'unit-b', 'base_url': 'http://127.0.0.1:18882/v1', 'api_key': 'fixture-only'},
        ],
    }))
    return client


def pair(value):
    return {key: value[key] for key in ('provider', 'model')}


def test_defaults_are_copied_and_edits_preserve_identity_and_retry(configured):
    c = configured
    response = c.get(DEFAULT)
    assert response.status_code == 200, response.text
    default = response.json()
    assert pair(default) == A
    first = c.post(URL, json=BODY).json()
    assert pair(first['model_selection']) == A
    assert first['model_selection']['source'] == 'default'
    updated = c.put(DEFAULT, json={**B, 'expected_revision': default['revision']})
    assert updated.status_code == 200, updated.text
    second = c.post(URL, json={**BODY, 'request_id': 'second'}).json()
    assert pair(second['model_selection']) == B
    assert pair(c.get(URL+'/'+first['id']).json()['model_selection']) == A
    override = c.post(URL, json={**BODY, 'request_id': 'override', 'model_selection': A}).json()
    assert pair(override['model_selection']) == A
    changed = c.put(URL+'/'+first['id']+'/model', json={**B, 'expected_revision': first['model_selection']['revision']})
    assert changed.status_code == 200, changed.text
    final = changed.json()
    for key in ('id', 'purpose', 'soul_revision', 'startup', 'work'):
        assert final[key] == first[key]
    assert pair(final['model_selection']) == B
    assert c.post(URL, json=BODY).json()['id'] == first['id']
    assert c.post(URL, json={**BODY, 'model_selection': A}).status_code == 409
    assert c.put(URL+'/'+first['id']+'/model', json={**A, 'expected_revision': first['model_selection']['revision']}).status_code == 409


def test_model_settings_reject_invalid_choices_and_untrusted_writes(configured):
    c = configured
    default = c.get(DEFAULT)
    assert default.status_code == 200
    before = default.json()
    assert c.put(DEFAULT, json={**B, 'expected_revision': 999}).status_code == 409
    assert c.put(DEFAULT, json={'provider': 'custom:missing', 'model': 'cheap', 'expected_revision': before['revision']}).status_code == 422
    assert c.post(URL, json={**BODY, 'model_selection': {**A, 'api_key': 'not-allowed'}}).status_code == 422
    assert c.post(URL, json={**BODY, 'model_selection': {'provider': 'auto', 'model': 'cheap'}}).status_code == 422
    assert c.get(URL).json() == []
    assert c.get(DEFAULT).json() == before
    c.headers.pop('X-Hermes-Session-Token')
    for method, path, body in [('GET', DEFAULT, None), ('PUT', DEFAULT, {**B, 'expected_revision': 1}), ('PUT', URL+'/missing/model', {**A, 'expected_revision': 1}), ('GET', '/api/agent-native/models/options', None)]:
        assert c.request(method, path, json=body).status_code == 401


def test_attempt_selection_is_stable_and_default_change_pins_legacy(configured):
    c = configured
    response = c.post(URL, json=BODY)
    assert 'model_selection' in response.json()
    root = response.json()
    from agent_native import model_settings
    from hermes_cli.kanban_db_connect import connect_closing
    with connect_closing(board='default') as conn:
        original = model_settings.snapshot_attempt(conn, root['id'], 'work', 'attempt-one')
    changed = c.put(URL+'/'+root['id']+'/model', json={**B, 'expected_revision': root['model_selection']['revision']})
    assert changed.status_code == 200
    with connect_closing(board='default') as conn:
        assert model_settings.snapshot_attempt(conn, root['id'], 'work', 'attempt-one') == original
        assert pair(model_settings.snapshot_attempt(conn, root['id'], 'chat', 'message-next')) == B
        # Simulate an identity from before the model-settings schema. Changing
        # defaults must pin its previous profile choice before the new default.
        conn.execute('DELETE FROM agent_native_model_selections WHERE agent_id=?', (root['id'],))
    default = c.get(DEFAULT).json()
    assert c.put(DEFAULT, json={**B, 'expected_revision': default['revision']}).status_code == 200
    assert pair(c.get(URL+'/'+root['id']).json()['model_selection']) == A
    with connect_closing(board='default') as conn:
        assert model_settings.read_attempt(conn, 'work', 'attempt-one') == original


def test_unconfigured_model_does_not_consume_initial_work_attempt(client):
    home = Path(os.environ['HERMES_HOME'])
    home.mkdir(parents=True, exist_ok=True)
    (home / 'config.yaml').write_text(yaml.safe_dump({'model': {'provider': 'auto', 'default': ''}}))
    limits = {'timeout_seconds': 60, 'max_iterations': 5}
    refused = client.post(URL, json={**BODY, 'work': limits})
    assert refused.status_code == 422, refused.text
    assert client.get(URL).json() == []
    conversation = client.post(URL, json=BODY)
    assert conversation.status_code == 201
    root = conversation.json()
    assert root['work'] is None
    refused = client.post(URL+'/'+root['id']+'/work', json={**limits, 'expected_revision': 1})
    assert refused.status_code == 422, refused.text
    assert client.get(URL+'/'+root['id']).json()['work'] is None


def test_explicit_creation_retry_survives_edit_and_removed_original_connection(configured):
    c = configured
    original = {**BODY, 'model_selection': A}
    first = c.post(URL, json=original).json()
    changed = c.put(URL+'/'+first['id']+'/model', json={**B, 'expected_revision': first['model_selection']['revision']})
    assert changed.status_code == 200
    path = Path(os.environ['HERMES_HOME']) / 'config.yaml'
    config = yaml.safe_load(path.read_text())
    config['custom_providers'] = [p for p in config['custom_providers'] if p['name'] != 'unit-a']
    path.write_text(yaml.safe_dump(config))
    replay = c.post(URL, json=original)
    assert replay.status_code == 201, replay.text
    assert replay.json()['id'] == first['id']
    assert pair(replay.json()['model_selection']) == B
    assert len(c.get(URL).json()) == 1
    assert c.post(URL, json={**original, 'model_selection': B}).status_code == 409
