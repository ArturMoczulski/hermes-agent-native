"""Owner-configured check-ins; missed intervals coalesce into one bounded attempt."""
from datetime import datetime, timedelta
from uuid import uuid4
from agent_native.identity import _now, _require_owner, ConflictError
from hermes_cli.kanban_db_connect import write_txn

SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_native_cadence (
 agent_id TEXT PRIMARY KEY REFERENCES agent_native_agents(id),
 soul_revision INTEGER NOT NULL, enabled INTEGER NOT NULL,
 interval_seconds INTEGER NOT NULL, next_due TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS agent_native_cadence_wakes (
 agent_id TEXT PRIMARY KEY REFERENCES agent_native_agents(id),
 requested_at TEXT NOT NULL, reason TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS agent_native_one_active_run
 ON agent_native_work_runs(agent_id) WHERE state IN ('queued','preparing','running','stopping');
"""


def read(conn, agent_id):
    row=conn.execute('SELECT soul_revision,enabled,interval_seconds,next_due FROM agent_native_cadence WHERE agent_id=?',(agent_id,)).fetchone()
    return dict(zip(('soul_revision','enabled','interval_seconds','next_due'),(row[0],bool(row[1]),row[2],row[3]))) if row else {'enabled':False,'interval_seconds':None,'next_due':None,'soul_revision':None}


def wake(conn, agent_id, reason, *, requested_at=None):
    """Make enabled cadence promptly eligible after durable actionable input."""
    if not isinstance(reason, str) or not reason or len(reason) > 128:
        raise ValueError('Cadence wake reason must be bounded text')
    requested_at = requested_at or _now()
    changed = conn.execute(
        'UPDATE agent_native_cadence SET next_due=? WHERE agent_id=? AND enabled=1',
        (requested_at, agent_id),
    ).rowcount
    if changed:
        conn.execute(
            'INSERT INTO agent_native_cadence_wakes(agent_id,requested_at,reason) VALUES(?,?,?) '
            'ON CONFLICT(agent_id) DO UPDATE SET requested_at=excluded.requested_at,reason=excluded.reason',
            (agent_id, requested_at, reason),
        )
    return bool(changed)


def configure(conn, *, actor, agent_id, expected_revision, interval_seconds, enabled,
              _allow_nested=False):
    _require_owner(actor)
    if type(enabled) is not bool or type(interval_seconds) is not int or not 1<=interval_seconds<=2592000:
        raise ValueError('Choose an interval of 1 to 2592000 seconds and an explicit enabled setting')
    with write_txn(conn, allow_nested=_allow_nested):
        from agent_native.identity import require_active
        require_active(conn, agent_id)
        if enabled:
            from agent_native.subtree_lifecycle import require_not_paused
            require_not_paused(conn, agent_id)
        root=conn.execute('SELECT soul_revision FROM agent_native_agents WHERE id=?',(agent_id,)).fetchone()
        if not root: raise KeyError(agent_id)
        if root[0]!=expected_revision: raise ConflictError('Purpose changed; reload cadence settings')
        from agent_native.work_state import read_work, event
        work=read_work(conn,agent_id)
        if not work: raise ConflictError('Configure bounded work before enabling cadence')
        if enabled and conn.execute(
                "SELECT 1 FROM agent_native_progress_concerns WHERE agent_id=? AND status='open'",
                (agent_id,)).fetchone():
            raise ConflictError('Review the open progress concern before resuming cadence')
        if enabled and work['state'] in ('paused','failed','unknown','stopping'):
            raise ConflictError('Work requires owner review before cadence can be enabled')
        due=(datetime.fromisoformat(_now())+timedelta(seconds=interval_seconds)).isoformat()
        conn.execute('INSERT INTO agent_native_cadence VALUES(?,?,?,?,?) ON CONFLICT(agent_id) DO UPDATE SET soul_revision=excluded.soul_revision,enabled=excluded.enabled,interval_seconds=excluded.interval_seconds,next_due=excluded.next_due',
            (agent_id,expected_revision,int(enabled),interval_seconds,due))
        conn.execute('DELETE FROM agent_native_cadence_wakes WHERE agent_id=?', (agent_id,))
        event(conn,work['id'],'work.cadence','Cadence enabled: every '+str(interval_seconds)+' seconds' if enabled else 'Cadence disabled')
    return read(conn,agent_id)


def queue_due(conn, *, now=None, busy_agents=()):
    from agent_native.work_state import event
    now=now or _now()
    queued=[]
    with write_txn(conn):
        for agent_id,revision,interval,due in conn.execute('SELECT agent_id,soul_revision,interval_seconds,next_due FROM agent_native_cadence WHERE enabled=1 AND next_due<=?',(now,)).fetchall():
            if agent_id in busy_agents: continue
            from agent_native.progress_concerns import suspend_if_stalled
            if suspend_if_stalled(conn, agent_id): continue
            from agent_native.acceptance import pending_required
            if pending_required(conn, agent_id): continue
            latest_evaluation=conn.execute('SELECT record_json FROM agent_native_purpose_evaluations '
                'WHERE agent_id=? ORDER BY created_at DESC,id DESC LIMIT 1',(agent_id,)).fetchone()
            if latest_evaluation:
                import json
                evaluation=json.loads(latest_evaluation[0])
                if evaluation['judgment']=='clarify':
                    question=conn.execute('SELECT answer FROM agent_native_questions WHERE id=? AND agent_id=?',
                                          (evaluation['question_id'],agent_id)).fetchone()
                    if question and question[0] is None: continue
            root=conn.execute('SELECT soul_revision FROM agent_native_agents WHERE id=?',(agent_id,)).fetchone()
            previous=conn.execute('SELECT id,activation_id,soul_revision,limits,state,finished_at FROM agent_native_work_runs WHERE agent_id=? ORDER BY rowid DESC LIMIT 1',(agent_id,)).fetchone()
            wake_row=conn.execute(
                'SELECT reason FROM agent_native_cadence_wakes WHERE agent_id=?', (agent_id,),
            ).fetchone()
            if (not previous or root[0]!=revision or previous[2]!=revision
                    or previous[4] not in ('completed','interrupted','limit_reached','retryable_failure','paused')): continue
            if (not wake_row and previous[5]
                    and datetime.fromisoformat(now)<datetime.fromisoformat(previous[5])+timedelta(seconds=interval)):
                continue
            if conn.execute("SELECT 1 FROM agent_native_work_runs WHERE agent_id=? AND state IN ('queued','preparing','running','stopping')",(agent_id,)).fetchone(): continue
            from agent_native.delivery_barrier import unresolved_terminal_notices, record_notices
            try:
                notices = unresolved_terminal_notices(conn, agent_id)
            except ConflictError:
                continue
            key=str(uuid4())
            conn.execute('INSERT INTO agent_native_work_runs(id,agent_id,activation_id,soul_revision,session_id,limits,state,created_at) VALUES(?,?,?,?,?,?,?,?)',
                (key,agent_id,previous[1],revision,'an_work_'+uuid4().hex,previous[3],'queued',now))
            conn.execute('UPDATE agent_native_cadence SET next_due=? WHERE agent_id=?',((datetime.fromisoformat(now)+timedelta(seconds=interval)).isoformat(),agent_id))
            conn.execute('DELETE FROM agent_native_cadence_wakes WHERE agent_id=?', (agent_id,))
            summary = ('Scheduled check-in after actionable input: ' + wake_row[0] + '.' if wake_row else
                       'Scheduled check-in: review progress and decide whether to work, ask or wait.')
            event(conn,key,'work.queued',summary)
            record_notices(conn, key, notices)
            queued.append(key)
    return queued


def migrate_runs(conn):
    """Remove legacy per-agent/per-activation uniqueness, retaining every FK target."""
    old=conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='agent_native_work_runs'").fetchone()
    if not old or 'agent_id TEXT NOT NULL UNIQUE' not in old[0]: return
    if conn.in_transaction: raise RuntimeError('Run migration requires an initialization boundary')
    foreign=conn.execute('PRAGMA foreign_keys').fetchone()[0]
    conn.execute('PRAGMA foreign_keys=OFF')
    try:
        conn.execute('BEGIN IMMEDIATE')
        sql=old[0].replace('agent_native_work_runs','agent_native_work_runs_new',1).replace('agent_id TEXT NOT NULL UNIQUE','agent_id TEXT NOT NULL').replace('activation_id TEXT NOT NULL UNIQUE','activation_id TEXT NOT NULL')
        conn.execute(sql)
        conn.execute('INSERT INTO agent_native_work_runs_new SELECT * FROM agent_native_work_runs ORDER BY rowid')
        conn.execute('DROP TABLE agent_native_work_runs')
        conn.execute('ALTER TABLE agent_native_work_runs_new RENAME TO agent_native_work_runs')
        if conn.execute('PRAGMA foreign_key_check').fetchone(): raise RuntimeError('Run migration would break references')
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.execute('PRAGMA foreign_keys='+str(foreign))
