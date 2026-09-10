"""Owner holds for one selected work item without disabling agent cadence."""
from agent_native.identity import _now, _require_owner, ConflictError, require_active
from hermes_cli.kanban_db_connect import write_txn

SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_native_work_holds (
 agent_id TEXT PRIMARY KEY REFERENCES agent_native_agents(id),
 run_id TEXT NOT NULL REFERENCES agent_native_work_runs(id),
 item_id TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL
);
"""


def read(conn, agent_id):
    row = conn.execute('SELECT run_id,item_id,reason,created_at FROM agent_native_work_holds WHERE agent_id=?', (agent_id,)).fetchone()
    return dict(zip(('run_id','item_id','reason','created_at'), row)) if row else None


def hold(conn, *, actor, agent_id, reason):
    _require_owner(actor)
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 1000:
        raise ValueError('A bounded reason is required to hold current work')
    with write_txn(conn):
        require_active(conn, agent_id)
        work = conn.execute('SELECT id,state FROM agent_native_work_runs WHERE agent_id=? ORDER BY rowid DESC LIMIT 1', (agent_id,)).fetchone()
        if not work or work[1] not in ('queued','preparing','running','stopping'):
            raise ConflictError('There is no active work attempt to hold')
        from agent_native.work_focus import read_focus
        focus = read_focus(conn, work[0])
        if not focus:
            raise ConflictError('The current attempt has not selected a work item yet')
        conn.execute('INSERT INTO agent_native_work_holds(agent_id,run_id,item_id,reason,created_at) VALUES(?,?,?,?,?) '
                     'ON CONFLICT(agent_id) DO UPDATE SET run_id=excluded.run_id,item_id=excluded.item_id,reason=excluded.reason,created_at=excluded.created_at',
                     (agent_id,work[0],focus['item_id'],reason.strip(),_now()))
        if work[1] in ('queued','preparing','running'):
            target = 'paused' if work[1] == 'queued' else 'stopping'
            conn.execute('UPDATE agent_native_work_runs SET state=?,stop_requested=1 WHERE id=?', (target, work[0]))
            from agent_native.work_state import event
            event(conn, work[0], 'work.'+target, 'Owner held the selected work item: '+reason.strip())
        return read(conn, agent_id)


def release(conn, *, actor, agent_id):
    _require_owner(actor)
    with write_txn(conn):
        require_active(conn, agent_id)
        if conn.execute('DELETE FROM agent_native_work_holds WHERE agent_id=?', (agent_id,)).rowcount != 1:
            raise ConflictError('Current work is not held')
        from agent_native.cadence import wake
        wake(conn, agent_id, 'work_hold_released')
        return {'released': True}
