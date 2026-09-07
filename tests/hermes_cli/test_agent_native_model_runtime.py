"""Agent model choices use real profile configuration without inference or fallbacks."""
import socket
import json

import pytest
import yaml


@pytest.fixture
def configured_profile(tmp_path, monkeypatch):
    home = tmp_path / 'profile'
    home.mkdir()
    monkeypatch.setenv('HERMES_HOME', str(home))
    # Supply an isolated cached external catalog; native transport resolution
    # may inspect metadata, but this test must never fetch the public registry.
    (home / 'models_dev_cache.json').write_text(json.dumps({
        'deepseek': {'name': 'DeepSeek', 'api': 'https://api.deepseek.com/v1',
                     'env': ['DEEPSEEK_API_KEY'], 'models': {}}}))
    config = {
        'model': {'provider': 'First fixture', 'default': 'fixture-small'},
        'custom_providers': [
            {'name': 'First fixture', 'base_url': 'http://127.0.0.1:19001/v1',
             'api_key': 'first-fixture-secret', 'model': 'fixture-small'},
            {'name': 'Second fixture', 'base_url': 'http://127.0.0.1:19002/v1',
             'api_key': 'second-fixture-secret', 'model': 'fixture-other'},
        ],
        'fallback_model': {'provider': 'openai', 'model': 'do-not-call-fallback'},
    }
    path = home / 'config.yaml'
    path.write_text(yaml.safe_dump(config))
    def save():
        path.write_text(yaml.safe_dump(config))
    def no_network(*args, **kwargs):
        pytest.fail('Model selection must not make a network request')
    monkeypatch.setattr(socket.socket, 'connect', no_network)
    return config, save


def test_profile_default_and_explicit_choices_are_canonical_and_network_free(configured_profile):
    from agent_native.model_runtime import profile_default, validate_choice
    assert profile_default() == {'provider': 'custom:first-fixture', 'model': 'fixture-small'}
    assert validate_choice({'provider': 'Second fixture', 'model': ' cheap-v2 '}) == {
        'provider': 'custom:second-fixture', 'model': 'cheap-v2'}
    config, save = configured_profile
    config['model'] = {'provider': 'auto', 'base_url': 'http://127.0.0.1:19099/v1'}
    save()
    assert profile_default() == {'provider': '', 'model': ''}


def test_explicit_custom_choice_resolves_its_own_endpoint_and_credentials(configured_profile):
    from agent_native.model_runtime import resolve_selection
    selection = {'provider': 'custom:second-fixture', 'model': 'fixture-other', 'revision': 2}
    model, runtime = resolve_selection(selection)
    assert model == 'fixture-other'
    assert runtime['base_url'] == 'http://127.0.0.1:19002/v1'
    assert runtime['api_key'] == 'second-fixture-secret'
    assert runtime['requested_provider'] == 'custom:second-fixture'
    assert runtime['provider'] == 'custom'
    assert runtime['api_mode'] == 'chat_completions'


def test_unknown_disabled_and_ambiguous_connections_fail_without_fallback(configured_profile):
    from agent_native.model_runtime import resolve_selection, validate_choice
    for provider in ('missing', 'custom:missing', 'auto', 'custom', 'moa'):
        with pytest.raises(ValueError):
            validate_choice({'provider': provider, 'model': 'anything'})
    config, save = configured_profile
    config['providers'] = {'disabled': {'enabled': False, 'api': 'http://127.0.0.1:19003/v1'}}
    save()
    with pytest.raises(ValueError):
        resolve_selection({'provider': 'custom:disabled', 'model': 'anything'})
    config['custom_providers'] = config['custom_providers'][:1]
    save()
    with pytest.raises(ValueError):
        resolve_selection({'provider': 'custom:second-fixture', 'model': 'fixture-other'})


def test_explicit_cloud_choice_is_not_hijacked_by_an_auto_local_default(configured_profile, monkeypatch):
    from agent_native.model_runtime import resolve_selection
    config, save = configured_profile
    config['model'] = {'provider': 'auto', 'default': 'fixture-small',
                       'base_url': 'http://127.0.0.1:19001/v1'}
    save()
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'cloud-fixture-secret')
    model, runtime = resolve_selection({'provider': 'deepseek', 'model': 'deepseek-chat'})
    assert model == 'deepseek-chat'
    assert runtime['provider'] == 'deepseek'
    assert runtime['base_url'] == 'https://api.deepseek.com/v1'
    assert runtime['api_key'] == 'cloud-fixture-secret'
