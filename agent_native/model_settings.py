"""Owner model assignments and immutable attempt selections; credentials stay native."""
import json

from agent_native.identity import ConflictError, _now, _require_owner
from hermes_cli.kanban_db_connect import write_txn

MODEL_SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_native_model_default (
 id INTEGER PRIMARY KEY CHECK(id=1), provider TEXT NOT NULL, model TEXT NOT NULL,
 revision INTEGER NOT NULL, updated_at TEXT NOT NULL,
 reasoning_effort TEXT NOT NULL DEFAULT 'default'
);
CREATE TABLE IF NOT EXISTS agent_native_model_selections (
 agent_id TEXT PRIMARY KEY REFERENCES agent_native_agents(id),
 provider TEXT NOT NULL, model TEXT NOT NULL, revision INTEGER NOT NULL,
 source TEXT NOT NULL, updated_at TEXT NOT NULL,
 reasoning_effort TEXT NOT NULL DEFAULT 'default'
);
CREATE TABLE IF NOT EXISTS agent_native_creation_model (
 agent_id TEXT PRIMARY KEY REFERENCES agent_native_agents(id), input_json TEXT
);
CREATE TABLE IF NOT EXISTS agent_native_model_attempts (
 kind TEXT NOT NULL, attempt_id TEXT NOT NULL,
 agent_id TEXT NOT NULL REFERENCES agent_native_agents(id),
 provider TEXT NOT NULL, model TEXT NOT NULL, revision INTEGER NOT NULL,
 source TEXT NOT NULL, created_at TEXT NOT NULL,
 reasoning_effort TEXT NOT NULL DEFAULT 'default', PRIMARY KEY(kind,attempt_id)
);
CREATE TABLE IF NOT EXISTS agent_native_model_events (
 sequence INTEGER PRIMARY KEY AUTOINCREMENT, agent_id TEXT,
 kind TEXT NOT NULL, provider TEXT NOT NULL, model TEXT NOT NULL,
 revision INTEGER NOT NULL, actor TEXT NOT NULL, created_at TEXT NOT NULL,
 reasoning_effort TEXT NOT NULL DEFAULT 'default'
);
"""


def migrate_reasoning(conn):
    """Add preferences to pre-feature records under the native initializer lock."""
    for table in ('agent_native_model_default', 'agent_native_model_selections',
                  'agent_native_model_attempts', 'agent_native_model_events'):
        columns = {row[1] for row in conn.execute(f'PRAGMA table_info({table})')}
        if 'reasoning_effort' not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN reasoning_effort TEXT NOT NULL DEFAULT 'default'")


def creation_input(choice):
    if choice is None:
        return None
    if (not isinstance(choice, dict) or not {'provider', 'model'} <= set(choice)
            or set(choice) - {'provider', 'model', 'reasoning_effort'}
            or any(not isinstance(v, str) or not v.strip() or len(v) > 256
                   or any(ord(c) < 32 for c in v) for v in choice.values())):
        raise ValueError('Choose an explicit provider and model')
    return json.dumps({k: v.strip() for k, v in choice.items()}, sort_keys=True)


def _row(conn, table, where, args, keys):
    row = conn.execute(f'SELECT {",".join(keys)} FROM {table} WHERE {where}', args).fetchone()
    return dict(zip(keys, row)) if row is not None else None


def _default(conn):
    result = _row(conn, 'agent_native_model_default', 'id=1', (),
                  ('provider', 'model', 'revision', 'updated_at', 'reasoning_effort'))
    if result is None:
        from agent_native.model_runtime import profile_default
        choice = profile_default()
        from agent_native.reasoning import get_reasoning_options
        from agent.model_metadata import strip_codex_context_variant_suffix
        astra = strip_codex_context_variant_suffix(choice['model']) == 'gpt-6-astra'
        effort = ('low' if astra and 'low' in get_reasoning_options(
            choice['provider'], choice['model'])['efforts'] else 'default')
        result = {**choice, 'revision': 1, 'updated_at': _now(), 'reasoning_effort': effort}
        conn.execute('INSERT INTO agent_native_model_default '
                     '(id,provider,model,revision,updated_at,reasoning_effort) VALUES(1,?,?,?,?,?)',
                     (result['provider'], result['model'], 1, result['updated_at'], result['reasoning_effort']))
    return result


def _legacy(conn, agent_id=None):
    query = ('SELECT a.id FROM agent_native_agents a LEFT JOIN agent_native_model_selections s '
             'ON s.agent_id=a.id WHERE s.agent_id IS NULL')
    rows = conn.execute(query + (' AND a.id=?' if agent_id else ''),
                        (agent_id,) if agent_id else ()).fetchall()
    if not rows:
        return
    from agent_native.model_runtime import profile_default
    choice, now = profile_default(), _now()
    conn.executemany('INSERT INTO agent_native_model_selections '
                     '(agent_id,provider,model,revision,source,updated_at,reasoning_effort) VALUES(?,?,?,?,?,?,?)',
                     [(row[0], choice['provider'], choice['model'], 1, 'legacy', now, 'default') for row in rows])


def get_default(conn):
    with write_txn(conn, allow_nested=True):
        return _default(conn)


def get_selection(conn, agent_id):
    keys = ('provider', 'model', 'revision', 'source', 'updated_at', 'reasoning_effort')
    result = _row(conn, 'agent_native_model_selections', 'agent_id=?', (agent_id,), keys)
    if result is not None:
        return result
    with write_txn(conn, allow_nested=True):
        if not conn.execute('SELECT 1 FROM agent_native_agents WHERE id=?', (agent_id,)).fetchone():
            raise KeyError(agent_id)
        _legacy(conn, agent_id)
        return _row(conn, 'agent_native_model_selections', 'agent_id=?', (agent_id,), keys)


def _event(conn, agent_id, kind, setting):
    conn.execute('INSERT INTO agent_native_model_events '
                 '(agent_id,kind,provider,model,revision,actor,created_at,reasoning_effort) VALUES(?,?,?,?,?,?,?,?)',
                 (agent_id, kind, setting['provider'], setting['model'], setting['revision'], 'owner', _now(), setting['reasoning_effort']))


def initialize_agent(conn, agent_id, choice):
    """Called inside the atomic identity-creation transaction, before startup."""
    from agent_native.model_runtime import validate_choice, validate_reasoning
    original = creation_input(choice)
    selected = ({**validate_choice(choice), 'reasoning_effort': validate_reasoning(choice)}
                if choice is not None else _default(conn))
    now = _now()
    conn.execute('INSERT INTO agent_native_model_selections '
                 '(agent_id,provider,model,revision,source,updated_at,reasoning_effort) VALUES(?,?,?,?,?,?,?)',
                 (agent_id, selected['provider'], selected['model'], 1,
                  'override' if choice is not None else 'default', now, selected['reasoning_effort']))
    conn.execute('INSERT INTO agent_native_creation_model VALUES(?,?)', (agent_id, original))
    _event(conn, agent_id, 'model.selected', get_selection(conn, agent_id))


def _revision(current, expected):
    if type(expected) is not int or current['revision'] != expected:
        raise ConflictError('Model setting changed; reload before saving')


def change_default(conn, *, actor, expected_revision, choice):
    _require_owner(actor)
    from agent_native.model_runtime import validate_choice, validate_reasoning
    creation_input(choice)
    selected = {**validate_choice(choice), 'reasoning_effort': validate_reasoning(choice)}
    with write_txn(conn, allow_nested=True):
        current = _default(conn)
        _revision(current, expected_revision)
        # Pin pre-feature identities to their native connection before changing
        # the new-agent default; no existing identity follows this mutable value.
        _legacy(conn)
        if all(current[k] == selected[k] for k in ('provider', 'model', 'reasoning_effort')):
            return current
        conn.execute('UPDATE agent_native_model_default SET provider=?,model=?,revision=revision+1,updated_at=?,reasoning_effort=? WHERE id=1',
                     (selected['provider'], selected['model'], _now(), selected['reasoning_effort']))
        result = _default(conn)
        _event(conn, None, 'model.default_changed', result)
        return result


def change_selection(conn, *, actor, agent_id, expected_revision, choice):
    _require_owner(actor)
    from agent_native.model_runtime import validate_choice, validate_reasoning
    creation_input(choice)
    selected = {**validate_choice(choice), 'reasoning_effort': validate_reasoning(choice)}
    with write_txn(conn, allow_nested=True):
        current = get_selection(conn, agent_id)
        _revision(current, expected_revision)
        if all(current[k] == selected[k] for k in ('provider', 'model', 'reasoning_effort')):
            return current
        conn.execute('UPDATE agent_native_model_selections SET provider=?,model=?,revision=revision+1,source=?,updated_at=?,reasoning_effort=? WHERE agent_id=?',
                     (selected['provider'], selected['model'], 'override', _now(), selected['reasoning_effort'], agent_id))
        result = get_selection(conn, agent_id)
        _event(conn, agent_id, 'model.changed', result)
        return result


_ATTEMPT_KEYS = ('kind', 'attempt_id', 'agent_id', 'provider', 'model', 'revision', 'source', 'created_at', 'reasoning_effort')


def read_attempt(conn, kind, attempt_id):
    return _row(conn, 'agent_native_model_attempts', 'kind=? AND attempt_id=?',
                (kind, attempt_id), _ATTEMPT_KEYS)


def snapshot_attempt(conn, agent_id, kind, attempt_id):
    if kind not in ('work', 'chat') or not isinstance(attempt_id, str) or not attempt_id:
        raise ValueError('A work or chat attempt identity is required')
    with write_txn(conn, allow_nested=True):
        previous = read_attempt(conn, kind, attempt_id)
        if previous:
            if previous['agent_id'] != agent_id:
                raise PermissionError('Model attempt belongs to another agent')
            return previous
        choice = get_selection(conn, agent_id)
        conn.execute('INSERT INTO agent_native_model_attempts '
                     '(kind,attempt_id,agent_id,provider,model,revision,source,created_at,reasoning_effort) VALUES(?,?,?,?,?,?,?,?,?)',
                     (kind, attempt_id, agent_id, choice['provider'], choice['model'],
                      choice['revision'], choice['source'], _now(), choice['reasoning_effort']))
        return read_attempt(conn, kind, attempt_id)


def activity(conn, agent_id):
    rows = conn.execute('SELECT kind,attempt_id FROM agent_native_model_attempts WHERE agent_id=? ORDER BY rowid DESC',
                        (agent_id,)).fetchall()
    result, seen = [], set()
    for kind, attempt in rows:
        if kind not in seen:
            result.append(read_attempt(conn, kind, attempt))
            seen.add(kind)
        if len(seen) == 2:
            break
    return result
