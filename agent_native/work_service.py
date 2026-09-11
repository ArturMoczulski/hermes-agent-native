"""Dashboard-owned initial bounded work runs; browsers only observe and request stops.

Each run gets a native ComputeHost. Its private pipe delegates scoped effects to
one host thread. Process stopping never waits for that thread or a Plane request.
"""
import hashlib
import json
import logging
from pathlib import Path
import queue
import threading
import time
from uuid import uuid4

from agent_native.identity import OWNER, _now, get_root
from agent_native import work_state as state
from hermes_cli.kanban_db_connect import connect_closing, write_txn

_log = logging.getLogger(__name__)


def _workspace_name(root):
    """Short label for the activity row; falls back to the resolved path tail."""
    try:
        return Path(root).resolve().name or str(Path(root).resolve())
    except OSError:
        return str(root)


def _derive_repository_event_detail(tool, result, args, workspace):
    """Build the structured ``detail`` payload the Activity tab renders for repository tools.

    The dashboard needs to show what the agent actually did, not ``Repository
    operation: <tool>``. This returns a plain dict (JSON-serialized on the row)
    with the path, byte count, sha256, argv, exit code, and workspace name.
    """
    detail = {'operation': tool, 'workspace': _workspace_name(workspace)}
    if tool == 'repository_file_read':
        path = result.get('path')
        content = result.get('content')
        detail.update({
            'path': path,
            'sha256': result.get('sha256'),
            'bytes': len(content.encode('utf-8')) if isinstance(content, str) else None,
        })
    elif tool == 'repository_file_write':
        detail.update({
            'path': result.get('path'),
            'sha256': result.get('sha256'),
            'bytes': result.get('bytes'),
        })
    elif tool == 'repository_command':
        argv = list(args.get('argv') or [])
        body = result.get('output') or ''
        detail.update({
            'argv': argv,
            'command': ' '.join(argv),
            'exit_code': result.get('returncode'),
            'output_bytes': len(body.encode('utf-8', errors='replace')),
            'truncated': bool(result.get('truncated')),
            'timed_out': bool(result.get('timed_out')),
        })
    return detail


def _derive_repository_event_summary(tool, detail):
    """Human-readable summary derived from the structured ``detail`` payload.

    Kept narrow: one short line per kind, no embedded JSON, so the activity
    feed remains readable without expanding every row.
    """
    if tool == 'repository_file_read':
        return f'Read file {detail.get("path")}'
    if tool == 'repository_file_write':
        size = detail.get('bytes')
        return f'Wrote {detail.get("path")} ({size} bytes)' if size is not None else f'Wrote {detail.get("path")}'
    if tool == 'repository_command':
        cmd = detail.get('command') or 'command'
        exit_code = detail.get('exit_code')
        in_ws = detail.get('workspace')
        location = f' in {in_ws}' if in_ws else ''
        if detail.get('timed_out'):
            return f'Ran `{cmd}`{location} (timed out)'
        if exit_code is None:
            return f'Ran `{cmd}`{location}'
        return f'Ran `{cmd}`{location} (exit {exit_code})'
    return None


def _authority_revoked(validate, error):
    """Separate a denied operation from loss of the whole run capability."""
    if not isinstance(error, PermissionError):
        return False
    try:
        validate()
        return False
    except PermissionError:
        return True


def _recoverable_interruption(conn, run_id):
    """Return true only when a fresh attempt cannot duplicate unsettled effects."""
    if conn.execute(
            'SELECT 1 FROM agent_native_work_effects WHERE run_id=? AND result IS NULL LIMIT 1',
            (run_id,)).fetchone():
        return False
    if conn.execute(
            "SELECT 1 FROM agent_native_plane_mutations m "
            "JOIN agent_native_work_effects e ON e.operation_id=m.operation_id "
            "WHERE e.run_id=? AND m.status IN ('pending','unknown') LIMIT 1",
            (run_id,)).fetchone():
        return False
    if conn.execute(
            "SELECT 1 FROM agent_native_progress WHERE run_id=? "
            "AND status IN ('pending','unknown') LIMIT 1", (run_id,)).fetchone():
        return False
    return True


def _cadence_can_retry(conn, agent_id, run_id):
    cadence = conn.execute('SELECT enabled FROM agent_native_cadence WHERE agent_id=?',
                           (agent_id,)).fetchone()
    return bool(cadence and cadence[0]) and _recoverable_interruption(conn, run_id)


def _initial_context(snapshot, contracts, autonomy_policy=None):
    """Build the managed-work instruction with a clear planning/output boundary."""
    return ('Review your protected purpose and current project. Continue useful work, ask a scoped question or record a waiting result when appropriate. Use the supplied planning skill. '
            'Create or refine a short project brief, an undated outcome cycle and an actionable task with acceptance criteria. '
            'Choose useful work appropriate to your purpose and the supplied material. Use work_item_select before '
            'substantive work and whenever you switch tasks. The framework posts a work-selection progress comment; '
            'do not duplicate that start update. Use progress_report for meaningful checkpoints, details and blockers as you work. '
            'Owner verbosity controls delivery, and direct comment.create is not available to this worker. '
            'When clarification is needed, use work_question on the selected item and reuse its stable topic; '
            'read answers by question_id. Never treat a missing answer as permission. Do independent work or record a waiting result instead of polling repeatedly. '
            'Call work_feedback with empty arguments before substantive work and publication to read owner direction. '
            'Apply it within current purpose and grants, then report handling with work_feedback; never claim acceptance. '
            'Keep project briefs, cycle and module descriptions, task descriptions, acceptance criteria, dependencies, planning notes and progress updates in Plane. '
            'They are not saved outputs unless the purpose or selected assignment explicitly requests a planning document as its deliverable. '
            'Use output_publish only for the actual purpose-level work product when it is text or Markdown. Use output_media_publish for an image, audio or video file already created in the granted project workspace; a filesystem path in Markdown is not an attachment. '
            'A confirmed planning change is a valid result with an empty outputs list. '
            'Use output_read to read complete prior output versions when excerpts are truncated. Use output_id only when revising an existing output. The host reports saved outputs and result records in Plane; '
            'do not duplicate these notifications with artifact.record or rewrite the task description to announce completion. '
            'Use child_create only for a clearly independent delegated responsibility. Give the child a protected purpose, remain accountable for its work, and do not treat creating it as completing your assignment. Use child_replace only when a direct child\'s ongoing responsibility needs a clean successor; select the handoff explicitly. '
            'Use child_inspect to review descendant evidence and child_result_evaluate to evaluate an exact submitted result from your direct child. '
            'Inspect the task and use result_record to report its outcome and evaluation with saved output version references. '
            'Useful discovery, a plan change, waiting for input or a blocker may have an empty outputs list. '
            'When repository tools are available, they operate in this agent\'s granted project workspace. '
            'A granted project workspace may initially be empty. Inspect it with repository_command using rg --files; '
            'create the first files with repository_file_write and expected_sha256="missing". A rejected unsupported '
            'command or a read of a file that does not exist does not mean the workspace grant is absent. Use the '
            'returned operation error to correct the call before reporting an authority blocker. '
            'Before ending a work review, use purpose_evaluate to record whether the whole protected purpose should continue, wait, seek clarification or is a retirement candidate. '
            'The owner_decision_state in current planning state is authoritative. A result is an owner-review dependency only when its exact ID appears in required_result_reviews. '
            'Never infer a gate from prior prose, an optional review, a result ID absent from that list, or the mere existence of a submitted result. '
            'Use wait only while an exact deliverable appears in required_result_reviews. Optional review never justifies waiting. When owner input is actually required, ask a scoped work_question and use clarify with that question ID. Otherwise continue. '
            'External links are unverified references, never proof of saved content or successful actions. '
            +(autonomy_policy or 'Evaluation is required. Continue independently unless an explicit requirement makes owner acceptance mandatory.')+' '
            'The autonomy policy decides when the host creates a required review; it does not let you invent one. '
            'Regardless of autonomy level, an empty required_result_reviews list means there is no owner-review dependency and you must advance to the next useful milestone. '
            'Leave the task nonterminal only when owner acceptance is actually required; otherwise continue useful work under the autonomy policy. '
            'terminal task acceptance is not available in this increment. Explain any blocker. Stop after this bounded attempt; '
            'do not invent approval or schedule another run.\nCurrent planning state (work data):\n'+json.dumps(snapshot)+
            '\nSupported Plane operation argument contracts:\n'+json.dumps(contracts))


