"""Durable concerns for repeated cadence activity without useful progress."""
import json
from uuid import NAMESPACE_URL, uuid5

from agent_native.identity import ConflictError, _now, _require_owner
from hermes_cli.kanban_db_connect import write_txn

SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_native_progress_concern_settings (
 agent_id TEXT PRIMARY KEY REFERENCES agent_native_agents(id),
 failure_threshold INTEGER NOT NULL CHECK(failure_threshold BETWEEN 2 AND 10),
 updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS agent_native_progress_concerns (
 id TEXT PRIMARY KEY, agent_id TEXT NOT NULL REFERENCES agent_native_agents(id),
 kind TEXT NOT NULL CHECK(kind IN ('repeated_unproductive_failure','repeated_empty_completion')),
 status TEXT NOT NULL CHECK(status IN ('open','resolved')),
 attempt_ids TEXT NOT NULL, summary TEXT NOT NULL, created_at TEXT NOT NULL,
 resolved_at TEXT, response TEXT, resume_request_id TEXT,
 UNIQUE(agent_id,resume_request_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS agent_native_one_open_progress_concern
 ON agent_native_progress_concerns(agent_id,kind) WHERE status='open';
"""


def migrate_kinds(conn):
    """Extend the concern kinds on databases created by the first slice."""
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' "
        "AND name='agent_native_progress_concerns'"
    ).fetchone()
    if not row or 'repeated_empty_completion' in row[0]:
        return
    if conn.in_transaction:
        raise RuntimeError('Progress concern migration requires an initialization boundary')
    conn.execute('BEGIN IMMEDIATE')
    try:
        conn.execute('ALTER TABLE agent_native_progress_concerns RENAME TO '
                     'agent_native_progress_concerns_old')
        conn.executescript(SCHEMA)
        conn.execute(
            'INSERT INTO agent_native_progress_concerns SELECT * FROM '
            'agent_native_progress_concerns_old'
        )
        conn.execute('DROP TABLE agent_native_progress_concerns_old')
        conn.execute(
            'CREATE UNIQUE INDEX IF NOT EXISTS agent_native_one_open_progress_concern '
            "ON agent_native_progress_concerns(agent_id,kind) WHERE status='open'"
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def settings(conn, agent_id):
    row = conn.execute(
        'SELECT failure_threshold FROM agent_native_progress_concern_settings WHERE agent_id=?',
        (agent_id,),
    ).fetchone()
    return {'failure_threshold': row[0] if row else 3}


def configure(conn, *, actor, agent_id, failure_threshold):
    _require_owner(actor)
    if type(failure_threshold) is not int or not 2 <= failure_threshold <= 10:
        raise ValueError('Failure threshold must be an integer from 2 to 10')
    with write_txn(conn):
        if not conn.execute(
            'SELECT 1 FROM agent_native_agents WHERE id=?', (agent_id,)
        ).fetchone():
            raise KeyError(agent_id)
        conn.execute(
            'INSERT INTO agent_native_progress_concern_settings VALUES(?,?,?) '
            'ON CONFLICT(agent_id) DO UPDATE SET '
            'failure_threshold=excluded.failure_threshold,updated_at=excluded.updated_at',
            (agent_id, failure_threshold, _now()),
        )
    return settings(conn, agent_id)


def list_concerns(conn, agent_id):
    keys = (
        'id', 'kind', 'status', 'summary', 'created_at', 'resolved_at',
        'response', 'resume_request_id',
    )
    rows = conn.execute(
        'SELECT id,kind,status,summary,created_at,resolved_at,response,resume_request_id,attempt_ids '
        'FROM agent_native_progress_concerns WHERE agent_id=? ORDER BY created_at DESC,id DESC',
        (agent_id,),
    ).fetchall()
    return [dict(zip(keys, row[:8]), attempt_ids=json.loads(row[8])) for row in rows]


def _direction_cutoff(conn, agent_id):
    rows = conn.execute(
        'SELECT created_at FROM agent_native_feedback WHERE agent_id=? UNION ALL '
        'SELECT answered_at FROM agent_native_questions '
        'WHERE agent_id=? AND answered_at IS NOT NULL UNION ALL '
        'SELECT resolved_at FROM agent_native_progress_concerns '
        "WHERE agent_id=? AND status='resolved' AND resolved_at IS NOT NULL",
        (agent_id, agent_id, agent_id),
    ).fetchall()
    return max((row[0] for row in rows), default='')


def suspend_if_stalled(conn, agent_id):
    """Suspend before the next attempt once the approved threshold is met."""
    if conn.execute(
        "SELECT 1 FROM agent_native_progress_concerns WHERE agent_id=? AND status='open'",
        (agent_id,),
    ).fetchone():
        conn.execute(
            'UPDATE agent_native_cadence SET enabled=0 WHERE agent_id=?', (agent_id,)
        )
        return True
    cutoff = _direction_cutoff(conn, agent_id)
    threshold = settings(conn, agent_id)['failure_threshold']
    attempts = []
    kind = None
    latest_error = None
    for run_id, run_state, created_at, error in conn.execute(
        'SELECT id,state,created_at,error FROM agent_native_work_runs '
        'WHERE agent_id=? ORDER BY rowid DESC',
        (agent_id,),
    ).fetchall():
        candidate = {
            'retryable_failure': 'repeated_unproductive_failure',
            'completed': 'repeated_empty_completion',
        }.get(run_state)
        if candidate is None or created_at <= cutoff or (kind and candidate != kind):
            break
        if (
            conn.execute(
                'SELECT 1 FROM agent_native_work_results WHERE run_id=?', (run_id,)
            ).fetchone()
            or conn.execute(
                'SELECT 1 FROM agent_native_output_versions WHERE run_id=?', (run_id,)
            ).fetchone()
            or conn.execute(
                'SELECT 1 FROM agent_native_purpose_evaluations WHERE run_id=?',(run_id,)
            ).fetchone()
        ):
            break
        kind = candidate
        attempts.append(run_id)
        if latest_error is None and error:
            latest_error = error
        if len(attempts) == threshold:
            break
    if len(attempts) < threshold:
        return False
    attempts.reverse()
    concern_id = str(
        uuid5(NAMESPACE_URL, 'agent-native:no-progress:' + agent_id + ':' + attempts[-1])
    )
    if kind == 'repeated_empty_completion':
        summary = (
            f'Repeated work without progress: {threshold} consecutive attempts '
            'completed without recording progress or a saved output.'
        )
    else:
        summary = (
            f'Repeated work without progress: {threshold} consecutive attempts failed '
            'without a result or saved output.'
        )
        if latest_error:
            summary += ' Latest failure: ' + latest_error
    conn.execute(
        'INSERT OR IGNORE INTO agent_native_progress_concerns '
        '(id,agent_id,kind,status,attempt_ids,summary,created_at) '
        'VALUES(?,?,?,?,?,?,?)',
        (
            concern_id, agent_id, kind, 'open',
            json.dumps(attempts), summary, _now(),
        ),
    )
    conn.execute(
        'UPDATE agent_native_cadence SET enabled=0 WHERE agent_id=?', (agent_id,)
    )
    from agent_native.work_state import event
    event(
        conn, attempts[-1], 'work.progress_concern',
        summary + ' Automatic work suspended for owner review.',
    )
    return True


def resume(conn, *, actor, agent_id, concern_id, expected_revision, request_id):
    _require_owner(actor)
    if not isinstance(request_id, str) or not 1 <= len(request_id) <= 128:
        raise ValueError('Resume requires a bounded request identity')
    with write_txn(conn):
        root = conn.execute(
            'SELECT soul_revision FROM agent_native_agents WHERE id=?', (agent_id,)
        ).fetchone()
        if not root:
            raise KeyError(agent_id)
        if root[0] != expected_revision:
            raise ConflictError('Purpose changed; reload before resuming automatic work')
        row = conn.execute(
            'SELECT status,resume_request_id FROM agent_native_progress_concerns '
            'WHERE id=? AND agent_id=?',
            (concern_id, agent_id),
        ).fetchone()
        if not row:
            raise KeyError(concern_id)
        if row[0] == 'resolved':
            if row[1] != request_id:
                raise ConflictError('This progress concern was already resolved')
            return next(
                concern for concern in list_concerns(conn, agent_id)
                if concern['id'] == concern_id
            )
        now = _now()
        conn.execute(
            "UPDATE agent_native_progress_concerns SET status='resolved',"
            "resolved_at=?,response=?,resume_request_id=? WHERE id=?",
            (
                now, 'Owner resumed automatic work after reviewing repeated attempts.',
                request_id, concern_id,
            ),
        )
        conn.execute(
            'UPDATE agent_native_cadence SET enabled=1,next_due=? WHERE agent_id=?',
            (now, agent_id),
        )
        from agent_native.work_state import event
        latest = conn.execute(
            'SELECT id FROM agent_native_work_runs WHERE agent_id=? '
            'ORDER BY rowid DESC LIMIT 1',
            (agent_id,),
        ).fetchone()
        if latest:
            event(
                conn, latest[0], 'work.progress_concern_resolved',
                'Owner reviewed repeated failures and resumed automatic work.',
            )
        return next(
            concern for concern in list_concerns(conn, agent_id)
            if concern['id'] == concern_id
        )
