"""Immutable agent reports, distinct from saved content and owner acceptance."""
import hashlib
import json
from urllib.parse import urlsplit
from uuid import uuid4

RESULT_SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_native_work_results (
 id TEXT PRIMARY KEY, agent_id TEXT NOT NULL REFERENCES agent_native_agents(id),
 run_id TEXT NOT NULL REFERENCES agent_native_work_runs(id), item_id TEXT NOT NULL,
 call_id TEXT NOT NULL, request_sha256 TEXT NOT NULL,
 record_json TEXT NOT NULL, record_sha256 TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(run_id, call_id)
);
CREATE INDEX IF NOT EXISTS agent_native_results_agent ON agent_native_work_results(agent_id, created_at);
"""
OUTCOMES = frozenset({'submitted', 'discovery', 'waiting', 'blocked'})


def _text(value, name, limit=16000):
    if (not isinstance(value, str) or not value.strip() or '\x00' in value
            or len(value.encode('utf-8')) > limit):
        raise ValueError('Invalid result '+name)
    return value


def _json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


def _hash(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def _checked(row):
    record = json.loads(row[1])
    if _hash(row[1]) != row[2] or record['id'] != row[0]:
        raise ValueError('Result integrity check failed')
    return record


def list_results(conn, agent_id):
    results = [_checked(row) for row in conn.execute(
        'SELECT id,record_json,record_sha256 FROM agent_native_work_results '
        'WHERE agent_id=? ORDER BY created_at DESC,id DESC', (agent_id,))]
    from agent_native.acceptance import get as get_decision
    for result in results:
        decision = get_decision(conn, result['id'])
        if 'review' not in result:
            result['review'] = {
                'required': decision is not None,
                'source': 'legacy',
                'reason': 'A prior owner decision is retained.' if decision else None,
            }
        result['acceptance'] = decision['decision'] if decision else 'not_evaluated'
        result['owner_decision'] = decision
    return results


def record(conn, *, validate, workspace, agent_id, run_id, call_id, observation, arguments, record_progress=None):
    """Host supplies identity and a fresh scoped Plane observation, never the model.

    Criteria and their fingerprint describe what the host observed at submission.
    The evaluation remains an agent report; no independent acceptance is inferred.
    This local commit can be retried using the original native tool call identity.
    """
    from agent_native.identity import _now
    from agent_native.output_store import read_output
    from hermes_cli.kanban_db_connect import write_txn

    required = {'item_id', 'summary', 'outcome', 'evaluation', 'outputs'}
    if not isinstance(arguments, dict) or not required <= set(arguments) or set(arguments) - required - {'references'}:
        raise ValueError('Result requires item, summary, outcome, evaluation and outputs')
    args = {**arguments, 'references': arguments.get('references', [])}
    for name in ('item_id', 'summary', 'evaluation'):
        _text(args[name], name, 255 if name == 'item_id' else 16000)
    if args['outcome'] not in OUTCOMES:
        raise ValueError('Result outcome does not grant acceptance')
    if not isinstance(args['outputs'], list) or len(args['outputs']) > 100:
        raise ValueError('Result outputs must be a bounded list')
    if not isinstance(args['references'], list) or len(args['references']) > 100:
        raise ValueError('Result references must be a bounded list')
    references = []
    for ref in args['references']:
        if not isinstance(ref, dict) or set(ref) != {'label', 'url'}:
            raise ValueError('References require label and URL')
        _text(ref['label'], 'reference label', 255)
        _text(ref['url'], 'reference URL', 4096)
        url = urlsplit(ref['url'])
        if url.scheme not in ('https', 'http') or not url.hostname or url.username or url.password:
            raise ValueError('External references require an HTTP URL without credentials')
        references.append({**ref, 'verified': False})
    request_hash = _hash(_json(args))
    with write_txn(conn):
        validate(conn)
        previous = conn.execute('SELECT id,record_json,record_sha256,request_sha256 '
                                'FROM agent_native_work_results WHERE run_id=? AND call_id=?',
                                (run_id, call_id)).fetchone()
        if previous:
            if previous[3] != request_hash:
                raise ValueError('Result call identity was reused with different input')
            result = _checked(previous)
            if record_progress is not None:
                record_progress(conn, result)
            return result
        work = conn.execute('SELECT agent_id,soul_revision FROM agent_native_work_runs WHERE id=?', (run_id,)).fetchone()
        if work is None or work[0] != agent_id:
            raise PermissionError('Result identity does not match this work run')
        purpose = conn.execute('SELECT purpose FROM agent_native_events WHERE agent_id=? AND soul_revision=?',
                               (agent_id, work[1])).fetchone()
        if purpose is None:
            raise PermissionError('Result purpose revision is unavailable')
        if observation['resource']['id'] != args['item_id']:
            raise PermissionError('Result item was not observed in this project')
        outputs, seen = [], set()
        for ref in args['outputs']:
            if (not isinstance(ref, dict) or set(ref) != {'output_id', 'version'}
                    or not isinstance(ref['output_id'], str) or type(ref['version']) is not int or ref['version'] < 1):
                raise ValueError('Output references require identity and positive version')
            key = (ref['output_id'], ref['version'])
            if key in seen:
                raise ValueError('Duplicate output version in result')
            seen.add(key)
            output = read_output(conn, agent_id, *key, workspace=workspace)
            if output['item_id'] != args['item_id']:
                raise PermissionError('Output belongs to a different assignment')
            outputs.append(ref)
        observed = [dict(zip(('operation_id', 'operation', 'resource_id', 'status'), row), source='plane')
                    for row in conn.execute(
                        'SELECT m.operation_id,m.operation,m.resource_id,m.status '
                        'FROM agent_native_work_effects e JOIN agent_native_plane_mutations m '
                        'ON m.operation_id=e.operation_id WHERE e.run_id=? AND m.status=\'confirmed\' '
                        'ORDER BY m.created_at,m.operation_id', (run_id,))]
        autonomy = conn.execute(
            'SELECT level FROM agent_native_autonomy_attempts WHERE run_id=? ORDER BY created_at DESC LIMIT 1',
            (run_id,)).fetchone()
        if autonomy is None:
            autonomy = conn.execute('SELECT level FROM agent_native_autonomy_settings WHERE agent_id=?',
                                    (agent_id,)).fetchone()
        review_required = bool(autonomy and autonomy[0] == 1 and args['outcome'] == 'submitted' and outputs)
        review = {
            'required': review_required,
            'source': 'autonomy',
            'reason': ('Approval-driven autonomy requires owner review of submitted deliverables.'
                       if review_required else None),
        }
        criteria = observation['resource'].get('description_html') or ''
        record = {'id': str(uuid4()), 'agent_id': agent_id, 'run_id': run_id, 'item_id': args['item_id'],
                  'soul_revision': work[1], 'purpose': purpose[0], 'criteria_snapshot': criteria,
                  'criteria_revision': _hash(criteria), 'assignment_fingerprint': observation['fingerprint'],
                  'criteria_observed_at': _now(), 'summary': args['summary'], 'outcome': args['outcome'],
                  'evaluation': {'report': args['evaluation'], 'source': 'agent'}, 'acceptance': 'not_evaluated',
                  'owner_decision': None,
                  'review': review,
                  'outputs': outputs, 'references': references, 'observed_effects': observed,
                  'observed_effect_scope': 'attempt', 'created_at': _now()}
        encoded = _json(record)
        validate(conn)
        conn.execute('INSERT INTO agent_native_work_results '
                     '(id,agent_id,run_id,item_id,call_id,request_sha256,record_json,record_sha256,created_at) '
                     'VALUES (?,?,?,?,?,?,?,?,?)',
                     (record['id'],agent_id,run_id,args['item_id'],call_id,request_hash,encoded,_hash(encoded),record['created_at']))
        if record_progress is not None:
            record_progress(conn, record)
            validate(conn)
    return record
