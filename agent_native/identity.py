"""Trusted host operations for inactive roots, using the shared control database.

OWNER is an in-process capability: never deserialize it from a request or expose
these operations to generated code. Transport authentication and worker isolation
must exist before any managed worker is launched. This module alone is not a sandbox.
"""
from datetime import datetime, timezone
from uuid import uuid4

from hermes_cli.kanban_db_connect import write_txn

OWNER = object()


class ConflictError(ValueError):
    """A request was reused with different input or references an obsolete soul."""


def _require_owner(actor):
    if actor is not OWNER:
        raise PermissionError('Authenticated owner capability required')


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{field} must be nonblank text')
    return value.strip()


def _now():
    return datetime.now(timezone.utc).isoformat()


def _read(conn, agent_id):
    row = conn.execute(
        'SELECT id, name, purpose, soul_revision, execution, created_at '
        'FROM agent_native_agents WHERE id = ?', (agent_id,),
    ).fetchone()
    if row is None:
        raise KeyError(agent_id)
    return dict(zip(('id', 'name', 'purpose', 'soul_revision', 'execution', 'created_at'), row))


def _event(conn, root, kind):
    conn.execute(
        'INSERT INTO agent_native_events '
        '(agent_id, kind, soul_revision, purpose, actor, created_at) VALUES (?, ?, ?, ?, ?, ?)',
        (root['id'], kind, root['soul_revision'], root['purpose'], 'owner', _now()),
    )


def create_root(conn, *, actor, request_id, name, purpose):
    """Persist an inactive root and event atomically; retries do not create duplicates."""
    _require_owner(actor)
    request_id, name, purpose = (_text(v, k) for v, k in
                                 ((request_id, 'request_id'), (name, 'name'), (purpose, 'purpose')))
    with write_txn(conn):
        previous = conn.execute(
            'SELECT id, name, initial_purpose FROM agent_native_agents WHERE request_id = ?',
            (request_id,),
        ).fetchone()
        if previous is not None:
            if (previous[1], previous[2]) != (name, purpose):
                raise ConflictError('Creation request already used with different input')
            return _read(conn, previous[0])
        agent_id = str(uuid4())
        conn.execute(
            'INSERT INTO agent_native_agents '
            '(id, request_id, name, initial_purpose, purpose, soul_revision, execution, created_at) '
            'VALUES (?, ?, ?, ?, ?, 1, ?, ?)',
            (agent_id, request_id, name, purpose, purpose, 'not_started', _now()),
        )
        root = _read(conn, agent_id)
        _event(conn, root, 'agent.created')
        return root


def get_root(conn, *, actor, agent_id):
    _require_owner(actor)
    return _read(conn, agent_id)


def revise_soul(conn, *, actor, agent_id, expected_revision, purpose):
    """Owner-only revision for inactive roots; stale edits cannot overwrite newer ones."""
    _require_owner(actor)
    purpose = _text(purpose, 'purpose')
    with write_txn(conn):
        root = _read(conn, agent_id)
        if root['soul_revision'] != expected_revision:
            raise ConflictError('Soul revision changed; reload before editing')
        conn.execute(
            'UPDATE agent_native_agents SET purpose = ?, soul_revision = soul_revision + 1 WHERE id = ?',
            (purpose, agent_id),
        )
        root = _read(conn, agent_id)
        _event(conn, root, 'agent.soul_revised')
        return root


def events(conn, *, actor, agent_id):
    _require_owner(actor)
    _read(conn, agent_id)
    rows = conn.execute(
        'SELECT sequence, kind, soul_revision, purpose, actor, created_at '
        'FROM agent_native_events WHERE agent_id = ? ORDER BY sequence', (agent_id,),
    ).fetchall()
    return [dict(zip(('sequence', 'kind', 'soul_revision', 'purpose', 'actor', 'created_at'), row))
            for row in rows]
