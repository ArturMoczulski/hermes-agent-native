"""Owner-granted repository roots for ordinary managed agents."""

from pathlib import Path

from agent_native.identity import OWNER, _now, _require_owner, get_root
from hermes_cli.kanban_db_connect import write_txn

SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_native_project_workspaces (
 agent_id TEXT PRIMARY KEY REFERENCES agent_native_agents(id),
 root TEXT NOT NULL UNIQUE,
 revision INTEGER NOT NULL CHECK(revision > 0),
 active INTEGER NOT NULL CHECK(active IN (0, 1)),
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL
);
"""


def grant(conn, *, actor, agent_id, expected_revision, root):
    _require_owner(actor)
    agent = get_root(conn, actor=OWNER, agent_id=agent_id)
    if agent["soul_revision"] != expected_revision:
        raise ValueError("Agent changed; refresh before granting a workspace")
    row = conn.execute("SELECT 1 FROM agent_native_first_builder WHERE agent_id=?", (agent_id,)).fetchone()
    if row:
        raise PermissionError("First Builder repository authority uses its protected launch gate")
    path = Path(root)
    if path.is_symlink() or not path.is_dir():
        raise ValueError("Project workspace must be an existing directory")
    path = path.resolve()
    now = _now()
    with write_txn(conn):
        current = conn.execute(
            "SELECT root,revision,active FROM agent_native_project_workspaces WHERE agent_id=?", (agent_id,)
        ).fetchone()
        if current:
            if current[0] != str(path):
                raise ValueError("Agent already has a different project workspace")
            if not current[2]:
                conn.execute(
                    "UPDATE agent_native_project_workspaces SET active=1,revision=revision+1,updated_at=? WHERE agent_id=?",
                    (now, agent_id),
                )
        else:
            conn.execute(
                "INSERT INTO agent_native_project_workspaces VALUES(?,?,?,?,?,?)",
                (agent_id, str(path), 1, 1, now, now),
            )
    return read(conn, agent_id)


def read(conn, agent_id):
    row = conn.execute(
        "SELECT root,revision,active FROM agent_native_project_workspaces WHERE agent_id=?", (agent_id,)
    ).fetchone()
    if not row:
        raise KeyError("Project workspace is not granted")
    return {"root": row[0], "revision": row[1], "active": bool(row[2])}


def active_repository(conn, agent_id):
    row = conn.execute(
        "SELECT root FROM agent_native_project_workspaces WHERE agent_id=? AND active=1", (agent_id,)
    ).fetchone()
    if not row:
        raise PermissionError("Project repository tools are not active")
    root = Path(row[0])
    if root.is_symlink() or not root.is_dir() or str(root.resolve()) != row[0]:
        raise PermissionError("Project workspace grant changed")
    return root
