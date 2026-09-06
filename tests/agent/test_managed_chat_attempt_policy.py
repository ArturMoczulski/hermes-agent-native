"""Private attempt context stays with its native agent, including late persistence."""

import time
from uuid import uuid4

import pytest

from agent.managed_chat_attempt import Attempt, bind_managed_attempt, current_attempt
from hermes_state import SessionDB
from tests.agent import test_managed_chat_policy as fixtures
from tests.state.test_managed_chat_attempt import write_receipt

binding = fixtures.binding
provider = fixtures.provider


@pytest.fixture
def managed(binding, tmp_path):
    db = SessionDB(tmp_path / "native-attempt.db")
    db.create_session(binding.session_id, source="tui")
    db.set_session_title(binding.session_id, binding.name)
    attempt = Attempt(
        binding.session_id,
        str(uuid4()),
        str(uuid4()),
        time.monotonic() + 60,
        db.db_path,
    )
    write_receipt(db, attempt)
    agent = fixtures.make_agent(binding, session_db=db)
    agent._disable_streaming = True
    try:
        yield agent, db, attempt
    finally:
        db.close()


def test_native_turn_retains_immutable_attempt_for_late_persistence(managed, provider):
    agent, db, attempt = managed
    with bind_managed_attempt(attempt, db=db):
        result = agent.run_conversation("Tell me about your purpose.")
    assert result["final_response"] == provider.text
    assert current_attempt() is None
    assert current_attempt(agent) is attempt
    before = db.get_messages(attempt.session_id)
    write_receipt(db, attempt, status="unknown")
    with pytest.raises(PermissionError):
        agent._persist_session(
            result["messages"] + [{"role": "assistant", "content": "late callback"}]
        )
    assert db.get_messages(attempt.session_id) == before


def test_optional_json_snapshot_is_disabled_for_managed_attempt(managed):
    agent, db, attempt = managed
    agent._session_json_enabled = True
    with bind_managed_attempt(attempt, db=db):
        agent._save_session_log([{"role": "assistant", "content": "unfenced snapshot"}])
    assert not (agent.logs_dir / f"session_{attempt.session_id}.json").exists()


def test_terminal_receipt_prevents_native_model_call(managed, provider):
    agent, db, attempt = managed
    write_receipt(db, attempt, status="error")
    with bind_managed_attempt(attempt, db=db), pytest.raises(PermissionError):
        agent.run_conversation("This attempt has already ended.")
    assert provider.requests == []
    assert db.get_messages(attempt.session_id) == []


def test_attempt_cannot_promote_an_unbound_native_agent(managed):
    from types import SimpleNamespace
    from agent.managed_chat_policy import managed_turn

    _, db, attempt = managed
    agent = SimpleNamespace(session_id=attempt.session_id, _session_db=db)
    calls = []

    @managed_turn
    def run(agent, user_message):
        calls.append(user_message)

    with bind_managed_attempt(attempt, db=db), pytest.raises(PermissionError):
        run(agent, "unrestricted native agent")
    assert calls == []


def test_reply_after_deadline_never_becomes_native_history(managed, provider):
    from dataclasses import replace
    import threading

    agent, db, old = managed
    attempt = replace(old, deadline_monotonic=time.monotonic() + 0.2)
    write_receipt(db, attempt)
    provider.text = "EXPIRED PROVIDER REPLY"

    def late_reply():
        threading.Event().wait(
            max(0, attempt.deadline_monotonic - time.monotonic()) + 0.03
        )

    provider.before_reply = late_reply
    with bind_managed_attempt(attempt, db=db), pytest.raises(PermissionError):
        agent.run_conversation("Please answer before the deadline.")
    assert len(provider.requests) == 1
    assert [row["role"] for row in db.get_messages(attempt.session_id)] == ["user"]
    assert provider.text not in str(db.get_messages(attempt.session_id))
