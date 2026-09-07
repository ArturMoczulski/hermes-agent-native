"""Host-observed current assignment and immutable selection history for an attempt."""
import hashlib
import json
from uuid import uuid4

from agent_native.identity import _now
from hermes_cli.kanban_db_connect import write_txn

FOCUS_SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_native_work_selections (
 sequence INTEGER PRIMARY KEY AUTOINCREMENT,
 selection_id TEXT NOT NULL UNIQUE,
 run_id TEXT NOT NULL REFERENCES agent_native_work_runs(id),
 call_id TEXT NOT NULL, item_id TEXT NOT NULL,
 record_json TEXT NOT NULL, record_sha256 TEXT NOT NULL,
 UNIQUE(run_id, call_id)
);
CREATE INDEX IF NOT EXISTS agent_native_selection_run
 ON agent_native_work_selections(run_id, sequence);
"""


def _hash(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def _checked(row):
    record = json.loads(row[1])
    if record['selection_id'] != row[0] or _hash(row[1]) != row[2]:
        raise ValueError('Work selection integrity check failed')
    return record


def read_focus(conn, run_id):
    row = conn.execute('SELECT selection_id,record_json,record_sha256 '
                       'FROM agent_native_work_selections WHERE run_id=? '
                       'ORDER BY sequence DESC LIMIT 1', (run_id,)).fetchone()
    return _checked(row) if row else None


def _previous(conn, run_id, call_id, item_id):
    row = conn.execute('SELECT selection_id,record_json,record_sha256,item_id '
                       'FROM agent_native_work_selections WHERE run_id=? AND call_id=?',
                       (run_id, call_id)).fetchone()
    if row is not None:
        if row[3] != item_id:
            raise PermissionError('Selection call identity was reused with different input')
        return _checked(row)
    return None


def select(conn, *, validate, inspect, agent_id, run_id, call_id, arguments):
    """Record explicit focus without widening authority or accepting any work.

    The immutable selection is also the local idempotence record. If the separate
    broker receipt is lost, replay returns the old snapshot without fetching a
    changed/deleted item or making an old selection current again. No network
    call holds the database transaction.
    """
    if not isinstance(arguments, dict) or set(arguments) != {'item_id'}:
        raise ValueError('Work selection requires only an item identity')
    item_id = arguments['item_id']
    if (not isinstance(item_id, str) or not item_id.strip() or '\x00' in item_id
            or len(item_id.encode('utf-8')) > 255):
        raise ValueError('Invalid work item identity')
    with write_txn(conn):
        validate(conn)
        previous = _previous(conn, run_id, call_id, item_id)
        if previous is not None:
            return previous
    observation = inspect({'kind': 'item', 'resource_id': item_id})
    with write_txn(conn):
        validate(conn)
        previous = _previous(conn, run_id, call_id, item_id)
        if previous is not None:
            return previous
        work = conn.execute('SELECT agent_id,soul_revision FROM agent_native_work_runs WHERE id=?',
                            (run_id,)).fetchone()
        if work is None or work[0] != agent_id:
            raise PermissionError('Selection identity does not match the work run')
        resource = observation['resource']
        if resource['id'] != item_id:
            raise PermissionError('Selected item was not observed in this project')
        record = {'selection_id': str(uuid4()), 'run_id': run_id, 'item_id': item_id,
                  'soul_revision': work[1], 'cycle_id': observation.get('cycle_id'),
                  'name': resource['name'], 'description_html': resource.get('description_html') or '',
                  'assignment_fingerprint': observation['fingerprint'], 'selected_at': _now()}
        encoded = json.dumps(record, sort_keys=True, ensure_ascii=False, allow_nan=False)
        conn.execute('INSERT INTO agent_native_work_selections '
                     '(selection_id,run_id,call_id,item_id,record_json,record_sha256) VALUES (?,?,?,?,?,?)',
                     (record['selection_id'], run_id, call_id, item_id, encoded, _hash(encoded)))
        from agent_native.work_state import event
        event(conn, run_id, 'work.focus', 'Selected work item: '+record['name'])
        from agent_native.progress import selected
        selected(conn, agent_id, record)
        validate(conn)
    return record
