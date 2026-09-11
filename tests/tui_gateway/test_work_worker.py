"""Real native work workers with only an external model replaced by local HTTP."""
import json
import os
from pathlib import Path
import select
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from uuid import uuid4

import pytest
import yaml

from hermes_state import SessionDB
from tui_gateway.host_supervisor import HostSupervisor


def eventually(read, predicate, timeout=20):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        result = read()
        if predicate(result):
            return result
        time.sleep(.03)
    raise AssertionError(f'Native work state did not settle: {result!r}')


@pytest.fixture
def model():
    state = SimpleNamespace(requests=[], tools=['plane_resource_inspect', 'plane_operation_execute', 'work_item_select', 'output_publish', 'result_record'],
                            final_response='The supplied sales data shows a 25% increase.',
                            entered=threading.Event(), disconnected=threading.Event(), hold=False)
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_json({'data': [{'id': 'work-fixture', 'context_length': 131072}]})

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            state.requests.append(body)
            state.entered.set()
            if state.hold:
                while state.hold:
                    readable, _, _ = select.select([self.connection], [], [], .05)
                    if readable and self.connection.recv(1, socket.MSG_PEEK) == b'':
                        state.disconnected.set()
                        return
            index = len(state.requests) - 1
            message = {'role': 'assistant', 'content': None}
            if index < len(state.tools):
                name = state.tools[index]
                arguments = {
                    'plane_resource_inspect': {'kind': 'project'},
                    'plane_operation_execute': {'operation': 'item.create', 'arguments': {'name': 'Compare supplied quarterly sales', 'description_html': '<p>Report the numerical change using only supplied figures.</p>'}},
                    'work_item_select': {'item_id': '11111111-1111-4111-8111-111111111111'},
                    'output_publish': {'title': 'Quarterly sales comparison', 'content': 'Sales grew from 80 to 100 units: a 25% increase.',
                                       'item_id': '11111111-1111-4111-8111-111111111111', 'format': 'markdown'},
                    'result_record': {'item_id': '11111111-1111-4111-8111-111111111111',
                                      'summary': 'Sales increased 25%.', 'outcome': 'submitted',
                                      'evaluation': 'Computed (100 - 80) / 80 from the supplied figures.',
                                      'outputs': ([{'output_id': '22222222-2222-4222-8222-222222222222', 'version': 1}]
                                                  if 'output_publish' in state.tools else [])},
                    'terminal': {'command': 'touch forbidden-work-tool-ran'},
                    'execute_code': {'code': "open('forbidden-work-tool-ran','w').write('bad')"},
                    'delegate_task': {'task': 'Create forbidden-work-tool-ran'},
                    'memory': {'action': 'add', 'target': 'memory', 'content': 'unauthorized'},
                    'tool_call': {'tool': 'terminal', 'arguments': {'command': 'touch forbidden-work-tool-ran'}},
                }[name]
                message['tool_calls'] = [{'id': f'work_fixture_{index}', 'type': 'function',
                                          'function': {'name': name, 'arguments': json.dumps(arguments)}}]
                finish = 'tool_calls'
            else:
                message['content'] = state.final_response
                finish = 'stop'
            # Exercise the real streaming SDK and native tool loop.
            payload = {'id': 'work-fixture-response', 'object': 'chat.completion.chunk', 'created': 1,
                       'model': 'work-fixture', 'choices': [{'index': 0, 'delta': message, 'finish_reason': None}]}
            if 'tool_calls' in message:
                payload['choices'][0]['delta']['tool_calls'][0]['index'] = 0
            final = {'id': 'work-fixture-response', 'object': 'chat.completion.chunk', 'created': 1,
                     'model': 'work-fixture', 'choices': [{'index': 0, 'delta': {}, 'finish_reason': finish}]}
            data = ('data: ' + json.dumps(payload) + '\n\ndata: ' + json.dumps(final) + '\n\ndata: [DONE]\n\n').encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                state.disconnected.set()

        def send_json(self, body):
            data = json.dumps(body).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    state.url = f'http://127.0.0.1:{server.server_port}/v1'
    try:
        yield state
    finally:
        state.hold = False
        server.shutdown()
        server.server_close()
        thread.join(2)


