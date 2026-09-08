"""Owner-controlled autonomy policy, frozen for each admitted work attempt."""
from agent_native.identity import ConflictError, _now, _require_owner
from hermes_cli.kanban_db_connect import write_txn

DEFAULT_LEVEL = 3
AUTONOMY_SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_native_autonomy_settings (
 agent_id TEXT PRIMARY KEY REFERENCES agent_native_agents(id), level INTEGER NOT NULL CHECK(level BETWEEN 1 AND 5),
 require_owner_review INTEGER NOT NULL DEFAULT 0 CHECK(require_owner_review IN (0,1)),
 revision INTEGER NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS agent_native_creation_autonomy (
 agent_id TEXT PRIMARY KEY REFERENCES agent_native_agents(id), level INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS agent_native_autonomy_attempts (
 attempt_id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES agent_native_work_runs(id),
 agent_id TEXT NOT NULL REFERENCES agent_native_agents(id),
 level INTEGER NOT NULL, require_owner_review INTEGER NOT NULL DEFAULT 0 CHECK(require_owner_review IN (0,1)),
 revision INTEGER NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS agent_native_autonomy_events (
 sequence INTEGER PRIMARY KEY AUTOINCREMENT, agent_id TEXT NOT NULL REFERENCES agent_native_agents(id),
 level INTEGER NOT NULL, require_owner_review INTEGER NOT NULL DEFAULT 0 CHECK(require_owner_review IN (0,1)),
 revision INTEGER NOT NULL, actor TEXT NOT NULL, created_at TEXT NOT NULL);
"""

def migrate_review_policy(conn):
    for table in ('agent_native_autonomy_settings','agent_native_autonomy_attempts',
                  'agent_native_autonomy_events'):
        columns={row[1] for row in conn.execute(f'PRAGMA table_info({table})')}
        if 'require_owner_review' not in columns:
            conn.execute(f'ALTER TABLE {table} ADD COLUMN require_owner_review '
                         'INTEGER NOT NULL DEFAULT 0 CHECK(require_owner_review IN (0,1))')

def validate_level(level):
    if type(level) is not int or not 1 <= level <= 5:
        raise ValueError('Autonomy level must be an integer from 1 to 5')
    return level

def initialize_agent(conn, agent_id, level=DEFAULT_LEVEL):
    level, now = validate_level(level), _now()
    conn.execute('INSERT INTO agent_native_autonomy_settings '
                 '(agent_id,level,require_owner_review,revision,updated_at) VALUES(?,?,?,?,?)',
                 (agent_id, level, 0, 1, now))
    conn.execute('INSERT INTO agent_native_creation_autonomy VALUES(?,?)', (agent_id, level))
    conn.execute('INSERT INTO agent_native_autonomy_events'
                 '(agent_id,level,require_owner_review,revision,actor,created_at) VALUES(?,?,?,?,?,?)',
                 (agent_id, level, 0, 1, 'owner', now))

def get_settings(conn, agent_id):
    if not conn.execute('SELECT 1 FROM agent_native_agents WHERE id=?', (agent_id,)).fetchone():
        raise KeyError(agent_id)
    row = conn.execute('SELECT level,require_owner_review,revision,updated_at '
                       'FROM agent_native_autonomy_settings WHERE agent_id=?', (agent_id,)).fetchone()
    if not row: return {'level':DEFAULT_LEVEL,'require_owner_review':False,'revision':1,'updated_at':None}
    return {'level':row[0],'require_owner_review':bool(row[1]),'revision':row[2],'updated_at':row[3]}

def change_settings(conn, *, actor, agent_id, level, expected_revision,
                    require_owner_review=None, _allow_nested=False,
                    _recorded_actor='owner'):
    _require_owner(actor); level = validate_level(level)
    if (_recorded_actor != 'owner'
            and (not isinstance(_recorded_actor, str) or not _recorded_actor.startswith('parent:'))):
        raise ValueError('Invalid autonomy actor')
    with write_txn(conn, allow_nested=_allow_nested):
        current = get_settings(conn, agent_id)
        if type(expected_revision) is not int or current['revision'] != expected_revision:
            raise ConflictError('Autonomy setting changed; reload before saving')
        required=current['require_owner_review'] if require_owner_review is None else require_owner_review
        if type(required) is not bool: raise ValueError('Review policy must be explicit')
        if current['level'] == level and current['require_owner_review'] == required: return current
        revision, now = current['revision'] + 1, _now()
        conn.execute('INSERT INTO agent_native_autonomy_settings '
                     '(agent_id,level,require_owner_review,revision,updated_at) VALUES(?,?,?,?,?) '
                     'ON CONFLICT(agent_id) DO UPDATE SET level=excluded.level,'
                     'require_owner_review=excluded.require_owner_review,revision=excluded.revision,'
                     'updated_at=excluded.updated_at',(agent_id,level,int(required),revision,now))
        conn.execute('INSERT INTO agent_native_autonomy_events'
                     '(agent_id,level,require_owner_review,revision,actor,created_at) VALUES(?,?,?,?,?,?)',
                     (agent_id,level,int(required),revision,_recorded_actor,now))
        return get_settings(conn, agent_id)

def snapshot_attempt(conn, agent_id, run_id, attempt_id):
    with write_txn(conn, allow_nested=True):
        row = conn.execute('SELECT agent_id,level,require_owner_review,revision,created_at '
                           'FROM agent_native_autonomy_attempts WHERE attempt_id=?', (attempt_id,)).fetchone()
        if row:
            if row[0] != agent_id: raise PermissionError('Autonomy attempt belongs to another agent')
            return {'agent_id':row[0],'level':row[1],'require_owner_review':bool(row[2]),
                    'revision':row[3],'created_at':row[4]}
        current = get_settings(conn, agent_id)
        conn.execute('INSERT INTO agent_native_autonomy_attempts '
                     '(attempt_id,run_id,agent_id,level,require_owner_review,revision,created_at) '
                     'VALUES(?,?,?,?,?,?,?)',(attempt_id,run_id,agent_id,current['level'],
                                             int(current['require_owner_review']),current['revision'],_now()))
        return snapshot_attempt(conn, agent_id, run_id, attempt_id)

def policy(level, require_owner_review=False):
    guidance = {
        1: 'Request owner acceptance after nearly every meaningful deliverable before continuing dependent work.',
        2: 'Continue small reversible steps; request owner acceptance between major stages or consequential outputs.',
        3: 'Continue ordinary reversible work; request owner acceptance for significant commitments, costly actions, or material direction changes.',
        4: 'Continue proactively across milestones; request owner acceptance only for high-impact ambiguity or consequential commitments.',
        5: 'Continuously pursue the purpose across outputs and milestones. Treat review as optional and keep working unless a decision is extremely consequential, outside granted authority, unsafe to infer, or effectively irreversible.',
    }[validate_level(level)]
    review = (' Owner policy requires acceptance of every submitted deliverable before dependent work continues.'
              if require_owner_review else '')
    return (f'Autonomy level {level}/5: {guidance}{review} Explicit owner instructions, assignment requirements, authority limits, '
            'and mandatory policy gates always remain binding. Evaluation is always required; do not invent an owner-acceptance gate.')
