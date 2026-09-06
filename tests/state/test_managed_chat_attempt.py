"""Managed turn deadlines fence the actual native SQLite transaction."""

import json
import os
import time
from dataclasses import replace
from uuid import uuid4

import pytest

from agent.managed_chat_attempt import Attempt, bind_managed_attempt
from hermes_state import SessionDB


@pytest.fixture
def native(tmp_path):
    db = SessionDB(tmp_path / "native.db")
    sid = "an_chat_" + uuid4().hex
    db.create_session(sid, source="tui")
    attempt = Attempt(
        sid, str(uuid4()), str(uuid4()), time.monotonic() + 60, db.db_path
    )
    write_receipt(db, attempt)
    try:
        yield db, attempt
    finally:
        db.close()


def write_receipt(db, attempt, **changes):
    receipt = {
        "id": attempt.message_id,
        "instance": attempt.receipt_instance,
        "status": "running",
        "deadline_monotonic": attempt.deadline_monotonic,
    }
    receipt.update(changes)

    def write(conn):
        for key, value in (
            (f"managed_prompt:{attempt.session_id}:{attempt.message_id}", receipt),
            (f"managed_prompt_active:{attempt.session_id}", attempt.message_id),
        ):
            conn.execute(
                "INSERT OR REPLACE INTO state_meta (key,value) VALUES (?,?)",
                (key, json.dumps(value)),
            )

    db._execute_write(write)


def holder(label="managed"):
    return f"pid={os.getpid()}:turn={label}"


def leases(db):
    with db._read_ctx() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM session_turn_leases")]


def test_active_attempt_can_acquire_and_persist_native_rows(native):
    db, attempt = native
    with bind_managed_attempt(attempt, db=db):
        assert db.try_acquire_session_turn_lease(attempt.session_id, holder())
        db.append_messages_batch(
            attempt.session_id,
            [{"role": "user", "content": "hello"}],
            turn_lease_holder=holder(),
        )
    assert [row["content"] for row in db.get_messages(attempt.session_id)] == ["hello"]


def test_expired_attempt_cannot_acquire_even_without_parent_revocation(native):
    db, old = native
    attempt = replace(old, deadline_monotonic=time.monotonic() - 1)
    write_receipt(db, attempt)
    with bind_managed_attempt(attempt, db=db), pytest.raises(PermissionError):
        db.try_acquire_session_turn_lease(attempt.session_id, holder())
    assert leases(db) == []


@pytest.mark.parametrize(
    "changes",
    [
        {"status": "error"},
        {"status": "unknown"},
        {"status": "complete"},
        {"instance": str(uuid4())},
        {"id": str(uuid4())},
        {"deadline_monotonic": 0},
    ],
)
def test_noncurrent_receipt_cannot_acquire(native, changes):
    db, attempt = native
    write_receipt(db, attempt, **changes)
    with bind_managed_attempt(attempt, db=db), pytest.raises(PermissionError):
        db.try_acquire_session_turn_lease(attempt.session_id, holder())
    assert leases(db) == []


@pytest.mark.parametrize("mode", ["single", "batch"])
def test_terminal_receipt_fences_late_append_with_existing_lease(native, mode):
    db, attempt = native
    assert db.try_acquire_session_turn_lease(attempt.session_id, holder())
    write_receipt(db, attempt, status="error")
    with bind_managed_attempt(attempt, db=db), pytest.raises(PermissionError):
        if mode == "single":
            db.append_message(
                attempt.session_id,
                "assistant",
                "late reply",
                turn_lease_holder=holder(),
            )
        else:
            db.append_messages_batch(
                attempt.session_id,
                [{"role": "assistant", "content": "late reply"}],
                turn_lease_holder=holder(),
            )
    assert db.get_messages(attempt.session_id) == []


def test_ordinary_native_sessions_keep_unmanaged_behavior(native):
    db, attempt = native
    write_receipt(db, attempt, status="error")
    assert db.try_acquire_session_turn_lease(attempt.session_id, holder())
    db.append_message(
        attempt.session_id, "user", "ordinary native path", turn_lease_holder=holder()
    )
    assert len(db.get_messages(attempt.session_id)) == 1


