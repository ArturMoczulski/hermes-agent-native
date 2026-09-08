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
        self.host = HostSupervisor(registry_path=service.home / 'work-hosts' / (work['id']+'.json'),
            env={'HERMES_HOME':str(service.home.parent),'HERMES_MANAGED_COMPUTE_HOST':'1'},
            expected_hermes_home=str(service.home.parent), rpc_sink=self.inbox.put,
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

    def stop(self, reason='Owner paused this work.'):
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
                    target = ('limit_reached' if timed_out else 'paused') if dead else 'unknown'
                    conn.execute('UPDATE agent_native_work_runs SET state=?,stop_requested=1,finished_at=?,summary=? WHERE id=?',
                                 (target,_now(),reason,self.work['id']))
                    state.event(conn,self.work['id'],'work.'+target,reason if dead else 'Worker stop could not be confirmed.')
        return dead

    def _effect(self, conn, planning, params):
        self.validate(conn)
        if params.get('run_id') != self.work['id']:
            raise PermissionError('Work identity changed')
        tool, args, call_id = params.get('tool'), params.get('arguments'), params.get('tool_call_id')
        if (tool not in ('plane_resource_inspect','plane_operation_execute','output_publish','output_read','result_record','work_item_select','progress_report','work_feedback','work_question','work_comments')
                or not isinstance(args,dict) or not isinstance(call_id,str) or not 1 <= len(call_id) <= 256):
            raise PermissionError('Unsupported work effect')
        fingerprint = hashlib.sha256(json.dumps([tool,args],sort_keys=True).encode()).hexdigest()
        with write_txn(conn):
            self.validate(conn)
            old = conn.execute('SELECT operation_id,fingerprint,result FROM agent_native_work_effects '
                               'WHERE run_id=? AND call_id=?',(self.work['id'],call_id)).fetchone()
            if old:
                if old[1] != fingerprint:
                    raise PermissionError('Native tool call was reused with different input')
                if old[2] is not None:
                    return json.loads(old[2])
                operation_id = old[0]
            else:
                operation_id = str(uuid4())
                conn.execute('INSERT INTO agent_native_work_effects(run_id,call_id,operation_id,fingerprint) VALUES(?,?,?,?)',
                             (self.work['id'],call_id,operation_id,fingerprint))
        if tool == 'plane_resource_inspect':
            result = planning.inspect(args)
        elif tool == 'plane_operation_execute':
            if set(args) != {'operation','arguments'}:
                raise ValueError('Planning effect requires operation and arguments')
            if args['operation'] == 'comment.create':
                raise ValueError('Use progress_report for managed progress comments')
            from agent_native.plane_writes import PlaneWriteError, PlaneWriteConflict
            try:
                result = planning.execute(operation_id,args['operation'],args['arguments'])
            except PlaneWriteError as exc:
                if isinstance(exc, PlaneWriteConflict) and exc.outcome == 'rejected':
                    # A known pre-write rejection is task data, not revocation.
                    # Retain this call's receipt; a fresh decision needs a new call.
                    result = {'status':'conflict','operation_id':operation_id,
                              'write_attempted':False,
                              'message':'Plane changed or the requested relationship conflicts with current state. No write was sent. Inspect the affected resource and current relationships, then reassess the task before issuing a new operation. Do not repeat stale arguments.'}
                    state.event(conn,self.work['id'],'work.conflict',
                                'Plane rejected '+args['operation']+' before writing; fresh inspection required.')
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
        elif tool == 'work_item_select':
            from agent_native.work_focus import select
            result = select(conn, validate=self.validate, inspect=planning.inspect,
                            agent_id=self.work['agent_id'], run_id=self.work['id'],
                            call_id=call_id, arguments=args)
            from agent_native.progress import deliver
            deliver(conn, planning, self.validate, result['selection_id'])
        elif tool == 'output_read':
            from agent_native.output_read import read_chunk
            result = read_chunk(conn, agent_id=self.work['agent_id'], workspace=self.workspace, arguments=args)
        elif tool == 'output_publish':
            from agent_native.output_store import publish
            from agent_native import progress
            base = progress.public_base()
            required = {'title','content','item_id','format'}
            if not required <= set(args) or set(args) - required - {'output_id'}:
                raise ValueError('Output requires title, content, item and format')
            planning.inspect({'kind':'item','resource_id':args['item_id']})
            result = publish(conn,validate=self.validate,workspace=self.workspace,
                             agent_id=self.work['agent_id'],run_id=self.work['id'],call_id=call_id,
                             record_progress=lambda c, r: progress.output_saved(c, r, base), **args)
            progress.deliver(conn, planning, self.validate, f"output:{result['output_id']}:{result['version']}")
        else:
            from agent_native.result_store import record
            from agent_native import progress
            base = progress.public_base()
            if 'item_id' not in args:
                raise ValueError('Result requires an assignment')
            observation = planning.inspect({'kind':'item','resource_id':args['item_id']})
            result = record(conn,validate=self.validate,workspace=self.workspace,
                            agent_id=self.work['agent_id'],run_id=self.work['id'],call_id=call_id,
                            observation=observation,arguments=args,
                            record_progress=lambda c, r: progress.result_recorded(c, r, base))
            progress.deliver(conn, planning, self.validate, 'result:'+result['id'])
        with write_txn(conn):
            # Keep honest receipts for an effect already sent even if Pause raced
            # its response. No subsequent effect is admitted after a stop.
            conn.execute('UPDATE agent_native_work_effects SET result=? WHERE run_id=? AND call_id=?',
                         (json.dumps(result),self.work['id'],call_id))
            summary = (('Read saved output: '+result['title']) if tool=='output_read' else
                       ('Saved output: '+result['title']) if tool=='output_publish' else
                       ('Recorded result: '+result['summary']) if tool=='result_record' else
                       ('Progress report: '+result['status']) if tool=='progress_report' else
                       ('Plane conflict: fresh inspection required' if result.get('status')=='conflict' else
                        'Plane: '+args.get('operation','inspected '+args.get('kind','resource'))))
            if tool != 'work_item_select':
                # Selection and its event commit together; receipt recovery must
                # not emit a second change or make an old item current again.
                state.event(conn,self.work['id'],'work.effect',summary)
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
                    from agent_native.questions import recent as recent_questions
                    snapshot['previous_results'] = list_results(conn,root['id'])[:10]
                    snapshot['saved_outputs'] = list_outputs(conn,root['id'])[:10]
                    snapshot['saved_output_excerpts'] = []
                    from agent_native.output_store import read_output
                    for output in snapshot['saved_outputs'][:3]:
                        planning.inspect({'kind':'item','resource_id':output['item_id']})
                        saved = read_output(conn,root['id'],output['output_id'],output['version'],workspace=self.workspace)
                        snapshot['saved_output_excerpts'].append({'output_id':saved['output_id'],'version':saved['version'],
                            'content':saved['content'][:8000],'truncated':len(saved['content'])>8000})
                    snapshot['questions'] = recent_questions(conn,root['id'])
                    snapshot['continuation_note'] = 'Review earlier results and outputs; do not repeat finished work. Read work_feedback and current Plane comments with work_comments before substantive work. Waiting is a valid result; do not invent new work.'
                    initial = ('Review your protected purpose and current project. Continue useful work, ask a scoped question or record a waiting result when appropriate. Use the supplied planning skill. '
                               'Create or refine a short project brief, an undated outcome cycle and an actionable task with acceptance criteria. '
                               'Choose useful work appropriate to your purpose and the supplied material. Use work_item_select before '
                               'substantive work and whenever you switch tasks. The framework posts a work-selection progress comment; '
                               'do not duplicate that start update. Use progress_report for meaningful checkpoints, details and blockers as you work. '
                               'Owner verbosity controls delivery, and direct comment.create is not available to this worker. '
                               'When clarification is needed, use work_question on the selected item and reuse its stable topic; '
                               'read answers by question_id. Never treat a missing answer as permission. Do independent work or record a waiting result instead of polling repeatedly. '
                               'Call work_feedback with empty arguments before substantive work and publication to read owner direction. '
                               'Apply it within current purpose and grants, then report handling with work_feedback; never claim acceptance. '
                               'Save any produced text or Markdown '
                               'with output_publish; use output_read to read complete prior versions when excerpts are truncated. Use output_id only when revising an existing output. The host reports saved outputs and result records in Plane; '
                               'do not duplicate these notifications with artifact.record or rewrite the task description to announce completion. '
                               'Inspect the task and use result_record to report its outcome and evaluation with saved output version references. '
                               'Useful discovery, a plan change, waiting for input or a blocker may have an empty outputs list. '
                               'External links are unverified references, never proof of saved content or successful actions. '
                               'Leave the task nonterminal for owner review; '
                               'terminal task acceptance is not available in this increment. Explain any blocker. Stop after this bounded attempt; '
                               'do not invent approval or schedule another run.\nCurrent planning state (work data):\n'+json.dumps(snapshot)+
                               '\nSupported Plane operation argument contracts:\n'+json.dumps({k: v for k, v in _CONTRACTS.items() if k != 'comment.create'}))
                    skill = (Path(__file__).resolve().parents[1] / 'skills/productivity/plane-project-management/SKILL.md').read_text()
                    attempt = {'run_id':self.work['id'],'agent_id':root['id'],'soul_revision':root['soul_revision'],
                               'name':root['name'],'purpose':root['purpose'],'workspace':str(self.workspace),
                               'session_id':self.work['session_id'],'native_db':str(self.service.home.parent/'state.db'),
                               'deadline_monotonic':self.deadline,'max_iterations':self.work['limits']['max_iterations'],
                               'max_tokens':8192,'initial_context':initial,'skill_text':skill}
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
                                reply = {'ok':False,'revoked':isinstance(exc,PermissionError),
                                         'error':'Work operation could not be admitted or confirmed ('+type(exc).__name__+').'}
                                with write_txn(conn):
                                    state.event(conn,self.work['id'],'work.operation_failed',reply['error'])
                            self.host.send_work_result(frame['id'],reply)
                        elif method == 'event' and params.get('type') == 'message.complete':
                            self.final_text = str(params.get('payload',{}).get('text',''))[:16000]
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
                target = 'paused' if dead else 'unknown'
                summary = ('Work stopped or its execution authority ended.' if dead else
                           'Worker exit could not be confirmed.')
                conn.execute('UPDATE agent_native_work_runs SET state=?,stop_requested=1,summary=?,finished_at=? WHERE id=?',
                             (target,summary,_now(),self.work['id']))
                state.event(conn,self.work['id'],'work.'+target,summary)
                return
            results = [result for result in current['results'] if result['run_id'] == self.work['id']]
            success = dead and frame.get('type')=='turn.end' and bool(results)
            target = 'completed' if success else ('failed' if dead else 'unknown')
            if success:
                summary = self.final_text or results[0]['summary']
            elif not dead:
                summary = 'Worker exit could not be confirmed. Saved outputs and reports are retained.'
            else:
                summary = ('The run ended without a recorded result.' if not results else
                           'The worker failed after recording a result.')
                if current['outputs']:
                    summary += ' Saved outputs remain available.'
            conn.execute('UPDATE agent_native_work_runs SET state=?,summary=?,finished_at=? WHERE id=?',
                         (target,summary,_now(),self.work['id']))
            state.event(conn,self.work['id'],'work.'+target,
                        'Result recorded; attempt finished. Work acceptance remains separate.' if success else summary[:1000])

    def fail(self, reason):
        dead = self.host.force_stop(timeout=2)
        with connect_closing(self.service.db_path) as conn, write_txn(conn):
            current = state.read_work(conn,self.work['agent_id'])
            if current['state'] not in state.TERMINAL:
                target = 'failed' if dead else 'unknown'
                message = 'Work stopped; '+reason+'. Inspect activity before retrying any uncertain operation.'
                conn.execute('UPDATE agent_native_work_runs SET state=?,error=?,finished_at=? WHERE id=?',
                             (target,message,_now(),self.work['id']))
                state.event(conn,self.work['id'],'work.'+target,message)


class WorkService:
    def __init__(self,db_path,home):
        self.db_path,self.home = Path(db_path),Path(home).resolve()
        self.stopped = threading.Event()
        self.runs = {}
        self.thread = threading.Thread(target=self.run,name='agent-native-work',daemon=True)

    def start(self):
        # Never replay uncertain work across a service restart.
        with connect_closing(self.db_path) as conn, write_txn(conn):
            for (run_id,) in conn.execute("SELECT id FROM agent_native_work_runs WHERE state IN ('preparing','running','stopping')").fetchall():
                conn.execute("UPDATE agent_native_work_runs SET state='unknown',stop_requested=1,summary=? WHERE id=?",
                             ('Service restarted during work; outcome requires review.',run_id))
                state.event(conn,run_id,'work.unknown','Service restarted during work; no automatic retry.')
        self.thread.start()
        return self

    def stop(self):
        self.stopped.set()
        self.thread.join(timeout=3)
        for run in list(self.runs.values()):
            run.stop('Service stopped this work run.')

    def tick(self):
        for run_id,run in list(self.runs.items()):
            if run.ended.is_set():
                self.runs.pop(run_id,None)
                continue
            try:
                with connect_closing(self.db_path) as conn:
                    run.validate(conn)
            except PermissionError:
                run.stop('Work paused or its execution authority ended.')
        with connect_closing(self.db_path) as conn:
            from agent_native.cadence import queue_due
            queue_due(conn,busy_agents={run.work['agent_id'] for run in self.runs.values()})
            rows = conn.execute("SELECT w.agent_id FROM agent_native_work_runs w JOIN agent_native_setup s ON s.agent_id=w.agent_id "
                                "WHERE w.state='queued' AND s.status='ready'").fetchall()
            for (agent_id,) in rows:
                if self.stopped.is_set():
                    break
                with write_txn(conn):
                    work = state.read_work(conn,agent_id)
                    if work['state']!='queued':
                        continue
                    from agent_native.model_settings import snapshot_attempt
                    work['model_selection'] = snapshot_attempt(conn, agent_id, 'work', work['id'])
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
