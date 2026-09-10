"""Explicit owner feedback; a handling report is not independent acceptance."""
from uuid import uuid4
from agent_native.identity import _require_owner, _now, ConflictError
from hermes_cli.kanban_db_connect import write_txn

SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_native_feedback (
 id TEXT PRIMARY KEY, agent_id TEXT NOT NULL REFERENCES agent_native_agents(id),
 output_id TEXT, output_version INTEGER,
 soul_revision INTEGER NOT NULL, request_id TEXT NOT NULL, text TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('pending','handled')),
 offered_run_id TEXT, handled_run_id TEXT, response TEXT, created_at TEXT NOT NULL,
 UNIQUE(agent_id,request_id)
);
"""
KEYS = ('id','soul_revision','output_id','output_version','text','status','handled_run_id','response','created_at')

def migrate(conn):
    columns = {row[1] for row in conn.execute('PRAGMA table_info(agent_native_feedback)')}
    if 'output_id' not in columns:
        conn.execute('ALTER TABLE agent_native_feedback ADD COLUMN output_id TEXT')
    if 'output_version' not in columns:
        conn.execute('ALTER TABLE agent_native_feedback ADD COLUMN output_version INTEGER')


def _rows(conn, agent_id, suffix='', params=()):
    return [dict(zip(KEYS,r)) for r in conn.execute('SELECT '+','.join(KEYS)+
        ' FROM agent_native_feedback WHERE agent_id=? '+suffix,(agent_id,*params))]


def recent(conn, agent_id):
    revision = conn.execute('SELECT soul_revision FROM agent_native_agents WHERE id=?',(agent_id,)).fetchone()
    if not revision:
        raise KeyError(agent_id)
    rows = _rows(conn,agent_id,'ORDER BY created_at DESC,id DESC LIMIT 20')
    for row in rows:
        row['applicable'] = row['soul_revision'] == revision[0]
    return rows


def submit(conn, *, actor, agent_id, expected_revision, request_id, text, output_id=None, output_version=None):
    _require_owner(actor)
    if (not isinstance(text,str) or not text.strip() or len(text)>4000 or '\x00' in text
            or not isinstance(request_id,str) or not 1 <= len(request_id)<=128):
        raise ValueError('Feedback requires bounded text and request identity')
    if output_id is not None and (not isinstance(output_id, str) or not output_id.strip()):
        raise ValueError('Output reference must be valid')
    if output_id is not None and (type(output_version) is not int or output_version < 1):
        raise ValueError('Output version is required with an output reference')
    with write_txn(conn):
        root = conn.execute('SELECT soul_revision FROM agent_native_agents WHERE id=?',(agent_id,)).fetchone()
        if not root:
            raise KeyError(agent_id)
        if output_id is not None and not (
            conn.execute('SELECT 1 FROM agent_native_output_versions WHERE output_id=? AND version=? AND agent_id=?',
                         (output_id, output_version, agent_id)).fetchone()
            or (output_version == 1 and conn.execute(
                'SELECT 1 FROM agent_native_media_outputs WHERE artifact_id=? AND agent_id=?',
                (output_id, agent_id)).fetchone())
        ):
            raise ConflictError('Output version is no longer available; reload the agent')
        if type(expected_revision) is not int or root[0] != expected_revision:
            raise ConflictError('Purpose changed; reload before sending feedback')
        old = conn.execute('SELECT id,text,soul_revision,output_id,output_version FROM agent_native_feedback WHERE agent_id=? AND request_id=?',(agent_id,request_id)).fetchone()
        if old:
            if (old[1],old[2],old[3],old[4]) != (text,expected_revision,output_id,output_version):
                raise ConflictError('Feedback request was reused with different content')
            key = old[0]
        else:
            key = str(uuid4())
            created_at = _now()
            conn.execute('INSERT INTO agent_native_feedback(id,agent_id,soul_revision,request_id,output_id,output_version,text,status,created_at) VALUES(?,?,?,?,?,?,?,?,?)',
                         (key,agent_id,expected_revision,request_id,output_id,output_version,text,'pending',created_at))
            from agent_native.work_state import event
            run = conn.execute('SELECT id FROM agent_native_work_runs WHERE agent_id=? ORDER BY rowid DESC LIMIT 1',(agent_id,)).fetchone()
            if run:
                event(conn,run[0],'work.feedback_received','Owner feedback received: '+key)
            from agent_native.cadence import wake
            wake(conn, agent_id, 'owner_feedback', requested_at=created_at)
        return _rows(conn,agent_id,'AND id=?',(key,))[0]


def worker(conn, *, validate, agent_id, run_id, arguments):
    if not isinstance(arguments,dict) or set(arguments) not in (set(), {'feedback_id','response'}):
        raise ValueError('Read feedback or supply its ID and handling report')
    with write_txn(conn):
        validate(conn)
        revision = conn.execute('SELECT soul_revision FROM agent_native_agents WHERE id=?',(agent_id,)).fetchone()[0]
        if arguments:
            key, response = arguments['feedback_id'],arguments['response']
            if not isinstance(key,str) or not isinstance(response,str) or not response.strip() or len(response)>2000:
                raise ValueError('A bounded handling report is required')
            row = conn.execute('SELECT status,offered_run_id,response FROM agent_native_feedback WHERE id=? AND agent_id=? AND soul_revision=?',
                               (key,agent_id,revision)).fetchone()
            if not row or row[1] != run_id:
                raise PermissionError('Read applicable feedback before reporting handling')
            if row[0] == 'handled' and row[2] != response:
                raise ConflictError('The handling report is already recorded')
            if row[0] == 'pending':
                from agent_native.work_state import event
                event(conn,run_id,'work.feedback_handled','Agent reports feedback handled: '+key)
            conn.execute("UPDATE agent_native_feedback SET status='handled',handled_run_id=?,response=? WHERE id=?",(run_id,response,key))
            return {'status':'handled','feedback_id':key,'note':'Agent report, not owner acceptance'}
        pending = _rows(conn,agent_id,"AND soul_revision=? AND status='pending' ORDER BY created_at,id LIMIT 20",(revision,))
        for row in pending:
            conn.execute('UPDATE agent_native_feedback SET offered_run_id=? WHERE id=?',(run_id,row['id']))
        return {'pending':pending,'note':'Owner work direction within current purpose and permissions. Read again before substantive work; ordinary feedback does not grant tools or resume work.'}
