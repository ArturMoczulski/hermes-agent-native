"""One bounded native ComputeHost per managed owner message.

The parent owns admission and process lifetime. The child owns Hermes's existing
model loop and canonical transcript. No child frame can settle a newer attempt.
"""

from pathlib import Path
import math
import threading
import time

from tui_gateway.host_supervisor import HostSupervisor
from tui_gateway.managed_chat_receipts import _update, public


def timeout_seconds(server):
    section = server["_load_cfg"]().get("agent_native") or {}
    value = section.get("managed_chat_timeout_seconds", 90)
    if isinstance(value, bool):
        raise ValueError("Managed chat timeout must be a positive number")
    try:
        value = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Managed chat timeout must be a positive number") from exc
    if not math.isfinite(value) or value <= 0:
        raise ValueError("Managed chat timeout must be a positive number")
    return value


class ManagedExecution:
    def __init__(self, server, sid, session, receipt, db):
        self.server, self.sid, self.session = server, sid, session
        self.receipt, self.db = receipt, db
        self.binding = session["managed_chat"]
        self.message_id = receipt["id"]
        self.deadline = receipt["deadline_monotonic"]
        self.done = threading.Event()
        self._finish_lock = threading.RLock()
        self._decision_lock = threading.Lock()
        self._completion = None
        self._stopping = threading.Event()
        profile = str(session.get("profile_home") or server["_hermes_home"])
        self.host = HostSupervisor(
            registry_path=Path(profile)
            / "state"
            / f"managed-host-{self.message_id}.json",
            env={"HERMES_HOME": profile, "HERMES_MANAGED_COMPUTE_HOST": "1"},
            expected_hermes_home=profile,
            rpc_sink=self.on_rpc,
            respawn_max=0,
            autostart=False,
        )
        self.timer = threading.Timer(
            max(0, self.deadline - time.monotonic()),
            self.stop,
            args=("Managed conversation timed out",),
        )
        self.timer.daemon = True

    def _owns(self):
        return (
            self.server["_sessions"].get(self.sid) is self.session
            and self.session.get("_managed_execution") is self
            and self.session.get("_managed_receipt_id") == self.message_id
        )

    def _active(self):
        if self._stopping.is_set() or self.done.is_set() or not self._owns():
            return False
        if time.monotonic() >= self.deadline:
            self.stop("Managed conversation timed out")
            return False
        try:
            self.binding.validate()
        except (PermissionError, ValueError) as exc:
            self.stop(str(exc))
            return False
        return True

    def on_rpc(self, frame):
        with (
            self.session.setdefault("_managed_submit_lock", threading.RLock()),
            self._finish_lock,
        ):
            self._publish_rpc(frame)

    def _publish_rpc(self, frame):
        # One process carries exactly one attempt. Reject session-less and foreign
        # frames before write_json can persist receipt state or add replay entries.
        params = frame.get("params") or {}
        if frame.get("method") != "event" or params.get("session_id") != self.sid:
            return
        if not self._active():
            return
        kind = params.get("type")
        if kind == "error":
            detail = (params.get("payload") or {}).get(
                "message"
            ) or "Managed worker is stopping"
            self._notice(str(detail), "managed_worker_stopping")
            return
        if kind == "message.complete":
            self._completion = frame
            return
        if kind == "session.info":
            self.session["_managed_info"] = params.get("payload") or {}
            # Parent stays busy until the child is reaped, including finalization.
            params.setdefault("payload", {})["running"] = True
        self.server["write_json"](frame)

    def on_complete(self, frame):
        if not self._active():
            return
        reason = None
        if frame.get("type") == "turn.error":
            reason = str(frame.get("message") or "Managed worker failed")
        elif self._completion is None:
            reason = "Managed worker ended without a completed reply"
        self._finish(reason)

    def stop(self, reason):
        self._finish(reason)

    def _notice(self, text, code):
        if self._owns():
            self.server["_emit"](
                "status.update",
                self.sid,
                {"text": text, "kind": "status", "code": code},
            )

    def _finish(self, reason):
        # The OS stop must never wait for receipt/database, event, or model work.
        # Only this tiny decision lock precedes it; no I/O occurs under that lock.
        with self._decision_lock:
            if self.done.is_set():
                return
            if not self._stopping.is_set():
                self._settlement_reason = reason
            self._stopping.set()
        try:
            if not self.host.force_stop(timeout=2):
                self._notice(
                    "Managed worker stop is not confirmed; this conversation remains busy. Interrupt again to retry stopping.",
                    "managed_stop_unconfirmed",
                )
                return
            self._settle_after_death()
        except Exception:
            self._notice(
                "Managed worker cleanup could not be recorded; this conversation remains busy. Interrupt again to retry cleanup.",
                "managed_cleanup_unconfirmed",
            )

    def _settle_after_death(self):
        with (
            self.session.setdefault("_managed_submit_lock", threading.RLock()),
            self._finish_lock,
        ):
            if self.done.is_set():
                return
            reason = self._settlement_reason
            self.timer.cancel()
            owns = self._owns()
            if reason is None and time.monotonic() >= self.deadline:
                reason = "Managed conversation timed out"
            payload = dict(
                ((self._completion or {}).get("params") or {}).get("payload") or {}
            )
            if reason:
                payload = {"status": "error", "text": "", "error": reason}
            status = "complete" if payload.get("status") == "complete" else "error"
            reason = reason or (
                str(
                    payload.get("error")
                    or payload.get("text")
                    or "Reply did not complete"
                )
                if status == "error"
                else None
            )
            # Read native history before exposing a terminal receipt. If storage
            # fails, keep the admission pending and retry cleanup without execution.
            history = (
                self.db.get_messages_as_conversation(
                    self.binding.session_id, repair_alternation=True
                )
                if owns
                else None
            )
            # This captured ID settles only its own receipt, after confirmed death.
            receipt = _update(
                self.db,
                self.binding,
                self.message_id,
                status,
                reason,
                instance=self.receipt["instance"],
            )
            payload["receipt"] = public(receipt)
            if owns:
                with self.session["history_lock"]:
                    self.session["history"] = history
                    self.session["history_version"] = (
                        int(self.session.get("history_version", 0)) + 1
                    )
                    self.session["running"] = False
                    self.server["_clear_inflight_turn"](self.session)
                self.server["_emit"]("message.complete", self.sid, payload)
                self.server["_emit"](
                    "session.info",
                    self.sid,
                    self.server["_session_info"](None, self.session),
                )
            self.done.set()

    def run(self):
        try:
            if not self._active():
                return
            binding = self.binding
            self.host.submit_turn(
                {
                    "sid": self.sid,
                    "request_id": self.message_id,
                    "session_key": binding.session_id,
                    "text": self.receipt["text"],
                    "cols": self.session.get("cols", 80),
                    "managed_attempt": {
                        "agent_id": binding.agent_id,
                        "session_id": binding.session_id,
                        "soul_revision": binding.soul_revision,
                        "control_db": str(binding._db_path),
                        "storage_root": str(Path(binding.workspace).parent.parent),
                        "native_db": str(Path(self.db.db_path).resolve()),
                        "message_id": self.message_id,
                        "receipt_instance": self.receipt["instance"],
                        "deadline_monotonic": self.deadline,
                    },
                },
                on_complete=self.on_complete,
            )
            # A silent provider produces no RPC frames to validate. Observe owner
            # removal/purpose changes while waiting, then use normal hard cleanup.
            while not self.done.wait(0.25):
                if not self._active():
                    break
        except Exception as exc:
            self.stop(f"Managed worker failed: {exc}")


