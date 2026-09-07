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

from tests.hermes_cli.writer_plane_fixture import writer_plane_server as plane_server

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

    @app.post('/__e2e__/expire-managed-renderer')
    async def expire_managed_renderer(request: Request, body: dict):
        _require_token(request)
        from agent_native.chat import issue_binding
        from agent_native.identity import OWNER
        from hermes_cli.web_server_chat import PTY_REGISTRY
        binding = issue_binding(actor=OWNER, agent_id=body['agent_id'])
        token = body.get('attach_token')
        if not isinstance(token, str) or len(token) != 32 or any(c not in '0123456789abcdef' for c in token):
            from fastapi import HTTPException
            raise HTTPException(400, 'Invalid test browser attach token')
        key = f'{token}\0agent\0{binding.session_id}'
        session = PTY_REGISTRY._sessions.pop(key, None)
        if session is not None:
            await session.close()
        return {'expired': int(session is not None)}

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
        # Managed gateway sessions hold routing metadata. Their actual AIAgent
        # lives only in the per-message ComputeHost, after owner submission.
        managed_ready_ids = [s['managed_chat'].agent_id for s in sessions
                             if s.get('managed_chat') and s.get('agent_ready') is not None
                             and s['agent_ready'].is_set() and not s.get('agent_error')]
        managed_workers = [{'agent_id': s['managed_chat'].agent_id,
                            'message_id': s.get('_managed_receipt_id'),
                            'pid': host.pid, 'running': host.is_running()}
                           for s in sessions if s.get('managed_chat')
                           and (host := s.get('_managed_host')) is not None]
        return {'ready': ready, 'native_ready_session_ids': native_ready_session_ids,
                'managed_ready_ids': managed_ready_ids, 'managed_workers': managed_workers,
                'model_requests': list(model.requests)}

    app.router.routes.insert(0, app.router.routes.pop())

    @app.patch('/__e2e__/planning-control/{agent_id}')
    def planning_control(request: Request, agent_id: str, body: dict):
        """Alter only the external Plane fixture; production state stays real."""
        _require_token(request)
        from threading import Event
        projects = [p for p in plane.projects.values() if p.get('external_id') == agent_id]
        if len(projects) != 1:
            from fastapi import HTTPException
            raise HTTPException(404, 'Fixture project not found')
        project = projects[0]
        slug = next(w['slug'] for w in plane.workspaces.values() if w['id'] == project['workspace'])
        path = f'/api/v1/workspaces/{slug}/projects/{project["id"]}/'
        item = plane.items.get(body.get('item_id'))
        if item and item['project'] == project['id']:
            if 'description_html' in body:
                item['description_html'] = body['description_html']
            if body.get('delete_item'):
                del plane.items[item['id']]
        if 'outage' in body:
            if body['outage']:
                plane.overrides['GET', path] = lambda _: (503, {}, {'error': 'Fixture Plane unavailable'})
            else:
                plane.overrides.pop(('GET', path), None)
        if not hasattr(plane, 'planning_holds'):
            plane.planning_holds = {}
        if body.get('hold'):
            hold = plane.planning_holds[agent_id] = {'entered': Event(), 'release': Event()}
            def delayed(_):
                hold['entered'].set()
                hold['release'].wait(15)
                return 200, {}, project
            plane.overrides['GET', path] = delayed
        if body.get('release') and agent_id in plane.planning_holds:
            plane.planning_holds[agent_id]['release'].set()
            plane.overrides.pop(('GET', path), None)
        hold = plane.planning_holds.get(agent_id)
        return {'hold_entered': bool(hold and hold['entered'].is_set()),
                'project_gets': sum(r['method'] == 'GET' and r['path'] == path for r in plane.requests)}

    @app.get('/__e2e__/writer-evidence/{agent_id}')
    def writer_evidence(request: Request, agent_id: str):
        _require_token(request)
        from agent_native.work_state import read_work
        from hermes_cli.kanban_db_connect import connect_closing
        from hermes_state import SessionDB
        with connect_closing(Path(home)/'kanban.db') as conn:
            work = read_work(conn,agent_id)
            pid = conn.execute('SELECT worker_pid FROM agent_native_work_runs WHERE agent_id=?',(agent_id,)).fetchone()
        alive = False
        if pid and pid[0]:
            try:
                os.kill(pid[0],0)
                alive = True
            except ProcessLookupError:
                pass
        projects = [p for p in plane.projects.values() if p.get('external_id')==agent_id]
        project_ids = {p['id'] for p in projects}
        outputs = (work.get('outputs') or work.get('stories') or []) if work else []
        content = (Path(home)/'agent-native'/'agents'/agent_id/'workspace'/outputs[0]['relative_path']).read_text() if outputs else None
        with SessionDB(Path(home)/'state.db') as db:
            messages = db.get_messages_as_conversation(work['session_id']) if work else []
        return {'worker_alive':alive,'file_content':content,
                'items':[i for i in plane.items.values() if i['project'] in project_ids],
                'cycles':[c for c in plane.cycles.values() if c['project'] in project_ids],
                'comments':[c for c in plane.comments.values() if c['project'] in project_ids],
                'native_roles':[m['role'] for m in messages],
                'model_requests':list(getattr(model, 'writer_requests', []))}

    app.router.routes.insert(0, app.router.routes.pop())

    from managed_delivery_fixture import install_delivery_fault_fixture
    install_delivery_fault_fixture(app, _require_token, home)

    from managed_deadline_fixture import install_deadline_fixture
    install_deadline_fixture(app, _require_token, home, model)

    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=19219, log_level='warning')
