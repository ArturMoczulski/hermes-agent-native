"""Host-attributed Plane progress with durable intent and honest delivery state.

The source record and intent commit together. Delivery uses the existing scoped
adapter and its mutation journal, never a second credential or retry transport.
"""
from uuid import uuid4

from agent_native.identity import OWNER, _now
from hermes_cli.kanban_db_connect import write_txn

PROGRESS_SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_native_progress_settings (
 agent_id TEXT PRIMARY KEY REFERENCES agent_native_agents(id),
 verbosity TEXT NOT NULL CHECK(verbosity IN ('concise','standard','detailed')),
 revision INTEGER NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS agent_native_progress (
 operation_id TEXT PRIMARY KEY,
 source_id TEXT NOT NULL UNIQUE,
 agent_id TEXT NOT NULL REFERENCES agent_native_agents(id),
 run_id TEXT NOT NULL REFERENCES agent_native_work_runs(id),
 item_id TEXT NOT NULL, summary TEXT NOT NULL, text TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('pending','confirmed','failed','unknown')),
 comment_id TEXT, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS agent_native_progress_run ON agent_native_progress(run_id,created_at);
"""


def selected(conn, agent_id, record):
    """Caller commits this intent atomically with the observed selection."""
    if not conn.in_transaction:
        raise RuntimeError('Progress intent requires the source transaction')
    summary = 'Selected work item: ' + record['name']
    text = (f"Agent: {agent_id}\nAttempt: {record['run_id']}\nWork item: {record['item_id']}\n"
            f"{summary}\nNext: work against the selected requirements; report results for review.")
    conn.execute('INSERT INTO agent_native_progress '
                 '(operation_id,source_id,agent_id,run_id,item_id,summary,text,status,created_at) '
                 'VALUES(?,?,?,?,?,?,?,?,?)',
                 (str(uuid4()), record['selection_id'], agent_id, record['run_id'],
                  record['item_id'], summary, text, 'pending', _now()))


def deliver(conn, planning, validate, selection_id):
    """Attempt once. Uncertainty is retained for reconciliation, never redelivery.

    Mark uncertainty before crossing the network boundary. If the process dies,
    the mutation journal proves whether delivery began. No DB transaction spans
    HTTP, and the run's independent stop path never waits for this operation.
    """
    with write_txn(conn):
        validate(conn)
        row = conn.execute('SELECT operation_id,item_id,text,status FROM agent_native_progress '
                           'WHERE source_id=?', (selection_id,)).fetchone()
        if row is None or row[3] != 'pending':
            return
        operation_id, item_id, text, _ = row
        conn.execute("UPDATE agent_native_progress SET status='unknown' WHERE operation_id=?", (operation_id,))
    status, comment_id = 'unknown', None
    try:
        result = planning.execute(operation_id, 'comment.create', {'item_id': item_id, 'text': text})
        status, comment_id = 'confirmed', result['resource']['id']
    except Exception:
        # Never expose HTTP bodies or credentials, nor label an uncertain write
        # as failed just because the client did not receive its acknowledgement.
        from agent_native.plane_write_journal import MutationJournal
        try:
            receipt = MutationJournal(conn).get(operation_id, actor=OWNER)
            if receipt['status'] == 'confirmed':
                status, comment_id = 'confirmed', receipt['resource_id']
            elif receipt['status'] == 'rejected':
                status = 'failed'
        except KeyError:
            status = 'failed'  # Adapter never began a delivery intent.
    with write_txn(conn):
        conn.execute('UPDATE agent_native_progress SET status=?,comment_id=? WHERE operation_id=?',
                     (status, comment_id, operation_id))


def recent(conn, run_id):
    keys = ('operation_id', 'source_id', 'item_id', 'summary', 'status', 'comment_id', 'created_at')
    rows = conn.execute('SELECT '+','.join(keys)+' FROM agent_native_progress WHERE run_id=? '
                        'ORDER BY created_at DESC,operation_id DESC LIMIT 20', (run_id,)).fetchall()
    return [dict(zip(keys, row)) for row in rows]


def get_settings(conn, agent_id):
    if not conn.execute('SELECT 1 FROM agent_native_agents WHERE id=?', (agent_id,)).fetchone():
        raise KeyError(agent_id)
    row = conn.execute('SELECT verbosity,revision,updated_at FROM agent_native_progress_settings WHERE agent_id=?', (agent_id,)).fetchone()
    return dict(zip(('verbosity', 'revision', 'updated_at'), row)) if row else {
        'verbosity': 'standard', 'revision': 1, 'updated_at': None}


def change_settings(conn, *, actor, agent_id, verbosity, expected_revision):
    from agent_native.identity import _require_owner, ConflictError
    _require_owner(actor)
    if verbosity not in ('concise', 'standard', 'detailed'):
        raise ValueError('Unsupported progress verbosity')
    with write_txn(conn):
        current = get_settings(conn, agent_id)
        if type(expected_revision) is not int or current['revision'] != expected_revision:
            raise ConflictError('Reporting settings changed; reload before saving')
        if current['verbosity'] == verbosity:
            return current
        conn.execute('INSERT INTO agent_native_progress_settings VALUES(?,?,?,?) '
                     'ON CONFLICT(agent_id) DO UPDATE SET verbosity=excluded.verbosity,revision=excluded.revision,updated_at=excluded.updated_at',
                     (agent_id, verbosity, current['revision'] + 1, _now()))
        return get_settings(conn, agent_id)


def checkpoint(conn, *, validate, planning, agent_id, run_id, call_id, arguments):
    from agent_native.work_focus import read_focus
    if (not isinstance(arguments, dict) or set(arguments) != {'item_id', 'kind', 'summary', 'evidence', 'next_action'}
            or arguments['kind'] not in ('checkpoint', 'detail', 'blocker')
            or any(not isinstance(arguments[k], str) or not arguments[k].strip()
                   or len(arguments[k].encode('utf-8')) > limit
                   for k, limit in (('item_id', 255), ('summary', 1000), ('evidence', 2000), ('next_action', 2000)))):
        raise ValueError('Progress requires bounded summary, evidence, next action and kind')
    source_id = f'checkpoint:{run_id}:{call_id}'
    with write_txn(conn):
        validate(conn)
        old = conn.execute('SELECT 1 FROM agent_native_progress WHERE source_id=?', (source_id,)).fetchone()
        if not old:
            focus = read_focus(conn, run_id)
            if not focus or focus['item_id'] != arguments['item_id']:
                raise PermissionError('Report progress on the currently selected work item')
            verbosity = get_settings(conn, agent_id)['verbosity']
            kind = arguments['kind']
            if kind != 'blocker' and (verbosity == 'concise' or (kind == 'detail' and verbosity != 'detailed')):
                return {'status': 'suppressed', 'verbosity': verbosity}
            summary = 'Agent reports: ' + arguments['summary']
            text = (f"Agent: {agent_id}\nAttempt: {run_id}\nWork item: {arguments['item_id']}\n"
                    f"{summary}\nReported evidence: {arguments['evidence']}\nNext: {arguments['next_action']}")
            conn.execute('INSERT INTO agent_native_progress '
                         '(operation_id,source_id,agent_id,run_id,item_id,summary,text,status,created_at) VALUES(?,?,?,?,?,?,?,?,?)',
                         (str(uuid4()), source_id, agent_id, run_id, arguments['item_id'], summary, text, 'pending', _now()))
    deliver(conn, planning, validate, source_id)
    row = conn.execute('SELECT operation_id,status,comment_id FROM agent_native_progress WHERE source_id=?', (source_id,)).fetchone()
    return dict(zip(('operation_id', 'status', 'comment_id'), row))
