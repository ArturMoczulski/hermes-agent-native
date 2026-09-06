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

with tempfile.TemporaryDirectory(prefix='agent-native-e2e-') as home, plane_server() as plane:
    os.environ.update(HERMES_HOME=home, HERMES_KANBAN_HOME=home,
                      HERMES_KANBAN_DB=str(Path(home) / 'kanban.db'),
                      HERMES_DASHBOARD_SESSION_TOKEN='agent-native-local-e2e-only')
    from fastapi import Request
    from hermes_cli.web_server import app, _require_token

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

    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=19219, log_level='warning')