class _Run:
    def __init__(self, service, work):
        from tui_gateway.host_supervisor import HostSupervisor
        self.service, self.work = service, work
        self.deadline = time.monotonic() + work['limits']['timeout_seconds']
        self.inbox = queue.Queue()
        self.ended = threading.Event()
        self.stopped = threading.Event()
        self.final_text = ''
        self.stop_lock = threading.Lock()
        # Saved outputs are host-owned evidence. Their storage root must remain
        # stable when the owner later grants a separate coding repository.
        self.output_workspace = service.home / 'agents' / work['agent_id'] / 'workspace'
        self.host = HostSupervisor(registry_path=service.home / 'work-hosts' / (work['id']+'.json'),
            env={'HERMES_HOME':str(service.home.parent),'HERMES_MANAGED_COMPUTE_HOST':'1'},
            expected_hermes_home=str(service.home.parent), rpc_sink=self.inbox.put,
            source_root=work.get('runtime_release'),
            autostart=False,respawn_max=0)
        self.thread = threading.Thread(target=self.run,name='work-'+work['id'][:8],daemon=True)
        self.watchdog = threading.Thread(target=self._watch_deadline,
                                        name='work-deadline-'+work['id'][:8],daemon=True)
        self.watchdog.start()

    def _watch_deadline(self):
        # Each run enforces its own clock even while another run's settlement
        # or a queued-work claim blocks the shared service monitor on SQLite.
        if not self.ended.wait(max(0, self.deadline - time.monotonic())):
            self.stop('Work reached its time limit.')

    def validate(self, conn):
        if self.stopped.is_set() or time.monotonic() >= self.deadline:
            raise PermissionError('Work was stopped or reached its time limit')
        state.validate(conn,self.work['id'])

    def stop(self, reason='Owner paused this work.', *, recoverable=False, superseded=False):
        # No broker/HTTP/database lock may be acquired before process termination.
        self.stopped.set()
        dead = self.host.force_stop(timeout=2)
        self.inbox.put(None)
        timed_out = time.monotonic() >= self.deadline
        if timed_out:
            reason = 'Work reached its time limit.'
        with self.stop_lock:
            with connect_closing(self.service.db_path) as conn, write_txn(conn):
                row = conn.execute('SELECT state FROM agent_native_work_runs WHERE id=?',(self.work['id'],)).fetchone()
                if row[0] not in state.TERMINAL:
                    can_continue = recoverable and _cadence_can_retry(
                        conn, self.work['agent_id'], self.work['id'])
                    target = ('limit_reached' if timed_out else 'interrupted' if superseded or can_continue else 'paused') if dead else 'unknown'
                    conn.execute('UPDATE agent_native_work_runs SET state=?,stop_requested=1,finished_at=?,summary=? WHERE id=?',
                                 (target,_now(),reason,self.work['id']))
                    state.event(conn,self.work['id'],'work.'+target,reason if dead else 'Worker stop could not be confirmed.')
        return dead

    def _effect(self, conn, planning, params):
        try:
            return self._effect_unsettled(conn, planning, params)
        except (ValueError, PermissionError) as exc:
            if _authority_revoked(lambda: self.validate(conn), exc):
                raise
            tool, arguments = params.get('tool'), params.get('arguments')
            fingerprint = (hashlib.sha256(
                json.dumps([tool, arguments], sort_keys=True).encode()).hexdigest()
                if isinstance(tool, str) and isinstance(arguments, dict) else None)
            result = self._reject_effect(
                conn, params.get('tool_call_id'), tool, type(exc), fingerprint,
                # Purpose evaluation is the mandatory end-of-attempt checkpoint.
                # Its validation messages are bounded, non-secret remediation the
                # worker needs to correct its next call rather than looping on a
                # generic rejection until the turn guardrail stops it.
                message=str(exc) if tool == 'purpose_evaluate' else None)
            if result is None:
                raise
            return result
        except Exception as exc:
            # The operation raised before it could complete. That is a known
            # local outcome, not an external mutation with an unknown receipt:
            # settle the effect so a null result cannot wedge the run at
            # ``framework_reconciliation`` forever. A still-pending Plane
            # mutation keeps its null receipt and is reconciled by read-back.
            self._settle_effect_failure(conn, params, exc)
            raise

    def _settle_effect_failure(self, conn, params, exc):
        """Record a known in-process failure as a settled effect result."""
        call_id, tool = params.get('tool_call_id'), params.get('tool')
        row = conn.execute(
            'SELECT operation_id,result FROM agent_native_work_effects '
            'WHERE run_id=? AND call_id=?', (self.work['id'], call_id)).fetchone()
        if row is None or row[1] is not None:
            return
        mutation = conn.execute(
            'SELECT status FROM agent_native_plane_mutations WHERE operation_id=?',
            (row[0],)).fetchone()
        if mutation and mutation[0] in ('pending', 'unknown'):
            return
        result = {
            'status': 'error',
            'tool': tool,
            'error': type(exc).__name__,
            'message': ('The managed tool failed while executing; no external '
                        'mutation was recorded for it.'),
        }
        with write_txn(conn):
            conn.execute(
                'UPDATE agent_native_work_effects SET result=? '
                'WHERE run_id=? AND call_id=?',
                (json.dumps(result), self.work['id'], call_id))
            state.event(
                conn, self.work['id'], 'work.effect_error',
                f'{tool} failed while executing ({type(exc).__name__}).',
            )

    def _effect_unsettled(self, conn, planning, params):
        self.validate(conn)
        if params.get('run_id') != self.work['id']:
            raise PermissionError('Work identity changed')
        tool, args, call_id = params.get('tool'), params.get('arguments'), params.get('tool_call_id')
        if (tool not in ('child_create','child_replace','child_inspect','child_result_evaluate','child_autonomy_configure','plane_resource_inspect','plane_operation_execute','output_publish','output_media_publish','output_read','result_record','purpose_evaluate','purpose_retire','work_item_select','progress_report','work_feedback','work_question','work_comments','repository_file_read','repository_file_write','repository_command','repository_preview_publish')
                or not isinstance(args,dict) or not isinstance(call_id,str) or not 1 <= len(call_id) <= 256):
            raise PermissionError('Unsupported work effect')
        fingerprint = hashlib.sha256(json.dumps([tool,args],sort_keys=True).encode()).hexdigest()
        with write_txn(conn):
            self.validate(conn)
            old = conn.execute('SELECT operation_id,fingerprint,result,tool FROM agent_native_work_effects '
                               'WHERE run_id=? AND call_id=?',(self.work['id'],call_id)).fetchone()
            if old:
                if old[1] != fingerprint:
                    raise PermissionError('Native tool call was reused with different input')
                if old[2] is not None:
                    return json.loads(old[2])
                operation_id = old[0]
            else:
                operation_id = str(uuid4())
                conn.execute('INSERT INTO agent_native_work_effects(run_id,call_id,operation_id,fingerprint,tool) VALUES(?,?,?,?,?)',
                             (self.work['id'],call_id,operation_id,fingerprint,tool))
        if tool == 'child_create':
            from agent_native.child_delegation import create
            result=create(conn,validate=self.validate,parent_id=self.work['agent_id'],
                          parent_run_id=self.work['id'],call_id=call_id,arguments=args)
        elif tool == 'child_replace':
            from agent_native.replacement import replace_child
            result=replace_child(conn,validate=self.validate,parent_id=self.work['agent_id'],
                                 parent_run_id=self.work['id'],call_id=call_id,arguments=args)
        elif tool == 'child_inspect':
            from agent_native.child_supervision import inspect
            result=inspect(conn,validate=self.validate,home=self.service.home,
                           parent_id=self.work['agent_id'],arguments=args)
        elif tool == 'child_result_evaluate':
            from agent_native.child_supervision import evaluate
            result=evaluate(conn,validate=self.validate,parent_id=self.work['agent_id'],
                            parent_run_id=self.work['id'],call_id=call_id,arguments=args)
        elif tool == 'child_autonomy_configure':
            from agent_native.child_autonomy import configure
            result=configure(conn,validate=self.validate,parent_id=self.work['agent_id'],
                             parent_run_id=self.work['id'],call_id=call_id,arguments=args)
        elif tool == 'plane_resource_inspect':
            result = planning.inspect(args)
        elif tool == 'plane_operation_execute':
            if set(args) != {'operation','arguments'}:
                return self._reject_effect(conn, call_id, tool, ValueError)
            if args['operation'] == 'comment.create':
                return self._reject_effect(conn, call_id, tool, ValueError)
            from agent_native.plane_write_contracts import ContractError
            from agent_native.plane_writes import PlaneWriteError, PlaneWriteConflict
            try:
                result = planning.execute(operation_id,args['operation'],args['arguments'])
            except ContractError:
                operation = args['operation']
                result = {
                    'status':'invalid_arguments',
                    'operation':operation,
                    'write_attempted':False,
                    'message':operation+' arguments do not match the tool contract. Review its required fields and use IDs and fingerprints from current Plane observations.',
                }
                state.event(conn,self.work['id'],'work.contract_rejected',
                            'Plane rejected invalid '+operation+' arguments before execution.')
            except PlaneWriteError as exc:
                if isinstance(exc, PlaneWriteConflict) and exc.outcome == 'rejected':
                    # A known pre-write rejection is task data, not revocation.
                    # Retain this call's receipt; a fresh decision needs a new call.
                    operation = args['operation']
                    operation_args = args['arguments']
                    inspect_target = (
                        ('item', operation_args.get('item_id')) if operation in ('item.update','cycle.assign','cycle.remove','dependency.add') else
                        ('cycle', operation_args.get('cycle_id')) if operation == 'cycle.update' else
                        ('project', None) if operation == 'project.update' else None)
                    fresh = None
                    if inspect_target is not None:
                        try:
                            fresh = {'kind':inspect_target[0], **planning.inspect({'kind':inspect_target[0], **({'resource_id':inspect_target[1]} if inspect_target[1] else {})})}
                        except Exception:
                            # The original rejection remains authoritative. A
                            # failed convenience read must not change its status.
                            pass
                    result = {'status':'conflict','operation_id':operation_id,
                              'operation':operation,
                              'write_attempted':False,
                              'message':'Plane changed or the requested relationship conflicts with current state. No write was sent. Inspect the affected resource and current relationships, then reassess the task before issuing a new operation. Do not repeat stale arguments.'}
                    if fresh is not None:
                        result['fresh'] = fresh
                    state.event(conn,self.work['id'],'work.conflict',
                                'Plane rejected '+operation+' before writing; refreshed '+inspect_target[0]+' state is available in the tool result.' if fresh is not None else
                                'Plane rejected '+operation+' before writing; fresh inspection required.')
                elif exc.outcome == 'unknown':
                    # The mutation journal retains the original operation. Revoke
                    # this run before another model request or effect is admitted;
                    # neither settlement nor a retry may relabel it as failed.
                    message = ('Plane write outcome is unknown. Inspect the existing '
                               'operation before continuing; it was not retried.')
                    with write_txn(conn):
                        conn.execute(
                            "UPDATE agent_native_work_runs SET state='unknown',stop_requested=1,"
                            'error=?,summary=?,finished_at=? WHERE id=?',
                            (message,message,_now(),self.work['id']))
                        state.event(conn,self.work['id'],'work.unknown',message)
                    raise
                else:
                    raise
        elif tool == 'work_comments':
            from agent_native.comments import worker
            result = worker(conn, validate=self.validate, planning=planning, agent_id=self.work['agent_id'],
                            run_id=self.work['id'], arguments=args)
        elif tool == 'work_question':
            from agent_native.questions import worker
            result = worker(conn, validate=self.validate, inspect=planning.inspect, agent_id=self.work['agent_id'],
                            run_id=self.work['id'], arguments=args)
            if 'question' in args:
                from agent_native.progress import deliver
                deliver(conn, planning, self.validate, 'question:'+result['id'])
        elif tool == 'work_feedback':
            from agent_native.feedback import worker
            result = worker(conn, validate=self.validate, agent_id=self.work['agent_id'],
                            run_id=self.work['id'], arguments=args)
        elif tool == 'progress_report':
            from agent_native.progress import checkpoint
            result = checkpoint(conn, validate=self.validate, planning=planning,
                                agent_id=self.work['agent_id'], run_id=self.work['id'], call_id=call_id, arguments=args)
        elif tool == 'repository_preview_publish':
            from agent_native.identity import OWNER
            from agent_native.project_preview import publish
            result = publish(conn, actor=OWNER, agent_id=self.work['agent_id'], **args)
        elif tool in ('repository_file_read', 'repository_file_write', 'repository_command'):
            from agent_native.repository_access import active_repository
            from agent_native import builder_repository
            repository = active_repository(conn, self.work['agent_id'])
            operation = {'repository_file_read': builder_repository.read_file,
                         'repository_file_write': builder_repository.write_file,
                         'repository_command': builder_repository.command}[tool]
            result = operation(repository, args)
            self._repository_detail = _derive_repository_event_detail(tool, result, args, repository)
            self._repository_summary = _derive_repository_event_summary(tool, self._repository_detail)
        elif tool == 'work_item_select':
            from agent_native.work_focus import select
            from agent_native.plane_reads import PlaneReadError
            try:
                result = select(conn, validate=self.validate, inspect=planning.inspect,
                                agent_id=self.work['agent_id'], run_id=self.work['id'],
                                call_id=call_id, arguments=args)
            except PlaneReadError as exc:
                # Only inspection happens before the selection is committed.
                # A missing/out-of-scope item or unavailable read is a settled
                # rejection, not evidence of an uncertain external mutation.
                # Keep comment delivery outside this handler: it CAN write.
                if conn.execute('SELECT 1 FROM agent_native_work_selections '
                                'WHERE run_id=? AND call_id=?',
                                (self.work['id'], call_id)).fetchone():
                    raise
                return self._reject_effect(
                    conn, call_id, tool, type(exc),
                    message='Plane could not read the requested item. No work selection or write '
                            'was made. Inspect the project for a valid item ID; if Plane is '
                            'unavailable, retry the read later with a new tool call.')
            from agent_native.progress import deliver
            deliver(conn, planning, self.validate, result['selection_id'])
        elif tool == 'output_read':
            from agent_native.output_read import read_chunk
            result = read_chunk(conn, agent_id=self.work['agent_id'], workspace=self.output_workspace, arguments=args)
        elif tool == 'purpose_evaluate':
            from agent_native.purpose_evaluation import record
            result=record(conn,validate=self.validate,agent_id=self.work['agent_id'],
                          run_id=self.work['id'],call_id=call_id,arguments=args)
        elif tool == 'purpose_retire':
            from agent_native.retirement import retire
            result=retire(conn,validate=self.validate,agent_id=self.work['agent_id'],
                          run_id=self.work['id'],call_id=call_id,arguments=args)
        elif tool == 'output_publish':
            from agent_native.output_store import publish
            from agent_native import progress
            base = progress.public_base()
            required = {'title','content','item_id','format'}
            if not required <= set(args) or set(args) - required - {'output_id'}:
                return self._reject_effect(conn, call_id, tool, ValueError)
            planning.inspect({'kind':'item','resource_id':args['item_id']})
            result = publish(conn,validate=self.validate,workspace=self.output_workspace,
                             agent_id=self.work['agent_id'],run_id=self.work['id'],call_id=call_id,
                             record_progress=lambda c, r: progress.output_saved(c, r, base), **args)
            progress.deliver(conn, planning, self.validate, f"output:{result['output_id']}:{result['version']}")
        elif tool == 'output_media_publish':
            if set(args) != {'title', 'item_id', 'path'}:
                return self._reject_effect(conn, call_id, tool, ValueError)
            planning.inspect({'kind':'item','resource_id':args['item_id']})
            from agent_native.media_store import publish
            from agent_native.repository_access import active_repository
            result = publish(conn, validate=self.validate,
                             project_workspace=active_repository(conn, self.work['agent_id']),
                             output_workspace=self.output_workspace,
                             agent_id=self.work['agent_id'], run_id=self.work['id'],
                             call_id=call_id, **args)
        else:
            from agent_native.result_store import record
            from agent_native import progress
            base = progress.public_base()
            if 'item_id' not in args:
                return self._reject_effect(conn, call_id, tool, ValueError)
            observation = planning.inspect({'kind':'item','resource_id':args['item_id']})
            result = record(conn,validate=self.validate,workspace=self.output_workspace,
                            agent_id=self.work['agent_id'],run_id=self.work['id'],call_id=call_id,
                            observation=observation,arguments=args,
                            record_progress=lambda c, r: progress.result_recorded(c, r, base))
            progress.deliver(conn, planning, self.validate, 'result:'+result['id'])
        with write_txn(conn):
            # Keep honest receipts for an effect already sent even if Pause raced
            # its response. No subsequent effect is admitted after a stop.
            conn.execute('UPDATE agent_native_work_effects SET result=? WHERE run_id=? AND call_id=?',
                         (json.dumps(result),self.work['id'],call_id))
            summary = (('Created child agent: '+result['child_id']) if tool=='child_create' else
                       ('Replaced child agent: '+result['predecessor_id']+' with '+result['successor_id']) if tool=='child_replace' else
                       ('Inspected descendant: '+result.get('child_id',result.get('child',{}).get('id','unknown'))) if tool=='child_inspect' else
                       ('Evaluated child result: '+result['decision']) if tool=='child_result_evaluate' else
                       ('Read saved output: '+result['title']) if tool=='output_read' else
                       ('Saved output: '+result['title']) if tool=='output_publish' else
                       ('Published media output: '+result['title']) if tool=='output_media_publish' else
                       ('Recorded result: '+result['summary']) if tool=='result_record' else
                       ('Evaluated whole purpose: '+result['judgment']) if tool=='purpose_evaluate' else
                       ('Retired agent from purpose evaluation') if tool=='purpose_retire' else
                       ('Progress report: '+result['status']) if tool=='progress_report' else
                       getattr(self, '_repository_summary', None) if tool.startswith('repository_') else
                       ('Plane rejected invalid '+result.get('operation','operation')+' arguments' if result.get('status')=='invalid_arguments' else
                        ('Plane conflict in '+result.get('operation','operation')+': refreshed state returned' if result.get('fresh') else 'Plane conflict: fresh inspection required') if result.get('status')=='conflict' else
                        'Plane: '+args.get('operation','inspected '+args.get('kind','resource'))))
            if tool != 'work_item_select':
                # Selection and its event commit together; receipt recovery must
                # not emit a second change or make an old item current again.
                detail = getattr(self, '_repository_detail', None) if tool.startswith('repository_') else None
                state.event(conn, self.work['id'], 'work.effect', summary, detail=detail)
            if tool.startswith('repository_'):
                self._repository_detail = None
                self._repository_summary = None
        return result

    def _reject_effect(self, conn, call_id, tool, error_type, fingerprint=None, message=None):
        row = conn.execute(
            'SELECT tool,result,fingerprint FROM agent_native_work_effects '
            'WHERE run_id=? AND call_id=?',
            (self.work['id'], call_id),
        ).fetchone()
        if (row is None or row[0] != tool
                or fingerprint is not None and row[2] != fingerprint):
            return None
        if row[1] is not None:
            return json.loads(row[1])
        result = {
            'status': 'rejected',
            'tool': tool,
            'error': error_type.__name__,
            'message': message or ('The managed tool rejected this call before any effect was '
                                   'attempted. Review its arguments and retry with a new tool call.'),
        }
        with write_txn(conn):
            conn.execute(
                'UPDATE agent_native_work_effects SET result=? '
                'WHERE run_id=? AND call_id=?',
                (json.dumps(result), self.work['id'], call_id),
            )
            state.event(
                conn, self.work['id'], 'work.effect_rejected',
                f'{tool} rejected the call before any effect was attempted '
                f'({error_type.__name__}).',
            )
        return result

    def _admit(self, conn, params):
        if params.get('run_id') != self.work['id'] or params.get('boundary') not in ('model','persist'):
            raise PermissionError('Unsupported work boundary')
        with write_txn(conn):
            self.validate(conn)
            if params['boundary']=='model':
                count = conn.execute('SELECT model_calls FROM agent_native_work_runs WHERE id=?',(self.work['id'],)).fetchone()[0]
                if count >= self.work['limits']['max_iterations']:
                    raise PermissionError('Model step limit reached')
                conn.execute('UPDATE agent_native_work_runs SET model_calls=model_calls+1 WHERE id=?',(self.work['id'],))
                state.event(conn,self.work['id'],'work.model','Model step '+str(count+1))
        return {}

    def run(self):
        from agent_native.writer_planning import install_grants, open_planning
        from agent_native.plane_write_contracts import _CONTRACTS
        try:
            with connect_closing(self.service.db_path) as conn:
                self.validate(conn)
                root = get_root(conn,actor=OWNER,agent_id=self.work['agent_id'])
                binding = install_grants(conn,actor=OWNER,agent_id=root['id'])
                with write_txn(conn):
                    self.validate(conn)
                    conn.execute('UPDATE agent_native_work_runs SET binding_id=? WHERE id=?',(binding,self.work['id']))
                from agent_native.repository_access import active_repository
                try:
                    self.workspace = active_repository(conn, root['id'])
                except PermissionError:
                    self.workspace = self.service.home / 'agents' / root['id'] / 'workspace'
                def read_retry(phase, status_code, delay):
                    with write_txn(conn):
                        self.validate(conn)
                        summary = (f'Waiting for Plane (HTTP {status_code}); retrying this read in {delay} seconds.'
                                   if phase == 'waiting' else 'Plane read recovered; continuing the same attempt.')
                        state.event(conn, self.work['id'], 'work.dependency_'+phase, summary)
                with open_planning(db_path=self.service.db_path,home=self.service.home,
                                   agent_id=root['id'],binding_id=binding,validate=self.validate,
                                   on_read_retry=read_retry) as planning:
                    snapshot = planning.snapshot()
                    from agent_native.result_store import list_results
                    from agent_native.output_store import list_outputs
                    from agent_native.media_store import list_media
                    from agent_native.questions import recent as recent_questions
                    snapshot['previous_results'] = list_results(conn,root['id'])[:10]
                    required_reviews = [
                        {'result_id': result['id'], 'item_id': result['item_id'],
                         'summary': result['summary'], 'reason': result['review']['reason']}
                        for result in list_results(conn, root['id'])
                        if result['review']['required'] and result['acceptance'] == 'not_evaluated'
                    ]
                    snapshot['owner_decision_state'] = {
                        'required_result_reviews': required_reviews,
                        'message': ('Owner review is required only for the exact results listed here.'
                                    if required_reviews else
                                    'No result currently requires owner review. Continue useful work; do not wait for result acceptance.'),
                    }
                    snapshot['saved_outputs'] = list_outputs(conn,root['id'])[:10]
                    snapshot['saved_media_outputs'] = list_media(conn,root['id'])[:10]
                    snapshot['saved_output_excerpts'] = []
                    from agent_native.output_store import read_output
                    for output in snapshot['saved_outputs'][:3]:
                        planning.inspect({'kind':'item','resource_id':output['item_id']})
                        saved = read_output(conn,root['id'],output['output_id'],output['version'],workspace=self.output_workspace)
                        snapshot['saved_output_excerpts'].append({'output_id':saved['output_id'],'version':saved['version'],
                            'content':saved['content'][:8000],'truncated':len(saved['content'])>8000})
                    snapshot['questions'] = recent_questions(conn,root['id'])
                    from agent_native.purpose_evaluation import list_evaluations
                    snapshot['previous_purpose_evaluations']=list_evaluations(conn,root['id'])[:5]
                    from agent_native.child_supervision import summaries as child_summaries
                    snapshot['children'] = child_summaries(conn, root['id'], 20)
                    if (root.get('replacement') or {}).get('role') == 'successor':
                        snapshot['replacement_handoff'] = root['replacement']
                    snapshot['continuation_note'] = 'Review earlier results and outputs; do not repeat finished work. Read work_feedback and current Plane comments with work_comments before substantive work. Waiting is a valid result; do not invent new work.'
                    initial = _initial_context(snapshot, {k: v for k, v in _CONTRACTS.items() if k != 'comment.create'},
                                               self.work['autonomy']['policy'])
                    skill = (Path(__file__).resolve().parents[1] / 'skills/productivity/plane-project-management/SKILL.md').read_text()
                    from agent.work_policy import TOOL_NAMES, BUILDER_TOOL_NAMES
                    from agent_native.repository_access import active_repository
                    try:
                        active_repository(conn, root['id'])
                    except PermissionError:
                        authorized_tools = TOOL_NAMES
                    else:
                        authorized_tools = TOOL_NAMES | BUILDER_TOOL_NAMES
                        from agent_native.first_builder import active_instructions
                        try:
                            protected = active_instructions(conn, root['id'])
                        except PermissionError:
                            pass
                        else:
                            skill = (protected / 'PLANE.md').read_text() + '\n\n' + skill
                            initial = '\n\n'.join((
                                (protected / 'SOUL.md').read_text(),
                                (protected / 'INSTRUCTIONS.md').read_text(),
                                (protected / 'PRACTICES.md').read_text(),
                                initial,
                            ))
                    attempt = {'run_id':self.work['id'],'agent_id':root['id'],'soul_revision':root['soul_revision'],
                               'name':root['name'],'purpose':root['purpose'],'workspace':str(self.workspace),
                               'session_id':self.work['session_id'],'native_db':str(self.service.home.parent/'state.db'),
                               'deadline_monotonic':self.deadline,'max_iterations':self.work['limits']['max_iterations'],
                               'max_tokens':8192,'initial_context':initial,'skill_text':skill,
                               'authorized_tools':sorted(authorized_tools)}
                    with write_txn(conn):
                        self.validate(conn)
                        conn.execute("UPDATE agent_native_work_runs SET state='running' WHERE id=?",(self.work['id'],))
                        state.event(conn,self.work['id'],'work.running','Working from the purpose and current Plane project.')
                    self.host.submit_turn({'sid':attempt['session_id'],'session_key':attempt['session_id'],
                        'request_id':attempt['run_id'],'work_attempt':attempt,
                        'model_selection':self.work['model_selection']},
                        on_complete=lambda frame:self.inbox.put({'finished':frame}))
                    with write_txn(conn):
                        conn.execute('UPDATE agent_native_work_runs SET worker_pid=? WHERE id=?',(self.host.pid,self.work['id']))
                    while not self.stopped.is_set():
                        frame = self.inbox.get()
                        if frame is None:
                            break
                        if 'finished' in frame:
                            self.finish(conn,frame['finished'])
                            break
                        method, params = frame.get('method'), frame.get('params',{})
                        if method in ('work.admit','work.effect'):
                            try:
                                result = self._admit(conn,params) if method=='work.admit' else self._effect(conn,planning,params)
                                reply = {'ok':True,'result':result}
                            except Exception as exc:
                                # Never return credentials/HTTP response bodies in errors.
                                reply = {'ok':False,'revoked':_authority_revoked(lambda: self.validate(conn), exc),
                                         'error':'Work operation could not be admitted or confirmed ('+type(exc).__name__+').'}
                                with write_txn(conn):
                                    state.event(conn,self.work['id'],'work.operation_failed',reply['error'])
                            self.host.send_work_result(frame['id'],reply)
                        elif method == 'event' and params.get('type') == 'message.complete':
                            self.final_text = str(params.get('payload',{}).get('text',''))[:16000]
                        elif method == 'event' and params.get('type') == 'usage.complete':
                            from agent_native.usage import record
                            payload = dict(params.get('payload', {}))
                            record(conn, run_id=self.work['id'], agent_id=self.work['agent_id'], usage=payload)
        except Exception as exc:
            _log.warning('Work run stopped (%s)',type(exc).__name__)
            self.fail(type(exc).__name__)
        finally:
            self.host.force_stop(timeout=2)
            self._report_terminal()
            self.ended.set()

    def _report_terminal(self):
        """Host-only notification of committed evidence after the worker stopped.

        This validator never reaches a model or its effect broker. Existing
        Plane grants and purpose/configuration checks still govern delivery.
        Unknown attempts are not retried; only never-attempted reports are sent.
        """
        from agent_native import progress
        from agent_native.writer_planning import open_planning
        budget_end = time.monotonic() + 15

        def validate(conn):
            row = conn.execute('SELECT w.state,w.agent_id,w.soul_revision,a.soul_revision '
                               'FROM agent_native_work_runs w JOIN agent_native_agents a ON a.id=w.agent_id '
                               'WHERE w.id=?', (self.work['id'],)).fetchone()
            if (not row or row[0] not in state.TERMINAL or row[1] != self.work['agent_id']
                    or row[2] != self.work['soul_revision'] or row[2] != row[3]
                    or time.monotonic() >= budget_end):
                raise PermissionError('Terminal reporting authority ended')
        try:
            with connect_closing(self.service.db_path) as conn:
                pending = conn.execute("SELECT source_id FROM agent_native_progress WHERE run_id=? AND agent_id=? AND status='pending' ORDER BY created_at,operation_id",
                                       (self.work['id'], self.work['agent_id'])).fetchall()
                if not pending:
                    return
                validate(conn)
                binding = conn.execute('SELECT binding_id FROM agent_native_work_runs WHERE id=?', (self.work['id'],)).fetchone()[0]
                if not binding:
                    return
                with open_planning(db_path=self.service.db_path, home=self.service.home,
                                   agent_id=self.work['agent_id'], binding_id=binding, validate=validate) as planning:
                    for (source_id,) in pending:
                        progress.deliver(conn, planning, validate, source_id)
        except Exception as exc:
            _log.warning('Terminal reporting remains pending or uncertain (%s)', type(exc).__name__)

    def finish(self, conn, frame):
        dead = self.host.force_stop(timeout=2)
        with write_txn(conn):
            current = state.read_work(conn,self.work['agent_id'])
            if current['state'] in state.TERMINAL or self.stopped.is_set():
                return
            try:
                self.validate(conn)
                authorized = True
            except PermissionError:
                authorized = False
            if current['state']=='stopping' or not authorized:
                revision = conn.execute(
                    'SELECT w.soul_revision,a.soul_revision FROM agent_native_work_runs w '
                    'JOIN agent_native_agents a ON a.id=w.agent_id WHERE w.id=?',
                    (self.work['id'],),
                ).fetchone()
                superseded = bool(revision and revision[0] != revision[1])
                target = ('interrupted' if superseded else 'paused') if dead else 'unknown'
                summary = ('Purpose changed; obsolete work was stopped.' if superseded and dead else
                           'Work stopped or its execution authority ended.' if dead else
                           'Worker exit could not be confirmed.')
                conn.execute('UPDATE agent_native_work_runs SET state=?,stop_requested=1,summary=?,finished_at=? WHERE id=?',
                             (target,summary,_now(),self.work['id']))
                state.event(conn,self.work['id'],'work.'+target,summary)
                return
            results = [result for result in current['results'] if result['run_id'] == self.work['id']]
            if (dead and frame.get('type') == 'turn.end'
                    and frame.get('limit_reached') == 'model_steps'
                    and current['model_calls'] >= current['limits']['max_iterations']):
                target = 'limit_reached' if _recoverable_interruption(conn, self.work['id']) else 'unknown'
                summary = 'Work reached its model-step limit. Recorded work is retained.'
                if target == 'unknown':
                    summary += ' An unsettled operation must be reconciled before continuing.'
                conn.execute('UPDATE agent_native_work_runs SET state=?,stop_requested=1,summary=?,finished_at=? WHERE id=?',
                             (target, summary, _now(), self.work['id']))
                state.event(conn, self.work['id'], 'work.' + target, summary)
                return
            success = dead and frame.get('type')=='turn.end' and bool(results)
            target = ('completed' if success else
                      ('retryable_failure' if dead and _cadence_can_retry(
                          conn, self.work['agent_id'], self.work['id']) else
                       'failed' if dead else 'unknown'))
            if success:
                summary = self.final_text or results[0]['summary']
            elif not dead:
                summary = 'Worker exit could not be confirmed. Saved outputs and reports are retained.'
            else:
                summary = ('The run ended without a recorded result.' if not results else
                           'The worker failed after recording a result.')
                if current['outputs']:
                    summary += ' Saved outputs remain available.'
            conn.execute('UPDATE agent_native_work_runs SET state=?,stop_requested=1,summary=?,finished_at=? WHERE id=?',
                         (target,summary,_now(),self.work['id']))
            if success:
                required = [result for result in results
                            if result['review']['required'] and result['acceptance'] == 'not_evaluated']
                event_summary = ('Deliverable recorded; owner review is required before dependent work continues.'
                                 if required else
                                 'Result recorded; this attempt finished and automatic work may continue.')
            else:
                event_summary = summary[:1000]
            state.event(conn,self.work['id'],'work.'+target,event_summary)

    def fail(self, reason):
        dead = self.host.force_stop(timeout=2)
        with connect_closing(self.service.db_path) as conn, write_txn(conn):
            current = state.read_work(conn,self.work['agent_id'])
            if current['state'] not in state.TERMINAL:
                revision = conn.execute(
                    'SELECT w.soul_revision,a.soul_revision FROM agent_native_work_runs w '
                    'JOIN agent_native_agents a ON a.id=w.agent_id WHERE w.id=?',
                    (self.work['id'],),
                ).fetchone()
                superseded = bool(revision and revision[0] != revision[1])
                target = ('interrupted' if dead and superseded else
                          'retryable_failure' if dead and _cadence_can_retry(
                    conn, self.work['agent_id'], self.work['id']) else 'failed') if dead else 'unknown'
                message = ('Purpose changed; obsolete work was stopped.' if superseded else
                           'Work stopped; '+reason+'. Inspect activity before retrying any uncertain operation.')
                conn.execute('UPDATE agent_native_work_runs SET state=?,error=?,finished_at=? WHERE id=?',
                             (target,None if superseded else message,_now(),self.work['id']))
                state.event(conn,self.work['id'],'work.'+target,message)


