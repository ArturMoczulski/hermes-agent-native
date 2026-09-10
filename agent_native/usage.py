"""Durable model usage accounting for managed Agent Native runs."""

from agent_native.identity import _now
from hermes_cli.kanban_db_connect import write_txn


SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_native_usage (
 run_id TEXT PRIMARY KEY REFERENCES agent_native_work_runs(id),
 agent_id TEXT NOT NULL REFERENCES agent_native_agents(id),
 provider TEXT NOT NULL, model TEXT NOT NULL,
 api_calls INTEGER NOT NULL, input_tokens INTEGER NOT NULL,
 output_tokens INTEGER NOT NULL, cache_read_tokens INTEGER NOT NULL,
 cache_write_tokens INTEGER NOT NULL, reasoning_tokens INTEGER NOT NULL,
 estimated_cost_usd REAL, actual_cost_usd REAL,
 cost_status TEXT NOT NULL, cost_source TEXT NOT NULL,
 recorded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS agent_native_usage_agent_idx
 ON agent_native_usage(agent_id, recorded_at);
"""

TOKEN_FIELDS = ('input_tokens', 'output_tokens', 'cache_read_tokens',
                'cache_write_tokens', 'reasoning_tokens')
INTEGER_FIELDS = ('api_calls',) + TOKEN_FIELDS
FIELDS = ('run_id', 'agent_id', 'provider', 'model') + INTEGER_FIELDS + (
    'estimated_cost_usd', 'actual_cost_usd', 'cost_status', 'cost_source', 'recorded_at')
VALID_COST_STATUSES = frozenset({'known', 'estimated', 'included', 'free', 'unknown'})


def _non_negative_int(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f'{name} must be a non-negative integer')
    return value


def _optional_cost(value, name):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ValueError(f'{name} must be a non-negative number or null')
    return float(value)


def record(conn, *, run_id, agent_id, usage):
    """Store final absolute counters. A retry replaces rather than double-counts."""
    if not isinstance(usage, dict):
        raise ValueError('usage must be an object')
    provider, model = usage.get('provider'), usage.get('model')
    if not isinstance(provider, str) or not provider.strip() or not isinstance(model, str) or not model.strip():
        raise ValueError('provider and model are required')
    integers = {name: _non_negative_int(usage.get(name), name) for name in INTEGER_FIELDS}
    estimated = _optional_cost(usage.get('estimated_cost_usd'), 'estimated_cost_usd')
    actual = _optional_cost(usage.get('actual_cost_usd'), 'actual_cost_usd')
    status = usage.get('cost_status', 'unknown')
    source = usage.get('cost_source', 'none')
    if status not in VALID_COST_STATUSES or not isinstance(source, str) or not source:
        raise ValueError('invalid cost metadata')
    relation = conn.execute('SELECT agent_id FROM agent_native_work_runs WHERE id=?', (run_id,)).fetchone()
    if relation is None or relation[0] != agent_id:
        raise PermissionError('Usage does not belong to this run and agent')
    values = (run_id, agent_id, provider.strip(), model.strip(),
              *(integers[name] for name in INTEGER_FIELDS), estimated, actual,
              status, source, _now())
    placeholders = ','.join('?' for _ in FIELDS)
    updates = ','.join(f'{name}=excluded.{name}' for name in FIELDS[2:])
    with write_txn(conn, allow_nested=True):
        conn.execute(f'INSERT INTO agent_native_usage ({",".join(FIELDS)}) VALUES ({placeholders}) '
                     f'ON CONFLICT(run_id) DO UPDATE SET {updates}', values)
    return for_run(conn, run_id)


def for_run(conn, run_id):
    row = conn.execute(f'SELECT {",".join(FIELDS)} FROM agent_native_usage WHERE run_id=?',
                       (run_id,)).fetchone()
    return dict(zip(FIELDS, row)) if row else None


def _totals(rows):
    result = {'record_count': len(rows), 'api_calls': 0,
              **{name: 0 for name in TOKEN_FIELDS},
              'estimated_cost_usd': None, 'actual_cost_usd': None,
              'cost_kind': 'unavailable'}
    for name in INTEGER_FIELDS:
        result[name] = sum(row[name] for row in rows)
    for name in ('estimated_cost_usd', 'actual_cost_usd'):
        known = [row[name] for row in rows if row[name] is not None]
        result[name] = sum(known) if known else None
    statuses = {row['cost_status'] for row in rows}
    if result['actual_cost_usd'] is not None:
        result['cost_kind'] = 'measured'
    elif rows and statuses <= {'included', 'free'}:
        result['cost_kind'] = 'included'
    elif result['estimated_cost_usd'] is not None:
        result['cost_kind'] = 'estimated'
    return result


def summary(conn, agent_id):
    """Return direct-agent and recursive-subtree totals without duplicate runs."""
    descendants = [agent_id]
    seen = {agent_id}
    for current in descendants:
        for row in conn.execute('SELECT agent_id FROM agent_native_agent_parents WHERE parent_id=?',
                                (current,)).fetchall():
            if row[0] not in seen:
                seen.add(row[0])
                descendants.append(row[0])
    rows = [dict(zip(FIELDS, row)) for row in conn.execute(
        f'SELECT {",".join(FIELDS)} FROM agent_native_usage WHERE agent_id IN '
        f'({",".join("?" for _ in descendants)})', descendants).fetchall()]
    return {'agent': _totals([row for row in rows if row['agent_id'] == agent_id]),
            'subtree': _totals(rows)}
