"""Exact managed reasoning controls over native provider capabilities."""
from agent.reasoning_effort import EFFORT_LADDER, OPENAI_COMPAT_WIRE_EFFORTS, codex_supported_efforts
from hermes_cli import runtime_provider
from providers import get_provider_profile


def get_reasoning_options(provider, model):
    """Describe exact supported controls without inference or credential resolution.

    Unknown capabilities remain usable through Runtime automatic. They are not
    permission to guess a reasoning vocabulary from a model name.
    """
    provider = str(provider or '').strip().lower()
    model = str(model or '').strip()
    supported = None
    mode = None
    if provider in {'openai-codex', 'codex', 'openai_codex'}:
        from hermes_cli.codex_models import DEFAULT_CODEX_MODELS
        from agent.model_metadata import strip_codex_context_variant_suffix
        bare = strip_codex_context_variant_suffix(model).rsplit('/', 1)[-1]
        if bare in DEFAULT_CODEX_MODELS or bare == 'gpt-6-astra':
            supported = codex_supported_efforts(bare)
        mode = 'codex_responses'
    else:
        entry = runtime_provider._get_named_custom_provider(provider)
        profile = get_provider_profile('custom' if entry else provider)
        mode = (entry or {}).get('api_mode') or (profile.api_mode if profile else None)
        if profile and mode != 'anthropic_messages':
            try:
                supported = profile.supported_reasoning_efforts(model)
            except Exception:
                supported = None
        if provider in {'openrouter', 'nous'}:
            from hermes_cli.models_reasoning_caps import (
                openrouter_model_reasoning_capabilities, nous_model_reasoning_capabilities,
            )
            read = openrouter_model_reasoning_capabilities if provider == 'openrouter' else nous_model_reasoning_capabilities
            caps = read(model, allow_fetch=False)
            if caps and caps.get('supports_reasoning') and caps.get('supported_efforts'):
                supported = caps['supported_efforts']
                if caps.get('mandatory'):
                    supported = [effort for effort in supported if effort != 'none']
            # Native OpenRouter maps modern Claude reasoning onto verbosity.
            # That is a different setting, not an exact reasoning-effort wire.
            if provider == 'openrouter' and ('claude' in model.lower() or model.lower().startswith('anthropic/')):
                supported = None
    if not isinstance(supported, (tuple, list)):
        supported = None
    allowed = set(OPENAI_COMPAT_WIRE_EFFORTS)
    if mode == 'codex_responses':
        # Native disable omits reasoning on this wire; do not label it "none".
        allowed.discard('none')
    efforts = [effort for effort in EFFORT_LADDER if effort in allowed and effort in (supported or ())]
    return {
        'efforts': ['default', *efforts], 'default_label': 'Runtime automatic',
        'message': None if efforts else 'Exact reasoning controls are not declared for this route. Runtime automatic remains available.',
    }


def validate_reasoning(choice):
    if not isinstance(choice, dict):
        raise ValueError('Choose model settings')
    effort = choice.get('reasoning_effort', 'default')
    if not isinstance(effort, str) or not effort.strip():
        raise ValueError('Choose a reasoning effort')
    effort = effort.strip().lower()
    if effort == 'default':
        return effort
    options = get_reasoning_options(choice.get('provider'), choice.get('model'))
    if effort not in options['efforts']:
        raise ValueError('This reasoning effort is not supported exactly by the selected provider and model')
    return effort


def reasoning_config(selection):
    """Translate an admitted selection; default retains native Hermes behavior."""
    effort = validate_reasoning(selection)
    return None if effort == 'default' else {'enabled': effort != 'none', 'effort': effort}


def bind_reasoning(agent, selection):
    """Freeze the requested effort independently of mutable native session state."""
    effort = selection.get('reasoning_effort', 'default')
    agent._managed_reasoning_effort = None if effort == 'default' else effort
    return agent


def _wire_efforts(request):
    efforts = []
    containers = [request]
    if isinstance(request.get('extra_body'), dict):
        containers.append(request['extra_body'])
    for body in containers:
        if 'reasoning_effort' in body:
            efforts.append(body['reasoning_effort'])
        if 'reasoning' in body:
            value = body['reasoning']
            efforts.append(('none' if value.get('enabled') is False else value.get('effort'))
                           if isinstance(value, dict) else None)
    return efforts


def assert_request_reasoning(agent, request):
    """Reject implicit native clamps or middleware changes to an explicit choice."""
    expected = getattr(agent, '_managed_reasoning_effort', None)
    if expected is None:
        return
    current = getattr(agent, 'reasoning_config', None)
    current_effort = (('none' if current.get('enabled') is False else current.get('effort'))
                      if isinstance(current, dict) else None)
    wire = _wire_efforts(request)
    if current_effort != expected or not wire or any(value != expected for value in wire):
        agent.interrupt('Managed reasoning selection changed before the provider request', hard_cancel=True)
        raise InterruptedError('Managed reasoning effort must reach the provider exactly as selected')
