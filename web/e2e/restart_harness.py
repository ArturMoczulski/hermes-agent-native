"""Stable external fixtures around an actually restarted dashboard subprocess.

Only this disposable entrypoint exposes lifecycle controls. A stop kills the
owned backend alone, and records surviving descendants instead of cleaning them
up to make acceptance pass. Final harness teardown reaps any recorded leftovers.
"""
from contextlib import contextmanager
import hmac
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
import time
from urllib.error import URLError
from urllib.request import Request as URLRequest, urlopen
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException, Request
import psutil
import uvicorn

from managed_deadline_fixture import install_deadline_fixture
from native_chat_fixture import configure_native_chat, native_model_server

CONTROL_TOKEN = 'agent-native-restart-control-e2e-only'
CONTROL_PORT = 19218
BACKEND_PORT = 19219


def require_control(request):
    supplied = request.headers.get('X-Hermes-Fixture-Token', '')
    if not hmac.compare_digest(supplied, CONTROL_TOKEN):
        raise HTTPException(401, 'Restart fixture token required')


def _identity(process, *, backend_pid):
    try:
        argv = process.cmdline()
        name = process.name()
        role = ('backend' if process.pid == backend_pid else
                'managed_worker' if 'tui_gateway.compute_host' in argv else
                'renderer' if argv and Path(argv[0]).name == 'node' else 'descendant')
        return {'pid': process.pid, 'created_at': process.create_time(), 'role': role, 'name': name}
    except psutil.NoSuchProcess:
        return None


def _same_process(identity):
    try:
        process = psutil.Process(identity['pid'])
        return process if process.create_time() == identity['created_at'] else None
    except psutil.NoSuchProcess:
        return None


def _evidence(identity):
    try:
        process = _same_process(identity)
        return {**identity, 'alive': process is not None}
    except psutil.AccessDenied:
        # Inability to inspect an owned PID is not proof of its disappearance.
        return {**identity, 'alive': True, 'inspection_error': 'access_denied'}


class RestartService:
    def __init__(self, home):
        self.home = Path(home)
        self.home_id = uuid4().hex
        self.generation = 0
        self.process = None
        self.previous = []
        self.observed = {}
        self.lock = threading.RLock()

    def processes(self):
        process = self.process
        if process is not None and process.poll() is None:
            try:
                parent = psutil.Process(process.pid)
                family = [parent, *parent.children(recursive=True)]
            except psutil.NoSuchProcess:
                family = []
            for member in family:
                identity = _identity(member, backend_pid=process.pid)
                if identity is not None:
                    self.observed[(identity['pid'], identity['created_at'])] = identity
        return [_evidence(identity) for identity in self.observed.values()]

    def status(self):
        with self.lock:
            previous = [_evidence(identity) for identity in self.previous]
            return {'generation': self.generation, 'home_id': self.home_id,
                    'backend_pid': self.process.pid if self.process is not None else None,
                    'backend_alive': self.process is not None and self.process.poll() is None,
                    'previous_processes': previous,
                    'survivors': [identity for identity in previous if identity['alive']]}

    def start(self):
        with self.lock:
            if self.process is not None and self.process.poll() is None:
                raise HTTPException(409, 'The fixture backend is already running')
            if self.status()['survivors']:
                raise HTTPException(409, 'Old owned processes still exist; inspect restart status')
            env = {key: value for key, value in os.environ.items()
                   if not key.startswith('HERMES_')
                   and not key.endswith(('_API_KEY', '_TOKEN', '_SECRET', '_PASSWORD'))}
            startup_id = uuid4().hex
            # The child establishes HERMES_HOME and lets production mint a token.
            self.process = subprocess.Popen(
                [sys.executable, str(Path(__file__).with_name('restart_backend.py')),
                 '--home', str(self.home), '--port', str(BACKEND_PORT), '--startup-id', startup_id,
                 '--parent-pid', str(os.getpid())],
                cwd=str(ROOT), env=env, stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
            self.generation += 1
            self.observed = {}
            deadline = time.monotonic() + 45
            while time.monotonic() < deadline:
                if self.process.poll() is not None:
                    raise HTTPException(503, 'Restart fixture backend exited during startup')
                try:
                    # Obtain the token exactly as the real browser/dev proxy does:
                    # normal dashboard HTML, never an injected fixed credential.
                    with urlopen(f'http://127.0.0.1:{BACKEND_PORT}/', timeout=.5) as response:
                        html = response.read().decode('utf-8')
                    token = re.search(r'window\.__HERMES_SESSION_TOKEN__\s*=\s*"([^"]+)"', html)
                    if token is not None:
                        request = URLRequest(f'http://127.0.0.1:{BACKEND_PORT}/__e2e__/restart-identity',
                                             headers={'X-Hermes-Session-Token': token.group(1)})
                        with urlopen(request, timeout=.5) as response:
                            identity = json.load(response)
                        if identity == {'backend_pid': self.process.pid, 'startup_id': startup_id}:
                            return self.status()
                except (OSError, URLError, ValueError):
                    pass
                time.sleep(.05)
            raise HTTPException(503, 'Restart fixture backend did not become healthy')

    def stop(self):
        with self.lock:
            # Snapshot concrete process identities while the parent relation still
            # exists. Reparented children remain identifiable by PID + creation time.
            self.processes()
            if self.process is not None and self.process.poll() is None:
                self.previous = list(self.observed.values())
                self.process.kill()
                self.process.wait(timeout=5)
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline and self.status()['survivors']:
                time.sleep(.05)
            return self.status()

    def cleanup(self):
        with self.lock:
            self.processes()
            all_owned = {(item['pid'], item['created_at']): item
                         for item in [*self.previous, *self.observed.values()]}
            # Emergency teardown only, after the test could inspect survivors.
            for identity in all_owned.values():
                try:
                    if process := _same_process(identity):
                        process.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            if self.process is not None:
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass


@contextmanager
def fixture_app():
    with tempfile.TemporaryDirectory(prefix='agent-native-restart-e2e-') as home, native_model_server() as model:
        configure_native_chat(home, model)
        service = RestartService(home)
        app = FastAPI()

        @app.get('/__e2e__/health')
        def health():
            return {'ready': True}

        @app.get('/__e2e__/restart/status')
        def status(request: Request):
            require_control(request)
            return service.status()

        @app.get('/__e2e__/processes')
        def processes(request: Request):
            require_control(request)
            with service.lock:
                return {'processes': service.processes()}

        @app.post('/__e2e__/restart/stop')
        def stop(request: Request, body: dict):
            require_control(request)
            if body.get('mode', 'crash') != 'crash':
                raise HTTPException(400, 'This acceptance fixture supports actual backend crash only')
            return service.stop()

        @app.post('/__e2e__/restart/start')
        def start(request: Request, body: dict):
            require_control(request)
            return service.start()

        @app.get('/__e2e__/model-requests')
        def requests(request: Request):
            require_control(request)
            return {'model_requests': list(model.requests)}

        install_deadline_fixture(app, require_control, home, model)
        try:
            service.start()
            yield app
        finally:
            model.holds.release_all()
            service.cleanup()


def main():
    with fixture_app() as app:
        uvicorn.run(app, host='127.0.0.1', port=CONTROL_PORT, log_level='warning')


if __name__ == '__main__':
    main()
