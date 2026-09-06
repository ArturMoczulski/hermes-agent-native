"""Managed message admission receipts in native SessionDB scheduler metadata.

The accepted body is durable before launch. Receipts are not a second transcript:
Hermes still owns user/assistant rows, correlated by platform_message_id. Unknown
prior-process outcomes are never replayed as new model work.
"""

import hashlib
import json
import threading
import time
from uuid import UUID, uuid4

_INSTANCE = str(uuid4())
_PENDING = {"accepted", "running"}


def validate_id(value):
    if not isinstance(value, str) or len(value) != 36:
        raise ValueError("Managed chat requires a stable client_message_id UUID")
    try:
        if str(UUID(value)) != value.lower():
            raise ValueError
    except ValueError as exc:
        raise ValueError(
            "Managed chat requires a stable client_message_id UUID"
        ) from exc
    return value.lower()


def _keys(binding, message_id):
    return (
        f"managed_prompt:{binding.session_id}:{message_id}",
        f"managed_prompt_active:{binding.session_id}",
    )


def _load(conn, key):
    row = conn.execute("SELECT value FROM state_meta WHERE key = ?", (key,)).fetchone()
    return json.loads(row[0]) if row is not None else None


def _save(conn, key, value):
    conn.execute(
        "INSERT INTO state_meta (key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, json.dumps(value)),
    )


def _recover(conn, key, active_key):
    receipt = _load(conn, key)
    if receipt and receipt["status"] in _PENDING and receipt["instance"] != _INSTANCE:
        receipt.update(
            status="unknown",
            reason="The server restarted before the outcome was recorded. Inspect the conversation before sending a new message.",
            updated_at=time.time(),
        )
        _save(conn, key, receipt)
        if _load(conn, active_key) == receipt["id"]:
            conn.execute("DELETE FROM state_meta WHERE key = ?", (active_key,))
    return receipt


