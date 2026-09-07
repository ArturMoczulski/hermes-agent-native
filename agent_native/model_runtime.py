"""Explicit managed-agent model selection using host-owned Hermes connections.

Selection records contain names only. Authentication remains in the native
provider resolver; it must never replace an unavailable choice with a fallback.
"""
from hermes_cli import config as native_config
from hermes_cli import auth
from hermes_cli import runtime_provider
from hermes_cli.providers import custom_provider_slug
from agent_native.reasoning import (
    get_reasoning_options, validate_reasoning, reasoning_config, bind_reasoning, assert_request_reasoning,
)

_SUPPORTED_MODES = frozenset({'chat_completions', 'codex_responses', 'anthropic_messages'})


def _text(value, field):
    if (not isinstance(value, str) or not value.strip() or len(value) > 256
            or any(ord(char) < 32 for char in value)):
        raise ValueError(f'Choose an explicit {field}')
    return value.strip()


def validate_choice(choice):
    """Validate configured connection identity without discovery or inference.

    Model IDs may be newer than a cached catalog. Their availability is checked
    by the chosen provider at execution, never by sending a paid validation call.
    """
    if not isinstance(choice, dict):
        raise ValueError('Choose a provider and model')
    provider = _text(choice.get('provider'), 'provider').lower()
    model = _text(choice.get('model'), 'model')
    if provider in {'auto', 'moa'}:
        raise ValueError('Choose one explicit configured model provider')
    entry = runtime_provider._get_named_custom_provider(provider)
    if entry:
        if entry.get('api_mode') and entry['api_mode'] not in _SUPPORTED_MODES:
            raise ValueError('This connection does not support managed agent execution')
        return {'provider': custom_provider_slug(entry['name'], entry.get('provider_key', '')), 'model': model}
    if provider == 'custom' or provider.startswith('custom:'):
        raise ValueError('Choose a configured named custom provider')
    try:
        provider = auth.resolve_provider(provider)
    except auth.AuthError as exc:
        raise ValueError('Choose a configured model provider') from exc
    if provider == 'custom' or not auth.is_provider_explicitly_configured(provider):
        raise ValueError('Configure this model provider in Hermes before selecting it')
    definition = auth.PROVIDER_REGISTRY.get(provider)
    if definition and definition.auth_type == 'external_process':
        raise ValueError('External agent runtimes are not supported for managed agents')
    config = native_config.load_config()
    configured = (config.get('providers') or {}).get(provider)
    if isinstance(configured, dict) and not native_config.is_provider_enabled(configured):
        raise ValueError('This model provider is disabled')
    native_model = config.get('model')
    if (provider in {'openai', 'openai-codex'} and isinstance(native_model, dict)
            and native_model.get('openai_runtime') == 'codex_app_server'):
        raise ValueError('Use the native model API connection for managed agents')
    return {'provider': provider, 'model': model}


def profile_default():
    """Read an explicit native default without probing endpoints or credentials."""
    model_config = native_config.load_config().get('model')
    if not isinstance(model_config, dict):
        return {'provider': '', 'model': ''}
    value = model_config.get('default') or model_config.get('model') or model_config.get('name')
    if isinstance(value, dict):
        model, embedded_provider = native_config.split_model_config_default(value)
    else:
        model, embedded_provider = value, None
    provider = model_config.get('provider') or embedded_provider
    if not isinstance(provider, str) or provider.strip().lower() in {'', 'auto'} or not model:
        return {'provider': '', 'model': ''}
    try:
        return validate_choice({'provider': provider, 'model': model})
    except ValueError:
        return {'provider': '', 'model': ''}


def resolve_selection(selection):
    """Resolve exactly the admitted pair; never use native auth fallback models."""
    choice = validate_choice(selection)
    provider, model = choice['provider'], choice['model']
    runtime = runtime_provider.resolve_runtime_provider(requested=provider, target_model=model, strict_requested=True)
    expected_runtime_provider = 'custom' if provider.startswith('custom:') else provider
    if runtime.get('provider') != expected_runtime_provider:
        raise ValueError('Configured connection resolved to a different provider; execution was not started')
    if runtime.get('api_mode') not in _SUPPORTED_MODES or runtime.get('command'):
        raise ValueError('This connection does not support managed agent execution')
    # Named custom connections preserve their identity even though their native
    # wire provider is the shared OpenAI-compatible "custom" transport.
    runtime['requested_provider'] = provider
    return model, runtime


def assert_request_model(agent, request):
    """Keep the managed pair fixed after middleware, immediately before I/O."""
    if (getattr(agent, '_managed_chat_binding', None) is None
            and getattr(agent, '_work_context', None) is None):
        return
    admitted = getattr(agent, '_managed_model_choice', None)
    extra = request.get('extra_body') if isinstance(request, dict) else None
    current = (getattr(agent, 'model', None), getattr(agent, 'provider', None))
    if (admitted is None or current != admitted or not isinstance(request, dict)
            or request.get('model') != admitted[0]
            or (isinstance(extra, dict) and 'model' in extra and extra['model'] != admitted[0])):
        agent.interrupt('Managed model selection changed before the provider request', hard_cancel=True)
        raise InterruptedError('Managed model selection cannot change during an admitted attempt')

    assert_request_reasoning(agent, request)
