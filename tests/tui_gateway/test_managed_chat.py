"""Managed owner chat uses the real native dispatcher and session database."""
import threading

import pytest


class Transport:
    def __init__(self, binding=None):
        self.managed_chat = binding
        self.frames = []
        self.condition = threading.Condition()
        self.auth_identity = None

    def write(self, frame):
        with self.condition:
            self.frames.append(frame)
            self.condition.notify_all()
        return True

    def closed(self):
        return False

    def request(self, server, method, params):
        rid = str(len(self.frames)) + method
        response = server.dispatch({'id': rid, 'method': method, 'params': params}, self)
        if response is not None:
            return response
        with self.condition:
            found = lambda: next((f for f in self.frames if f.get('id') == rid), None)
            assert self.condition.wait_for(found, timeout=10), method
            return found()


@pytest.fixture
def binding(tmp_path, monkeypatch):
    from agent_native.identity import OWNER, create_root
    from agent_native.chat import issue_binding
    from hermes_cli.kanban_db_connect import connect_closing
    control = tmp_path / 'control.db'
    monkeypatch.setenv('HERMES_KANBAN_DB', str(control))
    with connect_closing(control) as conn:
        root = create_root(conn, actor=OWNER, request_id='chat', name='Writer', purpose='Write fantasy stories about moonlit citadels.')
    return issue_binding(actor=OWNER, agent_id=root['id'], db_path=control, storage_root=tmp_path / 'agents')


def test_managed_transport_cannot_branch_through_native_rpc(binding):
    from tui_gateway import server
    result = Transport(binding).request(server, 'session.branch', {'session_id': 'unknown'})
    assert result['error']['code'] == 4030
    assert 'managed chat' in result['error']['message'].lower()


@pytest.mark.parametrize('method', ['session.branch', 'session.compress', 'session.cwd.set', 'config.set',
    'slash.exec', 'command.dispatch', 'subagent.spawn', 'image.attach', 'file.attach', 'clipboard.paste',
    'prompt.preview', 'model.switch'])
def test_managed_chat_rejects_other_native_capabilities(binding, method):
    from tui_gateway import server
    result = Transport(binding).request(server, method, {'session_id': 'unknown'})
    assert result['error']['code'] == 4030


def test_unscoped_transport_cannot_rebind_managed_runtime(binding):
    from tui_gateway import server
    from tui_gateway.transport import bind_transport, reset_transport
    managed = Transport(binding)
    token = bind_transport(managed)
    try:
        record = server._deferred_session_record(binding.session_id, cols=80, cwd=binding.workspace,
            history=[], lease=None)
    finally:
        reset_transport(token)
    server._sessions['managed-test'] = record
    try:
        result = Transport().request(server, 'session.status', {'session_id': 'managed-test'})
        assert result['error']['code'] == 4030
        assert record['transport'] is managed
        result = Transport().request(server, 'session.resume', {'session_id': binding.session_id})
        assert result['error']['code'] == 4030
    finally:
        server._sessions.pop('managed-test', None)


def test_synthetic_turn_has_no_managed_owner_admission(binding):
    from tui_gateway.managed_chat import admit_turn, issue_turn_permit
    record = {'managed_chat': binding, 'session_key': binding.session_id, 'history_lock': threading.Lock()}
    with pytest.raises(PermissionError):
        admit_turn(record, None)
    permit = issue_turn_permit(record)
    admit_turn(record, permit)
    with pytest.raises(PermissionError):
        admit_turn(record, permit)


@pytest.fixture
def native(binding, tmp_path, monkeypatch):
    import importlib.util
    from pathlib import Path
    path = Path(__file__).resolve().parents[2] / 'web/e2e/native_chat_fixture.py'
    spec = importlib.util.spec_from_file_location('managed_chat_provider_fixture', path)
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    profile = tmp_path / 'profile'
    profile.mkdir()
    monkeypatch.setenv('HERMES_HOME', str(profile))
    with fixture.native_model_server() as model:
        fixture.configure_native_chat(profile, model)
        from hermes_state import SessionDB
        from tui_gateway import server
        db = SessionDB(tmp_path / 'native.db')
        monkeypatch.setattr(server, '_db', db)
        monkeypatch.setattr(server, '_hermes_home', profile)
        try:
            yield server, db, model, fixture
        finally:
            for sid, record in list(server._sessions.items()):
                if record.get('managed_chat') == binding:
                    if thread := record.get('_run_thread'):
                        thread.join(timeout=10)
                    server._close_session_by_id(sid, end_reason='test_cleanup')
            db.close()


