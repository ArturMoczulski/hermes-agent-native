"""Trusted host identity and initial-review requests in the shared control database.

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
    root = dict(zip(('id', 'name', 'purpose', 'soul_revision', 'execution', 'created_at'), row))
    startup = conn.execute(
        'SELECT id, cause, soul_revision, requested_at '
        'FROM agent_native_initial_activations WHERE agent_id = ?', (agent_id,),
    ).fetchone()
    root['startup'] = (dict(zip(('id', 'cause', 'soul_revision', 'requested_at'), startup))
                       if startup is not None else None)
    from agent_native.startup import read_setup
    root['setup'] = read_setup(conn, agent_id)
    from agent_native.work_state import read_work
    root['work'] = read_work(conn, agent_id)
    from agent_native.cadence import read as read_cadence
    root['cadence'] = read_cadence(conn, agent_id)
    from agent_native import model_settings
    root['model_selection'] = model_settings.get_selection(conn, agent_id)
    root['model_activity'] = model_settings.activity(conn, agent_id)
    if root['work'] is not None:
        root['execution'] = root['work']['state']
    return root


def _event(conn, root, kind):
    conn.execute(
        'INSERT INTO agent_native_events '
        '(agent_id, kind, soul_revision, purpose, actor, created_at) VALUES (?, ?, ?, ?, ?, ?)',
        (root['id'], kind, root['soul_revision'], root['purpose'], 'owner', _now()),
    )


def create_root(conn, *, actor, request_id, name, purpose, work=None, model_selection=None):
    """Persist identity, first-review intent and event together; never launch a worker.

    The intent records the creating owner's request, not execution authority or
    observed work. Future admission must check current soul, grants, configuration
    and planning readiness. Retrying creation never adds an intent to an older
    record or changes the original purpose revision attached to its intent.
    """
    _require_owner(actor)
    request_id, name, purpose = (_text(v, k) for v, k in
                                 ((request_id, 'request_id'), (name, 'name'), (purpose, 'purpose')))
    from agent_native.work_state import configure, limits_json
    original_work = limits_json(work) if work is not None else None
    from agent_native import model_settings
    original_model = model_settings.creation_input(model_selection)
    with write_txn(conn):
        previous = conn.execute(
            'SELECT id, name, initial_purpose FROM agent_native_agents WHERE request_id = ?',
            (request_id,),
        ).fetchone()
        if previous is not None:
            if (previous[1], previous[2]) != (name, purpose):
                raise ConflictError('Creation request already used with different input')
            # Idempotency compares immutable creation input, not mutable work.
            # Pre-upgrade identities have no row and were created without work.
            original = conn.execute(
                'SELECT work_limits FROM agent_native_creation_work WHERE agent_id = ?',
                (previous[0],),
            ).fetchone()
            if (original[0] if original else None) != original_work:
                raise ConflictError('Creation request already used with different work limits')
            saved_model = conn.execute(
                'SELECT input_json FROM agent_native_creation_model WHERE agent_id=?', (previous[0],),
            ).fetchone()
            if (saved_model[0] if saved_model else None) != original_model:
                raise ConflictError('Creation request already used with a different model selection')
            return _read(conn, previous[0])
        agent_id = str(uuid4())
        conn.execute(
            'INSERT INTO agent_native_agents '
            '(id, request_id, name, initial_purpose, purpose, soul_revision, execution, created_at) '
            'VALUES (?, ?, ?, ?, ?, 1, ?, ?)',
            (agent_id, request_id, name, purpose, purpose, 'not_started', _now()),
        )
        conn.execute(
            'INSERT INTO agent_native_creation_work (agent_id, work_limits) VALUES (?, ?)',
            (agent_id, original_work),
        )
        conn.execute(
            'INSERT INTO agent_native_initial_activations '
            '(id, agent_id, cause, soul_revision, requested_at) VALUES (?, ?, ?, 1, ?)',
            (str(uuid4()), agent_id, 'creation', _now()),
        )
        model_settings.initialize_agent(conn, agent_id, model_selection)
        from agent_native.startup import queue_setup
        queue_setup(conn, agent_id)
        if work is not None:
            configure(conn, actor=actor, agent_id=agent_id, expected_revision=1, limits=work)
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
        conn.execute("UPDATE agent_native_setup SET status = 'superseded', "
                     "message = 'Purpose changed. This setup request cannot start work.', updated_at = ? "
                     'WHERE agent_id = ?', (_now(), agent_id))
        from agent_native.startup import _event as setup_event
        setup_event(conn, agent_id)
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


def list_roots(conn, *, actor):
    """Installation roster; only the trusted owner may enumerate roots."""
    _require_owner(actor)
    return [_read(conn, row[0]) for row in conn.execute(
        'SELECT id FROM agent_native_agents ORDER BY created_at, id'
    ).fetchall()]
