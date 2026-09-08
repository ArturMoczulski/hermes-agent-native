"""Owner-controlled autonomy policy, frozen for each admitted work attempt."""
from agent_native.identity import ConflictError, _now, _require_owner
from hermes_cli.kanban_db_connect import write_txn

DEFAULT_LEVEL = 3
AUTONOMY_SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_native_autonomy_settings (
 agent_id TEXT PRIMARY KEY REFERENCES agent_native_agents(id), level INTEGER NOT NULL CHECK(level BETWEEN 1 AND 5),
 revision INTEGER NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS agent_native_creation_autonomy (
 agent_id TEXT PRIMARY KEY REFERENCES agent_native_agents(id), level INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS agent_native_autonomy_attempts (
 attempt_id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES agent_native_work_runs(id),
 agent_id TEXT NOT NULL REFERENCES agent_native_agents(id),
 level INTEGER NOT NULL, revision INTEGER NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS agent_native_autonomy_events (
 sequence INTEGER PRIMARY KEY AUTOINCREMENT, agent_id TEXT NOT NULL REFERENCES agent_native_agents(id),
 level INTEGER NOT NULL, revision INTEGER NOT NULL, actor TEXT NOT NULL, created_at TEXT NOT NULL);
"""

def validate_level(level):
    if type(level) is not int or not 1 <= level <= 5:
        raise ValueError('Autonomy level must be an integer from 1 to 5')
    return level

def initialize_agent(conn, agent_id, level=DEFAULT_LEVEL):
    level, now = validate_level(level), _now()
    conn.execute('INSERT INTO agent_native_autonomy_settings VALUES(?,?,?,?)', (agent_id, level, 1, now))
    conn.execute('INSERT INTO agent_native_creation_autonomy VALUES(?,?)', (agent_id, level))
    conn.execute('INSERT INTO agent_native_autonomy_events(agent_id,level,revision,actor,created_at) VALUES(?,?,?,?,?)',
                 (agent_id, level, 1, 'owner', now))

def get_settings(conn, agent_id):
    if not conn.execute('SELECT 1 FROM agent_native_agents WHERE id=?', (agent_id,)).fetchone():
        raise KeyError(agent_id)
    row = conn.execute('SELECT level,revision,updated_at FROM agent_native_autonomy_settings WHERE agent_id=?', (agent_id,)).fetchone()
    return dict(zip(('level','revision','updated_at'), row)) if row else {'level': DEFAULT_LEVEL, 'revision': 1, 'updated_at': None}

def change_settings(conn, *, actor, agent_id, level, expected_revision):
    _require_owner(actor); level = validate_level(level)
    with write_txn(conn):
        current = get_settings(conn, agent_id)
        if type(expected_revision) is not int or current['revision'] != expected_revision:
            raise ConflictError('Autonomy setting changed; reload before saving')
        if current['level'] == level: return current
        revision, now = current['revision'] + 1, _now()
        conn.execute('INSERT INTO agent_native_autonomy_settings VALUES(?,?,?,?) ON CONFLICT(agent_id) DO UPDATE SET level=excluded.level,revision=excluded.revision,updated_at=excluded.updated_at',
                     (agent_id, level, revision, now))
        conn.execute('INSERT INTO agent_native_autonomy_events(agent_id,level,revision,actor,created_at) VALUES(?,?,?,?,?)',
                     (agent_id, level, revision, 'owner', now))
        return get_settings(conn, agent_id)

def snapshot_attempt(conn, agent_id, run_id, attempt_id):
    with write_txn(conn, allow_nested=True):
        row = conn.execute('SELECT agent_id,level,revision,created_at FROM agent_native_autonomy_attempts WHERE attempt_id=?', (attempt_id,)).fetchone()
        if row:
            if row[0] != agent_id: raise PermissionError('Autonomy attempt belongs to another agent')
            return dict(zip(('agent_id','level','revision','created_at'), row))
        current = get_settings(conn, agent_id)
        conn.execute('INSERT INTO agent_native_autonomy_attempts VALUES(?,?,?,?,?,?)', (attempt_id, run_id, agent_id, current['level'], current['revision'], _now()))
        return snapshot_attempt(conn, agent_id, run_id, attempt_id)

def policy(level):
    guidance = {
        1: 'Request owner acceptance after nearly every meaningful deliverable before continuing dependent work.',
        2: 'Continue small reversible steps; request owner acceptance between major stages or consequential outputs.',
        3: 'Continue ordinary reversible work; request owner acceptance for significant commitments, costly actions, or material direction changes.',
        4: 'Continue proactively across milestones; request owner acceptance only for high-impact ambiguity or consequential commitments.',
        5: 'Continuously pursue the purpose across outputs and milestones. Treat review as optional and keep working unless a decision is extremely consequential, outside granted authority, unsafe to infer, or effectively irreversible.',
    }[validate_level(level)]
    return (f'Autonomy level {level}/5: {guidance} Explicit owner instructions, assignment requirements, authority limits, '
            'and mandatory policy gates always remain binding. Evaluation is always required; do not invent an owner-acceptance gate.')
