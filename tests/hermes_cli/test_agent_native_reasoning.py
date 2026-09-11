"""Managed reasoning choices use native route capabilities without inference."""
import pytest

from tests.hermes_cli.test_agent_native_model_runtime import configured_profile  # noqa: F401


def test_codex_reasoning_options_are_exact_and_unknown_models_are_default_only(configured_profile):
    from agent_native.model_runtime import get_reasoning_options, validate_reasoning
    options = get_reasoning_options('openai-codex', 'gpt-6-astra')
    assert options['efforts'] == ['default', 'low', 'medium', 'high', 'xhigh', 'max']
    assert options['default_label'] == 'Runtime automatic'
    for effort in ('none', 'minimal', 'ultra', 'invalid'):
        with pytest.raises(ValueError):
            validate_reasoning({'provider': 'openai-codex', 'model': 'gpt-6-astra', 'reasoning_effort': effort})
    assert get_reasoning_options('openai-codex', 'future-unverified-model')['efforts'] == ['default']
    assert get_reasoning_options('custom:first-fixture', 'fixture-small')['efforts'] == ['default']


def test_declared_profile_reasoning_and_explicit_default_ignore_ambient_effort(configured_profile, monkeypatch):
    from agent_native.model_runtime import get_reasoning_options, reasoning_config, validate_reasoning
    import providers
    from providers.base import ProviderProfile
    providers.list_providers()
    class FixtureProfile(ProviderProfile):
        def supported_reasoning_efforts(self, model):
            return ('low', 'high') if model == 'fixture-small' else None
    monkeypatch.setitem(providers._REGISTRY, 'custom', FixtureProfile(name='custom'))
    config, save = configured_profile
    config['agent'] = {'reasoning_effort': 'ultra', 'reasoning_overrides': {'fixture-small': 'high'}}
    save()
    pair = {'provider': 'custom:first-fixture', 'model': 'fixture-small'}
    assert get_reasoning_options(**pair)['efforts'] == ['default', 'low', 'high']
    assert validate_reasoning({**pair, 'reasoning_effort': 'low'}) == 'low'
    assert reasoning_config({**pair, 'reasoning_effort': 'low'}) == {'enabled': True, 'effort': 'low'}
    assert reasoning_config({**pair, 'reasoning_effort': 'default'}) is None
    assert reasoning_config(pair) is None
    with pytest.raises(ValueError):
        validate_reasoning({**pair, 'reasoning_effort': 'medium'})


def test_astra_native_responses_preserves_max_without_product_ultra():
    from agent.reasoning_effort import codex_supported_efforts
    from agent.transports import get_transport
    import agent.transports.codex  # noqa: F401
    assert codex_supported_efforts('gpt-6-astra') == ('low', 'medium', 'high', 'xhigh', 'max')
    request = get_transport('codex_responses').build_kwargs(
        model='gpt-6-astra', messages=[{'role': 'user', 'content': 'hi'}], tools=[],
        reasoning_config={'enabled': True, 'effort': 'max'})
    assert request['reasoning']['effort'] == 'max'
