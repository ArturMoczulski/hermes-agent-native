"""Durable, explicitly bounded initial work, owned by the dashboard service."""
import json
from uuid import uuid4

from hermes_cli.kanban_db_connect import write_txn
from agent_native.identity import OWNER, ConflictError, _now, _require_owner

WORK_SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_native_work_runs (
 id TEXT PRIMARY KEY, agent_id TEXT NOT NULL REFERENCES agent_native_agents(id),
 activation_id TEXT NOT NULL REFERENCES agent_native_initial_activations(id),
 soul_revision INTEGER NOT NULL, session_id TEXT NOT NULL UNIQUE,
 limits TEXT NOT NULL, state TEXT NOT NULL,
 model_calls INTEGER NOT NULL DEFAULT 0, stop_requested INTEGER NOT NULL DEFAULT 0,
 binding_id TEXT, worker_pid INTEGER, summary TEXT, error TEXT,
 created_at TEXT NOT NULL, started_at TEXT, finished_at TEXT
);
CREATE TABLE IF NOT EXISTS agent_native_work_events (
 id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL REFERENCES agent_native_work_runs(id),
 kind TEXT NOT NULL, summary TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS agent_native_work_effects (
 run_id TEXT NOT NULL REFERENCES agent_native_work_runs(id), call_id TEXT NOT NULL,
 operation_id TEXT NOT NULL UNIQUE, fingerprint TEXT NOT NULL, result TEXT,
 PRIMARY KEY(run_id, call_id)
);
"""
from agent_native.result_store import RESULT_SCHEMA
from agent_native.work_focus import FOCUS_SCHEMA
from agent_native.progress import PROGRESS_SCHEMA
from agent_native.feedback import SCHEMA as FEEDBACK_SCHEMA
from agent_native.questions import SCHEMA as QUESTIONS_SCHEMA
from agent_native.cadence import SCHEMA as CADENCE_SCHEMA
from agent_native.comments import SCHEMA as COMMENTS_SCHEMA
from agent_native.progress_concerns import SCHEMA as CONCERNS_SCHEMA
from agent_native.assignment_review import SCHEMA as ASSIGNMENT_REVIEW_SCHEMA
from agent_native.purpose_evaluation import SCHEMA as PURPOSE_EVALUATION_SCHEMA
from agent_native.retirement import SCHEMA as RETIREMENT_SCHEMA
from agent_native.child_delegation import SCHEMA as CHILD_DELEGATION_SCHEMA
from agent_native.child_supervision import SCHEMA as CHILD_SUPERVISION_SCHEMA
from agent_native.subtree_lifecycle import SCHEMA as SUBTREE_LIFECYCLE_SCHEMA
WORK_SCHEMA += CADENCE_SCHEMA + COMMENTS_SCHEMA + RESULT_SCHEMA + FOCUS_SCHEMA + PROGRESS_SCHEMA + FEEDBACK_SCHEMA + QUESTIONS_SCHEMA + CONCERNS_SCHEMA + ASSIGNMENT_REVIEW_SCHEMA + PURPOSE_EVALUATION_SCHEMA + RETIREMENT_SCHEMA + CHILD_DELEGATION_SCHEMA + CHILD_SUPERVISION_SCHEMA + SUBTREE_LIFECYCLE_SCHEMA

TERMINAL = frozenset({'paused', 'interrupted', 'limit_reached', 'completed', 'retryable_failure', 'failed', 'unknown'})


def migrate_legacy_time_limits(conn):
    """Relabel deadline stops written before ``limit_reached`` existed.

    The exact summary was emitted only by the watchdog deadline path. Owner
    pauses use a different summary, so this does not make them cadence eligible.
    """
    with write_txn(conn, allow_nested=True):
        run_ids = [row[0] for row in conn.execute(
            "SELECT id FROM agent_native_work_runs WHERE state='paused' "
            "AND stop_requested=1 AND summary='Work reached its time limit.'"
        ).fetchall()]
        progress_ids = [row[0] for row in conn.execute(
            "SELECT p.run_id FROM agent_native_progress p "
            "JOIN agent_native_work_runs w ON w.id=p.run_id "
            "WHERE w.state IN ('paused','limit_reached') AND w.stop_requested=1 "
            "AND w.summary='Work reached its time limit.' "
            "AND p.source_id='terminal:'||p.run_id AND p.summary='Attempt paused' "
            "AND p.status='pending'"
        ).fetchall()]
        changed = set(run_ids) | set(progress_ids)
        if not changed:
            return 0
        conn.executemany(
            "UPDATE agent_native_work_runs SET state='limit_reached' WHERE id=?",
            ((run_id,) for run_id in run_ids),
        )
        conn.executemany(
            "UPDATE agent_native_work_events SET kind='work.limit_reached' "
            "WHERE run_id=? AND kind='work.paused' "
            "AND summary='Work reached its time limit.'",
            ((run_id,) for run_id in run_ids),
        )
        conn.executemany(
            "UPDATE agent_native_progress SET summary='Attempt limit_reached',"
            "text=replace(text,char(10)||'Attempt paused'||char(10),"
            "char(10)||'Attempt limit_reached'||char(10)) "
            "WHERE run_id=? AND source_id='terminal:'||run_id "
            "AND summary='Attempt paused' AND status='pending'",
            ((run_id,) for run_id in progress_ids),
        )
        return len(changed)


def event(conn, run_id, kind, summary):
    with write_txn(conn, allow_nested=True):
        conn.execute('INSERT INTO agent_native_work_events(run_id,kind,summary,created_at) VALUES (?,?,?,?)',
                     (run_id, kind, summary, _now()))
        if kind in ('work.completed', 'work.paused', 'work.interrupted', 'work.limit_reached',
                    'work.retryable_failure', 'work.failed', 'work.unknown'):
            from agent_native.progress import terminal
            terminal(conn, run_id)


def read_work(conn, agent_id):
    row = conn.execute('SELECT * FROM agent_native_work_runs WHERE agent_id=? ORDER BY rowid DESC LIMIT 1', (agent_id,)).fetchone()
    if row is None:
        return None
    names = [c[1] for c in conn.execute('PRAGMA table_info(agent_native_work_runs)')]
    result = dict(zip(names, row))
    result['limits'] = json.loads(result['limits'])
    from agent_native.model_settings import read_attempt
    result['model_selection'] = read_attempt(conn, 'work', result['id'])
    result['events'] = [dict(zip(('id','kind','summary','created_at'), row)) for row in conn.execute(
        'SELECT id,kind,summary,created_at FROM agent_native_work_events WHERE run_id=? ORDER BY id',
        (result['id'],)).fetchall()]
    from agent_native.story_store import list_stories
    result['stories'] = list_stories(conn, agent_id)
    from agent_native.output_store import list_outputs
    from agent_native.result_store import list_results
    result['outputs'] = list_outputs(conn, agent_id)
    result['results'] = list_results(conn, agent_id)
    from agent_native.purpose_evaluation import list_evaluations
    result['purpose_evaluations'] = list_evaluations(conn,agent_id)
    from agent_native.work_focus import read_focus
    result['focus'] = read_focus(conn, result['id'])
    from agent_native.progress import recent
    result['progress'] = recent(conn, result['id'])
    from agent_native.output_sections import pending_sections
    result['output_sections'] = pending_sections(conn, result['id'])
    for private in ('binding_id', 'worker_pid', 'stop_requested'):
        result.pop(private, None)
    return result


def limits_json(limits):
    if (not isinstance(limits, dict) or set(limits) != {'timeout_seconds', 'max_iterations'}
            or type(limits['timeout_seconds']) is not int or not 1 <= limits['timeout_seconds'] <= 3600
            or type(limits['max_iterations']) is not int or not 1 <= limits['max_iterations'] <= 100):
        raise ValueError('Choose a positive time limit (up to 3600 seconds) and model steps (up to 100)')
    return json.dumps(limits, sort_keys=True)


def configure(conn, *, actor, agent_id, expected_revision, limits):
    _require_owner(actor)
    from agent_native.identity import require_active
    encoded = limits_json(limits)
    with write_txn(conn, allow_nested=True):
        require_active(conn, agent_id)
        from agent_native.subtree_lifecycle import require_not_paused
        require_not_paused(conn, agent_id)
        root = conn.execute('SELECT soul_revision FROM agent_native_agents WHERE id=?', (agent_id,)).fetchone()
        if root is None:
            raise KeyError(agent_id)
        activation = conn.execute('SELECT id,soul_revision FROM agent_native_initial_activations WHERE agent_id=?',
                                  (agent_id,)).fetchone()
        if root[0] != expected_revision or activation[1] != expected_revision:
            raise ConflictError('Purpose changed; reload before configuring work')
        previous = read_work(conn, agent_id)
        if previous:
            if previous['limits'] != limits:
                raise ConflictError('This initial work run is already configured')
            return previous
        from agent_native.model_settings import get_selection
        from agent_native.model_runtime import validate_choice
        try:
            validate_choice(get_selection(conn, agent_id))
        except ValueError as exc:
            raise ValueError('Choose a configured model before starting work') from exc
        run_id = str(uuid4())
        conn.execute('INSERT INTO agent_native_work_runs '
                     '(id,agent_id,activation_id,soul_revision,session_id,limits,state,created_at) '
                     'VALUES (?,?,?,?,?,?,?,?)',
                     (run_id,agent_id,activation[0],expected_revision,'an_work_'+uuid4().hex,encoded,'queued',_now()))
        event(conn,run_id,'work.queued','Initial work requested; waiting for project setup.')
    return read_work(conn,agent_id)


def request_pause(conn, *, actor, agent_id):
    from agent_native.subtree_lifecycle import request_pause as pause_subtree
    return pause_subtree(conn, actor=actor, agent_id=agent_id)


def validate(conn, run_id):
    row = conn.execute('SELECT w.state,w.stop_requested,w.soul_revision,a.soul_revision '
                       'FROM agent_native_work_runs w JOIN agent_native_agents a ON a.id=w.agent_id '
                       'WHERE w.id=?', (run_id,)).fetchone()
    if not row or row[0] not in ('preparing','running') or row[1] or row[2] != row[3]:
        raise PermissionError('This work run is no longer active')
