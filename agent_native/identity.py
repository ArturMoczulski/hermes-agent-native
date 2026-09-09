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
    parent = conn.execute('SELECT parent_id FROM agent_native_agent_parents WHERE agent_id=?', (agent_id,)).fetchone()
    root['parent_id'] = parent[0] if parent else None
    root['child_ids'] = [child[0] for child in conn.execute(
        'SELECT agent_id FROM agent_native_agent_parents WHERE parent_id=? ORDER BY created_at,agent_id',
        (agent_id,),
    ).fetchall()]
    startup = conn.execute(
        'SELECT id, cause, soul_revision, requested_at '
        'FROM agent_native_initial_activations WHERE agent_id = ?', (agent_id,),
    ).fetchone()
    removed = conn.execute('SELECT removed_at FROM agent_native_removals WHERE agent_id=?', (agent_id,)).fetchone()
    retired = conn.execute('SELECT evaluation_id,replacement_id,source,decision_agent_id,retired_at FROM agent_native_retirements WHERE agent_id=?', (agent_id,)).fetchone()
    root['retirement'] = (dict(zip(('evaluation_id','replacement_id','source','decision_agent_id','retired_at'), retired)) if retired else None)
    root['removed_at'] = removed[0] if removed else None
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
    from agent_native.autonomy import get_settings as get_autonomy
    root['autonomy'] = get_autonomy(conn, agent_id)
    from agent_native.progress_concerns import list_concerns, settings as concern_settings
    root['progress_concerns'] = list_concerns(conn, agent_id)
    root['progress_concern_settings'] = concern_settings(conn, agent_id)
    from agent_native.assignment_review import list_policies
    root['assignment_review_policies'] = list_policies(conn, agent_id)
    predecessor = conn.execute(
        'SELECT id,predecessor_id,reason,handoff,created_at FROM agent_native_replacements '
        'WHERE successor_id=?', (agent_id,),
    ).fetchone()
    successor = conn.execute(
        'SELECT id,successor_id,reason,handoff,created_at FROM agent_native_replacements '
        'WHERE predecessor_id=?', (agent_id,),
    ).fetchone()
    root['replacement'] = (
        dict(zip(('id', 'predecessor_id', 'reason', 'handoff', 'created_at'), predecessor), role='successor')
        if predecessor else
        dict(zip(('id', 'successor_id', 'reason', 'handoff', 'created_at'), successor), role='predecessor')
        if successor else None
    )
    if root['work'] is not None:
        root['execution'] = root['work']['state']
    from agent_native.subtree_lifecycle import read_pause
    root['pause'] = read_pause(conn, agent_id)
    if root['pause']['paused']:
        root['execution'] = 'paused'
    return root


def _event(conn, root, kind):
    conn.execute(
        'INSERT INTO agent_native_events '
        '(agent_id, kind, soul_revision, purpose, actor, created_at) VALUES (?, ?, ?, ?, ?, ?)',
        (root['id'], kind, root['soul_revision'], root['purpose'], 'owner', _now()),
    )


