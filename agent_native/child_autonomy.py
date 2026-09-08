"""Bounded, auditable autonomy configuration by an accountable direct parent."""
import hashlib
import json

from agent_native.identity import OWNER, ConflictError, _now
from hermes_cli.kanban_db_connect import write_txn

SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_native_child_autonomy_changes (
 parent_run_id TEXT NOT NULL REFERENCES agent_native_work_runs(id),
 call_id TEXT NOT NULL,
 parent_id TEXT NOT NULL REFERENCES agent_native_agents(id),
 child_id TEXT NOT NULL REFERENCES agent_native_agents(id),
 request_sha256 TEXT NOT NULL,
 previous_revision INTEGER NOT NULL,
 resulting_revision INTEGER NOT NULL,
 level INTEGER NOT NULL CHECK(level BETWEEN 1 AND 5),
 reason TEXT NOT NULL,
 created_at TEXT NOT NULL,
 PRIMARY KEY(parent_run_id,call_id)
);
"""


def _read(conn, parent_run_id, call_id):
    row = conn.execute(
        'SELECT parent_id,child_id,previous_revision,resulting_revision,level,reason,created_at '
        'FROM agent_native_child_autonomy_changes WHERE parent_run_id=? AND call_id=?',
        (parent_run_id, call_id),
    ).fetchone()
    if not row:
        return None
    from agent_native.autonomy import get_settings
    return {
        'status': 'configured', 'parent_id': row[0], 'child_id': row[1],
        'previous_revision': row[2], 'resulting_revision': row[3], 'level': row[4],
        'reason': row[5], 'created_at': row[6], 'autonomy': get_settings(conn, row[1]),
    }


def configure(conn, *, validate, parent_id, parent_run_id, call_id, arguments):
    required = {'child_id', 'level', 'expected_revision', 'reason'}
    if not isinstance(arguments, dict) or set(arguments) != required:
        raise ValueError('Child autonomy configuration requires child, level, revision and reason')
    child_id, level = arguments['child_id'], arguments['level']
    expected_revision, reason = arguments['expected_revision'], arguments['reason']
    if not isinstance(child_id, str) or not child_id or len(child_id) > 255:
        raise ValueError('Child identity must be bounded text')
    if type(expected_revision) is not int or expected_revision < 1:
        raise ValueError('Expected autonomy revision must be positive')
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 4000 or '\x00' in reason:
        raise ValueError('Autonomy reason must be bounded nonblank text')
    reason = reason.strip()
    from agent_native.autonomy import validate_level
    validate_level(level)
    request = json.dumps({
        'child_id': child_id, 'level': level,
        'expected_revision': expected_revision, 'reason': reason,
    }, sort_keys=True, ensure_ascii=False)
    request_hash = hashlib.sha256(request.encode()).hexdigest()

    with write_txn(conn):
        validate(conn)
        prior = conn.execute(
            'SELECT request_sha256 FROM agent_native_child_autonomy_changes '
            'WHERE parent_run_id=? AND call_id=?', (parent_run_id, call_id),
        ).fetchone()
        if prior:
            if prior[0] != request_hash:
                raise ConflictError('Child autonomy call was reused with different input')
            return _read(conn, parent_run_id, call_id)
        run = conn.execute(
            'SELECT agent_id FROM agent_native_work_runs WHERE id=?', (parent_run_id,),
        ).fetchone()
        if not run or run[0] != parent_id:
            raise PermissionError('Parent work identity changed')
        relationship = conn.execute(
            'SELECT 1 FROM agent_native_agent_parents WHERE agent_id=? AND parent_id=?',
            (child_id, parent_id),
        ).fetchone()
        if not relationship:
            raise PermissionError('Only a direct child autonomy policy can be configured')
        from agent_native.identity import require_active
        require_active(conn, child_id)
        from agent_native.autonomy import change_settings, get_settings
        current = get_settings(conn, child_id)
        if current['revision'] != expected_revision:
            raise ConflictError('Child autonomy setting changed; inspect the child and retry')
        changed = change_settings(
            conn, actor=OWNER, agent_id=child_id, level=level,
            expected_revision=expected_revision,
            require_owner_review=current['require_owner_review'], _allow_nested=True,
            _recorded_actor='parent:' + parent_id,
        )
        created_at = _now()
        conn.execute(
            'INSERT INTO agent_native_child_autonomy_changes '
            '(parent_run_id,call_id,parent_id,child_id,request_sha256,previous_revision,'
            'resulting_revision,level,reason,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
            (parent_run_id, call_id, parent_id, child_id, request_hash,
             expected_revision, changed['revision'], level, reason, created_at),
        )
        from agent_native.work_state import event
        event(conn, parent_run_id, 'work.child_autonomy_changed',
              f'Configured child {child_id} autonomy to level {level}/5.')
        validate(conn)
        return _read(conn, parent_run_id, call_id)
