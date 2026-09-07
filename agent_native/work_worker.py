"""One private ComputeHost work turn using Hermes's native engine and SessionDB."""
from pathlib import Path
import time

from agent.work_policy import TOOL_NAMES, WorkContext, bind  # noqa: F401


def run_turn(host, frame):
    from run_agent import AIAgent
    from hermes_state import SessionDB
    from agent_native.model_runtime import resolve_selection

    data = dict(frame['work_attempt'])
    context = WorkContext(**data, request=host.request_work)
    sid = str(frame.get('sid') or '')
    request_id = str(frame.get('request_id') or '')
    if sid != context.session_id or frame.get('session_key') != sid or request_id != context.run_id:
        raise PermissionError('Work bootstrap does not match its native session')
    context.admit('persist')
    db = SessionDB(Path(context.native_db))
    agent = None

    def emit(kind, payload):
        context.check()
        host._transport.write({'jsonrpc': '2.0', 'method': 'event',
                               'params': {'type': kind, 'session_id': sid, 'payload': payload}})

    def tool_start(call_id, name, arguments):
        emit('tool.start', {'tool_call_id': call_id, 'tool': name, 'args': arguments})

    def tool_complete(call_id, name, arguments, result):
        emit('tool.complete', {'tool_call_id': call_id, 'tool': name, 'args': arguments, 'result': result})

    def stream(text):
        emit('message.delta', {'text': text})

    try:
        db.ensure_session(sid, source='agent-native-work', cwd=context.workspace)
        if db.get_session_title_source(sid) != 'user':
            title = ' '.join(context.name.split())[:60] + ' work'
            try:
                db.set_session_title(sid, title)
            except ValueError:
                db.set_session_title(sid, db.get_next_title_in_lineage(title))
        history = db.get_messages_as_conversation(sid, repair_alternation=True)
        selection = frame.get('model_selection')
        if (not isinstance(selection, dict) or selection.get('agent_id') != context.agent_id
                or selection.get('kind') != 'work' or selection.get('attempt_id') != context.run_id):
            raise PermissionError('Work bootstrap has no matching admitted model selection')
        model, runtime = resolve_selection(selection)
        with bind(context):
            agent = AIAgent(model=model, provider=runtime.get('provider'), base_url=runtime.get('base_url'),
                api_key=runtime.get('api_key'), api_mode=runtime.get('api_mode'),
                credential_pool=runtime.get('credential_pool'), requested_provider=runtime.get('requested_provider'),
                capabilities=runtime.get('capabilities'), session_id=sid, session_db=db,
                platform='agent-native-work', enabled_toolsets=[], skip_context_files=True,
                load_soul_identity=False, skip_memory=True, skip_background_review=True,
                save_trajectories=False, checkpoints_enabled=False, quiet_mode=True,
                max_iterations=context.max_iterations, max_tokens=context.max_tokens,
                run_budget_seconds=max(.01, context.deadline_monotonic - time.monotonic()),
                tool_start_callback=tool_start, tool_complete_callback=tool_complete,
                stream_delta_callback=stream,
                status_callback=lambda text: emit('status.update', {'text': str(text), 'kind': 'status'}))
            if getattr(agent, '_work_context', None) is not context:
                raise PermissionError('Native engine did not retain its work authority')
            emit('work.started', {'run_id': context.run_id, 'agent_id': context.agent_id})
            host._reply('turn.started', sid, request_id, started_ns=time.perf_counter_ns())
            result = agent.run_conversation(context.initial_context, conversation_history=history,
                                            task_id=context.run_id, persist_user_platform_id=context.run_id)
            context.admit('persist', agent)
            if result.get('error') or result.get('failed') or result.get('interrupted'):
                raise RuntimeError('Managed native work did not complete successfully')
            emit('message.complete', {'status': 'complete', 'text': result.get('final_response') or '',
                                      'run_id': context.run_id})
            host._reply('turn.end', sid, request_id, ended_ns=time.perf_counter_ns(),
                        interrupted=bool(result.get('interrupted')))
    finally:
        db.close()
