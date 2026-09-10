"""Stable static previews rooted inside an explicitly granted project workspace."""

from pathlib import Path, PurePosixPath
import secrets
from threading import Lock
import time

from agent_native.identity import _now, _require_owner
from hermes_cli.kanban_db_connect import write_txn

SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_native_project_previews (
 agent_id TEXT PRIMARY KEY REFERENCES agent_native_agents(id),
 relative_root TEXT NOT NULL,
 revision INTEGER NOT NULL CHECK(revision > 0),
 published_at TEXT NOT NULL
);
"""

_LAUNCH_TTL_SECONDS = 30
_SESSION_TTL_SECONDS = 3600
_launches = {}
_sessions = {}
_session_lock = Lock()


def _prune(now):
    for store in (_launches, _sessions):
        for key, value in list(store.items()):
            if value[1] <= now:
                store.pop(key, None)


def mint_launch(agent_id):
    """Create one short-lived, single-use launch ticket bound to one preview."""
    ticket, now = secrets.token_urlsafe(32), time.monotonic()
    with _session_lock:
        _prune(now)
        _launches[ticket] = (agent_id, now + _LAUNCH_TTL_SECONDS)
    return ticket


def exchange_launch(agent_id, ticket):
    """Consume a ticket and return an opaque preview-only browser session."""
    now = time.monotonic()
    with _session_lock:
        _prune(now)
        value = _launches.pop(ticket, None)
        if value is None or value[0] != agent_id:
            raise PermissionError('Preview launch is invalid or expired')
        session = secrets.token_urlsafe(32)
        _sessions[session] = (agent_id, now + _SESSION_TTL_SECONDS)
        return session


def authorize_session(agent_id, session):
    now = time.monotonic()
    with _session_lock:
        _prune(now)
        value = _sessions.get(session)
        if value is None or value[0] != agent_id:
            raise PermissionError('Preview session is invalid or expired')


def _relative(value):
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ValueError("Preview path must be nonblank text")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or value.startswith("~"):
        raise PermissionError("Preview path escapes the granted workspace")
    return path


def _preview_root(repository, value):
    repository = Path(repository).resolve()
    relative = _relative(value)
    current = repository
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise PermissionError("Preview symlinks are outside the workspace grant")
    if not current.is_dir() or not (current / "index.html").is_file() or (current / "index.html").is_symlink():
        raise ValueError("Preview directory must contain a regular index.html")
    if not current.resolve().is_relative_to(repository):
        raise PermissionError("Preview path escapes the granted workspace")
    return current.resolve(), str(relative)


def publish(conn, *, actor, agent_id, path):
    _require_owner(actor)
    from agent_native.project_workspace import active_repository
    root, relative = _preview_root(active_repository(conn, agent_id), path)
    now = _now()
    with write_txn(conn):
        current = conn.execute(
            "SELECT revision FROM agent_native_project_previews WHERE agent_id=?", (agent_id,)
        ).fetchone()
        revision = current[0] + 1 if current else 1
        conn.execute(
            "INSERT INTO agent_native_project_previews(agent_id,relative_root,revision,published_at) VALUES(?,?,?,?) "
            "ON CONFLICT(agent_id) DO UPDATE SET relative_root=excluded.relative_root,revision=excluded.revision,published_at=excluded.published_at",
            (agent_id, relative, revision, now),
        )
    return {"relative_root": relative, "revision": revision, "published_at": now,
            "url": f"/api/agent-native/agents/{agent_id}/preview/"}


def read(conn, agent_id):
    row = conn.execute(
        "SELECT relative_root,revision,published_at FROM agent_native_project_previews WHERE agent_id=?", (agent_id,)
    ).fetchone()
    if not row:
        raise KeyError("Project preview is not published")
    return {"relative_root": row[0], "revision": row[1], "published_at": row[2],
            "url": f"/api/agent-native/agents/{agent_id}/preview/"}


def asset(conn, agent_id, asset_path="index.html"):
    from agent_native.project_workspace import active_repository
    preview = read(conn, agent_id)
    root, _ = _preview_root(active_repository(conn, agent_id), preview["relative_root"])
    relative = _relative(asset_path or "index.html")
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise PermissionError("Preview asset escapes the published directory")
    if not current.is_file() or not current.resolve().is_relative_to(root):
        raise KeyError("Preview asset not found")
    return current.resolve()