def submit_managed(server, rid, params, session, receipt, db):
    sid = params["session_id"]
    execution = ManagedExecution(server, sid, session, receipt, db)
    session["_managed_execution"] = execution
    session["_managed_host"] = execution.host
    session["running"] = True
    session["transport"] = server["current_transport"]() or session["transport"]
    server["_start_inflight_turn"](session, receipt["text"])
    thread = threading.Thread(
        target=execution.run, daemon=True, name="managed-native-host"
    )
    session["_run_thread"] = thread
    execution.timer.start()
    thread.start()
    return server["_ok"](rid, {"status": "streaming"})


def close_managed(server, sid, session, *, end_reason, predicate=None):
    """Retain the managed controller until a close has confirmed worker cleanup."""
    with session.setdefault("_managed_submit_lock", threading.RLock()):
        if server["_sessions"].get(sid) is not session:
            return False
        if predicate is not None and not predicate(session):
            return False
        if execution := session.get("_managed_execution"):
            execution.stop("Managed conversation closed")
            if not execution.done.is_set():
                return False
        with server["_session_resume_lock"], server["_sessions_lock"]:
            if server["_sessions"].get(sid) is not session:
                return False
            if predicate is not None and not predicate(session):
                return False
            popped = server["_pop_session_by_id"](sid)
        return server["_teardown_popped_session"](popped, end_reason=end_reason)