def test_native_managed_roundtrip_keeps_purpose_history_and_exact_session(binding, native):
    server, db, model, fixture = native
    first = Transport(binding)
    created = first.request(server, 'session.create', {'cols': 80})
    assert 'error' not in created, created
    result = created['result']
    assert result['stored_session_id'] == binding.session_id
    sid = result['session_id']
    record = server._sessions[sid]
    assert record['cwd'] == binding.workspace
    assert record['agent_ready'].wait(20)
    assert record['agent_error'] is None
    assert record['agent'].tools == []
    sent = first.request(server, 'prompt.submit', {'session_id': sid, 'text': fixture.OPENER})
    assert sent['result']['status'] == 'streaming'
    with first.condition:
        complete = lambda: next((f for f in first.frames if f.get('params', {}).get('type') == 'message.complete'), None)
        assert first.condition.wait_for(complete, timeout=20)
    record['_run_thread'].join(timeout=10)
    assert model.requests[0]['last_user'] == fixture.OPENER
    assert [m['content'] for m in db.get_messages(binding.session_id) if m['role'] in ('user', 'assistant')] == [fixture.OPENER, fixture.REPLY]
    second = Transport(binding)
    resumed = second.request(server, 'session.create', {'cols': 80})
    assert 'error' not in resumed, resumed
    assert resumed['result']['session_key'] == binding.session_id
    sid = resumed['result']['session_id']
    sent = second.request(server, 'prompt.submit', {'session_id': sid, 'text': fixture.FOLLOWUP})
    assert 'error' not in sent, sent
    with second.condition:
        assert second.condition.wait_for(lambda: any(f.get('params', {}).get('type') == 'message.complete' for f in second.frames), timeout=20)
    server._sessions[sid]['_run_thread'].join(timeout=10)
    assert len(model.requests) == 2
    assert model.requests[-1]['history_has_first_exchange'] is True
    assert [m['content'] for m in db.get_messages(binding.session_id) if m['role'] in ('user', 'assistant')] == [fixture.OPENER, fixture.REPLY, fixture.FOLLOWUP, fixture.RECALLED]


def test_unscoped_title_alias_cannot_resume_managed_history(binding, native):
    server, db, model, _ = native
    db.ensure_session(binding.session_id, source='tui', cwd=binding.workspace)
    db.set_session_title(binding.session_id, 'Protected managed conversation')
    result = Transport().request(server, 'session.resume', {'session_id': 'Protected managed conversation'})
    assert result['error']['code'] == 4030
    assert not model.requests
    assert not any(s.get('session_key') == binding.session_id for s in server._sessions.values())


def test_concurrent_managed_open_reuses_one_native_session(binding, native):
    from concurrent.futures import ThreadPoolExecutor
    server, _, model, _ = native
    clients = [Transport(binding), Transport(binding)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda client: client.request(server, 'session.create', {'cols': 80}), clients))
    assert all('error' not in r for r in results), results
    assert len({r['result']['session_id'] for r in results}) == 1
    records = [s for s in server._sessions.values() if s.get('session_key') == binding.session_id]
    assert len(records) == 1
    assert records[0]['agent_ready'].wait(20)
    assert records[0]['agent_error'] is None
    assert not model.requests


def test_changed_purpose_invalidates_existing_chat_transport(binding):
    from agent_native.identity import OWNER, revise_soul
    from hermes_cli.kanban_db_connect import connect_closing
    from tui_gateway import server
    with connect_closing(binding._db_path) as conn:
        revise_soul(conn, actor=OWNER, agent_id=binding.agent_id, expected_revision=1, purpose='Write historical fiction instead')
    result = Transport(binding).request(server, 'session.create', {'cols': 80})
    assert result['error']['code'] == 4030
    assert 'purpose changed' in result['error']['message'].lower()


def test_managed_stream_drops_obsolete_reply_before_live_and_replay_delivery(binding, native):
    from agent_native.identity import OWNER, revise_soul
    from hermes_cli.kanban_db_connect import connect_closing
    from tui_gateway.event_replay import events_since
    server, _, model, _ = native
    client = Transport(binding)
    opened = client.request(server, 'session.create', {'cols': 80})
    sid = opened['result']['session_id']
    record = server._sessions[sid]
    assert record['agent_ready'].wait(20)
    assert record['agent_error'] is None
    server._emit('message.delta', sid, {'text': 'Earlier valid reply'})
    with connect_closing(binding._db_path) as conn:
        revise_soul(conn, actor=OWNER, agent_id=binding.agent_id, expected_revision=1,
                    purpose='Write historical fiction instead')
    server._emit('message.delta', sid, {'text': 'Obsolete streamed reply'})
    server._emit('message.complete', sid, {'text': 'Obsolete final reply', 'status': 'complete'})
    events = [f['params'] for f in client.frames if f.get('method') == 'event']
    assert [e['payload']['text'] for e in events if e['type'] == 'message.delta'] == ['Earlier valid reply']
    failures = [e for e in events if e['type'] == 'message.complete']
    assert len(failures) == 1
    assert failures[0]['payload']['status'] == 'error'
    assert 'purpose changed' in failures[0]['payload']['error'].lower()
    assert record['agent']._interrupt_requested is True
    assert 'Obsolete' not in str(events_since(sid, 0))
    assert not model.requests


@pytest.mark.parametrize('persist', [False, True])
def test_managed_native_boot_reports_wake_disabled_without_starting_it(binding, persist):
    from tui_gateway import server
    result = Transport(binding).request(server, 'wake.start', {'surface': 'tui', 'persist': persist})
    assert result['result'] == {'started': False, 'reason': 'disabled'}


def test_managed_cold_resume_metadata_keeps_identity_and_private_workspace(binding, native):
    server, db, model, _ = native
    db.ensure_session(binding.session_id, source='tui', cwd=binding.workspace)
    resumed = Transport(binding).request(server, 'session.resume', {'session_id': binding.session_id, 'cols': 80})
    assert 'error' not in resumed, resumed
    info = resumed['result']['info']
    assert info['managed_agent']['id'] == binding.agent_id
    assert info['managed_agent']['purpose'] == binding.purpose
    assert info['cwd'] == binding.workspace
    assert not model.requests