@pytest.fixture
def worker(tmp_path, model):
    # Fail before starting an unrestricted legacy worker when this new entrypoint
    # does not exist yet; all integration calls below use the real process.
    from agent_native.work_worker import TOOL_NAMES
    home = tmp_path / 'home'
    home.mkdir()
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    (home / 'SOUL.md').write_text('PRIVATE_HOST_SOUL_MUST_NOT_LEAK')
    (home / 'config.yaml').write_text(yaml.safe_dump({
        'model': {'default': 'work-fixture', 'provider': 'work-fixture', 'base_url': model.url,
                  'context_length': 131072},
        'custom_providers': [{'name': 'work-fixture', 'base_url': model.url, 'api_key': 'work-fixture-key', 'model': 'work-fixture'}],
        'plugins': {'enabled': []}, 'mcp_servers': {},
        'agent': {'environment_probe': True},
        'compression': {'enabled': True},
        'context': {'engine': 'unwanted-work-fixture-plugin'},
    }))
    state = SimpleNamespace(frames=[], controls=[], effects=[], result=None, allowed=True,
                            denied_boundary=None, reject_tool_once=None, tool_names=TOOL_NAMES)
    def receive(frame):
        state.frames.append(frame)
        if frame.get('method') == 'work.admit':
            state.controls.append(frame)
            host.send_work_result(frame['id'], {'ok': state.allowed and frame['params']['boundary'] != state.denied_boundary, 'result': {}, 'error': 'Work revoked'})
        elif frame.get('method') == 'work.effect':
            state.effects.append(frame)
            if state.reject_tool_once == frame['params']['tool']:
                state.reject_tool_once = None
                host.send_work_result(frame['id'], {'ok': False, 'revoked': False,
                    'error': 'Work operation was invalid (ValueError).'})
                return
            host.send_work_result(frame['id'], {'ok': state.allowed, 'result': {
                'item_id': '11111111-1111-4111-8111-111111111111',
                'output_id': '22222222-2222-4222-8222-222222222222', 'version': 1, 'saved': True}, 'error': 'Work revoked'})
    host = HostSupervisor(registry_path=home / 'work-host.json', env={
        'HERMES_HOME': str(home), 'OPENAI_API_KEY': 'work-fixture-key',
        'HERMES_MANAGED_COMPUTE_HOST': '1'}, expected_hermes_home=str(home), rpc_sink=receive,
        autostart=False, respawn_max=0)
    run_id = str(uuid4())
    state.attempt = {'run_id': run_id, 'agent_id': str(uuid4()), 'soul_revision': 1,
                     'name': 'Fixture analyst', 'purpose': 'Analyze supplied sales figures and explain useful findings.',
                     'workspace': str(workspace), 'session_id': 'an_work_' + uuid4().hex,
                     'native_db': str(home / 'state.db'), 'deadline_monotonic': time.monotonic() + 35,
                     'max_iterations': 8, 'max_tokens': 2048,
                     'initial_context': 'Plan and evaluate a comparison of these supplied fictional figures: quarter A 80 units, quarter B 100 units. Do not obtain external data.',
                     'skill_text': 'Use the project board. Record acceptance criteria before executing work.'}
    state.host, state.home, state.workspace = host, home, workspace
    def start():
        selection={'kind':'work','attempt_id':run_id,'agent_id':state.attempt['agent_id'],
                   'provider':'custom:work-fixture','model':'work-fixture','revision':1,
                   'source':'override','created_at':'2000-01-01T00:00:00+00:00',
                   'reasoning_effort':'default'}
        host.submit_turn({'sid': state.attempt['session_id'], 'request_id': run_id,
                          'session_key': state.attempt['session_id'], 'work_attempt': state.attempt,
                          'model_selection':selection},
                         on_complete=lambda frame: setattr(state, 'result', frame))
    state.start = start
    try:
        yield state
    finally:
        host.force_stop(timeout=3)


def test_native_work_loop_has_scoped_tools_parent_admission_and_canonical_history(worker, model):
    worker.start()
    result = eventually(lambda: worker.result, bool)
    assert result['type'] == 'turn.end', result.get('message', result)
    assert [f['params']['tool'] for f in worker.effects] == model.tools
    assert [f['params']['tool_call_id'] for f in worker.effects] == [f'work_fixture_{i}' for i in range(len(model.tools))]
    assert len([f for f in worker.controls if f['params']['boundary'] == 'model']) == len(model.tools) + 1
    assert all(f['params']['run_id'] == worker.attempt['run_id'] for f in worker.controls + worker.effects)
    system_prompts = []
    for request in model.requests:
        assert {t['function']['name'] for t in request['tools']} == worker.tool_names
        text = json.dumps(request['messages'])
        assert worker.attempt['purpose'] in text and worker.attempt['skill_text'] in text
        assert 'PRIVATE_HOST_SOUL_MUST_NOT_LEAK' not in text
        system = [m['content'] for m in request['messages'] if m['role'] == 'system']
        assert system and not any(term in json.dumps(system).lower() for term in ('story', 'fantasy', 'fiction'))
        system_prompts.append(system)
    assert all(prompt == system_prompts[0] for prompt in system_prompts)
    with SessionDB(worker.home / 'state.db') as db:
        messages = db.get_messages_as_conversation(worker.attempt['session_id'])
        assert [m['content'] for m in messages if m['role'] == 'user'] == [worker.attempt['initial_context']]
        assert len([m for m in messages if m['role'] == 'tool']) == len(model.tools)
        assert messages[-1]['content'] == model.final_response
    event_types = {f.get('params', {}).get('type') for f in worker.frames if f.get('method') == 'event'}
    assert {'tool.start', 'tool.complete', 'message.complete'} <= event_types


