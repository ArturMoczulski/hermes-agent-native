"""Authenticated deadline controls installed only by the disposable E2E server."""
from math import isfinite
from pathlib import Path
import re
from threading import Lock

from fastapi import HTTPException, Request
import yaml


def install_deadline_fixture(app, require_token, home, model):
    config_lock = Lock()

    def marker_from(value):
        if not isinstance(value, str) or re.fullmatch(r'[A-Za-z0-9_-]{1,100}', value) is None:
            raise HTTPException(400, 'Use a unique ASCII model hold marker')
        return value

    @app.post('/__e2e__/managed-deadline-config')
    def configure(request: Request, body: dict):
        require_token(request)
        seconds = body.get('timeout_seconds', 90)
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not isfinite(seconds) or seconds <= 0:
            raise HTTPException(400, 'timeout_seconds must be a positive finite number')
        with config_lock:
            path = Path(home) / 'config.yaml'
            config = yaml.safe_load(path.read_text()) or {}
            config.setdefault('agent_native', {})['managed_chat_timeout_seconds'] = seconds
            temporary = path.with_name('config.deadline-fixture.tmp')
            temporary.write_text(yaml.safe_dump(config))
            temporary.chmod(0o600)
            temporary.replace(path)
        return {'managed_chat_timeout_seconds': seconds}

    @app.post('/__e2e__/hold-model')
    def hold(request: Request, body: dict):
        require_token(request)
        marker = marker_from(body.get('marker'))
        try:
            return model.holds.arm(marker)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.post('/__e2e__/release-model')
    def release(request: Request, body: dict):
        require_token(request)
        marker = marker_from(body.get('marker'))
        try:
            return model.holds.release(marker)
        except KeyError as exc:
            raise HTTPException(404, 'Model hold not found') from exc

    @app.get('/__e2e__/model-holds/{marker}')
    def evidence(request: Request, marker: str):
        require_token(request)
        try:
            return model.holds.evidence(marker_from(marker))
        except KeyError as exc:
            raise HTTPException(404, 'Model hold not found') from exc

    # GET fixture evidence must precede the production SPA catch-all.
    app.router.routes.insert(0, app.router.routes.pop())
