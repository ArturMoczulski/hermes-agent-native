"""Host-mediated creation of a direct child from frozen parent-run settings."""
import hashlib
import json

from agent_native.identity import OWNER, ConflictError, _now, create_root
from hermes_cli.kanban_db_connect import write_txn

SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_native_child_delegations (
 parent_run_id TEXT NOT NULL REFERENCES agent_native_work_runs(id),
 call_id TEXT NOT NULL,
 parent_id TEXT NOT NULL REFERENCES agent_native_agents(id),
 child_id TEXT NOT NULL UNIQUE REFERENCES agent_native_agents(id),
 request_sha256 TEXT NOT NULL,
 reason TEXT NOT NULL,
 configuration_json TEXT NOT NULL,
 created_at TEXT NOT NULL,
 PRIMARY KEY(parent_run_id, call_id)
);
"""


def _bounded_text(value, field, limit):
    if not isinstance(value, str) or not value.strip() or len(value) > limit or '\x00' in value:
        raise ValueError(f'{field} must be bounded nonblank text')
    return value.strip()


def _read(conn, parent_run_id, call_id):
    row = conn.execute(
        'SELECT parent_id,child_id,reason,configuration_json,created_at '
        'FROM agent_native_child_delegations WHERE parent_run_id=? AND call_id=?',
        (parent_run_id, call_id),
    ).fetchone()
    if not row:
        return None
    return {'status': 'created', 'parent_id': row[0], 'child_id': row[1],
            'reason': row[2], 'configuration': json.loads(row[3]), 'created_at': row[4]}


def create(conn, *, validate, parent_id, parent_run_id, call_id, arguments):
    required = {'name', 'purpose', 'reason'}
    if not isinstance(arguments, dict) or set(arguments) != required:
        raise ValueError('Child creation requires name, purpose and reason')
    name = _bounded_text(arguments['name'], 'name', 200)
    purpose = _bounded_text(arguments['purpose'], 'purpose', 20000)
    reason = _bounded_text(arguments['reason'], 'reason', 4000)
    encoded_request = json.dumps({'name': name, 'purpose': purpose, 'reason': reason},
                                 sort_keys=True, ensure_ascii=False)
    request_hash = hashlib.sha256(encoded_request.encode()).hexdigest()

    with write_txn(conn):
        validate(conn)
        prior = conn.execute(
            'SELECT request_sha256 FROM agent_native_child_delegations '
            'WHERE parent_run_id=? AND call_id=?', (parent_run_id, call_id),
        ).fetchone()
        if prior:
            if prior[0] != request_hash:
                raise ConflictError('Child delegation call was reused with different input')
            return _read(conn, parent_run_id, call_id)
        run = conn.execute(
            'SELECT agent_id,limits FROM agent_native_work_runs WHERE id=?', (parent_run_id,),
        ).fetchone()
        if not run or run[0] != parent_id:
            raise PermissionError('Child delegation parent identity changed')
        model = conn.execute(
            'SELECT provider,model,reasoning_effort FROM agent_native_model_attempts '
            "WHERE kind='work' AND attempt_id=? AND agent_id=?", (parent_run_id, parent_id),
        ).fetchone()
        autonomy = conn.execute(
            'SELECT level FROM agent_native_autonomy_attempts WHERE run_id=? AND agent_id=? '
            'ORDER BY created_at DESC LIMIT 1', (parent_run_id, parent_id),
        ).fetchone()
        if not model or not autonomy:
            raise PermissionError('Child delegation requires frozen parent admission settings')
        work_limits = json.loads(run[1])
        model_choice = {'provider': model[0], 'model': model[1], 'reasoning_effort': model[2]}
        parent_cadence = conn.execute(
            'SELECT enabled,interval_seconds FROM agent_native_cadence WHERE agent_id=?', (parent_id,),
        ).fetchone()
        configuration = {'model': model_choice, 'autonomy_level': autonomy[0],
                         'work_limits': work_limits,
                         'cadence': {'enabled': bool(parent_cadence and parent_cadence[0]),
                                     'interval_seconds': parent_cadence[1] if parent_cadence else None}}
        request_id = 'delegation:' + hashlib.sha256(
            f'{parent_id}:{parent_run_id}:{call_id}'.encode()).hexdigest()
        child = create_root(conn, actor=OWNER, request_id=request_id, name=name, purpose=purpose,
                            work=work_limits, model_selection=model_choice,
                            autonomy_level=autonomy[0], parent_id=parent_id,
                            _allow_nested=True)
        if configuration['cadence']['enabled']:
            from agent_native.cadence import configure
            configure(conn, actor=OWNER, agent_id=child['id'], expected_revision=1,
                      interval_seconds=configuration['cadence']['interval_seconds'], enabled=True,
                      _allow_nested=True)
        created_at = _now()
        conn.execute(
            'INSERT INTO agent_native_child_delegations '
            '(parent_run_id,call_id,parent_id,child_id,request_sha256,reason,configuration_json,created_at) '
            'VALUES(?,?,?,?,?,?,?,?)',
            (parent_run_id, call_id, parent_id, child['id'], request_hash, reason,
             json.dumps(configuration, sort_keys=True), created_at),
        )
        from agent_native.work_state import event
        event(conn, parent_run_id, 'work.child_created',
              f'Created child agent {name} ({child["id"]}) for delegated work.')
        return _read(conn, parent_run_id, call_id)
