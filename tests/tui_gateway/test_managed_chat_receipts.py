"""Managed retry receipts use native SessionDB and the real native provider path."""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest

from tests.tui_gateway.test_managed_chat import Transport, binding, native  # noqa: F401


def _open(binding, native):
    server, db, model, fixture = native
    client = Transport(binding)
    opened = client.request(server, "session.create", {"cols": 80})
    sid = opened["result"]["session_id"]
    assert server._sessions[sid]["agent_ready"].wait(20)
    return server, db, model, fixture, client, sid


def test_lost_submit_ack_retry_reuses_one_persisted_turn(binding, native):
    server, db, model, fixture, client, sid = _open(binding, native)
    message_id = str(uuid4())
    params = {
        "session_id": sid,
        "text": fixture.OPENER,
        "client_message_id": message_id,
    }
    first = client.request(server, "prompt.submit", params)
    assert first["result"]["receipt"]["id"] == message_id
    # The first reply is deliberately not used to decide whether to retry.
    again = Transport(binding).request(server, "prompt.submit", params)
    assert again["result"]["receipt"]["id"] == message_id
    with client.condition:
        client.condition.wait_for(
            lambda: any(
                f.get("params", {}).get("type") == "message.complete"
                for f in client.frames
            ),
            timeout=5,
        )
    server._sessions[sid]["_run_thread"].join(timeout=20)
    receipt = client.request(
        server, "prompt.receipt", {"session_id": sid, "client_message_id": message_id}
    )["result"]["receipt"]
    assert receipt["status"] == "complete"
    assert len(model.requests) == 1
    rows = db.get_messages(binding.session_id)
    assert [m["content"] for m in rows if m["role"] in ("user", "assistant")] == [
        fixture.OPENER,
        fixture.REPLY,
    ]
    assert (
        next(m for m in rows if m["role"] == "user")["platform_message_id"]
        == message_id
    )
    replay = client.request(server, "prompt.submit", params)
    assert replay["result"]["receipt"]["status"] == "complete"
    assert len(model.requests) == 1


def test_concurrent_duplicate_submits_invoke_native_model_once(binding, native):
    server, db, model, fixture, _, sid = _open(binding, native)
    params = {
        "session_id": sid,
        "text": fixture.OPENER,
        "client_message_id": str(uuid4()),
    }
    clients = [Transport(binding), Transport(binding)]
    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(
            workers.map(lambda c: c.request(server, "prompt.submit", params), clients)
        )
    assert all(
        "result" in r and r["result"]["receipt"]["id"] == params["client_message_id"]
        for r in results
    ), results
    server._sessions[sid]["_run_thread"].join(timeout=20)
    assert len(model.requests) == 1
    assert (
        len([m for m in db.get_messages(binding.session_id) if m["role"] == "user"])
        == 1
    )


def test_receipt_claim_durably_rejects_busy_id_without_releasing_active_owner(
    binding, native
):
    from tui_gateway.managed_chat_receipts import claim, read

    _, db, _, fixture = native
    first, second = str(uuid4()), str(uuid4())
    receipt, created = claim(db, binding, first, fixture.OPENER)
    assert created and receipt["status"] == "accepted"
    assert read(db, binding, first)["text"] == fixture.OPENER
    with pytest.raises(ValueError, match="different"):
        claim(db, binding, first, "Different owner message")
    rejected, created = claim(db, binding, second, "Another owner intent")
    assert not created and rejected["status"] == "error"
    assert "busy" in rejected["reason"]
    assert read(db, binding, second)["text"] == "Another owner intent"
    assert read(db, binding, first)["status"] == "accepted"
    from tui_gateway.managed_chat_receipts import _update

    _update(db, binding, first, "complete")
    delayed, created = claim(db, binding, second, "Another owner intent")
    assert not created and delayed["status"] == "error"
    third, created = claim(
        db, binding, str(uuid4()), "An explicitly retried owner intent"
    )
    assert created and third["status"] == "accepted"


