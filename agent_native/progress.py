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
 comment_id TEXT, created_at TEXT NOT NULL, link_url TEXT, link_label TEXT
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


def deliver(conn, planning, validate, source_id):
    """Attempt once. Uncertainty is retained for reconciliation, never redelivery.

    Mark uncertainty before crossing the network boundary. If the process dies,
    the mutation journal proves whether delivery began. No DB transaction spans
    HTTP, and the run's independent stop path never waits for this operation.
    """
    with write_txn(conn):
        validate(conn)
        row = conn.execute('SELECT operation_id,item_id,text,status,link_url,link_label FROM agent_native_progress '
                           'WHERE source_id=?', (source_id,)).fetchone()
        if row is None or row[3] != 'pending':
            return
        operation_id, item_id, text, _, link_url, link_label = row
        conn.execute("UPDATE agent_native_progress SET status='unknown' WHERE operation_id=?", (operation_id,))
    status, comment_id = 'unknown', None
    try:
        arguments = {'item_id': item_id, 'text': text}
        if link_url:
            arguments.update(link_url=link_url, link_label=link_label)
        result = planning.execute(operation_id, 'comment.create', arguments)
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
    keys = ('operation_id', 'source_id', 'item_id', 'summary', 'status', 'comment_id', 'created_at', 'link_url', 'link_label')
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


def migrate_links(conn):
    columns = {row[1] for row in conn.execute('PRAGMA table_info(agent_native_progress)')}
    for name in ('link_url', 'link_label'):
        if name not in columns:
            conn.execute(f'ALTER TABLE agent_native_progress ADD COLUMN {name} TEXT')


def public_base():
    """Use only the operator's declared dashboard URL, never an incoming Host."""
    from urllib.parse import urlsplit
    from hermes_cli.dashboard_auth.prefix import resolve_public_url
    base = resolve_public_url()
    try:
        parts = urlsplit(base)
        if (not parts.hostname or parts.scheme not in ('http', 'https') or parts.username or parts.password
                or parts.query or parts.fragment or len(base) > 1700
                or any(ord(c) < 33 or ord(c) == 127 for c in base)):
            return ''
        _ = parts.port
    except ValueError:
        return ''
    return base.rstrip('/')


def _evidence_intent(conn, *, source_id, record, summary, details, link_url=None, link_label=None):
    if not conn.in_transaction:
        raise RuntimeError('Evidence reporting requires the source transaction')
    if conn.execute('SELECT 1 FROM agent_native_progress WHERE source_id=?', (source_id,)).fetchone():
        return
    text = (f"Agent: {record['agent_id']}\nAttempt: {record['run_id']}\nWork item: {record['item_id']}\n"
            f"{summary}\n{details}")
    conn.execute('INSERT INTO agent_native_progress '
                 '(operation_id,source_id,agent_id,run_id,item_id,summary,text,status,created_at,link_url,link_label) '
                 'VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                 (str(uuid4()), source_id, record['agent_id'], record['run_id'], record['item_id'],
                  summary, text, 'pending', _now(), link_url, link_label))


def output_saved(conn, record, base):
    source_id = f"output:{record['output_id']}:{record['version']}"
    url = (f"{base}/agents/{record['agent_id']}?output={record['output_id']}&version={record['version']}" if base else None)
    details = (f"Output: {record['output_id']}\nVersion: {record['version']}\nFormat: {record['format']}\n"
               f"SHA-256: {record['content_sha256']}\nSaved content; awaiting result evaluation and owner review.")
    if not url:
        details += '\nOpen this exact version in Saved outputs; no dashboard public URL is configured.'
    _evidence_intent(conn, source_id=source_id, record=record,
                     summary='Saved output: '+record['title'], details=details,
                     link_url=url, link_label=(f"Open saved output: {record['title'][:200]} (v{record['version']})" if url else None))


def result_recorded(conn, record, base):
    url = f"{base}/agents/{record['agent_id']}#result-{record['id']}" if base else None
    _evidence_intent(conn, source_id='result:'+record['id'], record=record,
                     summary='Result recorded: '+record['outcome'],
                     details=(f"Result: {record['id']}\nAgent summary: {record['summary'][:1500]}\n"
                              f"Agent evaluation: {record['evaluation']['report'][:1500]}\n"
                              'This is an agent report, not owner acceptance.'),
                     link_url=url, link_label='Open recorded result' if url else None)


def terminal(conn, run_id):
    from agent_native.work_focus import read_focus
    focus = read_focus(conn, run_id)
    if not focus:
        return
    row = conn.execute('SELECT agent_id,state FROM agent_native_work_runs WHERE id=?', (run_id,)).fetchone()
    if not row or row[1] not in ('completed', 'paused', 'failed', 'unknown'):
        return
    _evidence_intent(conn, source_id='terminal:'+run_id,
                     record={'agent_id': row[0], 'run_id': run_id, 'item_id': focus['item_id']},
                     summary='Attempt '+row[1],
                     details='This is the bounded attempt status, not acceptance of the assignment or completion of the agent purpose. Review saved evidence and any unresolved delivery before continuing.')
