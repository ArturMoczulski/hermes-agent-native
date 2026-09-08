"""Owner-controlled agent succession with explicit, immutable handoff provenance."""
import hashlib
import json
from uuid import uuid4

from agent_native.identity import (
    ConflictError, _now, _require_owner, _text, create_root, get_root, require_active,
)
from hermes_cli.kanban_db_connect import write_txn


def replace(conn, *, actor, predecessor_id, request_id, name, purpose, reason, handoff):
    """Create a clean successor and retire the predecessor subtree atomically."""
    _require_owner(actor)
    request_id = _text(request_id, 'request_id')
    name = _text(name, 'name')
    purpose = _text(purpose, 'purpose')
    reason = _text(reason, 'reason')
    handoff = _text(handoff, 'handoff')
    if (len(request_id) > 128 or len(name) > 200 or len(purpose) > 20000
            or len(reason) > 4000 or len(handoff) > 8000):
        raise ValueError('Replacement fields exceed their bounded size')
    fingerprint = hashlib.sha256(json.dumps(
        [predecessor_id, name, purpose, reason, handoff], ensure_ascii=False,
        separators=(',', ':'),
    ).encode()).hexdigest()

    with write_txn(conn):
        old = conn.execute(
            'SELECT fingerprint,predecessor_id,successor_id FROM agent_native_replacements '
            'WHERE request_id=?', (request_id,),
        ).fetchone()
        if old:
            if old[0] != fingerprint or old[1] != predecessor_id:
                raise ConflictError('Replacement request already used with different input')
            return {
                'replacement_id': conn.execute(
                    'SELECT id FROM agent_native_replacements WHERE request_id=?', (request_id,),
                ).fetchone()[0],
                'predecessor': get_root(conn, actor=actor, agent_id=old[1]),
                'successor': get_root(conn, actor=actor, agent_id=old[2]),
            }
        require_active(conn, predecessor_id)
        if conn.execute(
            'SELECT 1 FROM agent_native_replacements WHERE predecessor_id=?',
            (predecessor_id,),
        ).fetchone():
            raise ConflictError('Agent already has a recorded successor')

        from agent_native.subtree_lifecycle import _subtree
        from agent_native.retirement import retire_subtree, validate_subtree
        agent_ids = _subtree(conn, predecessor_id)
        validate_subtree(conn, agent_ids)
        parent = conn.execute(
            'SELECT parent_id FROM agent_native_agent_parents WHERE agent_id=?',
            (predecessor_id,),
        ).fetchone()
        parent_id = parent[0] if parent else None
        predecessor = get_root(conn, actor=actor, agent_id=predecessor_id)
        model = predecessor.get('model_selection')
        model_input = ({key: model[key] for key in ('provider', 'model', 'reasoning_effort')
                        if key in model} if model else None)
        work = predecessor.get('work')
        work_limits = work['limits'] if work else {'timeout_seconds': 180, 'max_iterations': 50}
        successor = create_root(
            conn, actor=actor, request_id='replacement-successor:' + request_id,
            name=name, purpose=purpose, parent_id=parent_id, work=work_limits,
            model_selection=model_input, autonomy_level=predecessor['autonomy']['level'],
            _allow_nested=True,
        )
        replacement_id = str(uuid4())
        created_at = _now()
        conn.execute(
            'INSERT INTO agent_native_replacements '
            '(id,request_id,fingerprint,predecessor_id,successor_id,parent_id,reason,handoff,created_at) '
            'VALUES(?,?,?,?,?,?,?,?,?)',
            (replacement_id, request_id, fingerprint, predecessor_id, successor['id'],
             parent_id, reason, handoff, created_at),
        )
        cadence = predecessor.get('cadence')
        if cadence and cadence['enabled']:
            from agent_native.cadence import configure
            configure(
                conn, actor=actor, agent_id=successor['id'], expected_revision=1,
                interval_seconds=cadence['interval_seconds'], enabled=True,
                _allow_nested=True,
            )
        retire_subtree(
            conn, agent_ids=agent_ids, decision_agent_id=predecessor_id,
            replacement_id=replacement_id, root_source='owner',
        )
        return {
            'replacement_id': replacement_id,
            'predecessor': get_root(conn, actor=actor, agent_id=predecessor_id),
            'successor': get_root(conn, actor=actor, agent_id=successor['id']),
        }