class WorkService:
    def __init__(self,db_path,home):
        self.db_path,self.home = Path(db_path),Path(home).resolve()
        self.stopped = threading.Event()
        self.runs = {}
        # Unknown runs may need a host-side Plane read before cadence can
        # continue. Keep that reconciliation bounded while Plane is unavailable;
        # this is deliberately process-local because it is only a read-back
        # throttle, never the source of truth for a mutation receipt.
        self._recovery_next = {}
        self._recovery_observations = {}
        self.thread = threading.Thread(target=self.run,name='agent-native-work',daemon=True)

    @staticmethod
    def _unknown_effects(conn, run_id):
        """Return unsettled Plane operation IDs for one unknown run.

        The worker's effect result can be absent even when Plane committed the
        mutation. The protected journal is the authority for whether a read-back
        is still needed; local result rows and progress receipts are both
        included because terminal reporting is a Plane comment mutation too.
        """
        rows = conn.execute(
            "SELECT DISTINCT e.operation_id "
            "FROM agent_native_work_effects e "
            "LEFT JOIN agent_native_plane_mutations m ON m.operation_id=e.operation_id "
            "WHERE e.run_id=? AND e.result IS NULL "
            "AND (m.status IS NULL OR m.status IN ('pending','unknown')) "
            "UNION SELECT DISTINCT p.operation_id "
            "FROM agent_native_progress p "
            "WHERE p.run_id=? AND p.status IN ('pending','unknown')",
            (run_id, run_id),
        ).fetchall()
        return [row[0] for row in rows if isinstance(row[0], str)]

    def _reconcile_unknown_run(self, run):
        """Read back unknown Plane effects without replaying them.

        A worker that cannot prove its exit must not be replaced blindly. Once
        every external effect has a confirmed or rejected journal receipt,
        ``reconcile_confirmed_unknown`` releases the old bounded attempt and the
        normal cadence path can queue a fresh one. A failed read-back stays a
        framework reconciliation state, with no model call and no owner click.
        """
        from agent_native.plane_recovery import PlaneRecoveryUnresolved
        from agent_native.plane_reads import PlaneReadError
        from agent_native.plane_writes import PlaneWriteError
        from agent_native.startup import _row as setup_row
        from agent_native.writer_planning import open_planning
        from agent_native import work_state

        with connect_closing(self.db_path) as conn:
            row = conn.execute(
                'SELECT agent_id,state,soul_revision,binding_id FROM agent_native_work_runs '
                'WHERE id=?', (run['run_id'],)
            ).fetchone()
            if not row or row[1] != 'unknown' or not row[3]:
                return False
            operation_ids = self._unknown_effects(conn, run['run_id'])
            if not operation_ids:
                return False
            setup = setup_row(conn, row[0])
            if not setup or setup['status'] != 'ready':
                return False
            expected_agent, expected_revision, binding_id = row[0], row[2], row[3]

        def validate(active_conn):
            current = active_conn.execute(
                'SELECT w.agent_id,w.state,w.stop_requested,w.soul_revision,'
                'a.soul_revision,w.binding_id FROM agent_native_work_runs w '
                'JOIN agent_native_agents a ON a.id=w.agent_id WHERE w.id=?',
                (run['run_id'],),
            ).fetchone()
            if (not current or current[0] != expected_agent or current[1] != 'unknown'
                    or current[2] != 1 or current[3] != expected_revision
                    or current[4] != expected_revision or current[5] != binding_id):
                raise PermissionError('Unknown work run is no longer eligible for reconciliation')

        confirmed, unresolved = 0, None
        try:
            with open_planning(
                    db_path=self.db_path, home=self.home, agent_id=expected_agent,
                    binding_id=binding_id, validate=validate) as planning:
                for operation_id in operation_ids[:32]:
                    try:
                        planning.recover(operation_id)
                        confirmed += 1
                    except (PlaneRecoveryUnresolved, PlaneReadError, PlaneWriteError,
                            PermissionError, KeyError, ValueError) as exc:
                        unresolved = type(exc).__name__
        except (PlaneRecoveryUnresolved, PlaneReadError, PlaneWriteError,
                PermissionError, KeyError, ValueError, OSError) as exc:
            unresolved = type(exc).__name__

        with connect_closing(self.db_path) as conn:
            # Terminal/progress receipts keep a local delivery row in
            # ``pending`` or ``unknown`` until the delivery helper sees its
            # acknowledgement. Recovery already proved the journal outcome;
            # project that proof into the progress row so it cannot keep the
            # entire run blocked forever.
            from agent_native.plane_write_journal import MutationJournal
            journal = MutationJournal(conn)
            for operation_id in operation_ids:
                try:
                    receipt = journal.get(operation_id, actor=OWNER)
                except KeyError:
                    continue
                if receipt['status'] == 'confirmed':
                    conn.execute(
                        "UPDATE agent_native_progress SET status='confirmed',"
                        'comment_id=COALESCE(comment_id,?) WHERE operation_id=? '
                        "AND status IN ('pending','unknown')",
                        (receipt.get('resource_id'), operation_id),
                    )
            released = work_state.reconcile_confirmed_unknown(conn, expected_agent)
            if released:
                self._recovery_observations.pop(run['run_id'], None)
                return True
            observation = unresolved or ('recovery_budget_exceeded' if len(operation_ids) > 32 else 'effect_not_confirmed')
            if self._recovery_observations.get(run['run_id']) != observation:
                work_state.event(
                    conn, run['run_id'], 'work.recovery_unresolved',
                    'Automatic Plane reconciliation could not confirm every effect '
                    f'({observation}); no mutation was resent.',
                )
                self._recovery_observations[run['run_id']] = observation
        return False

    def reconcile_unknown_runs(self):
        """Attempt at most one bounded read-back per unknown run per cooldown."""
        now = time.monotonic()
        with connect_closing(self.db_path) as conn:
            rows = conn.execute(
                "SELECT id,agent_id FROM agent_native_work_runs WHERE state='unknown' "
                "AND binding_id IS NOT NULL ORDER BY rowid"
            ).fetchall()
        for run_id, agent_id in rows:
            if now < self._recovery_next.get(run_id, 0):
                continue
            self._recovery_next[run_id] = now + 5
            self._reconcile_unknown_run({'run_id': run_id, 'agent_id': agent_id})

    def start(self):
        # Never replay an interrupted process. Cadence may start a fresh attempt
        # only when every prior effect has a settled receipt.
        with connect_closing(self.db_path) as conn, write_txn(conn):
            for (run_id,) in conn.execute("SELECT id FROM agent_native_work_runs WHERE state IN ('preparing','running','stopping')").fetchall():
                recoverable = _recoverable_interruption(conn, run_id)
                target = 'interrupted' if recoverable else 'unknown'
                summary = ('Service restarted during work. The stopped process will not be replayed; cadence may start a fresh attempt.'
                           if recoverable else 'Service restarted during work; an unsettled effect requires owner review.')
                conn.execute("UPDATE agent_native_work_runs SET state=?,stop_requested=1,summary=?,finished_at=? WHERE id=?",
                             (target,summary,_now(),run_id))
                state.event(conn,run_id,'work.'+target,summary)
        self.thread.start()
        return self

    def stop(self):
        self.stopped.set()
        self.thread.join(timeout=3)
        for run in list(self.runs.values()):
            run.stop('Service stopped this work run; cadence may continue with a fresh attempt.', recoverable=True)

    def tick(self):
        for run_id,run in list(self.runs.items()):
            if run.ended.is_set():
                self.runs.pop(run_id,None)
                continue
            try:
                with connect_closing(self.db_path) as conn:
                    run.validate(conn)
            except PermissionError:
                with connect_closing(self.db_path) as conn:
                    revision = conn.execute(
                        'SELECT soul_revision FROM agent_native_agents WHERE id=?',
                        (run.work['agent_id'],),
                    ).fetchone()
                superseded = bool(revision and revision[0] != run.work['soul_revision'])
                run.stop(
                    'Purpose changed; obsolete work was stopped.' if superseded
                    else 'Work paused or its execution authority ended.',
                    superseded=superseded,
                )
        # Resolve any lost Plane responses before cadence evaluates readiness.
        # This is host-side evidence reconciliation, not a model run or a
        # replay of the original mutation.
        self.reconcile_unknown_runs()
        with connect_closing(self.db_path) as conn:
            from agent_native.cadence import queue_due, queue_revised_purposes
            queue_revised_purposes(conn)
            queue_due(conn,busy_agents={run.work['agent_id'] for run in self.runs.values()})
            rows = conn.execute("SELECT w.agent_id FROM agent_native_work_runs w JOIN agent_native_setup s ON s.agent_id=w.agent_id "
                                "WHERE w.state='queued' AND s.status='ready' "
                                "AND w.agent_id NOT IN (SELECT agent_id FROM agent_native_first_builder WHERE launch_state!='active')").fetchall()
            for (agent_id,) in rows:
                if self.stopped.is_set():
                    break
                with write_txn(conn):
                    work = state.read_work(conn,agent_id)
                    if work['state']!='queued':
                        continue
                    from agent_native.model_settings import snapshot_attempt
                    work['model_selection'] = snapshot_attempt(conn, agent_id, 'work', work['id'])
                    from agent_native.autonomy import snapshot_attempt as snapshot_autonomy, policy
                    admission_id = str(uuid4())
                    work['autonomy'] = snapshot_autonomy(conn, agent_id, work['id'], admission_id)
                    work['autonomy']['policy'] = policy(
                        work['autonomy']['level'], work['autonomy']['require_owner_review'])
                    from agent_native.first_builder import active_runtime
                    try:
                        work['runtime_release'] = str(active_runtime(conn, agent_id))
                    except PermissionError:
                        pass
                    conn.execute("UPDATE agent_native_work_runs SET state='preparing',started_at=? WHERE id=?",(_now(),work['id']))
                    state.event(conn,work['id'],'work.preparing','Reading the prepared project before starting the native worker.')
                run = _Run(self,work)
                self.runs[work['id']] = run
                run.thread.start()

    def run(self):
        while not self.stopped.is_set():
            try:
                self.tick()
            except Exception as exc:
                _log.warning('Work service scan failed (%s)',type(exc).__name__)
            self.stopped.wait(.2)


def start_service():
    from hermes_constants import get_hermes_home
    from hermes_cli.kanban_db import kanban_db_path
    return WorkService(kanban_db_path(board='default'),get_hermes_home()/'agent-native').start()