@pytest.mark.parametrize("operation", ["acquire", "single", "batch", "refresh"])
def test_deadline_expiring_inside_native_write_rolls_transaction_back(
    native, operation
):
    import threading

    db, old = native
    attempt = replace(old, deadline_monotonic=time.monotonic() + 0.2)
    write_receipt(db, attempt)
    if operation != "acquire":
        assert db.try_acquire_session_turn_lease(attempt.session_id, holder())
    before_leases = leases(db)

    # A real SQLite trigger holds execution after the admission guard. Expiry
    # here must roll back both transcript rows/counters and lease renewal.
    def expire():
        threading.Event().wait(
            max(0, attempt.deadline_monotonic - time.monotonic()) + 0.02
        )
        return 0

    db._conn.create_function("expire_attempt", 0, expire)
    table = "messages" if operation in ("single", "batch") else "session_turn_leases"
    event = "UPDATE" if operation == "refresh" else "INSERT"
    db._execute_write(
        lambda conn: conn.execute(
            f"CREATE TRIGGER expire_write AFTER {event} ON {table} BEGIN SELECT expire_attempt(); END"
        )
    )
    with bind_managed_attempt(attempt, db=db), pytest.raises(PermissionError):
        if operation == "acquire":
            db.try_acquire_session_turn_lease(attempt.session_id, holder())
        elif operation == "single":
            db.append_message(
                attempt.session_id, "assistant", "late", turn_lease_holder=holder()
            )
        elif operation == "batch":
            db.append_messages_batch(
                attempt.session_id,
                [{"role": "assistant", "content": "late"}],
                turn_lease_holder=holder(),
            )
        else:
            db.refresh_session_turn_lease(attempt.session_id, holder())
    assert db.get_messages(attempt.session_id) == []
    assert db.get_session(attempt.session_id)["message_count"] == 0
    assert leases(db) == before_leases


_WORKER = r"""
import json, os, sys
from pathlib import Path
from agent.managed_chat_attempt import Attempt, bind_managed_attempt
from hermes_state import SessionDB
path, sid, mid, instance, deadline, operation = sys.argv[1:]
db = SessionDB(Path(path))
attempt = Attempt(sid, mid, instance, float(deadline), Path(path))
holder = f'pid={os.getpid()}:turn=managed-process'
try:
    with bind_managed_attempt(attempt, db=db):
        if operation == 'append':
            assert db.try_acquire_session_turn_lease(sid, holder)
        print('ready', flush=True)
        assert sys.stdin.readline().strip() == 'go'
        def trace(sql):
            if sql == 'BEGIN IMMEDIATE':
                print('begin', flush=True)
        db._conn.set_trace_callback(trace)
        try:
            if operation == 'acquire':
                db.try_acquire_session_turn_lease(sid, holder)
            else:
                db.append_messages_batch(sid, [{'role':'assistant', 'content':'late process reply'}], turn_lease_holder=holder)
        except PermissionError:
            print('denied', flush=True)
        else:
            print('WRITTEN', flush=True)
finally:
    db.close()
"""