def test_restart_receipt_is_unknown_and_retains_accepted_text(binding, native):
    import json
    import subprocess
    import sys
    from pathlib import Path
    from tui_gateway.managed_chat_receipts import read, claim

    _, db, _, fixture = native
    message_id = str(uuid4())
    script = """import sys
from pathlib import Path
from hermes_state import SessionDB
from agent_native.chat import issue_binding
from agent_native.identity import OWNER
from tui_gateway.managed_chat_receipts import claim
binding = issue_binding(actor=OWNER, agent_id=sys.argv[2], db_path=Path(sys.argv[3]), storage_root=Path(sys.argv[4]))
with SessionDB(Path(sys.argv[1])) as db:
    claim(db, binding, sys.argv[5], sys.argv[6])
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(db.db_path),
            binding.agent_id,
            str(binding._db_path),
            str(Path(binding.workspace).parent.parent),
            message_id,
            fixture.OPENER,
        ],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr[-1500:]
    receipt = read(db, binding, message_id)
    assert receipt["status"] == "unknown"
    assert receipt["text"] == fixture.OPENER
    assert receipt["reason"]
    again, created = claim(db, binding, message_id, fixture.OPENER)
    assert not created and again["status"] == "unknown"
    newer, created = claim(db, binding, str(uuid4()), "An explicitly new owner intent")
    assert created and newer["status"] == "accepted"
    assert fixture.OPENER in json.dumps(db.list_meta_prefix("managed_prompt:"))


@pytest.mark.parametrize("message_id", [None, "", "not-a-uuid"])
def test_managed_submit_requires_stable_uuid_before_acceptance(
    binding, native, message_id
):
    server, db, model, fixture, client, sid = _open(binding, native)
    params = {"session_id": sid, "text": fixture.OPENER}
    if message_id is not None:
        params["client_message_id"] = message_id
    response = client.request(server, "prompt.submit", params)
    assert response["error"]["code"] == 4030
    assert not model.requests
    assert not db.list_meta_prefix("managed_prompt:")


def test_receipt_reconciliation_does_not_call_abandoned_admission_running(
    binding, native
):
    from tui_gateway.managed_chat_receipts import claim

    server, _, model, fixture, client, sid = _open(binding, native)
    message_id = str(uuid4())
    claim(server._get_db(), binding, message_id, fixture.OPENER)
    # Durable claim exists, but the runtime has no admitted thread for it.
    # This is a stopped admission, not proof that a model is still working.
    response = client.request(
        server, "prompt.receipt", {"session_id": sid, "client_message_id": message_id}
    )
    assert response["result"]["receipt"]["status"] == "unknown"
    assert response["result"]["receipt"]["reason"]
    duplicate = client.request(
        server,
        "prompt.submit",
        {"session_id": sid, "client_message_id": message_id, "text": fixture.OPENER},
    )
    assert duplicate["result"]["receipt"]["status"] == "unknown"
    assert not model.requests


def test_provider_failure_records_terminal_receipt_and_retry_stays_duplicate(
    binding, native
):
    server, _, model, _, client, sid = _open(binding, native)
    message_id = str(uuid4())
    params = {
        "session_id": sid,
        "client_message_id": message_id,
        "text": "Reject this unexpected fixture prompt",
    }
    sent = client.request(server, "prompt.submit", params)
    assert sent["result"]["receipt"]["id"] == message_id
    with client.condition:
        assert client.condition.wait_for(
            lambda: any(
                f.get("params", {}).get("type") == "message.complete"
                for f in client.frames
            ),
            timeout=20,
        )
    server._sessions[sid]["_run_thread"].join(timeout=20)
    receipt = client.request(
        server, "prompt.receipt", {"session_id": sid, "client_message_id": message_id}
    )["result"]["receipt"]
    assert receipt["status"] == "error"
    assert receipt["reason"]
    requests_before = len(model.requests)
    assert requests_before > 0
    replay = client.request(server, "prompt.submit", params)
    assert replay["result"]["receipt"]["status"] == "error"
    assert len(model.requests) == requests_before


def test_busy_native_submit_returns_terminal_receipt_and_delayed_duplicate_never_runs(
    binding, native, monkeypatch
):
    from threading import Event

    server, _, model, fixture, client, sid = _open(binding, native)
    entered, release = Event(), Event()
    handler = model.RequestHandlerClass
    original = handler.do_POST

    def blocked_provider(request):
        entered.set()
        assert release.wait(10)
        return original(request)

    monkeypatch.setattr(handler, "do_POST", blocked_provider)
    first_id, second_id = str(uuid4()), str(uuid4())
    first = {"session_id": sid, "client_message_id": first_id, "text": fixture.OPENER}
    second = {"session_id": sid, "client_message_id": second_id, "text": fixture.OPENER}
    try:
        assert (
            client.request(server, "prompt.submit", first)["result"]["receipt"]["id"]
            == first_id
        )
        assert entered.wait(10)
        busy = Transport(binding).request(server, "prompt.submit", second)
        assert busy["result"]["receipt"]["status"] == "error"
        assert "busy" in busy["result"]["receipt"]["reason"]
        assert (
            client.request(
                server,
                "prompt.receipt",
                {"session_id": sid, "client_message_id": first_id},
            )["result"]["receipt"]["status"]
            == "running"
        )
    finally:
        release.set()
        server._sessions[sid]["_run_thread"].join(timeout=20)
    retry = client.request(server, "prompt.submit", second)
    assert retry["result"]["receipt"]["status"] == "error"
    assert len(model.requests) == 1
    fresh = {**second, "client_message_id": str(uuid4()), "text": fixture.FOLLOWUP}
    assert (
        client.request(server, "prompt.submit", fresh)["result"]["receipt"]["id"]
        == fresh["client_message_id"]
    )
    with client.condition:
        assert client.condition.wait_for(
            lambda: any(
                frame.get("params", {}).get("type") == "message.complete"
                and frame["params"].get("payload", {}).get("receipt", {}).get("id")
                == fresh["client_message_id"]
                for frame in client.frames
            ),
            timeout=20,
        )
    server._sessions[sid]["_run_thread"].join(timeout=20)
    assert len(model.requests) == 2
