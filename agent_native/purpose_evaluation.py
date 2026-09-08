"""Immutable whole-purpose evaluations, separate from assignment results."""
import hashlib
import json
from uuid import uuid4

from agent_native.identity import _now
from hermes_cli.kanban_db_connect import write_txn

SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_native_purpose_evaluations (
 id TEXT PRIMARY KEY,agent_id TEXT NOT NULL REFERENCES agent_native_agents(id),
 run_id TEXT NOT NULL REFERENCES agent_native_work_runs(id),call_id TEXT NOT NULL,
 record_json TEXT NOT NULL,record_sha256 TEXT NOT NULL,created_at TEXT NOT NULL,
 UNIQUE(run_id,call_id));
CREATE INDEX IF NOT EXISTS agent_native_purpose_evaluation_agent
 ON agent_native_purpose_evaluations(agent_id,created_at);
"""

def _encode(record):
    return json.dumps(record,sort_keys=True,ensure_ascii=False,allow_nan=False)

def list_evaluations(conn,agent_id):
    values=[]
    for encoded,digest in conn.execute('SELECT record_json,record_sha256 FROM '
        'agent_native_purpose_evaluations WHERE agent_id=? ORDER BY created_at DESC,id DESC',(agent_id,)):
        if hashlib.sha256(encoded.encode()).hexdigest()!=digest: raise ValueError('Purpose evaluation integrity check failed')
        values.append(json.loads(encoded))
    return values

def record(conn,*,validate,agent_id,run_id,call_id,arguments):
    required={'judgment','evidence','remaining_obligations','uncertainty','next_action','question_id'}
    if not isinstance(arguments,dict) or set(arguments)!=required: raise ValueError('Purpose evaluation fields are required')
    if arguments['judgment'] not in {'continue','wait','clarify','retire_candidate'}: raise ValueError('Invalid purpose judgment')
    for name in ('evidence','remaining_obligations'):
        value=arguments[name]
        if not isinstance(value,list) or len(value)>100 or any(not isinstance(v,str) or not v.strip() or len(v)>2000 for v in value):
            raise ValueError('Purpose evaluation requires bounded '+name.replace('_',' '))
    if arguments['judgment']=='retire_candidate' and arguments['remaining_obligations']:
        raise ValueError('Retirement candidate cannot retain remaining obligations')
    question_id=arguments['question_id']
    if arguments['judgment']=='clarify':
        if not isinstance(question_id,str) or not question_id: raise ValueError('Clarification requires a question')
        question=conn.execute('SELECT soul_revision,answer FROM agent_native_questions WHERE id=? AND agent_id=?',
                              (question_id,agent_id)).fetchone()
        revision=conn.execute('SELECT soul_revision FROM agent_native_agents WHERE id=?',(agent_id,)).fetchone()
        if not question or question[0]!=revision[0] or question[1] is not None:
            raise ValueError('Clarification requires an applicable unanswered question')
    elif question_id is not None:
        raise ValueError('Only clarification can reference a question')
    for name in ('uncertainty','next_action'):
        value=arguments[name]
        if (value is not None and not isinstance(value,str)) or (isinstance(value,str) and len(value)>4000): raise ValueError('Invalid '+name)
    if not isinstance(arguments['next_action'],str) or not arguments['next_action'].strip(): raise ValueError('Next action is required')
    with write_txn(conn):
        validate(conn)
        prior=conn.execute('SELECT record_json FROM agent_native_purpose_evaluations WHERE run_id=? AND call_id=?',(run_id,call_id)).fetchone()
        if prior:
            existing=json.loads(prior[0])
            comparable={key:existing[key] for key in required}
            if comparable!=arguments: raise ValueError('Purpose evaluation call identity was reused')
            return existing
        work=conn.execute('SELECT agent_id,soul_revision FROM agent_native_work_runs WHERE id=?',(run_id,)).fetchone()
        if not work or work[0]!=agent_id: raise PermissionError('Purpose evaluation identity changed')
        purpose=conn.execute('SELECT purpose FROM agent_native_events WHERE agent_id=? AND soul_revision=?',(agent_id,work[1])).fetchone()
        if not purpose: raise PermissionError('Purpose revision unavailable')
        value={'id':str(uuid4()),'agent_id':agent_id,'run_id':run_id,'soul_revision':work[1],
               'purpose':purpose[0],**arguments,'created_at':_now()}
        encoded=_encode(value)
        conn.execute('INSERT INTO agent_native_purpose_evaluations VALUES(?,?,?,?,?,?,?)',
                     (value['id'],agent_id,run_id,call_id,encoded,hashlib.sha256(encoded.encode()).hexdigest(),value['created_at']))
        return value
