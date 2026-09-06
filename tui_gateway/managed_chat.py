"""Trusted framework scope around the existing native gateway/session handlers."""
from contextlib import nullcontext
import threading

from agent_native.chat import Binding, lookup_session
from tui_gateway.transport import current_transport

_LOCKS = {}
_LOCKS_GUARD = threading.Lock()
_ALLOWED = frozenset({'session.create', 'session.resume', 'prompt.submit', 'session.history',
                      'session.status', 'session.interrupt', 'session.close', 'session.events'})


def binding_for_transport():
    binding = getattr(current_transport(), 'managed_chat', None)
    if binding is not None:
        if not isinstance(binding, Binding):
            raise PermissionError('Host-issued managed chat binding required')
        binding.validate()
    return binding


def metadata(binding):
    return {'id': binding.agent_id, 'name': binding.name, 'purpose': binding.purpose,
            'soul_revision': binding.soul_revision, 'mode': 'conversation_only'}


def check_session(server, target, record=None):
    binding = binding_for_transport()
    record = record or server['_sessions'].get(target)
    owner = record.get('managed_chat') if record else None
    stored = str(record.get('session_key') or target) if record else str(target)
    managed = owner is not None or (stored.startswith('an_chat_') and lookup_session(stored))
    if managed and (binding is None or binding.session_id != stored):
        raise PermissionError('Open this managed chat through its framework agent')
    if binding is not None and stored != binding.session_id:
        raise PermissionError('Managed chat cannot access another session')
    if owner is not None:
        owner.validate()
    return binding


def prepare_request(server, rid, method, params):
    """Fail closed before native handlers can mutate state or launch side work."""
    binding = binding_for_transport()
    if binding is None:
        for field in ('session_id', 'parent_session_id', 'source_session_id'):
            if target := params.get(field):
                check_session(server, target)
        return params, None
    # Minimal display-only responses keep the native composer boot path intact.
    if method == 'config.get':
        key = params.get('key')
        value = {'full': {'config': {'display': {'busy_input_mode': 'interrupt'}, 'agent': {'name': binding.name}}},
                 'mtime': {'mtime': 0, 'mcp_rev': 'managed-chat'},
                 'project': {'cwd': binding.workspace, 'branch': ''}}
        if key not in value:
            raise PermissionError('Setting is unavailable in managed chat')
        return params, server['_ok'](rid, value[key])
    if method == 'wake.start':
        return params, server['_ok'](rid, {'started': False, 'reason': 'disabled'})
    if method == 'commands.catalog':
        return params, server['_ok'](rid, {'pairs': [], 'canon': {}, 'categories': [], 'sub': {}, 'skill_count': 0})
    if method == 'setup.status':
        return {}, None
    if method not in _ALLOWED:
        raise PermissionError(f'{method} is unavailable in managed chat')
    if method in {'session.create', 'session.resume'}:
        allowed = {'cols'} if method == 'session.create' else {'cols', 'session_id', 'defer_history', 'omit_messages'}
        if set(params) - allowed:
            raise PermissionError('Managed chat session options are host-controlled')
        if method == 'session.resume' and params.get('session_id') != binding.session_id:
            raise PermissionError('Managed chat cannot resume another session')
        return {'cols': params.get('cols', 80), 'session_id': binding.session_id}, None
    target = params.get('session_id')
    if not target:
        raise PermissionError('Managed chat session is required')
    check_session(server, target)
    if method == 'prompt.submit':
        if set(params) - {'session_id', 'text', 'queued'}:
            raise PermissionError('Managed chat accepts plain owner messages only')
        if not isinstance(params.get('text'), str) or not params['text'].strip():
            raise ValueError('Message must contain text')
        if len(params['text']) > 32000:
            raise ValueError('Message is too long for this early managed chat')
        return {'session_id': target, 'text': params['text']}, None
    return params, None


