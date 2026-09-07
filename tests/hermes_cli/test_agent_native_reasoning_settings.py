"""Reasoning preferences through owner routes and real control storage."""
import pytest

from tests.hermes_cli.test_agent_native_model_settings import configured, client, URL, BODY, DEFAULT, A  # noqa: F401


@pytest.fixture
def reasoning(configured, monkeypatch):
    from agent_native import model_runtime, reasoning as native_reasoning
    # Isolate the capability catalog only; persistence/auth/admission stay real.
    monkeypatch.setattr(model_runtime, 'get_reasoning_options',
                        lambda provider, model: {'efforts': ['default', 'low', 'high'],
                                                 'default_label': 'Hermes default', 'message': None}, raising=False)
    monkeypatch.setattr(native_reasoning, 'get_reasoning_options', model_runtime.get_reasoning_options)
    return configured


def test_reasoning_defaults_overrides_and_attempts_are_independent(reasoning):
    c = reasoning
    default = c.get(DEFAULT).json()
    response = c.put(DEFAULT, json={**A, 'reasoning_effort': 'low', 'expected_revision': default['revision']})
    assert response.status_code == 200, response.text
    inherited = c.post(URL, json=BODY).json()
    assert inherited['model_selection']['reasoning_effort'] == 'low'
    original = {**BODY, 'request_id': 'explicit-reasoning', 'model_selection': {**A, 'reasoning_effort': 'high'}}
    created = c.post(URL, json=original).json()
    assert created['model_selection']['reasoning_effort'] == 'high'
    from agent_native import model_settings
    from hermes_cli.kanban_db_connect import connect_closing
    with connect_closing(board='default') as conn:
        first = model_settings.snapshot_attempt(conn, created['id'], 'work', 'reasoning-first')
    edit = c.put(URL+'/'+created['id']+'/model', json={**A, 'reasoning_effort': 'low', 'expected_revision': created['model_selection']['revision']})
    assert edit.status_code == 200, edit.text
    updated = edit.json()
    assert updated['model_selection']['revision'] == created['model_selection']['revision'] + 1
    for key in ('id', 'purpose', 'soul_revision', 'startup', 'work'):
        assert updated[key] == created[key]
    assert c.post(URL, json=original).json()['id'] == created['id']
    assert c.post(URL, json={**original, 'model_selection': {**A, 'reasoning_effort': 'low'}}).status_code == 409
    with connect_closing(board='default') as conn:
        assert model_settings.snapshot_attempt(conn, created['id'], 'work', 'reasoning-first') == first
        assert first['reasoning_effort'] == 'high'
        assert model_settings.snapshot_attempt(conn, created['id'], 'chat', 'reasoning-next')['reasoning_effort'] == 'low'
    assert c.get(URL+'/'+inherited['id']).json()['model_selection']['reasoning_effort'] == 'low'
    assert c.get(URL+'/'+created['id']).json()['model_selection']['reasoning_effort'] == 'low'


def test_reasoning_rejects_unsupported_and_stale_choices_without_mutation(reasoning):
    c = reasoning
    options = c.get('/api/agent-native/models/reasoning', params=A)
    assert options.status_code == 200, options.text
    assert options.json()['efforts'] == ['default', 'low', 'high']
    root = c.post(URL, json=BODY).json()
    setting = root['model_selection']
    path = URL+'/'+root['id']+'/model'
    for effort in ('ultra', 'none', '', None, False):
        response = c.put(path, json={**A, 'reasoning_effort': effort, 'expected_revision': setting['revision']})
        assert response.status_code == 422, response.text
    assert c.put(path, json={**A, 'reasoning_effort': 'high', 'expected_revision': 999}).status_code == 409
    assert c.get(URL+'/'+root['id']).json()['model_selection'] == setting
    c.headers.pop('X-Hermes-Session-Token')
    assert c.get('/api/agent-native/models/reasoning', params=A).status_code == 401
    assert c.put(path, json={**A, 'reasoning_effort': 'high', 'expected_revision': setting['revision']}).status_code == 401


def test_upgrade_preserves_existing_model_records_and_creation_retries(configured):
    c = configured
    original = {**BODY, 'model_selection': A}
    before = c.post(URL, json=original).json()
    from agent_native import model_settings
    from hermes_cli.kanban_db_connect import connect_closing
    tables = ('agent_native_model_default', 'agent_native_model_selections',
              'agent_native_model_attempts', 'agent_native_model_events')
    with connect_closing(board='default') as conn:
        old_attempt = model_settings.snapshot_attempt(conn, before['id'], 'chat', 'pre-upgrade')
        # Recreate the actual pre-feature column layout, then invoke the additive migration.
        for table in tables:
            conn.execute(f'ALTER TABLE {table} DROP COLUMN reasoning_effort')
        path = conn.execute('PRAGMA database_list').fetchone()[2]
    from hermes_cli.kanban_db_connect import _INITIALIZED_PATHS
    _INITIALIZED_PATHS.discard(path)
    # The real open path must install missing columns before reading selections.
    with connect_closing(board='default') as conn:
        model_settings.migrate_reasoning(conn)  # repeated migration is harmless
        upgraded = model_settings.read_attempt(conn, 'chat', 'pre-upgrade')
        assert upgraded == {**old_attempt, 'reasoning_effort': 'default'}
        assert conn.execute('SELECT input_json FROM agent_native_creation_model WHERE agent_id=?',
                            (before['id'],)).fetchone()[0] == model_settings.creation_input(A)
    replay = c.post(URL, json=original)
    assert replay.status_code == 201, replay.text
    assert replay.json()['id'] == before['id']
    assert replay.json()['model_selection'] == before['model_selection']
    legacy_work = c.post(URL, json={**BODY, 'request_id': 'after-upgrade', 'work': {'timeout_seconds': 60, 'max_iterations': 5}})
    assert legacy_work.status_code == 201, legacy_work.text
    assert legacy_work.json()['model_selection']['reasoning_effort'] == 'default'


def test_fresh_astra_default_uses_low_and_remains_owner_configurable(configured, monkeypatch):
    from agent_native import model_runtime
    monkeypatch.setattr(model_runtime, 'profile_default', lambda: {
        'provider': 'openai-codex', 'model': 'gpt-6-astra'})
    initial = configured.get(DEFAULT).json()
    assert initial['reasoning_effort'] == 'low'
    # Persisted owner choices win over the bootstrap default.
    changed = configured.put(DEFAULT, json={**A, 'reasoning_effort': 'default',
                                            'expected_revision': initial['revision']})
    assert changed.status_code == 200, changed.text
    assert configured.get(DEFAULT).json()['reasoning_effort'] == 'default'
