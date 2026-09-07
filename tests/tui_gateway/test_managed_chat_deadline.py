"""Managed deadlines exercise native Hermes against a stalled external HTTP peer."""

import os
import time
from uuid import uuid4

import yaml

from tests.tui_gateway.test_managed_chat import binding, native  # noqa: F401
from tests.tui_gateway.test_managed_chat_receipts import _open


def _eventually(read, predicate, *, timeout=10):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        last = read()
        if predicate(last):
            return last
        time.sleep(0.05)
    raise AssertionError(f"Expected native state did not settle: {last!r}")


def _dead(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    return False


def _receipt(client, server, sid, message_id):
    return client.request(
        server,
        "prompt.receipt",
        {
            "session_id": sid,
            "client_message_id": message_id,
        },
    )["result"]["receipt"]


def test_hard_deadline_kills_only_managed_worker_and_old_uuid_cannot_run_again(
    binding, native
):
    server, db, model, fixture, client, sid = _open(binding, native)
    config_path = server._hermes_home / "config.yaml"
    config = yaml.safe_load(config_path.read_text())
    config["agent_native"] = {"managed_chat_timeout_seconds": 5}
    config_path.write_text(yaml.safe_dump(config))
    # Prime a native conversation, keeping its actual transcript and process.
    first_id = str(uuid4())
    first = client.request(
        server,
        "prompt.submit",
        {
            "session_id": sid,
            "client_message_id": first_id,
            "text": fixture.OPENER,
        },
    )
    assert first["result"]["receipt"]["id"] == first_id
    _eventually(
        lambda: _receipt(client, server, sid, first_id),
        lambda r: r["status"] == "complete",
    )
    record = server._sessions[sid]
    message_id, marker = str(uuid4()), "nativeDeadline_" + uuid4().hex
    model.holds.arm(marker)
    params = {
        "session_id": sid,
        "client_message_id": message_id,
        "text": "Wait for this result " + marker,
    }
    started = time.monotonic()
    try:
        accepted = client.request(server, "prompt.submit", params)
        assert accepted["result"]["receipt"]["id"] == message_id
        _eventually(lambda: model.holds.evidence(marker), lambda e: e["entered"])
        worker_pid = record["_managed_host"].pid
        assert not _dead(worker_pid)
        receipt = _eventually(
            lambda: _receipt(client, server, sid, message_id),
            lambda r: r["status"] == "error",
            timeout=7,
        )
        assert "tim" in receipt["reason"].lower()
        assert time.monotonic() - started < 8
        assert worker_pid and worker_pid != os.getpid()
        _eventually(lambda: _dead(worker_pid), bool, timeout=2)
        _eventually(
            lambda: model.holds.evidence(marker),
            lambda e: e["client_disconnected"],
            timeout=2,
        )
        _eventually(lambda: record["running"], lambda running: not running, timeout=2)
        model.holds.release(marker)
        duplicate = client.request(server, "prompt.submit", params)
        assert duplicate["result"]["receipt"]["status"] == "error"
        assert model.holds.evidence(marker)["request_count"] == 1
        assert receipt["text"] == params["text"]
        assert not any(
            marker in m["content"]
            for m in db.get_messages(binding.session_id)
            if m["role"] == "assistant"
        )
        assert not any(
            marker in str(f.get("params", {}).get("payload", {}).get("text", ""))
            for f in client.frames
            if f.get("params", {}).get("type") in ("message.delta", "message.complete")
        )
        next_id = str(uuid4())
        sent = client.request(
            server,
            "prompt.submit",
            {
                "session_id": sid,
                "client_message_id": next_id,
                "text": fixture.FOLLOWUP,
            },
        )
        assert sent["result"]["receipt"]["id"] == next_id
        _eventually(
            lambda: _receipt(client, server, sid, next_id),
            lambda r: r["status"] == "complete",
        )
        assert record["_managed_host"].pid != worker_pid
        rows = db.get_messages(binding.session_id)
        assert rows[-1]["content"] == fixture.RECALLED
        assert (
            next(m for m in rows if m.get("platform_message_id") == first_id)["content"]
            == fixture.OPENER
        )
        assert len([m for m in rows if m.get("platform_message_id") == message_id]) == 1
        assert model.requests[-1]["tool_names"] == []
    finally:
        model.holds.release(marker)


def test_unconfirmed_stop_stays_busy_until_owner_retries_same_worker(
    binding, native, monkeypatch
):
    server, _, model, fixture, client, sid = _open(binding, native)
    marker, message_id = "stopUnconfirmed_" + uuid4().hex, str(uuid4())
    model.holds.arm(marker)
    client.request(
        server,
        "prompt.submit",
        {
            "session_id": sid,
            "client_message_id": message_id,
            "text": "Wait for " + marker,
        },
    )
    _eventually(lambda: model.holds.evidence(marker), lambda e: e["entered"])
    record = server._sessions[sid]
    execution, host = record["_managed_execution"], record["_managed_host"]
    pid, force_stop = host.pid, host.force_stop
    monkeypatch.setattr(host, "force_stop", lambda **_: False)
    try:
        client.request(server, "session.interrupt", {"session_id": sid})
        assert not _dead(pid)
        assert record["running"] and not execution.done.is_set()
        assert _receipt(client, server, sid, message_id)["status"] == "running"
        assert any(
            f.get("params", {}).get("payload", {}).get("code")
            == "managed_stop_unconfirmed"
            for f in client.frames
        )
        rejected = client.request(
            server,
            "prompt.submit",
            {
                "session_id": sid,
                "client_message_id": str(uuid4()),
                "text": "A different intent",
            },
        )
        assert rejected["result"]["receipt"]["status"] == "error"
        assert "busy" in rejected["result"]["receipt"]["reason"].lower()
        assert model.holds.evidence(marker)["request_count"] == 1
    finally:
        monkeypatch.setattr(host, "force_stop", force_stop)
        client.request(server, "session.interrupt", {"session_id": sid})
        model.holds.release(marker)
    assert _dead(pid) and not record["running"]
    assert _receipt(client, server, sid, message_id)["status"] == "error"
    # A callback retained by the old host cannot settle or stream into another attempt.
    next_marker, next_id = "nextHeld_" + uuid4().hex, str(uuid4())
    model.holds.arm(next_marker)
    try:
        client.request(
            server,
            "prompt.submit",
            {
                "session_id": sid,
                "client_message_id": next_id,
                "text": "Now wait for " + next_marker,
            },
        )
        _eventually(lambda: model.holds.evidence(next_marker), lambda e: e["entered"])
        before = len(client.frames)
        execution.on_rpc(
            server._event_frame("message.delta", sid, {"text": "obsolete callback"})
        )
        execution.on_rpc(
            server._event_frame(
                "message.complete",
                sid,
                {"text": "obsolete callback", "status": "complete"},
            )
        )
        assert len(client.frames) == before
        assert _receipt(client, server, sid, next_id)["status"] == "running"
    finally:
        client.request(server, "session.interrupt", {"session_id": sid})
        model.holds.release(next_marker)


def test_finalization_storage_failure_reports_pending_cleanup_and_owner_can_retry(
    binding, native, monkeypatch
):
    server, db, model, _, client, sid = _open(binding, native)
    marker, message_id = "finalizeFailure_" + uuid4().hex, str(uuid4())
    model.holds.arm(marker)
    try:
        client.request(
            server,
            "prompt.submit",
            {
                "session_id": sid,
                "client_message_id": message_id,
                "text": "Wait for " + marker,
            },
        )
        _eventually(lambda: model.holds.evidence(marker), lambda e: e["entered"])
        record = server._sessions[sid]
        execution, pid = record["_managed_execution"], record["_managed_host"].pid
        original = db.get_messages_as_conversation
        failed = []

        def fail_once(*args, **kwargs):
            if not failed:
                failed.append(True)
                raise RuntimeError("Fixture storage temporarily unavailable")
            return original(*args, **kwargs)

        monkeypatch.setattr(db, "get_messages_as_conversation", fail_once)
        model.holds.release(marker)
        _eventually(
            lambda: client.frames,
            lambda frames: any(
                f.get("params", {}).get("payload", {}).get("code")
                == "managed_cleanup_unconfirmed"
                for f in frames
            ),
        )
        assert _dead(pid) and record["running"] and not execution.done.is_set()
        client.request(server, "session.interrupt", {"session_id": sid})
        assert execution.done.is_set() and not record["running"]
        assert model.holds.evidence(marker)["request_count"] == 1
    finally:
        model.holds.release(marker)


def test_deadline_kills_worker_even_while_parent_admission_lock_is_busy(
    binding, native
):
    server, _, model, _, client, sid = _open(binding, native)
    config_path = server._hermes_home / "config.yaml"
    config = yaml.safe_load(config_path.read_text())
    config["agent_native"] = {"managed_chat_timeout_seconds": 5}
    config_path.write_text(yaml.safe_dump(config))
    marker, message_id = "blockedAdmission_" + uuid4().hex, str(uuid4())
    model.holds.arm(marker)
    try:
        client.request(
            server,
            "prompt.submit",
            {
                "session_id": sid,
                "client_message_id": message_id,
                "text": "Wait for " + marker,
            },
        )
        _eventually(lambda: model.holds.evidence(marker), lambda e: e["entered"])
        record = server._sessions[sid]
        execution, pid = record["_managed_execution"], record["_managed_host"].pid
        with record["_managed_submit_lock"]:
            _eventually(
                lambda: _dead(pid),
                bool,
                timeout=max(1, execution.deadline - time.monotonic() + 2),
            )
            _eventually(
                lambda: model.holds.evidence(marker),
                lambda e: e["client_disconnected"],
                timeout=2,
            )
        _eventually(
            lambda: _receipt(client, server, sid, message_id),
            lambda r: r["status"] == "error",
        )
    finally:
        model.holds.release(marker)


def test_native_host_can_be_stopped_before_hello_without_waiting_startup_lock(tmp_path):
    import sys
    import threading
    import pytest
    from tui_gateway.host_supervisor import HostSupervisor

    host = HostSupervisor(
        registry_path=tmp_path / "host.json",
        argv=[sys.executable, "-c", "import time; time.sleep(60)"],
        autostart=False,
        respawn_max=0,
    )
    errors = []

    def start():
        try:
            host.start()
        except RuntimeError as exc:
            errors.append(str(exc))

    starter = threading.Thread(target=start, daemon=True)
    starter.start()
    try:
        pid = _eventually(lambda: host.pid, lambda value: value > 0)
        assert not _dead(pid)
        started = time.monotonic()
        assert host.force_stop(timeout=1)
        starter.join(timeout=1)
        assert not starter.is_alive() and _dead(pid)
        assert time.monotonic() - started < 2
        assert errors and "stopped" in errors[0]
        with pytest.raises(RuntimeError, match="stopped"):
            host.start()
        assert host.pid == pid
    finally:
        host.force_stop()


def test_private_ipc_eof_ends_actual_native_worker_and_provider_request(
    binding, native
):
    server, _, model, _, client, sid = _open(binding, native)
    marker, message_id = "privateEof_" + uuid4().hex, str(uuid4())
    model.holds.arm(marker)
    try:
        client.request(
            server,
            "prompt.submit",
            {
                "session_id": sid,
                "client_message_id": message_id,
                "text": "Wait for " + marker,
            },
        )
        _eventually(lambda: model.holds.evidence(marker), lambda e: e["entered"])
        host = server._sessions[sid]["_managed_host"]
        pid = host.pid
        assert not _dead(pid)
        # Real private host pipe closes; no fake model result or process-death flag.
        host._proc.stdin.close()
        _eventually(lambda: _dead(pid), bool, timeout=3)
        _eventually(
            lambda: model.holds.evidence(marker),
            lambda e: e["client_disconnected"],
            timeout=2,
        )
        receipt = _eventually(
            lambda: _receipt(client, server, sid, message_id),
            lambda r: r["status"] == "error",
        )
        assert "exited" in receipt["reason"]
        assert not server._sessions[sid]["running"]
        assert model.holds.evidence(marker)["request_count"] == 1
    finally:
        model.holds.release(marker)


def test_managed_close_cannot_discard_unconfirmed_live_worker(
    binding, native, monkeypatch
):
    server, _, model, _, client, sid = _open(binding, native)
    marker, message_id = "closeUnconfirmed_" + uuid4().hex, str(uuid4())
    model.holds.arm(marker)
    try:
        client.request(
            server,
            "prompt.submit",
            {
                "session_id": sid,
                "client_message_id": message_id,
                "text": "Wait for " + marker,
            },
        )
        _eventually(lambda: model.holds.evidence(marker), lambda e: e["entered"])
        record = server._sessions[sid]
        host, execution = record["_managed_host"], record["_managed_execution"]
        pid, force_stop = host.pid, host.force_stop
        monkeypatch.setattr(host, "force_stop", lambda **_: False)
        try:
            closed = client.request(server, "session.close", {"session_id": sid})
            assert closed["result"]["closed"] is False
            assert server._sessions[sid] is record
            assert record["running"] and not _dead(pid)
            assert _receipt(client, server, sid, message_id)["status"] == "running"
            reopened = client.request(server, "session.create", {"cols": 80})["result"]
            assert reopened["session_id"] == sid
            assert record["_managed_execution"] is execution
        finally:
            monkeypatch.setattr(host, "force_stop", force_stop)
            execution.stop("Test cleanup")
        closed = client.request(server, "session.close", {"session_id": sid})
        assert closed["result"]["closed"] is True
        assert sid not in server._sessions and _dead(pid)
    finally:
        model.holds.release(marker)


def test_removal_stops_silent_native_chat_without_waiting_for_model(binding, native, monkeypatch):
    from agent_native.identity import OWNER, remove_root
    from hermes_cli.kanban_db_connect import connect_closing
    server, db, model, fixture, client, sid = _open(binding, native)
    opener = str(uuid4())
    client.request(server, 'prompt.submit', {'session_id': sid, 'client_message_id': opener, 'text': fixture.OPENER})
    _eventually(lambda: _receipt(client, server, sid, opener), lambda r: r['status']=='complete')
    original_enter = model.holds.enter
    monkeypatch.setattr(model.holds, 'enter', lambda text: original_enter(text.split('Read-only work observations for this message.')[0].rstrip()))
    marker, message_id = 'removeSilent_' + uuid4().hex, str(uuid4())
    model.holds.arm(marker)
    try:
        client.request(server, 'prompt.submit', {'session_id': sid, 'client_message_id': message_id, 'text': 'Wait for ' + marker})
        _eventually(lambda: model.holds.evidence(marker), lambda e: e['entered'])
        record = server._sessions[sid]
        pid = record['_managed_host'].pid
        with connect_closing(binding._db_path) as conn:
            remove_root(conn, actor=OWNER, agent_id=binding.agent_id)
        _eventually(lambda: _dead(pid), bool, timeout=5)
        _eventually(lambda: record['running'], lambda value: not value, timeout=2)
        assert not any(marker in m['content'] for m in db.get_messages(binding.session_id) if m['role']=='assistant')
    finally:
        model.holds.release(marker)