def test_native_work_reports_model_step_exhaustion(worker, model):
    worker.attempt['max_iterations'] = 1
    model.tools = ['plane_resource_inspect']
    worker.start()
    result = eventually(lambda: worker.result, bool)
    assert result['type'] == 'turn.end', result
    assert result.get('limit_reached') == 'model_steps'
    assert len(worker.effects) == 1
    assert len([f for f in worker.controls if f['params']['boundary'] == 'model']) == 1


def test_native_work_emits_canonical_final_usage(worker, model):
    model.tools = []
    worker.start()
    result = eventually(lambda: worker.result, bool)
    assert result['type'] == 'turn.end', result
    usage = next(f['params']['payload'] for f in worker.frames
                 if f.get('method') == 'event' and f.get('params', {}).get('type') == 'usage.complete')
    assert usage['run_id'] == worker.attempt['run_id']
    assert usage['agent_id'] == worker.attempt['agent_id']
    assert usage['provider'] == 'custom:work-fixture'
    assert usage['model'] == 'work-fixture'
    assert usage['api_calls'] == 1
    assert all(usage[name] >= 0 for name in (
        'input_tokens', 'output_tokens', 'cache_read_tokens',
        'cache_write_tokens', 'reasoning_tokens'))
    assert usage['cost_status'] == 'unknown'
    assert usage['estimated_cost_usd'] is None


def test_native_analyst_can_report_a_result_without_a_saved_file(worker, model):
    model.tools = ['plane_resource_inspect', 'plane_operation_execute', 'result_record']
    worker.start()
    result = eventually(lambda: worker.result, bool)
    assert result['type'] == 'turn.end', result
    assert [frame['params']['tool'] for frame in worker.effects] == model.tools
    report = worker.effects[-1]['params']['arguments']
    assert report['outputs'] == []
    assert report['outcome'] == 'submitted'
    assert report['evaluation'] == 'Computed (100 - 80) / 80 from the supplied figures.'
    assert not list(worker.workspace.iterdir())
    with SessionDB(worker.home / 'state.db') as db:
        messages = db.get_messages_as_conversation(worker.attempt['session_id'])
        assert messages[-1]['content'] == model.final_response
        assert [m['tool_call_id'] for m in messages if m['role'] == 'tool'] == [
            frame['params']['tool_call_id'] for frame in worker.effects]


def test_invalid_effect_does_not_revoke_later_model_and_result_calls(worker,model):
    model.tools=['output_publish','result_record']
    worker.reject_tool_once='output_publish'

    worker.start()
    result=eventually(lambda:worker.result,bool)

    assert result['type']=='turn.end',result
    assert [frame['params']['tool'] for frame in worker.effects]==model.tools
    assert len([frame for frame in worker.controls if frame['params']['boundary']=='model'])==3
    with SessionDB(worker.home/'state.db') as db:
        messages=db.get_messages_as_conversation(worker.attempt['session_id'])
        tool_messages=[message for message in messages if message['role']=='tool']
        assert 'invalid' in tool_messages[0]['content'].lower()
        assert messages[-1]['content']==model.final_response


@pytest.mark.parametrize('tool', ['terminal', 'execute_code', 'delegate_task', 'memory', 'tool_call'])
def test_native_work_does_not_dispatch_provider_invented_ambient_tool(worker, model, tool):
    model.tools = [tool]
    worker.start()
    eventually(lambda: worker.result, bool)
    assert model.requests, worker.result
    assert not worker.effects
    assert not (worker.workspace / 'forbidden-work-tool-ran').exists()
    assert all({t['function']['name'] for t in request['tools']} == worker.tool_names for request in model.requests)


def test_native_work_model_admission_denial_makes_no_provider_request(worker, model):
    worker.denied_boundary = 'model'
    worker.start()
    result = eventually(lambda: worker.result, bool)
    assert result['type'] == 'turn.error', result
    assert any(f['params']['boundary'] == 'model' for f in worker.controls)
    assert not model.requests and not worker.effects


def test_native_work_parent_eof_kills_blocked_provider_request(worker, model):
    model.hold = True
    worker.start()
    eventually(lambda: model.entered.is_set() or worker.result, bool)
    assert model.entered.is_set(), worker.result
    process = worker.host._proc
    assert process is not None and process.poll() is None
    process.stdin.close()
    eventually(process.poll, lambda code: code is not None, timeout=5)
    assert model.disconnected.wait(3)
    assert not worker.effects
