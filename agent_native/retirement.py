"""Evidence-bound agent retirement, distinct from an owner's removal command."""
import hashlib
import json

from hermes_cli.kanban_db_connect import write_txn

SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_native_retirements (
 agent_id TEXT PRIMARY KEY REFERENCES agent_native_agents(id),
 evaluation_id TEXT NOT NULL REFERENCES agent_native_purpose_evaluations(id),
 source TEXT NOT NULL CHECK(source IN ('agent','parent','owner')),
 decision_agent_id TEXT NOT NULL REFERENCES agent_native_agents(id),
 retired_at TEXT NOT NULL
);
"""


def migrate_subtrees(conn):
    """Allow one verified parent decision to retire all of its descendants."""
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='agent_native_retirements'"
    ).fetchone()
    if not row or ('decision_agent_id' in row[0] and 'evaluation_id TEXT NOT NULL UNIQUE' not in row[0]):
        return
    if conn.in_transaction:
        raise RuntimeError('Retirement migration requires an initialization boundary')
    conn.execute('BEGIN IMMEDIATE')
    try:
        conn.execute('ALTER TABLE agent_native_retirements RENAME TO agent_native_retirements_old')
        conn.executescript(SCHEMA)
        old_columns = {column[1] for column in conn.execute(
            'PRAGMA table_info(agent_native_retirements_old)'
        )}
        decision = 'decision_agent_id' if 'decision_agent_id' in old_columns else 'agent_id'
        conn.execute(
            'INSERT INTO agent_native_retirements '
            '(agent_id,evaluation_id,source,decision_agent_id,retired_at) '
            f'SELECT agent_id,evaluation_id,source,{decision},retired_at '
            'FROM agent_native_retirements_old'
        )
        conn.execute('DROP TABLE agent_native_retirements_old')
        conn.commit()
    except Exception:
        conn.rollback()
        raise


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
        from agent_native.subtree_lifecycle import _subtree
        agent_ids = _subtree(conn, agent_id)
        from agent_native.acceptance import pending_required
        for current_id in agent_ids:
            current_revision = conn.execute(
                'SELECT soul_revision FROM agent_native_agents WHERE id=?', (current_id,),
            ).fetchone()[0]
            descendant = current_id != agent_id
            prefix = 'Retirement descendant has' if descendant else 'Retirement has'
            unanswered = conn.execute(
                'SELECT 1 FROM agent_native_questions WHERE agent_id=? AND soul_revision=? '
                'AND answer IS NULL LIMIT 1', (current_id, current_revision),
            ).fetchone()
            if unanswered:
                raise ValueError(prefix + ' an unanswered question')
            if pending_required(conn, current_id):
                raise ValueError(prefix + ' a required owner review')
            unresolved_effect = conn.execute(
                'SELECT 1 FROM agent_native_work_effects e '
                'JOIN agent_native_work_runs w ON w.id=e.run_id '
                'WHERE w.agent_id=? AND e.result IS NULL '
                'AND NOT (?=? AND e.run_id=? AND e.call_id=?) LIMIT 1',
                (current_id, current_id, agent_id, run_id, call_id),
            ).fetchone()
            if unresolved_effect:
                raise ValueError(prefix + ' an unresolved effect')
            uncertain_write = conn.execute(
                "SELECT 1 FROM agent_native_plane_mutations WHERE agent_id=? "
                "AND status IN ('pending','unknown') LIMIT 1", (current_id,),
            ).fetchone()
            if uncertain_write:
                raise ValueError(prefix + ' an unresolved Plane effect')

        from agent_native.identity import _now, _read, _event
        retired_at = _now()
        for current_id in agent_ids:
            conn.execute(
                'INSERT INTO agent_native_retirements '
                '(agent_id,evaluation_id,source,decision_agent_id,retired_at) '
                'VALUES(?,?,?,?,?)',
                (current_id, evaluation_id, 'agent' if current_id == agent_id else 'parent',
                 agent_id, retired_at),
            )
            conn.execute(
                'UPDATE agent_native_agents SET soul_revision=soul_revision+1 WHERE id=?',
                (current_id,),
            )
            conn.execute('UPDATE agent_native_cadence SET enabled=0 WHERE agent_id=?', (current_id,))
            conn.execute(
                "UPDATE agent_native_setup SET status='superseded',message='Agent retired.',updated_at=? "
                'WHERE agent_id=?', (retired_at, current_id),
            )
            latest = conn.execute(
                'SELECT id,state FROM agent_native_work_runs WHERE agent_id=? '
                'ORDER BY rowid DESC LIMIT 1', (current_id,),
            ).fetchone()
            if latest and latest[1] in ('queued', 'preparing', 'running', 'stopping'):
                next_state = 'paused' if latest[1] == 'queued' else 'stopping'
                conn.execute(
                    'UPDATE agent_native_work_runs SET stop_requested=1,state=? WHERE id=?',
                    (next_state, latest[0]),
                )
            root = _read(conn, current_id)
            # The legacy identity-event stream records trusted host lifecycle writes
            # with actor=owner. The retirement record carries initiating provenance.
            _event(conn, root, 'agent.retired')
        return {'status': 'retired', 'agent_id': agent_id,
                'evaluation_id': evaluation_id, 'retired_at': retired_at,
                'affected_agent_ids': agent_ids}