def create_or_resume(server, rid, params, create):
    binding = binding_for_transport()
    if binding is None:
        return create(rid, params)
    with _LOCKS_GUARD:
        lock = _LOCKS.setdefault(binding.session_id, threading.RLock())
    with lock:
        binding.validate()
        live = server['_find_live_session_by_key'](binding.session_id, None)
        db = server['_get_db']()
        if live is not None or (db is not None and db.get_session(binding.session_id)):
            return server['_methods']['session.resume'](rid, {'session_id': binding.session_id, 'cols': params.get('cols', 80)})
        return create(rid, {'cols': params.get('cols', 80), 'cwd': binding.workspace})


def construction_scope(binding):
    if binding is None:
        return nullcontext()
    from agent.managed_chat_policy import bind_managed_chat
    return bind_managed_chat(binding)


def make_agent(server, binding, key, session_db=None):
    """Construct Hermes's actual engine with provider credentials kept in the host."""
    from run_agent import AIAgent
    binding.validate()
    model, runtime = server['_resolve_agent_model_runtime'](None, None)
    db = session_db if session_db is not None else server['_get_db']()
    if db is None:
        raise RuntimeError('Native managed chat storage is unavailable')
    db.ensure_session(key, source='tui', cwd=binding.workspace)
    # Native title provenance suppresses the optional model-generated title.
    # Native de-duplication permits multiple agents/revisions with the same name.
    if db.get_session_title_source(key) != 'user':
        title = ' '.join(binding.name.split())[:80]
        try:
            db.set_session_title(key, title)
        except ValueError:
            db.set_session_title(key, db.get_next_title_in_lineage(title))
    with construction_scope(binding):
        return AIAgent(model=model, provider=runtime.get('provider'), base_url=runtime.get('base_url'),
                       api_key=runtime.get('api_key'), api_mode=runtime.get('api_mode'),
                       credential_pool=runtime.get('credential_pool'), session_id=key,
                       session_db=db,
                       enabled_toolsets=[], skip_context_files=True, load_soul_identity=False,
                       skip_memory=True, skip_background_review=True, checkpoints_enabled=False,
                       save_trajectories=False, max_iterations=2, max_tokens=2048, run_budget_seconds=90,
                       quiet_mode=True, ephemeral_system_prompt=binding.purpose)


def issue_turn_permit(session):
    if not session.get('managed_chat'):
        return None
    session['managed_chat'].validate()
    permit = object()
    session['_managed_chat_permit'] = permit
    return permit


def admit_turn(session, permit):
    binding = session.get('managed_chat')
    if binding is None:
        return
    binding.validate()
    with session['history_lock']:
        if permit is None or session.pop('_managed_chat_permit', None) is not permit:
            raise PermissionError('Managed chat requires a new owner message; automatic work is not enabled')
    if session.get('session_key') != binding.session_id:
        raise PermissionError('Managed chat session identity changed')


_CONTENT_EVENTS = frozenset({'message.delta', 'message.interim', 'message.complete',
                             'reasoning.delta', 'thinking.delta'})


def filter_event(server, frame):
    """Stop stale model output before either live delivery or native replay records it."""
    if frame.get('method') != 'event':
        return frame
    params = frame.get('params') or {}
    session = server['_sessions'].get(params.get('session_id'))
    binding = session.get('managed_chat') if session else None
    if binding is None or params.get('type') not in _CONTENT_EVENTS:
        return frame
    with session.setdefault('_managed_chat_event_lock', threading.RLock()):
        if session.get('_managed_chat_obsolete'):
            return None
        try:
            binding.validate()
        except (PermissionError, ValueError) as exc:
            session['_managed_chat_obsolete'] = True
            if agent := session.get('agent'):
                agent.interrupt('Managed chat authority changed', hard_cancel=True)
            return server['_event_frame']('message.complete', params['session_id'], {
                'text': 'This conversation stopped because its authority changed. Reopen the agent chat to continue.',
                'status': 'error', 'error': str(exc)})
    return frame
