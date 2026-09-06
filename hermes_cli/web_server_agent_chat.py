"""Owner-authenticated framework selection around the existing native chat launcher."""
from fastapi import HTTPException

from agent_native.chat import issue_binding
from agent_native.identity import OWNER, ConflictError


def resolve_chat_binding(query):
    # Invoked only after the dashboard's existing owner WebSocket gate succeeds.
    if 'agent' not in query:
        return None
    if not query['agent'] or any(query.get(key) for key in ('profile', 'resume', 'fresh')):
        raise HTTPException(400, 'Agent conversation identity is selected by the framework')
    try:
        binding = issue_binding(actor=OWNER, agent_id=query['agent'])
        expected = query.get('purpose_revision')
        if expected is not None and expected != str(binding.soul_revision):
            raise ConflictError('Agent purpose changed; reopen its conversation')
        return binding
    except KeyError as exc:
        raise HTTPException(404, 'Agent not found') from exc
    except (PermissionError, ConflictError, ValueError) as exc:
        raise HTTPException(409, str(exc)) from exc


def bind_chat_renderer(env, binding):
    from hermes_cli.web_server_chat import _server_internal_ws_url
    binding.validate()
    gateway_url = _server_internal_ws_url('/api/ws', agent=binding.agent_id, purpose_revision=str(binding.soul_revision))
    if gateway_url is None:
        raise HTTPException(503, 'Agent chat requires the running dashboard gateway')
    # Renderer connects to the host engine, which retains provider credentials.
    # Native create resolves the durable binding; browser resume never picks it.
    env = dict(env or {})
    env.pop('HERMES_TUI_RESUME', None)
    from hermes_cli.web_server_sessions import _open_session_db_for_profile
    db = _open_session_db_for_profile(None, read_only=True)
    try:
        if db.get_session(binding.session_id) is not None:
            env['HERMES_TUI_RESUME'] = binding.session_id
    finally:
        db.close()
    env['HERMES_TUI_GATEWAY_URL'] = gateway_url
    return env
