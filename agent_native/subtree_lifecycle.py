"""Durable owner pause causes applied atomically across an agent subtree."""
from agent_native.identity import ConflictError, _now, _require_owner, require_active
from hermes_cli.kanban_db_connect import write_txn

SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_native_agent_pauses (
 agent_id TEXT NOT NULL REFERENCES agent_native_agents(id),
 source_agent_id TEXT NOT NULL REFERENCES agent_native_agents(id),
 requested_at TEXT NOT NULL,
 PRIMARY KEY(agent_id, source_agent_id)
);
CREATE INDEX IF NOT EXISTS agent_native_pause_sources
 ON agent_native_agent_pauses(source_agent_id, agent_id);
"""


def read_pause(conn, agent_id):
    rows = conn.execute(
        'SELECT source_agent_id,requested_at FROM agent_native_agent_pauses '
        'WHERE agent_id=? ORDER BY requested_at,source_agent_id', (agent_id,),
    ).fetchall()
    return {
        'paused': bool(rows),
        'sources': [dict(zip(('source_agent_id', 'requested_at'), row)) for row in rows],
    }


def require_not_paused(conn, agent_id):
    if read_pause(conn, agent_id)['paused']:
        raise ConflictError('Agent is paused; resume its applicable pause before starting work')


def _subtree(conn, agent_id):
    rows = conn.execute(
        'WITH RECURSIVE subtree(id,depth,path) AS ('
        ' SELECT id,0,created_at||id FROM agent_native_agents WHERE id=?'
        ' UNION ALL SELECT p.agent_id,s.depth+1,s.path||p.created_at||p.agent_id'
        ' FROM agent_native_agent_parents p JOIN subtree s ON p.parent_id=s.id)'
        ' SELECT id FROM subtree WHERE id NOT IN (SELECT agent_id FROM agent_native_removals)'
        ' AND id NOT IN (SELECT agent_id FROM agent_native_retirements) ORDER BY path',
        (agent_id,),
    ).fetchall()
    if not rows:
        raise KeyError(agent_id)
    return [row[0] for row in rows]


def request_pause(conn, *, actor, agent_id):
    _require_owner(actor)
    with write_txn(conn):
        require_active(conn, agent_id)
        agent_ids = _subtree(conn, agent_id)
        now = _now()
        stopping = []
        newly_paused = []
        for current_id in agent_ids:
            inserted = conn.execute(
                'INSERT OR IGNORE INTO agent_native_agent_pauses '
                '(agent_id,source_agent_id,requested_at) VALUES(?,?,?)',
                (current_id, agent_id, now),
            ).rowcount
            if inserted:
                newly_paused.append(current_id)
            conn.execute(
                'UPDATE agent_native_cadence SET enabled=0 WHERE agent_id=?', (current_id,),
            )
            latest = conn.execute(
                'SELECT id,state FROM agent_native_work_runs WHERE agent_id=? '
                'ORDER BY rowid DESC LIMIT 1', (current_id,),
            ).fetchone()
            if latest and latest[1] in ('queued', 'preparing', 'running', 'stopping'):
                next_state = 'paused' if latest[1] == 'queued' else 'stopping'
                if next_state == 'stopping':
                    stopping.append(current_id)
                if latest[1] != next_state:
                    conn.execute(
                        'UPDATE agent_native_work_runs SET stop_requested=1,state=? WHERE id=?',
                        (next_state, latest[0]),
                    )
                    from agent_native.work_state import event
                    event(
                        conn, latest[0], 'work.' + next_state,
                        'Owner paused agent subtree; stopping work and preserving history.'
                        if next_state == 'stopping' else
                        'Owner paused agent subtree before this work started.',
                    )
        sources = {
            current_id: read_pause(conn, current_id)['sources'] for current_id in agent_ids
        }
        return {
            'source_agent_id': agent_id,
            'affected_agent_ids': agent_ids,
            'newly_paused_agent_ids': newly_paused,
            'stopping_agent_ids': stopping,
            'sources': sources,
        }
