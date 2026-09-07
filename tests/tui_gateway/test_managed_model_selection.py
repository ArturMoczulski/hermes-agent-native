"""Managed native messages retain the provider/model admitted with their receipt."""
import threading
from uuid import uuid4

from tests.tui_gateway.test_managed_chat import binding, native, Transport  # noqa: F401


def test_model_edit_after_admission_changes_only_the_next_native_message(binding, native, monkeypatch):
    from agent_native import model_settings
    from agent_native.identity import OWNER
    from hermes_cli.kanban_db_connect import connect_closing
    from tui_gateway.managed_chat_host import ManagedExecution

    server, db, model, fixture = native
    transport = Transport(binding)
    created = transport.request(server, 'session.create', {'cols': 80})
    assert 'error' not in created, created
    sid = created['result']['session_id']
    record = server._sessions[sid]
    assert record['agent_ready'].wait(20)
    gate = threading.Event()
    original_run = ManagedExecution.run
    def held_start(execution):
        assert gate.wait(20)
        return original_run(execution)
    monkeypatch.setattr(ManagedExecution, 'run', held_start)
    first_id = str(uuid4())
    first_choice = {'provider': 'custom:browser-fixture', 'model': fixture.MODEL}
    next_choice = {'provider': 'custom:browser-alternate', 'model': fixture.ALTERNATE_MODEL}
    try:
        response = transport.request(server, 'prompt.submit', {
            'session_id': sid, 'text': fixture.OPENER, 'client_message_id': first_id})
        assert response['result']['status'] == 'streaming', response
        with connect_closing(binding._db_path) as control:
            captured = model_settings.read_attempt(control, 'chat', first_id)
            assert captured is not None, 'Accepted message must capture its model before worker startup'
            assert {key: captured[key] for key in first_choice} == first_choice
            current = model_settings.get_selection(control, binding.agent_id)
            model_settings.change_selection(control, actor=OWNER, agent_id=binding.agent_id,
                expected_revision=current['revision'], choice=next_choice)
        assert model.requests == []
        gate.set()
        with transport.condition:
            assert transport.condition.wait_for(lambda: any(
                f.get('params', {}).get('type') == 'message.complete' for f in transport.frames), timeout=25)
        record['_run_thread'].join(10)
        assert model.requests[0]['model'] == fixture.MODEL
        assert model.requests[0]['path'] == '/v1/chat/completions'
        second_id = str(uuid4())
        response = transport.request(server, 'prompt.submit', {
            'session_id': sid, 'text': fixture.FOLLOWUP, 'client_message_id': second_id})
        assert 'error' not in response, response
        with transport.condition:
            assert transport.condition.wait_for(lambda: sum(
                f.get('params', {}).get('type') == 'message.complete' for f in transport.frames) == 2, timeout=25)
        record['_run_thread'].join(10)
        assert len(model.requests) == 2
        assert model.requests[1]['model'] == fixture.ALTERNATE_MODEL
        assert model.requests[1]['path'] == '/alternate/v1/chat/completions'
        assert model.requests[1]['history_has_first_exchange']
        with connect_closing(binding._db_path) as control:
            assert model_settings.read_attempt(control, 'chat', first_id) == captured
            assert {key: model_settings.read_attempt(control, 'chat', second_id)[key]
                    for key in next_choice} == next_choice
        assert [m['content'] for m in db.get_messages(binding.session_id)
                if m['role'] in ('user', 'assistant')] == [fixture.OPENER, fixture.REPLY, fixture.FOLLOWUP, fixture.RECALLED]
    finally:
        gate.set()
