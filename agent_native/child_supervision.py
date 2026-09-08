"""Bounded descendant evidence and accountable direct-parent evaluation."""
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from agent_native.identity import ConflictError, _now
from hermes_cli.kanban_db_connect import write_txn

SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_native_child_result_evaluations (
 id TEXT PRIMARY KEY,
 parent_id TEXT NOT NULL REFERENCES agent_native_agents(id),
 parent_run_id TEXT NOT NULL REFERENCES agent_native_work_runs(id),
 child_id TEXT NOT NULL REFERENCES agent_native_agents(id),
 result_id TEXT NOT NULL UNIQUE REFERENCES agent_native_work_results(id),
 call_id TEXT NOT NULL,
 request_sha256 TEXT NOT NULL,
 decision TEXT NOT NULL CHECK(decision IN ('accepted','revision_requested','rejected')),
 evaluation TEXT NOT NULL,
 uncertainty TEXT,
 created_at TEXT NOT NULL,
 UNIQUE(parent_run_id, call_id)
);
"""


def _text(value, name, limit=4000):
    if (not isinstance(value, str) or not value.strip() or '\x00' in value
            or len(value.encode('utf-8')) > limit):
        raise ValueError(f'{name} must be bounded nonblank text')
    return value.strip()


def _relationship(conn, parent_id, descendant_id):
    row = conn.execute(
        'WITH RECURSIVE descendants(id,depth) AS ('
        ' SELECT agent_id,1 FROM agent_native_agent_parents WHERE parent_id=?'
        ' UNION ALL SELECT p.agent_id,d.depth+1 FROM agent_native_agent_parents p'
        ' JOIN descendants d ON p.parent_id=d.id)'
        ' SELECT depth FROM descendants WHERE id=?',
        (parent_id, descendant_id),
    ).fetchone()
    if not row:
        raise PermissionError('Agent is outside this parent descendant scope')
    return 'direct_child' if row[0] == 1 else 'descendant'


def _evaluation(conn, result_id):
    row = conn.execute(
        'SELECT id,parent_id,parent_run_id,child_id,result_id,decision,evaluation,'
        'uncertainty,created_at FROM agent_native_child_result_evaluations WHERE result_id=?',
        (result_id,),
    ).fetchone()
    return dict(zip((
        'id', 'parent_id', 'parent_run_id', 'child_id', 'result_id', 'decision',
        'evaluation', 'uncertainty', 'created_at',
    ), row)) if row else None


def summaries(conn, parent_id, limit=20):
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError('Child summary limit must be between 1 and 100')
    rows = conn.execute(
        'SELECT p.agent_id,a.name,a.purpose,a.soul_revision,a.execution '
        'FROM agent_native_agent_parents p JOIN agent_native_agents a ON a.id=p.agent_id '
        'WHERE p.parent_id=? ORDER BY p.created_at,p.agent_id LIMIT ?',
        (parent_id, limit + 1),
    ).fetchall()
    children = []
    for child_id, name, purpose, revision, execution in rows[:limit]:
        latest = conn.execute(
            'SELECT id,state,summary,error,created_at,finished_at FROM agent_native_work_runs '
            'WHERE agent_id=? ORDER BY rowid DESC LIMIT 1', (child_id,),
        ).fetchone()
        result_count = conn.execute(
            'SELECT count(*) FROM agent_native_work_results WHERE agent_id=?', (child_id,),
        ).fetchone()[0]
        pending = conn.execute(
            'SELECT count(*) FROM agent_native_work_results r LEFT JOIN '
            'agent_native_child_result_evaluations e ON e.result_id=r.id '
            "WHERE r.agent_id=? AND e.id IS NULL "
            "AND json_extract(r.record_json,'$.outcome')='submitted'", (child_id,),
        ).fetchone()[0]
        children.append({
            'id': child_id, 'name': name, 'purpose': purpose,
            'soul_revision': revision, 'execution': latest[1] if latest else execution,
            'latest_work': (dict(zip(
                ('id', 'state', 'summary', 'error', 'created_at', 'finished_at'), latest,
            )) if latest else None),
            'result_count': result_count, 'unevaluated_result_count': pending,
        })
    return {'children': children, 'has_more': len(rows) > limit}


def inspect(conn, *, validate, home, parent_id, arguments):
    allowed = {'child_id', 'output_id', 'version', 'offset', 'limit'}
    if not isinstance(arguments, dict) or set(arguments) - allowed:
        raise ValueError('Child inspection accepts a child and optional exact output version')
    if not arguments:
        with write_txn(conn):
            validate(conn)
            return summaries(conn, parent_id, 100)
    if 'child_id' not in arguments:
        raise ValueError('Exact child inspection requires child_id')
    child_id = _text(arguments['child_id'], 'child_id', 255)
    output_keys = set(arguments) - {'child_id'}
    if output_keys and not {'output_id', 'version'} <= output_keys:
        raise ValueError('Child output inspection requires output_id and version')
    with write_txn(conn):
        validate(conn)
        relationship = _relationship(conn, parent_id, child_id)
        if output_keys:
            from agent_native.output_read import read_chunk
            result = read_chunk(
                conn, agent_id=child_id,
                workspace=Path(home) / 'agents' / child_id / 'workspace',
                arguments={key: value for key, value in arguments.items() if key != 'child_id'},
            )
            validate(conn)
            return {'relationship': relationship, 'child_id': child_id, **result}
        from agent_native.identity import OWNER, get_root
        root = get_root(conn, actor=OWNER, agent_id=child_id)
        work = root['work']
        child = {
            'id': root['id'], 'name': root['name'], 'purpose': root['purpose'],
            'soul_revision': root['soul_revision'], 'execution': root['execution'],
            'child_ids': root['child_ids'],
            'cadence': root['cadence'],
            'work': ({key: work.get(key) for key in (
                'id', 'state', 'summary', 'error', 'created_at', 'started_at', 'finished_at', 'focus'
            )} if work else None),
        }
        results = root['work']['results'][:20] if root['work'] else []
        validate(conn)
        return {
            'relationship': relationship, 'child': child, 'results': results,
            'outputs': root['work']['outputs'][:20] if root['work'] else [],
            'note': 'Public work evidence only; private reasoning and credentials are excluded.',
        }


def evaluate(conn, *, validate, parent_id, parent_run_id, call_id, arguments):
    required = {'child_id', 'result_id', 'decision', 'evaluation', 'uncertainty'}
    if not isinstance(arguments, dict) or set(arguments) != required:
        raise ValueError('Child result evaluation requires child, result, decision, evaluation and uncertainty')
    child_id = _text(arguments['child_id'], 'child_id', 255)
    result_id = _text(arguments['result_id'], 'result_id', 255)
    evaluation = _text(arguments['evaluation'], 'evaluation', 16000)
    uncertainty = arguments['uncertainty']
    if uncertainty is not None:
        uncertainty = _text(uncertainty, 'uncertainty', 4000)
    decision = arguments['decision']
    if decision not in ('accepted', 'revision_requested', 'rejected'):
        raise ValueError('Choose accepted, revision_requested or rejected')
    encoded = json.dumps({**arguments, 'child_id': child_id, 'result_id': result_id,
                          'evaluation': evaluation, 'uncertainty': uncertainty},
                         sort_keys=True, ensure_ascii=False)
    request_hash = hashlib.sha256(encoded.encode()).hexdigest()
    with write_txn(conn):
        validate(conn)
        relationship = _relationship(conn, parent_id, child_id)
        if relationship != 'direct_child':
            raise PermissionError('Only the direct parent can evaluate a child result')
        run = conn.execute(
            'SELECT agent_id FROM agent_native_work_runs WHERE id=?', (parent_run_id,),
        ).fetchone()
        if not run or run[0] != parent_id:
            raise PermissionError('Parent evaluation work identity changed')
        prior_call = conn.execute(
            'SELECT request_sha256,result_id FROM agent_native_child_result_evaluations '
            'WHERE parent_run_id=? AND call_id=?', (parent_run_id, call_id),
        ).fetchone()
        if prior_call:
            if prior_call != (request_hash, result_id):
                raise ConflictError('Parent evaluation call was reused with different input')
            return _evaluation(conn, result_id)
        if _evaluation(conn, result_id):
            raise ValueError('This result already has a parent evaluation')
        row = conn.execute(
            'SELECT agent_id,record_json,record_sha256 FROM agent_native_work_results WHERE id=?',
            (result_id,),
        ).fetchone()
        if not row or row[0] != child_id:
            raise PermissionError('Result does not belong to this direct child')
        from agent_native.result_store import _checked
        record = _checked((result_id, row[1], row[2]))
        if record.get('outcome') != 'submitted':
            raise ValueError('Only a submitted delegated result can be accepted or rejected')
        created_at = _now()
        key = str(uuid4())
        conn.execute(
            'INSERT INTO agent_native_child_result_evaluations '
            '(id,parent_id,parent_run_id,child_id,result_id,call_id,request_sha256,decision,'
            'evaluation,uncertainty,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
            (key, parent_id, parent_run_id, child_id, result_id, call_id, request_hash,
             decision, evaluation, uncertainty, created_at),
        )
        if decision in ('revision_requested', 'rejected'):
            prefix = ('Parent requested revision of delegated result '
                      if decision == 'revision_requested'
                      else 'Parent rejected delegated result ')
            text = prefix + result_id + ': ' + evaluation
            if uncertainty:
                text += ' Uncertainty: ' + uncertainty
            conn.execute(
                'INSERT INTO agent_native_feedback '
                '(id,agent_id,soul_revision,request_id,text,status,created_at) '
                'VALUES(?,?,?,?,?,?,?)',
                (str(uuid4()), child_id, record['soul_revision'], 'parent-result:' + result_id,
                 text, 'pending', created_at),
            )
        # Every parent evaluation is actionable context for the child's next
        # review; normal cadence busy and lifecycle guards still decide admission.
        from agent_native.cadence import wake
        wake(conn, child_id, 'parent_result_evaluation', requested_at=created_at)
        from agent_native.work_state import event
        event(conn, parent_run_id, 'work.child_result_' + decision,
              f'{decision.replace("_", " ").title()} child result {result_id}.')
        child_run = conn.execute(
            'SELECT id FROM agent_native_work_runs WHERE agent_id=? ORDER BY rowid DESC LIMIT 1',
            (child_id,),
        ).fetchone()
        if child_run:
            event(conn, child_run[0], 'work.parent_evaluation',
                  f'Parent evaluation of result {result_id}: {decision}.')
        validate(conn)
        return _evaluation(conn, result_id)
