"""Owner-configured check-ins; missed intervals coalesce into one bounded attempt."""
from datetime import datetime, timedelta
from uuid import uuid4
from agent_native.identity import _now, _require_owner, ConflictError
from hermes_cli.kanban_db_connect import write_txn
from agent_native.recovery_policy import recovery_identity

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
CREATE TABLE IF NOT EXISTS agent_native_cadence_skips (
 agent_id TEXT PRIMARY KEY REFERENCES agent_native_agents(id),
 state TEXT NOT NULL, blocker TEXT, release_condition TEXT,
 responsible_actor TEXT, overdue_since TEXT NOT NULL, observed_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS agent_native_one_active_run
 ON agent_native_work_runs(agent_id) WHERE state IN ('queued','preparing','running','stopping');
"""


def _decision(state, blocker=None, release=None, actor=None):
    return {'state': state, 'blocker': blocker, 'release_condition': release,
            'responsible_actor': actor}


def read_skip(conn, agent_id):
    """Return the durable classification of the latest overdue skipped check-in."""
    row = conn.execute(
        'SELECT state,blocker,release_condition,responsible_actor,overdue_since,observed_at '
        'FROM agent_native_cadence_skips WHERE agent_id=?', (agent_id,)).fetchone()
    return dict(zip(('state', 'blocker', 'release_condition', 'responsible_actor',
                     'overdue_since', 'observed_at'), row)) if row else None


def _record_skip(conn, agent_id, decision, overdue_since, now):
    """Upsert why a due, enabled cadence did not start this check-in."""
    conn.execute(
        'INSERT INTO agent_native_cadence_skips '
        '(agent_id,state,blocker,release_condition,responsible_actor,overdue_since,observed_at) '
        'VALUES(?,?,?,?,?,?,?) '
        'ON CONFLICT(agent_id) DO UPDATE SET state=excluded.state,blocker=excluded.blocker,'
        'release_condition=excluded.release_condition,responsible_actor=excluded.responsible_actor,'
        'overdue_since=excluded.overdue_since,observed_at=excluded.observed_at',
        (agent_id, decision['state'], decision.get('blocker'), decision.get('release_condition'),
         decision.get('responsible_actor'), overdue_since, now))


def clear_skip(conn, agent_id):
    conn.execute('DELETE FROM agent_native_cadence_skips WHERE agent_id=?', (agent_id,))


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
        clear_skip(conn, agent_id)
        event(conn,work['id'],'work.cadence','Cadence enabled: every '+str(interval_seconds)+' seconds' if enabled else 'Cadence disabled')
    return read(conn,agent_id)


def queue_due(conn, *, now=None, busy_agents=()):
    from agent_native.work_state import event
    now=now or _now()
    queued=[]
    with write_txn(conn):
        from agent_native.readiness import automatic_work
        for agent_id,revision,interval,due in conn.execute('SELECT agent_id,soul_revision,interval_seconds,next_due FROM agent_native_cadence WHERE enabled=1 AND next_due<=?',(now,)).fetchall():
            # Every skip of a due, enabled check-in is durably classified so an
            # overdue agent that does not start stays observable through the API/UI.
            if agent_id in busy_agents:
                _record_skip(conn, agent_id, _decision('working'), due, now)
                continue
            hold=conn.execute('SELECT reason FROM agent_native_work_holds WHERE agent_id=?', (agent_id,)).fetchone()
            if hold:
                _record_skip(conn, agent_id, _decision(
                    'held', blocker=hold[0] or 'Automatic work is held.',
                    release='Release the work hold.', actor='owner'), due, now)
                continue
            from agent_native.progress_concerns import suspend_if_stalled
            if suspend_if_stalled(conn, agent_id, now=now):
                # The open progress concern is the durable classification and
                # cadence is now disabled, so no skip record is needed.
                continue
            root=conn.execute('SELECT soul_revision FROM agent_native_agents WHERE id=?',(agent_id,)).fetchone()
            previous=conn.execute('SELECT id,activation_id,soul_revision,limits,state,finished_at FROM agent_native_work_runs WHERE agent_id=? ORDER BY rowid DESC LIMIT 1',(agent_id,)).fetchone()
            if previous and previous[4] == 'retryable_failure':
                from agent_native.recovery_policy import enforce_backoff
                if not enforce_backoff(conn, agent_id, now=now):
                    _record_skip(conn, agent_id, automatic_work(conn, agent_id, now=now), due, now)
                    continue
            if previous and previous[4] == 'unknown':
                # A lost Plane response may have been reconciled after the
                # worker stopped. Settle only when every linked effect is now
                # confirmed or rejected; an unresolved run remains blocked.
                from agent_native.work_state import reconcile_confirmed_unknown
                reconcile_confirmed_unknown(conn, agent_id)
                previous=conn.execute('SELECT id,activation_id,soul_revision,limits,state,finished_at FROM agent_native_work_runs WHERE agent_id=? ORDER BY rowid DESC LIMIT 1',(agent_id,)).fetchone()
            decision=automatic_work(conn, agent_id, now=now, busy=False)
            if not decision['may_start']:
                _record_skip(conn, agent_id, decision, due, now)
                continue
            wake_row=conn.execute(
                'SELECT reason FROM agent_native_cadence_wakes WHERE agent_id=?', (agent_id,),
            ).fetchone()
            if (not previous or root[0]!=revision or previous[2]!=revision
                    or previous[4] not in ('completed','interrupted','limit_reached','retryable_failure','paused')):
                _record_skip(conn, agent_id, _decision(
                    'framework_reconciliation',
                    blocker='The latest attempt is not eligible for a fresh check-in.',
                    release='Prepare the revised purpose or reconcile the latest attempt.',
                    actor='framework'), due, now)
                continue
            if conn.execute("SELECT 1 FROM agent_native_work_runs WHERE agent_id=? AND state IN ('queued','preparing','running','stopping')",(agent_id,)).fetchone():
                _record_skip(conn, agent_id, _decision('working'), due, now)
                continue
            from agent_native.delivery_barrier import unresolved_terminal_notices, record_notices
            notices = unresolved_terminal_notices(conn, agent_id)
            if previous[4] == 'retryable_failure':
                from agent_native.recovery_policy import recovery_identity
                key = recovery_identity(agent_id, previous[0])
            else:
                key=str(uuid4())
            conn.execute('INSERT INTO agent_native_work_runs(id,agent_id,activation_id,soul_revision,session_id,limits,state,created_at) VALUES(?,?,?,?,?,?,?,?)',
                (key,agent_id,previous[1],revision,'an_work_'+uuid4().hex,previous[3],'queued',now))
            conn.execute('UPDATE agent_native_cadence SET next_due=? WHERE agent_id=?',((datetime.fromisoformat(now)+timedelta(seconds=interval)).isoformat(),agent_id))
            conn.execute('DELETE FROM agent_native_cadence_wakes WHERE agent_id=?', (agent_id,))
            clear_skip(conn, agent_id)
            summary = ('Automatic recovery after a temporary failure; continuing with a stable recovery identity.'
                       if previous[4] == 'retryable_failure' else
                       'Scheduled check-in after actionable input: ' + wake_row[0] + '.' if wake_row else
                       'Scheduled check-in: review progress and decide whether to work, ask or wait.')
            event(conn,key,'work.queued',summary)
            record_notices(conn, key, notices)
            queued.append(key)
    return queued


def queue_revised_purposes(conn, *, now=None):
    """Start one fresh bounded attempt after a revised purpose is fully prepared."""
    from agent_native.work_state import event
    now = now or _now()
    queued = []
    with write_txn(conn):
        rows = conn.execute(
            "SELECT a.id,a.soul_revision,w.id,w.activation_id,w.soul_revision,w.limits,w.state "
            "FROM agent_native_agents a "
            "JOIN agent_native_setup s ON s.agent_id=a.id AND s.status='ready' "
            "JOIN agent_native_setup_revisions sr ON sr.agent_id=a.id AND sr.soul_revision=a.soul_revision "
            "JOIN agent_native_work_runs w ON w.rowid=(SELECT max(previous.rowid) "
            " FROM agent_native_work_runs previous WHERE previous.agent_id=a.id) "
            "WHERE w.soul_revision<a.soul_revision "
            "AND w.state IN ('paused','interrupted','limit_reached','completed','retryable_failure','failed') "
            "AND a.id NOT IN (SELECT agent_id FROM agent_native_removals) "
            "AND a.id NOT IN (SELECT agent_id FROM agent_native_retirements) "
            "AND a.id NOT IN (SELECT agent_id FROM agent_native_agent_pauses)"
        ).fetchall()
        for agent_id,revision,_previous_id,activation_id,_old_revision,limits,_state in rows:
            if conn.execute(
                "SELECT 1 FROM agent_native_work_runs WHERE agent_id=? "
                "AND (soul_revision=? OR state IN ('queued','preparing','running','stopping'))",
                (agent_id,revision),
            ).fetchone():
                continue
            run_id = str(uuid4())
            conn.execute(
                'INSERT INTO agent_native_work_runs '
                '(id,agent_id,activation_id,soul_revision,session_id,limits,state,created_at) '
                'VALUES(?,?,?,?,?,?,?,?)',
                (run_id,agent_id,activation_id,revision,'an_work_'+uuid4().hex,limits,'queued',now),
            )
            conn.execute(
                'UPDATE agent_native_cadence SET soul_revision=? WHERE agent_id=?',
                (revision,agent_id),
            )
            event(conn,run_id,'work.queued',
                  'Purpose changed; starting a fresh planning attempt from the prepared project.')
            queued.append(run_id)
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
