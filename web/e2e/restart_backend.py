"""Real disposable dashboard child for full-service restart acceptance.

The parent supplies only the private home and port. Dashboard authentication is
minted by normal production startup; it is never fixed or copied across restarts.
"""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys
import threading
from urllib.parse import quote
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def _watch_fixture_parent(parent_pid):

    def watch():
        while os.getppid() == parent_pid:
            threading.Event().wait(.2)
        # Emergency test teardown only: a controlled backend crash never runs
        # this branch, so it cannot disguise product child-recovery failures.
        try:
            import psutil
            for child in psutil.Process().children(recursive=True):
                try:
                    child.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        finally:
            os._exit(0)

    threading.Thread(target=watch, daemon=True, name='restart-fixture-parent-watch').start()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--home', type=Path, required=True)
    parser.add_argument('--port', type=int, default=19219)
    parser.add_argument('--startup-id', required=True)
    parser.add_argument('--parent-pid', type=int, required=True)
    args = parser.parse_args()
    home = args.home.resolve()
    _watch_fixture_parent(args.parent_pid)
    if not (home / 'config.yaml').is_file():
        raise RuntimeError('Restart fixture requires its existing private configuration')
    for key in list(os.environ):
        if key.startswith('HERMES_') or key.endswith(('_API_KEY', '_TOKEN', '_SECRET', '_PASSWORD')):
            os.environ.pop(key, None)
    os.environ.update(HERMES_HOME=str(home), HERMES_KANBAN_HOME=str(home),
                      HERMES_KANBAN_DB=str(home / 'kanban.db'))

    from fastapi import HTTPException, Request
    from hermes_cli.web_server import app, _require_token
    from managed_delivery_fixture import install_delivery_fault_fixture

    app.state.bound_host = '127.0.0.1'
    app.state.bound_port = args.port

    @app.get('/__e2e__/restart-identity')
    def startup_identity(request: Request):
        _require_token(request)
        return {'backend_pid': os.getpid(), 'startup_id': args.startup_id}

    app.router.routes.insert(0, app.router.routes.pop())

    @app.get('/__e2e__/native-chat-evidence')
    def native_evidence(request: Request):
        _require_token(request)
        from tui_gateway import server
        with server._sessions_lock:
            records = list(server._sessions.items())
        ready = [s['managed_chat'].agent_id for _, s in records
                 if s.get('managed_chat') and s.get('agent_ready') is not None
                 and s['agent_ready'].is_set() and not s.get('agent_error')]
        workers = [{'agent_id': s['managed_chat'].agent_id,
                    'message_id': s.get('_managed_receipt_id'),
                    'pid': host.pid, 'running': host.is_running()}
                   for _, s in records if s.get('managed_chat')
                   and (host := s.get('_managed_host')) is not None]
        return {'managed_ready_ids': ready, 'managed_workers': workers, 'backend_pid': os.getpid()}

    app.router.routes.insert(0, app.router.routes.pop())
    @app.get('/__e2e__/native-receipt/{agent_id}/{message_id}')
    def native_receipt(request: Request, agent_id: str, message_id: str):
        _require_token(request)
        from agent_native.chat import issue_binding
        from agent_native.identity import OWNER
        try:
            if str(UUID(message_id)) != message_id:
                raise ValueError
        except ValueError as exc:
            raise HTTPException(400, 'Use the canonical managed message UUID') from exc
        binding = issue_binding(actor=OWNER, agent_id=agent_id)
        path = home / 'state.db'
        receipt = None
        if path.is_file():
            # Observe canonical storage only. Do not construct SessionDB, invoke
            # receipt.read/_recover, or mutate recovery state to satisfy a test.
            connection = sqlite3.connect('file:' + quote(str(path), safe='/') + '?mode=ro', uri=True)
            try:
                row = connection.execute('SELECT value FROM state_meta WHERE key = ?',
                    (f'managed_prompt:{binding.session_id}:{message_id}',)).fetchone()
                receipt = json.loads(row[0]) if row is not None else None
            finally:
                connection.close()
        return {'session_id': binding.session_id, 'receipt': receipt}

    app.router.routes.insert(0, app.router.routes.pop())
    install_delivery_fault_fixture(app, _require_token, home)
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=args.port, log_level='warning')


if __name__ == '__main__':
    main()
