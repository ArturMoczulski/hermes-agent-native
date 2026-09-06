"""Private ComputeHost bootstrap for an admitted managed message.

The web client never supplies this frame. Reissue the protected binding from
host storage and run the existing native deferred build and conversation loop.
"""

from pathlib import Path
import time


def build_session(server, transport, frame, sid):
    from agent.managed_chat_attempt import Attempt, bind_managed_attempt
    from agent_native.chat import issue_binding
    from agent_native.identity import OWNER
    from hermes_state import SessionDB
    from tui_gateway.transport import bind_transport, reset_transport

    data = frame["managed_attempt"]
    binding = issue_binding(
        actor=OWNER,
        agent_id=data["agent_id"],
        db_path=Path(data["control_db"]),
        storage_root=data["storage_root"],
    )
    if (
        binding.session_id != data["session_id"]
        or binding.soul_revision != data["soul_revision"]
        or frame.get("session_key") != binding.session_id
    ):
        raise PermissionError("Managed chat authority changed before worker startup")
    attempt = Attempt(
        binding.session_id,
        data["message_id"],
        data["receipt_instance"],
        data["deadline_monotonic"],
        Path(data["native_db"]),
    )
    if time.monotonic() >= attempt.deadline_monotonic:
        raise PermissionError("Managed conversation deadline expired during startup")
    db = SessionDB(attempt.db_path)
    with bind_managed_attempt(attempt, db=db):
        pass  # Keep this dedicated database pinned for every worker/background write.
    server._db = db
    transport.managed_chat = binding
    token = bind_transport(transport)
    try:
        history = db.get_messages_as_conversation(
            binding.session_id, repair_alternation=True
        )
        session = server._deferred_session_record(
            binding.session_id,
            cols=int(frame.get("cols") or 80),
            cwd=binding.workspace,
            history=history,
            lease=None,
        )
        session["_managed_attempt"] = attempt
        session["_managed_receipt_id"] = attempt.message_id
        session["_managed_receipt_instance"] = attempt.receipt_instance
        server._sessions[sid] = session
        server._start_agent_build(sid, session)
        if not session["agent_ready"].wait(
            max(0, attempt.deadline_monotonic - time.monotonic())
        ):
            raise TimeoutError("Managed conversation timed out during agent startup")
        if session.get("agent_error"):
            raise RuntimeError(session["agent_error"])
        if session.get("agent") is None:
            raise RuntimeError("Managed native engine did not initialize")
        return session
    finally:
        reset_transport(token)