@pytest.mark.parametrize("operation", ["acquire", "append"])
@pytest.mark.parametrize("fence", ["terminal_receipt", "deadline"])
def test_process_waiting_on_sqlite_cannot_write_after_fence(native, operation, fence):
    import queue
    import sqlite3
    import subprocess
    import sys
    import threading

    db, old = native
    attempt = replace(
        old, deadline_monotonic=time.monotonic() + (3 if fence == "deadline" else 60)
    )
    write_receipt(db, attempt)
    worker = subprocess.Popen(
        [
            sys.executable,
            "-c",
            _WORKER,
            str(db.db_path),
            attempt.session_id,
            attempt.message_id,
            attempt.receipt_instance,
            str(attempt.deadline_monotonic),
            operation,
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    output = queue.Queue()

    def read_output():
        for line in worker.stdout:
            output.put(line.strip())

    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    blocker = sqlite3.connect(db.db_path, isolation_level=None)
    try:
        assert output.get(timeout=10) == "ready"
        before = leases(db)
        blocker.execute("BEGIN IMMEDIATE")
        if fence == "terminal_receipt":
            key = f"managed_prompt:{attempt.session_id}:{attempt.message_id}"
            receipt = json.loads(
                blocker.execute(
                    "SELECT value FROM state_meta WHERE key=?", (key,)
                ).fetchone()[0]
            )
            receipt["status"] = "error"
            blocker.execute(
                "UPDATE state_meta SET value=? WHERE key=?", (json.dumps(receipt), key)
            )
        worker.stdin.write("go\n")
        worker.stdin.flush()
        # The trace callback is in the child's real native BEGIN IMMEDIATE, not
        # a substituted persistence function. The parent still owns the writer lock.
        assert output.get(timeout=5) == "begin"
        if fence == "deadline":
            assert time.monotonic() < attempt.deadline_monotonic
            threading.Event().wait(attempt.deadline_monotonic - time.monotonic() + 0.03)
        blocker.commit()
        worker.wait(timeout=10)
        lines = []
        reader.join(timeout=2)
        while not output.empty():
            lines.append(output.get_nowait())
        assert worker.returncode == 0, worker.stderr.read()
        assert "denied" in lines and "WRITTEN" not in lines
        assert db.get_messages(attempt.session_id) == []
        assert leases(db) == before
    finally:
        blocker.rollback()
        blocker.close()
        if worker.poll() is None:
            worker.kill()
            worker.wait(timeout=5)
        worker.stdin.close()
        reader.join(timeout=2)
        worker.stdout.close()
        worker.stderr.close()


@pytest.mark.parametrize(
    "damage", ["missing_receipt", "invalid_receipt", "wrong_active"]
)
@pytest.mark.parametrize("operation", ["acquire", "append"])
def test_missing_or_ambiguous_receipt_evidence_fails_closed(native, damage, operation):
    db, attempt = native
    if operation == "append":
        assert db.try_acquire_session_turn_lease(attempt.session_id, holder())
    before = leases(db)
    key = f"managed_prompt:{attempt.session_id}:{attempt.message_id}"

    def damage_receipt(conn):
        if damage == "missing_receipt":
            conn.execute("DELETE FROM state_meta WHERE key=?", (key,))
        elif damage == "invalid_receipt":
            conn.execute(
                "UPDATE state_meta SET value=? WHERE key=?", ("invalid json", key)
            )
        else:
            conn.execute(
                "UPDATE state_meta SET value=? WHERE key=?",
                (
                    json.dumps(str(uuid4())),
                    f"managed_prompt_active:{attempt.session_id}",
                ),
            )

    db._execute_write(damage_receipt)
    with bind_managed_attempt(attempt, db=db), pytest.raises(PermissionError):
        if operation == "acquire":
            db.try_acquire_session_turn_lease(attempt.session_id, holder())
        else:
            db.append_message(
                attempt.session_id, "assistant", "late", turn_lease_holder=holder()
            )
    assert db.get_messages(attempt.session_id) == []
    assert leases(db) == before


def test_late_background_write_keeps_db_fence_after_context_unwinds(native):
    import threading
    from agent.managed_chat_attempt import current_attempt

    db, attempt = native
    with bind_managed_attempt(attempt, db=db):
        assert db.try_acquire_session_turn_lease(attempt.session_id, holder())
    write_receipt(db, attempt, status="complete")
    outcome = []

    def late():
        assert current_attempt() is None
        try:
            db.append_message(
                attempt.session_id, "assistant", "late", turn_lease_holder=holder()
            )
        except PermissionError:
            outcome.append("denied")
        else:
            outcome.append("written")

    thread = threading.Thread(target=late)
    thread.start()
    thread.join(timeout=5)
    assert not thread.is_alive()
    assert outcome == ["denied"]
    assert db.get_messages(attempt.session_id) == []


def test_worker_database_cannot_be_reassigned_to_another_attempt(native):
    db, attempt = native
    with bind_managed_attempt(attempt, db=db):
        pass
    replacement = replace(attempt, message_id=str(uuid4()))
    with pytest.raises(PermissionError):
        with bind_managed_attempt(replacement, db=db):
            pytest.fail("reassigned the worker database")
