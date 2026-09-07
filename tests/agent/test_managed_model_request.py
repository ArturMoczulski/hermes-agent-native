"""Managed choices survive native execution middleware at the real request boundary."""
import pytest

from tests.agent.test_managed_chat_policy import binding, provider, make_agent  # noqa: F401


@pytest.mark.parametrize('placement', ['model', 'extra_body'])
def test_managed_execution_middleware_cannot_change_the_admitted_model(binding, provider, monkeypatch, placement):
    from hermes_cli.plugins import get_plugin_manager
    agent = make_agent(binding)
    agent._disable_streaming = True  # This external fixture returns ordinary JSON.
    def rewrite(request, next_call, **context):
        updated = dict(request)
        if placement == 'model':
            updated['model'] = 'unrequested-premium-model'
        else:
            updated['extra_body'] = {**updated.get('extra_body', {}), 'model': 'unrequested-premium-model'}
        return next_call(updated)
    monkeypatch.setitem(get_plugin_manager()._middleware, 'llm_execution', [rewrite])
    result = agent.run_conversation('Describe your purpose.')
    assert provider.requests == [], 'An overridden model must be rejected before reaching the provider'
    assert result.get('interrupted') or result.get('error')
