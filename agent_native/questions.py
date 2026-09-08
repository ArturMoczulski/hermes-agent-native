"""Durable questions whose trusted answers wake enabled cadence, never paused work."""
from uuid import uuid4
from agent_native.identity import _require_owner, _now, ConflictError
from hermes_cli.kanban_db_connect import write_txn

SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_native_questions (
 id TEXT PRIMARY KEY, agent_id TEXT NOT NULL REFERENCES agent_native_agents(id),
 soul_revision INTEGER NOT NULL, run_id TEXT NOT NULL, item_id TEXT NOT NULL,
 fingerprint TEXT NOT NULL, topic TEXT NOT NULL, question TEXT NOT NULL,
 answer TEXT, created_at TEXT NOT NULL, answered_at TEXT,
 UNIQUE(agent_id,soul_revision,item_id,fingerprint,topic)
);
"""
KEYS=('id','soul_revision','run_id','item_id','fingerprint','topic','question','answer','created_at','answered_at')


def _get(conn,agent_id,key):
    row=conn.execute('SELECT '+','.join(KEYS)+' FROM agent_native_questions WHERE agent_id=? AND id=?',(agent_id,key)).fetchone()
    if not row:
        raise KeyError(key)
    return dict(zip(KEYS,row))


def recent(conn,agent_id):
    root=conn.execute('SELECT soul_revision FROM agent_native_agents WHERE id=?',(agent_id,)).fetchone()
    if not root:
        raise KeyError(agent_id)
    rows=conn.execute('SELECT '+','.join(KEYS)+' FROM agent_native_questions WHERE agent_id=? '
                     'ORDER BY (answer IS NULL) DESC,created_at DESC,id DESC LIMIT 20',(agent_id,)).fetchall()
    return [dict(zip(KEYS,row),applicable=row[1]==root[0]) for row in rows]


def answer(conn,*,actor,agent_id,question_id,expected_revision,answer):
    _require_owner(actor)
    if not isinstance(answer,str) or not answer.strip() or len(answer)>4000 or '\x00' in answer:
        raise ValueError('Supply a bounded answer')
    with write_txn(conn):
        q=_get(conn,agent_id,question_id)
        root=conn.execute('SELECT soul_revision FROM agent_native_agents WHERE id=?',(agent_id,)).fetchone()
        if type(expected_revision) is not int or root[0]!=expected_revision or q['soul_revision']!=expected_revision:
            raise ConflictError('This question belongs to an earlier purpose')
        if q['answer'] is not None:
            if q['answer']!=answer:
                raise ConflictError('An answer is already recorded; review it before giving new direction')
            return q
        conn.execute('UPDATE agent_native_questions SET answer=?,answered_at=? WHERE id=?',(answer,_now(),question_id))
        conn.execute('UPDATE agent_native_cadence SET next_due=? WHERE agent_id=? AND enabled=1',(_now(),agent_id))
        from agent_native.work_state import event
        event(conn,q['run_id'],'work.question_answered','Owner answered question: '+question_id)
        return _get(conn,agent_id,question_id)


def worker(conn,*,validate,inspect,agent_id,run_id,arguments):
    validate(conn)
    if not isinstance(arguments,dict) or set(arguments) not in ({'question_id'},{'item_id','topic','question'}):
        raise ValueError('Ask an item question or read a question by ID')
    from agent_native.work_focus import read_focus
    focus=read_focus(conn,run_id)
    reading='question_id' in arguments
    if reading:
        q=_get(conn,agent_id,arguments['question_id'])
        item_id=q['item_id']
    else:
        if not focus:
            raise ConflictError('Select work before asking questions')
        for key,limit in (('item_id',128),('topic',128),('question',2000)):
            if not isinstance(arguments[key],str) or not arguments[key].strip() or len(arguments[key])>limit or '\x00' in arguments[key]:
                raise ValueError('Question fields must be bounded text')
        item_id=arguments['item_id']
    if not reading and focus['item_id']!=item_id:
        raise ConflictError('This question is not for the selected work item')
    observation=inspect({'kind':'item','resource_id':item_id})
    with write_txn(conn):
        validate(conn)
        revision=conn.execute('SELECT soul_revision FROM agent_native_agents WHERE id=?',(agent_id,)).fetchone()[0]
        if reading:
            q=_get(conn,agent_id,arguments['question_id'])
            applicable=q['soul_revision']==revision and q['fingerprint']==observation['fingerprint']
            return {**q, 'applicable':applicable,
                    'has_recorded_answer':q['answer'] is not None,
                    'answer':q['answer'] if applicable else None,
                    'context_note':None if applicable else
                        'Question context changed. Reassess current requirements; any recorded answer is withheld as outdated.'}
        old=conn.execute('SELECT id FROM agent_native_questions WHERE agent_id=? AND soul_revision=? AND item_id=? AND fingerprint=? AND topic=?',
                         (agent_id,revision,item_id,observation['fingerprint'],arguments['topic'])).fetchone()
        if old:
            q=_get(conn,agent_id,old[0])
            if q['question']!=arguments['question']:
                raise ConflictError('Question topic already exists with different wording')
            return q
        key=str(uuid4())
        conn.execute('INSERT INTO agent_native_questions(id,agent_id,soul_revision,run_id,item_id,fingerprint,topic,question,created_at) VALUES(?,?,?,?,?,?,?,?,?)',
                     (key,agent_id,revision,run_id,item_id,observation['fingerprint'],arguments['topic'],arguments['question'],_now()))
        from agent_native.work_state import event
        event(conn,run_id,'work.question_asked','Agent asked an owner question: '+key)
        question = _get(conn,agent_id,key)
        from agent_native.progress import question_asked
        question_asked(conn, {**question, 'agent_id':agent_id})
        return question