def create_root(conn, *, actor, request_id, name, purpose, work=None, model_selection=None,
                autonomy_level=3, parent_id=None, _allow_nested=False):
    """Persist identity, first-review intent and event together; never launch a worker.

    The intent records the creating owner's request, not execution authority or
    observed work. Future admission must check current soul, grants, configuration
    and planning readiness. Retrying creation never adds an intent to an older
    record or changes the original purpose revision attached to its intent.
    """
    _require_owner(actor)
    request_id, name, purpose = (_text(v, k) for v, k in
                                 ((request_id, 'request_id'), (name, 'name'), (purpose, 'purpose')))
    if parent_id is not None:
        parent_id = _text(parent_id, 'parent_id')
        if len(parent_id) > 128:
            raise ValueError('parent_id is too long')
    from agent_native.work_state import configure, limits_json
    original_work = limits_json(work) if work is not None else None
    from agent_native import model_settings
    original_model = model_settings.creation_input(model_selection)
    from agent_native import autonomy
    autonomy_level = autonomy.validate_level(autonomy_level)
    with write_txn(conn, allow_nested=_allow_nested):
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
            saved_autonomy = conn.execute('SELECT level FROM agent_native_creation_autonomy WHERE agent_id=?', (previous[0],)).fetchone()
            if (saved_autonomy[0] if saved_autonomy else autonomy.DEFAULT_LEVEL) != autonomy_level:
                raise ConflictError('Creation request already used with a different autonomy level')
            saved_parent = conn.execute(
                'SELECT parent_id FROM agent_native_agent_parents WHERE agent_id=?', (previous[0],),
            ).fetchone()
            if (saved_parent[0] if saved_parent else None) != parent_id:
                raise ConflictError('Creation request already used with a different parent')
            return _read(conn, previous[0])
        if parent_id is not None:
            if not conn.execute('SELECT 1 FROM agent_native_agents WHERE id=?', (parent_id,)).fetchone():
                raise KeyError(parent_id)
            require_active(conn, parent_id)
            from agent_native.subtree_lifecycle import require_not_paused
            require_not_paused(conn, parent_id)
        agent_id = str(uuid4())
        conn.execute(
            'INSERT INTO agent_native_agents '
            '(id, request_id, name, initial_purpose, purpose, soul_revision, execution, created_at) '
            'VALUES (?, ?, ?, ?, ?, 1, ?, ?)',
            (agent_id, request_id, name, purpose, purpose, 'not_started', _now()),
        )
        if parent_id is not None:
            conn.execute('INSERT INTO agent_native_agent_parents(agent_id,parent_id,created_at) VALUES(?,?,?)',
                         (agent_id, parent_id, _now()))
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
        autonomy.initialize_agent(conn, agent_id, autonomy_level)
        from agent_native.startup import queue_setup
        queue_setup(conn, agent_id)
        if work is not None:
            configure(conn, actor=actor, agent_id=agent_id, expected_revision=1, limits=work)
            from agent_native.cadence import configure as configure_cadence
            configure_cadence(
                conn, actor=actor, agent_id=agent_id, expected_revision=1,
                interval_seconds=60, enabled=True, _allow_nested=True,
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
        require_active(conn, agent_id)
        root = _read(conn, agent_id)
        if root['soul_revision'] != expected_revision:
            raise ConflictError('Soul revision changed; reload before editing')
        conn.execute(
            'UPDATE agent_native_agents SET purpose = ?, soul_revision = soul_revision + 1 WHERE id = ?',
            (purpose, agent_id),
        )
        conn.execute("UPDATE agent_native_setup SET status = 'superseded', "
                     "message = 'Purpose changed. The prior setup revision was superseded.', updated_at = ? "
                     'WHERE agent_id = ?', (_now(), agent_id))
        from agent_native.startup import _event as setup_event
        setup_event(conn, agent_id)
        conn.execute(
            'UPDATE agent_native_setup_revisions SET soul_revision=soul_revision+1 WHERE agent_id=?',
            (agent_id,),
        )
        conn.execute(
            "UPDATE agent_native_setup SET status='queued',phase='files',attempted=0,files_ready=0,"
            "message='Purpose changed. Refreshing protected files and planning access.',updated_at=? "
            'WHERE agent_id=?', (_now(), agent_id),
        )
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


def list_roots(conn, *, actor, lifecycle='active'):
    """Installation roster; only the trusted owner may enumerate roots."""
    _require_owner(actor)
    if lifecycle not in ('active', 'retired'):
        raise ValueError('Choose active or retired agents')
    where = (
        'id IN (SELECT agent_id FROM agent_native_retirements) '
        'AND id NOT IN (SELECT agent_id FROM agent_native_removals)'
        if lifecycle == 'retired' else
        'id NOT IN (SELECT agent_id FROM agent_native_removals) '
        'AND id NOT IN (SELECT agent_id FROM agent_native_retirements)'
    )
    return [_read(conn, row[0]) for row in conn.execute(
        f'SELECT id FROM agent_native_agents WHERE {where} ORDER BY created_at, id'
    ).fetchall()]


def require_active(conn, agent_id):
    if conn.execute('SELECT 1 FROM agent_native_removals WHERE agent_id=?', (agent_id,)).fetchone():
        raise ConflictError('Agent removed; its retained history is read-only')
    if conn.execute('SELECT 1 FROM agent_native_retirements WHERE agent_id=?', (agent_id,)).fetchone():
        raise ConflictError('Agent retired; its retained history is read-only')


def remove_root(conn, *, actor, agent_id):
    """End a managed root without erasing its audit, results or external project."""
    _require_owner(actor)
    with write_txn(conn):
        root = _read(conn, agent_id)
        if root['removed_at']:
            return root
        active_child = conn.execute(
            'SELECT p.agent_id FROM agent_native_agent_parents p WHERE p.parent_id=? '
            'AND p.agent_id NOT IN (SELECT agent_id FROM agent_native_removals) '
            'AND p.agent_id NOT IN (SELECT agent_id FROM agent_native_retirements) LIMIT 1',
            (agent_id,),
        ).fetchone()
        if active_child:
            raise ConflictError('Agent has active children; retire or remove the subtree together')
        conn.execute('INSERT INTO agent_native_removals VALUES (?,?)', (agent_id, _now()))
        # Revision invalidation stops setup and all previously issued capabilities.
        conn.execute('UPDATE agent_native_agents SET soul_revision=soul_revision+1 WHERE id=?', (agent_id,))
        conn.execute('UPDATE agent_native_cadence SET enabled=0 WHERE agent_id=?', (agent_id,))
        conn.execute("UPDATE agent_native_setup SET status='superseded', message='Agent removed.', updated_at=? WHERE agent_id=?", (_now(),agent_id))
        from agent_native.work_state import event
        for run_id, state in conn.execute("SELECT id,state FROM agent_native_work_runs WHERE agent_id=? AND state IN ('queued','preparing','running','stopping')", (agent_id,)).fetchall():
            next_state = 'paused' if state == 'queued' else 'stopping'
            conn.execute('UPDATE agent_native_work_runs SET stop_requested=1,state=? WHERE id=?', (next_state,run_id))
            event(conn,run_id,'work.'+next_state,'Owner removed the agent; stopping work and preserving history.')
        root = _read(conn, agent_id)
        _event(conn,root,'agent.removed')
        return root
