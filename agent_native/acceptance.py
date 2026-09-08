"""Version-bound owner decisions for immutable work results."""
import json
from uuid import uuid4

from agent_native.identity import ConflictError, _now, _require_owner
from hermes_cli.kanban_db_connect import write_txn

ACCEPTANCE_SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_native_result_decisions (
 id TEXT PRIMARY KEY, request_id TEXT NOT NULL UNIQUE,
 result_id TEXT NOT NULL UNIQUE REFERENCES agent_native_work_results(id),
 agent_id TEXT NOT NULL REFERENCES agent_native_agents(id),
 decision TEXT NOT NULL CHECK(decision IN ('accepted','revision_requested')),
 note TEXT, actor TEXT NOT NULL, created_at TEXT NOT NULL
);
"""

def get(conn, result_id):
    row = conn.execute('SELECT id,result_id,agent_id,decision,note,actor,created_at FROM agent_native_result_decisions WHERE result_id=?',
                       (result_id,)).fetchone()
    return dict(zip(('id','result_id','agent_id','decision','note','actor','created_at'), row)) if row else None


def pending_required(conn, agent_id):
    """Return exact gated results that still require an owner decision."""
    pending = []
    for result_id, encoded in conn.execute(
        'SELECT r.id,r.record_json FROM agent_native_work_results r '
        'LEFT JOIN agent_native_result_decisions d ON d.result_id=r.id '
        'WHERE r.agent_id=? AND d.id IS NULL ORDER BY r.created_at,r.id',
        (agent_id,),
    ).fetchall():
        record = json.loads(encoded)
        if record.get('review', {}).get('required'):
            pending.append(result_id)
    return pending

def decide(conn, *, actor, agent_id, result_id, request_id, decision,
           expected_criteria_revision, note=None):
    _require_owner(actor)
    if decision not in ('accepted','revision_requested'):
        raise ValueError('Choose accept or request revision')
    if not isinstance(request_id, str) or not 1 <= len(request_id) <= 128:
        raise ValueError('Decision request identity is required')
    if (not isinstance(expected_criteria_revision, str)
            or not 1 <= len(expected_criteria_revision) <= 128):
        raise ValueError('Expected criteria revision is required')
    if note is not None and (not isinstance(note, str) or len(note) > 4000 or '\x00' in note):
        raise ValueError('Decision note must be bounded text')
    if decision == 'revision_requested' and (note is None or not note.strip()):
        raise ValueError('Explain the requested revision')
    note = note.strip() if note else None
    with write_txn(conn):
        result = conn.execute('SELECT agent_id,record_json FROM agent_native_work_results WHERE id=?', (result_id,)).fetchone()
        if not result or result[0] != agent_id:
            raise KeyError(result_id)
        record = json.loads(result[1])
        if not record.get('review', {}).get('required'):
            raise ValueError('This result does not require an owner decision')
        if record.get('criteria_revision') != expected_criteria_revision:
            raise ConflictError('Result criteria changed; reload before deciding')
        prior_request = conn.execute('SELECT result_id,decision,note FROM agent_native_result_decisions WHERE request_id=?', (request_id,)).fetchone()
        if prior_request:
            if tuple(prior_request) != (result_id, decision, note):
                raise ConflictError('Decision request was reused with different input')
            return get(conn, result_id)
        if get(conn, result_id):
            raise ConflictError('This exact result already has an owner decision')
        key = str(uuid4())
        conn.execute('INSERT INTO agent_native_result_decisions VALUES(?,?,?,?,?,?,?,?)',
                     (key, request_id, result_id, agent_id, decision, note, 'owner', _now()))
        if decision == 'revision_requested':
            feedback_id = str(uuid4())
            conn.execute('INSERT INTO agent_native_feedback(id,agent_id,soul_revision,request_id,text,status,created_at) VALUES(?,?,?,?,?,?,?)',
                         (feedback_id, agent_id, record['soul_revision'], 'result-revision:'+result_id,
                          'Owner requested revision of result '+result_id+': '+note, 'pending', _now()))
        # A decision is actionable input. An enabled cadence may pick it up now,
        # while its normal busy/terminal admission guards still apply.
        from agent_native.cadence import wake
        wake(conn, agent_id, 'owner_result_decision')
        run = conn.execute('SELECT id FROM agent_native_work_runs WHERE agent_id=? ORDER BY rowid DESC LIMIT 1', (agent_id,)).fetchone()
        if run:
            from agent_native.work_state import event
            event(conn, run[0], 'work.result_'+decision,
                  ('Owner accepted result ' if decision == 'accepted' else 'Owner requested revision of result ')+result_id)
        return get(conn, result_id)
