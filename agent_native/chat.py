"""Host-issued conversation bindings; native Hermes remains the transcript owner.

Bindings grant bounded conversation only, never project execution. The control
DB path is captured at issuance so profile changes cannot switch authority.
"""
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from agent_native.identity import OWNER, ConflictError, _now, _require_owner, get_root
from agent_native.provisioning import provision_root
from hermes_cli.kanban_db_connect import connect_closing, write_txn
from hermes_constants import get_hermes_home

_ISSUER = object()


@dataclass(frozen=True)
class Binding:
    agent_id: str
    session_id: str
    soul_revision: int
    name: str
    purpose: str
    workspace: str
    _db_path: Path = field(repr=False)
    _issuer: object = field(repr=False)

    def validate(self):
        if self._issuer is not _ISSUER:
            raise PermissionError('Host-issued conversation binding required')
        with connect_closing(self._db_path) as conn:
            row = conn.execute(
                'SELECT a.soul_revision, a.purpose, c.session_id FROM agent_native_agents a '
                'JOIN agent_native_chat_sessions c ON c.agent_id = a.id AND c.soul_revision = a.soul_revision '
                'WHERE a.id = ?', (self.agent_id,),
            ).fetchone()
        if row is None or tuple(row) != (self.soul_revision, self.purpose, self.session_id):
            raise ConflictError('Agent purpose changed; reopen its conversation')


def _workspace(conn, root, storage):
    base = storage / root['id']
    if not base.exists():
        return provision_root(conn, actor=OWNER, agent_id=root['id'], storage_root=storage)['workspace']
    # Conversation reads the current protected DB purpose directly. An older
    # filesystem projection can await setup repair without blocking conversation.
    for path in (storage, base, base / 'workspace'):
        if path.is_symlink() or not path.is_dir():
            raise PermissionError('Agent workspace is unavailable or unsafe')
    return str((base / 'workspace').resolve())


def issue_binding(*, actor, agent_id, db_path=None, storage_root=None):
    _require_owner(actor)
    storage = Path(storage_root) if storage_root is not None else get_hermes_home() / 'agents'
    with connect_closing(db_path, board='default') as conn:
        from agent_native.identity import require_active
        require_active(conn, agent_id)
        root = get_root(conn, actor=actor, agent_id=agent_id)
        workspace = _workspace(conn, root, storage)
        with write_txn(conn):
            require_active(conn, agent_id)
            current = get_root(conn, actor=actor, agent_id=agent_id)
            if current['soul_revision'] != root['soul_revision']:
                raise ConflictError('Agent purpose changed; reopen its conversation')
            conn.execute(
                'INSERT INTO agent_native_chat_sessions (agent_id, soul_revision, session_id, created_at) '
                'VALUES (?, ?, ?, ?) ON CONFLICT(agent_id, soul_revision) DO NOTHING',
                (agent_id, root['soul_revision'], 'an_chat_' + uuid4().hex, _now()),
            )
            session_id = conn.execute(
                'SELECT session_id FROM agent_native_chat_sessions WHERE agent_id = ? AND soul_revision = ?',
                (agent_id, root['soul_revision']),
            ).fetchone()[0]
            path = Path(conn.execute('PRAGMA database_list').fetchone()[2]).resolve()
    return Binding(agent_id, session_id, root['soul_revision'], root['name'], root['purpose'], workspace, path, _ISSUER)


def lookup_session(session_id, *, db_path=None):
    """Recognize managed history even after its purpose revision is superseded."""
    with connect_closing(db_path, board='default') as conn:
        return conn.execute('SELECT 1 FROM agent_native_chat_sessions WHERE session_id = ?', (session_id,)).fetchone() is not None
