"""Owner-authored review gates bound to an observed Plane assignment revision."""
from agent_native.identity import ConflictError, _now, _require_owner
from hermes_cli.kanban_db_connect import write_txn

SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_native_assignment_review_policies (
 agent_id TEXT NOT NULL REFERENCES agent_native_agents(id), item_id TEXT NOT NULL,
 assignment_fingerprint TEXT NOT NULL, required INTEGER NOT NULL CHECK(required IN (0,1)),
 revision INTEGER NOT NULL, updated_at TEXT NOT NULL,
 PRIMARY KEY(agent_id,item_id));
"""

def list_policies(conn, agent_id):
    return [dict(agent_id=row[0],item_id=row[1],assignment_fingerprint=row[2],
                 required=bool(row[3]),revision=row[4],updated_at=row[5]) for row in conn.execute(
        'SELECT agent_id,item_id,assignment_fingerprint,required,revision,updated_at '
        'FROM agent_native_assignment_review_policies WHERE agent_id=? ORDER BY item_id',(agent_id,))]

def configure_current(conn, *, actor, agent_id, run_id, required, expected_revision):
    _require_owner(actor)
    if type(required) is not bool: raise ValueError('Assignment review policy must be explicit')
    from agent_native.work_focus import read_focus
    focus=read_focus(conn,run_id)
    if not focus: raise ConflictError('This attempt has no selected work item')
    row=conn.execute('SELECT agent_id FROM agent_native_work_runs WHERE id=?',(run_id,)).fetchone()
    if not row or row[0]!=agent_id: raise KeyError(run_id)
    with write_txn(conn):
        prior=conn.execute('SELECT revision FROM agent_native_assignment_review_policies '
                           'WHERE agent_id=? AND item_id=?',(agent_id,focus['item_id'])).fetchone()
        revision=prior[0] if prior else 0
        if revision!=expected_revision: raise ConflictError('Assignment review policy changed; reload')
        revision+=1
        conn.execute('INSERT INTO agent_native_assignment_review_policies VALUES(?,?,?,?,?,?) '
                     'ON CONFLICT(agent_id,item_id) DO UPDATE SET '
                     'assignment_fingerprint=excluded.assignment_fingerprint,required=excluded.required,'
                     'revision=excluded.revision,updated_at=excluded.updated_at',
                     (agent_id,focus['item_id'],focus['assignment_fingerprint'],int(required),revision,_now()))
    return next(p for p in list_policies(conn,agent_id) if p['item_id']==focus['item_id'])

def applicable(conn, agent_id, item_id, fingerprint):
    row=conn.execute('SELECT assignment_fingerprint,required FROM '
                     'agent_native_assignment_review_policies WHERE agent_id=? AND item_id=?',
                     (agent_id,item_id)).fetchone()
    if not row or not row[1]: return False
    if row[0]!=fingerprint:
        raise ConflictError('Assignment changed after its review policy was set; owner must refresh the gate')
    return True
