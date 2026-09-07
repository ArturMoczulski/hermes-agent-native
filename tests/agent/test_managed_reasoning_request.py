"""Explicit managed reasoning survives the native provider request boundary."""
import pytest

from tests.agent.test_managed_chat_policy import binding, provider, make_agent  # noqa: F401


@pytest.mark.parametrize('rewrite', [None, 'high', 'missing'])
def test_managed_reasoning_is_exact_or_rejected_before_provider(binding, provider, monkeypatch, rewrite):
    import providers
    from providers.base import ProviderProfile
    from agent_native.model_runtime import bind_reasoning
    from hermes_cli.plugins import get_plugin_manager
    providers.list_providers()
    class FixtureProfile(ProviderProfile):
        def supported_reasoning_efforts(self, model):
            return ('low', 'high')
        def build_api_kwargs_extras(self, *, reasoning_config=None, **context):
            return ({'reasoning': dict(reasoning_config)} if reasoning_config else {}), {}
    monkeypatch.setitem(providers._REGISTRY, 'openai-compat', FixtureProfile(name='openai-compat'))
    agent = make_agent(binding)
    agent.reasoning_config = {'enabled': True, 'effort': 'low'}
    agent._disable_streaming = True
    bind_reasoning(agent, {'provider': 'openai-compat', 'model': 'test-model', 'reasoning_effort': 'low'})
    def middleware(request, next_call, **context):
        changed = dict(request)
        if rewrite:
            extra = dict(changed.get('extra_body') or {})
            if rewrite == 'missing':
                extra.pop('reasoning', None)
            else:
                extra['reasoning'] = {'enabled': True, 'effort': rewrite}
            changed['extra_body'] = extra
        return next_call(changed)
    monkeypatch.setitem(get_plugin_manager()._middleware, 'llm_execution', [middleware])
    result = agent.run_conversation('Describe your purpose.')
    if rewrite is None:
        assert len(provider.requests) == 1
        assert provider.requests[0]['reasoning']['effort'] == 'low'
        assert result.get('final_response') == provider.text
    else:
        assert provider.requests == [], 'Changed or ignored reasoning must fail before paid I/O'
        assert result.get('interrupted') or result.get('error')
