"""Evidence-bound agent retirement, distinct from an owner's removal command."""
import hashlib
import json

from hermes_cli.kanban_db_connect import write_txn

SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_native_retirements (
 agent_id TEXT PRIMARY KEY REFERENCES agent_native_agents(id),
 evaluation_id TEXT NOT NULL UNIQUE REFERENCES agent_native_purpose_evaluations(id),
 source TEXT NOT NULL CHECK(source IN ('agent','parent','owner')),
 retired_at TEXT NOT NULL
);
"""


def _evaluation(conn, evaluation_id):
    row = conn.execute(
        'SELECT record_json,record_sha256 FROM agent_native_purpose_evaluations WHERE id=?',
        (evaluation_id,),
    ).fetchone()
    if not row or hashlib.sha256(row[0].encode()).hexdigest() != row[1]:
        raise ValueError('A valid purpose evaluation is required')
    return json.loads(row[0])


def retire(conn, *, validate, agent_id, run_id, call_id, arguments):
    """Retire after rechecking the current, fully resolved purpose assessment."""
    if not isinstance(arguments, dict) or set(arguments) != {'evaluation_id'}:
        raise ValueError('Retirement requires the exact evaluation_id')
    evaluation_id = arguments['evaluation_id']
    if not isinstance(evaluation_id, str) or not evaluation_id:
        raise ValueError('Retirement requires the exact evaluation_id')

    with write_txn(conn):
        validate(conn)
        evaluation = _evaluation(conn, evaluation_id)
        revision = conn.execute(
            'SELECT soul_revision FROM agent_native_agents WHERE id=?', (agent_id,),
        ).fetchone()
        if (not revision or evaluation['agent_id'] != agent_id or evaluation['run_id'] != run_id
                or evaluation['soul_revision'] != revision[0]
                or evaluation['judgment'] != 'retire_candidate'):
            raise ValueError('Retirement requires a current retirement-candidate evaluation')
        latest = conn.execute(
            'SELECT id FROM agent_native_purpose_evaluations WHERE agent_id=? '
            'ORDER BY created_at DESC,id DESC LIMIT 1', (agent_id,),
        ).fetchone()
        if not latest or latest[0] != evaluation_id:
            raise ValueError('Retirement requires the latest purpose evaluation')
        if evaluation['remaining_obligations']:
            raise ValueError('Retirement has remaining obligations')
        if isinstance(evaluation['uncertainty'], str) and evaluation['uncertainty'].strip():
            raise ValueError('Retirement has unresolved uncertainty')
        unanswered = conn.execute(
            'SELECT 1 FROM agent_native_questions WHERE agent_id=? AND soul_revision=? '
            'AND answer IS NULL LIMIT 1', (agent_id, revision[0]),
        ).fetchone()
        if unanswered:
            raise ValueError('Retirement has an unanswered question')
        from agent_native.acceptance import pending_required
        if pending_required(conn, agent_id):
            raise ValueError('Retirement has a required owner review')
        active_child = conn.execute(
            'SELECT p.agent_id FROM agent_native_agent_parents p WHERE p.parent_id=? '
            'AND p.agent_id NOT IN (SELECT agent_id FROM agent_native_removals) '
            'AND p.agent_id NOT IN (SELECT agent_id FROM agent_native_retirements) LIMIT 1',
            (agent_id,),
        ).fetchone()
        if active_child:
            raise ValueError('Retirement has an active descendant')
        unresolved_effect = conn.execute(
            'SELECT 1 FROM agent_native_work_effects e JOIN agent_native_work_runs w ON w.id=e.run_id '
            'WHERE w.agent_id=? AND e.result IS NULL AND NOT (e.run_id=? AND e.call_id=?) LIMIT 1',
            (agent_id, run_id, call_id),
        ).fetchone()
        if unresolved_effect:
            raise ValueError('Retirement has an unresolved effect')
        uncertain_write = conn.execute(
            "SELECT 1 FROM agent_native_plane_mutations WHERE agent_id=? "
            "AND status IN ('pending','unknown') LIMIT 1", (agent_id,),
        ).fetchone()
        if uncertain_write:
            raise ValueError('Retirement has an unresolved Plane effect')

        from agent_native.identity import _now, _read, _event
        retired_at = _now()
        conn.execute(
            'INSERT INTO agent_native_retirements(agent_id,evaluation_id,source,retired_at) '
            "VALUES(?,?, 'agent', ?)", (agent_id, evaluation_id, retired_at),
        )
        conn.execute('UPDATE agent_native_agents SET soul_revision=soul_revision+1 WHERE id=?', (agent_id,))
        conn.execute('UPDATE agent_native_cadence SET enabled=0 WHERE agent_id=?', (agent_id,))
        conn.execute(
            "UPDATE agent_native_setup SET status='superseded',message='Agent retired.',updated_at=? "
            'WHERE agent_id=?', (retired_at, agent_id),
        )
        root = _read(conn, agent_id)
        # The legacy identity-event stream records trusted host lifecycle writes
        # with actor=owner. The retirement record above carries the initiating
        # source explicitly and is the authoritative provenance.
        _event(conn, root, 'agent.retired')
        return {'status': 'retired', 'agent_id': agent_id,
                'evaluation_id': evaluation_id, 'retired_at': retired_at}
