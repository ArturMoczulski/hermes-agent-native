"""Managed native conversations keep the real Hermes loop inside host authority."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import pytest

from agent_native import identity
from hermes_cli.kanban_db_connect import connect_closing


@pytest.fixture
def provider():
    state = SimpleNamespace(requests=[], before_reply=None, text='I write emerald dragon stories.')
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            state.requests.append(payload)
            if state.before_reply is not None:
                state.before_reply()
            body = json.dumps({
                'id': 'reply', 'object': 'chat.completion', 'model': 'test-model',
                'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': state.text}, 'finish_reason': 'stop'}],
                'usage': {'prompt_tokens': 20, 'completion_tokens': 8, 'total_tokens': 28},
            }).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    state.url = f'http://127.0.0.1:{server.server_port}/v1'
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.fixture
def binding(tmp_path, monkeypatch, provider):
    home = tmp_path / 'home'
    home.mkdir()
    monkeypatch.setenv('HERMES_HOME', str(home))
    (home / 'config.yaml').write_text(
        'model:\n  default: test-model\n  provider: openai-compat\n'
        f'  base_url: {provider.url}\n  context_length: 131072\n'
        'agent:\n  environment_probe: true\ncompression:\n  enabled: true\n  micro_compact: true\n'
        'context:\n  engine: unwanted-test-plugin\n'
    )
    (home / 'SOUL.md').write_text('PRIVATE HOST SOUL MUST NOT LEAK')
    (home / 'MEMORY.md').write_text('PRIVATE HOST MEMORY MUST NOT LEAK')
    db_path = tmp_path / 'control.db'
    with connect_closing(db_path) as conn:
        root = identity.create_root(conn, actor=identity.OWNER, request_id='writer', name='Fantasy Writer', purpose='Write stories of emerald dragons.')
    from agent_native.chat import issue_binding
    return issue_binding(actor=identity.OWNER, agent_id=root['id'], db_path=db_path, storage_root=tmp_path / 'agents')


def make_agent(binding, session_db=None):
    from agent.managed_chat_policy import bind_managed_chat
    from run_agent import AIAgent
    from hermes_cli.config import load_config_readonly
    base_url = load_config_readonly()['model']['base_url']
    with bind_managed_chat(binding):
        return AIAgent(
            api_key='test-key', base_url=base_url,
            provider='openai-compat', api_mode='chat_completions', model='test-model',
            session_id=binding.session_id, enabled_toolsets=['terminal', 'memory'],
            quiet_mode=True, max_iterations=2, session_db=session_db,
        )


def test_constructor_does_not_discover_plugins_probe_or_load_private_context(binding, monkeypatch):
    from run_agent import AIAgent  # Native process import is outside managed construction.
    assert AIAgent
    calls = []
    monkeypatch.setattr('hermes_cli.plugins.discover_plugins', lambda *a, **k: calls.append('plugins'))
    monkeypatch.setattr('tools.env_probe.warm_environment_probe_async', lambda: calls.append('probe'))
    monkeypatch.setattr('plugins.context_engine.load_context_engine', lambda *a: calls.append('engine'))
    agent = make_agent(binding)
    assert calls == []
    assert agent.tools == []
    assert not agent.valid_tool_names
    assert agent._memory_store is None
    assert agent._memory_manager is None
    assert agent.skip_background_review and not agent.compression_enabled
    prompt = agent._build_system_prompt()
    assert binding.purpose in prompt
    assert 'PRIVATE HOST' not in prompt


def test_real_loop_has_only_protected_identity_and_plain_messages(binding, monkeypatch, provider):
    agent = make_agent(binding)
    requests = provider.requests
    agent._disable_streaming = True
    import hermes_cli.lifecycle as lifecycle
    import hermes_cli.middleware as middleware
    hooks = []
    for module, name in [(lifecycle, 'invoke_hook'), (middleware, 'apply_llm_request_middleware'), (middleware, 'run_llm_execution_middleware')]:
        original = getattr(module, name)
        def observe(*args, _fn=original, _name=name, **kwargs):
            hooks.append(_name)
            return _fn(*args, **kwargs)
        monkeypatch.setattr(module, name, observe)
    first = agent.run_conversation('Who are you? @/etc/passwd')
    second = agent.run_conversation('Continue our conversation.', conversation_history=first['messages'])
    assert second['final_response'] == 'I write emerald dragon stories.'
    assert {'invoke_hook', 'apply_llm_request_middleware', 'run_llm_execution_middleware'} <= set(hooks)
    assert len(requests) == 2
    system = [r['messages'][0]['content'] for r in requests]
    assert system[0] == system[1]
    assert binding.purpose in system[0]
    assert 'PRIVATE HOST' not in system[0]
    assert all(not r.get('tools') for r in requests)
    assert requests[0]['messages'][-1]['content'] == 'Who are you? @/etc/passwd'
    assert not agent.compression_enabled


@pytest.mark.parametrize('name', ['terminal', 'write_file', 'memory', 'delegate_task', 'execute_code'])
def test_direct_dispatch_cannot_bypass_zero_tools(binding, name):
    agent = make_agent(binding)
    from agent.agent_runtime_helpers import invoke_tool
    # Even a stale/native registry snapshot cannot promote a conversation binding.
    agent.valid_tool_names = {name}
    with pytest.raises(PermissionError, match='conversation'):
        invoke_tool(agent, name, {}, 'task', pre_tool_block_checked=True, skip_tool_request_middleware=True, skip_tool_execution_middleware=True)


def test_obsolete_purpose_refuses_turn_before_provider(binding):
    agent = make_agent(binding)
    with connect_closing(binding._db_path) as conn:
        identity.revise_soul(conn, actor=identity.OWNER, agent_id=binding.agent_id, expected_revision=binding.soul_revision, purpose='Write mysteries.')
    with pytest.raises((PermissionError, identity.ConflictError)):
        agent.run_conversation('Who are you?')


@pytest.mark.parametrize('mode', ['encoded', 'explicit'])
def test_managed_admission_rejects_moa_before_decode_or_side_models(binding, monkeypatch, mode):
    import base64
    from hermes_cli.moa_config import MOA_MARKER_PREFIX
    agent = make_agent(binding)
    def forbidden_decode(*args):
        raise AssertionError('Managed input reached native MoA decoding')
    monkeypatch.setattr('agent.conversation_loop._decode_inline_moa_turn', forbidden_decode)
    if mode == 'encoded':
        message = MOA_MARKER_PREFIX + base64.urlsafe_b64encode(json.dumps({'prompt': 'Start extra models', 'config': {}}).encode()).decode()
        kwargs = {}
    else:
        message = 'Start extra models'
        kwargs = {'moa_config': {'reference_models': [{'model': 'test-model'}]}}
        # Explicit MoA bypasses decoding; stop at its aggregation boundary as well.
        monkeypatch.setattr('agent.moa_loop.aggregate_moa_context', forbidden_decode)
    with pytest.raises(PermissionError, match='conversation'):
        agent.run_conversation(message, **kwargs)


def test_managed_chat_refuses_inherited_worker_environment(binding, monkeypatch, provider):
    agent = make_agent(binding)
    agent._disable_streaming = True
    monkeypatch.setenv('HERMES_KANBAN_TASK', 'fixture-worker-assignment')
    with pytest.raises(PermissionError, match='worker'):
        agent.run_conversation('Tell me about your purpose.')
    assert provider.requests == []
    # Admission refuses this process context; it never changes global worker state.
    import os
    assert os.environ['HERMES_KANBAN_TASK'] == 'fixture-worker-assignment'


def test_revoked_reply_never_enters_native_session_history(binding, provider, tmp_path):
    from hermes_state import SessionDB
    native_path = tmp_path / 'native-state.db'
    db = SessionDB(db_path=native_path)
    try:
        db.create_session(binding.session_id, source='tui')
        db.set_session_title(binding.session_id, binding.name)
        agent = make_agent(binding, session_db=db)
        agent._disable_streaming = True
        agent._session_json_enabled = True
        accepted = agent.run_conversation('Tell me your purpose.')
        assert accepted['final_response'] == provider.text
        before = db.get_messages(binding.session_id)
        assert [row['role'] for row in before] == ['user', 'assistant']

        def revise_before_reply():
            provider.before_reply = None
            with connect_closing(binding._db_path) as conn:
                identity.revise_soul(conn, actor=identity.OWNER, agent_id=binding.agent_id,
                                     expected_revision=binding.soul_revision, purpose='Write mysteries.')
        provider.before_reply = revise_before_reply
        provider.text = 'OBSOLETE PURPOSE REPLY MUST NOT BECOME HISTORY'
        with pytest.raises((PermissionError, identity.ConflictError)):
            agent.run_conversation('Explain your next idea.', conversation_history=accepted['messages'])
        after = db.get_messages(binding.session_id)
        assert after[:len(before)] == before
        assert [row['role'] for row in after] == ['user', 'assistant', 'user']
        assert provider.text not in json.dumps(after)
        snapshot = agent.logs_dir / f'session_{binding.session_id}.json'
        assert provider.text not in snapshot.read_text()
        assert len(provider.requests) == 2
    finally:
        db.close()
    # A fresh native store sees the same durable boundary, not a filtered live view.
    reopened = SessionDB(db_path=native_path)
    try:
        assert reopened.get_messages(binding.session_id) == after
    finally:
        reopened.close()