def claim(db, binding, message_id, text, *, runtime_busy=False):
    message_id = validate_id(message_id)
    if not isinstance(text, str) or not text.strip() or len(text) > 32000:
        raise ValueError("Managed message must contain at most 32000 characters")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    key, active_key = _keys(binding, message_id)

    def write(conn):
        binding.validate()
        previous = _recover(conn, key, active_key)
        if previous:
            if previous["hash"] != digest or previous["text"] != text:
                raise ValueError(
                    "client_message_id was already used for different message text"
                )
            return previous, False
        busy = runtime_busy
        if active_id := _load(conn, active_key):
            active = _recover(conn, _keys(binding, active_id)[0], active_key)
            busy = busy or bool(active and active["status"] in _PENDING)
        receipt = {
            "id": message_id,
            "status": "error" if busy else "accepted",
            "text": text,
            "hash": digest,
            "instance": _INSTANCE,
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        if busy:
            # A durable rejection prevents an old delayed retry from becoming a
            # new accepted turn after the other owner's message finishes. It
            # never takes or releases the active message's admission pointer.
            receipt["reason"] = (
                "Managed chat is busy; this message was not accepted. Wait for the current reply before trying again."
            )
        _save(conn, key, receipt)
        if not busy:
            _save(conn, active_key, message_id)
        return receipt, not busy

    return db._execute_write(write)


def read(db, binding, message_id):
    key, active_key = _keys(binding, validate_id(message_id))

    def load(conn):
        binding.validate()
        return _recover(conn, key, active_key)

    return db._execute_write(load)


def _update(db, binding, message_id, status, reason=None):
    key, active_key = _keys(binding, message_id)

    def write(conn):
        receipt = _load(conn, key)
        if (
            not receipt
            or receipt["instance"] != _INSTANCE
            or receipt["status"] not in _PENDING
        ):
            return receipt
        receipt.update(status=status, updated_at=time.time())
        if reason:
            receipt["reason"] = reason
        _save(conn, key, receipt)
        if status not in _PENDING and _load(conn, active_key) == message_id:
            conn.execute("DELETE FROM state_meta WHERE key = ?", (active_key,))
        return receipt

    return db._execute_write(write)


def public(receipt, *, include_text=False):
    if receipt is None:
        return None
    keys = (
        ("id", "status", "reason", "text")
        if include_text
        else ("id", "status", "reason")
    )
    return {k: receipt[k] for k in keys if k in receipt}


def update_for_session(server, session, status, reason=None):
    if not (binding := session.get("managed_chat")) or not (
        message_id := session.get("_managed_receipt_id")
    ):
        return None
    db = server["_get_db"]()
    if db is None:
        raise RuntimeError("Native chat storage is unavailable")
    return _update(db, binding, message_id, status, reason)


def _read_runtime_receipt(server, db, binding, session, message_id):
    receipt = read(db, binding, message_id)
    if receipt and receipt["status"] in _PENDING:
        # Caller holds the admission lock. The inner native turn publishes its
        # thread under _sessions_lock; do not mistake that handoff for a crash.
        with server["_sessions_lock"]:
            thread = session.get("_run_thread")
            active = (
                session.get("_managed_receipt_id") == message_id
                and session.get("running")
                and thread is not None
                and thread.is_alive()
            )
        if not active:
            receipt = _update(
                db,
                binding,
                message_id,
                "unknown",
                "The accepted message has no live execution or recorded outcome. Inspect the conversation before sending a new message.",
            )
    return receipt


def submit(server, rid, params, run_native):
    from hermes_cli.input_sanitize import sanitize_user_prompt_text

    session, error = server["_sess_nowait"](params, rid)
    if error:
        return error
    binding = session.get("managed_chat")
    if binding is None:
        return run_native(rid, params)
    message_id = validate_id(params.get("client_message_id"))
    text = sanitize_user_prompt_text(params["text"])
    # Serialize only admission, never the model run. SQLite's atomic active pointer
    # additionally protects the same stored conversation across host processes.
    with session.setdefault("_managed_submit_lock", threading.RLock()):
        db = server["_get_db"]()
        if db is None:
            return server["_err"](rid, 5072, "Native chat storage is unavailable")
        try:
            _read_runtime_receipt(server, db, binding, session, message_id)
            receipt, created = claim(
                db, binding, message_id, text, runtime_busy=bool(session.get("running"))
            )
        except RuntimeError as exc:
            return server["_err"](rid, 4091, str(exc))
        except ValueError as exc:
            return server["_err"](rid, 4092, str(exc))
        if not created:
            return server["_ok"](
                rid, {"status": "streaming", "receipt": public(receipt)}
            )
        session["_managed_receipt_id"] = message_id
        try:
            response = run_native(rid, {**params, "text": text})
        except Exception as exc:
            update_for_session(server, session, "error", str(exc))
            raise
        if response.get("error"):
            receipt = update_for_session(
                server, session, "error", response["error"]["message"]
            )
            response["error"]["data"] = {"receipt": public(receipt)}
        else:
            # A fast local reply can settle before admission returns.
            response["result"]["receipt"] = public(read(db, binding, message_id))
        return response


def receipt_rpc(server, rid, params):
    session, error = server["_sess_nowait"](params, rid)
    if error:
        return error
    if not (binding := session.get("managed_chat")):
        return server["_err"](
            rid, 4030, "Message receipts are available in managed chat only"
        )
    db = server["_get_db"]()
    if db is None:
        return server["_err"](rid, 5072, "Native chat storage is unavailable")
    with session.setdefault("_managed_submit_lock", threading.RLock()):
        receipt = _read_runtime_receipt(
            server, db, binding, session, params["client_message_id"]
        )
    return server["_ok"](rid, {"receipt": public(receipt, include_text=True)})


def record_completion(server, frame):
    if frame.get("method") != "event":
        return
    params = frame.get("params") or {}
    if params.get("type") != "message.complete":
        return
    session = server["_sessions"].get(params.get("session_id"))
    if not session or not session.get("managed_chat"):
        return
    payload = params.setdefault("payload", {})
    status = "complete" if payload.get("status") == "complete" else "error"
    reason = (
        None
        if status == "complete"
        else str(
            payload.get("error") or payload.get("text") or "Reply did not complete"
        )
    )
    receipt = update_for_session(server, session, status, reason)
    if receipt:
        payload["receipt"] = public(receipt)
