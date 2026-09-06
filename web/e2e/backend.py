"""Real dashboard backend, disposable storage and an external Plane HTTP fixture.

The fixture controls below exist only in this test entry point. Production routers
never expose configuration injection or fixture evidence.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
for key in list(os.environ):
    if key.startswith('HERMES_') or key.endswith(('_API_KEY', '_TOKEN', '_SECRET', '_PASSWORD')):
        os.environ.pop(key, None)

from tests.hermes_cli.test_agent_native_plane_setup import plane_server

from native_chat_fixture import configure_native_chat, native_model_server

with tempfile.TemporaryDirectory(prefix='agent-native-e2e-') as home, plane_server() as plane, native_model_server() as model:
    os.environ.update(HERMES_HOME=home, HERMES_KANBAN_HOME=home,
                      HERMES_KANBAN_DB=str(Path(home) / 'kanban.db'),
                      HERMES_DASHBOARD_SESSION_TOKEN='agent-native-local-e2e-only')
    configure_native_chat(home, model)
    from fastapi import Request
    from hermes_cli.web_server import app, _require_token
    # Match dashboard launch metadata: native TUI attaches to this service's
    # existing gateway instead of spawning an unrelated stdio gateway.
    app.state.bound_host = '127.0.0.1'
    app.state.bound_port = 19219

    @app.put('/__e2e__/plane-config')
    def configure_plane(request: Request, body: dict):
        _require_token(request)
        folder = Path(home) / 'agent-native'
        folder.mkdir(mode=0o700, exist_ok=True)
        folder.chmod(0o700)
        path = folder / 'plane-setup.json'
        if body.get('enabled') is True:
            path.write_text(json.dumps(plane.config))
            path.chmod(0o600)
        else:
            path.unlink(missing_ok=True)
        return {'configured': path.exists()}

    @app.get('/__e2e__/plane-evidence/{agent_id}')
    def planning_evidence(request: Request, agent_id: str):
        _require_token(request)
        workspaces = [w for w in plane.workspaces.values() if w['slug'] == 'an-' + agent_id.replace('-', '')]
        projects = [p for p in plane.projects.values() if p.get('external_id') == agent_id]
        items = [i for i in plane.items.values() if i['project'] in {p['id'] for p in projects}]
        return {'workspace_count': len(workspaces), 'managed_project_count': len(projects),
                'private': len(projects) == 1 and projects[0]['network'] == 0,
                'discovery_count': len(items), 'discovery_id': items[0]['id'] if len(items) == 1 else None}

    # Register the test-only GET before the production SPA catch-all.
    app.router.routes.insert(0, app.router.routes.pop())

    @app.get('/__e2e__/native-chat-evidence')
    def native_chat_evidence(request: Request):
        _require_token(request)
        from tui_gateway import server
        with server._sessions_lock:
            records = list(server._sessions.items())
        sessions = [s for _, s in records]
        native_ready_session_ids = [sid for sid, s in records if s.get('source') == 'tui'
                                    and not s.get('managed_chat') and s.get('agent') is not None
                                    and s.get('agent_ready') is not None and s['agent_ready'].is_set()
                                    and not s.get('agent_error')]
        ready = bool(native_ready_session_ids)
        managed_ready_ids = [s['managed_chat'].agent_id for s in sessions
                             if s.get('managed_chat') and s.get('agent') is not None and not s.get('agent_error')]
        return {'ready': ready, 'native_ready_session_ids': native_ready_session_ids, 'managed_ready_ids': managed_ready_ids, 'model_requests': list(model.requests)}

    app.router.routes.insert(0, app.router.routes.pop())

    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=19219, log_level='warning')
