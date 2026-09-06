"""Private host context for one bounded managed conversation attempt.

The supervisor supplies this over private IPC, never from model/browser fields.
A dedicated worker's SessionDB stays pinned to that attempt until closed, so
background callbacks cannot lose the fence when the calling context unwinds.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import json
import math
from pathlib import Path
import time
from uuid import UUID

_attempt = ContextVar("managed_chat_attempt", default=None)


@dataclass(frozen=True)
class Attempt:
    session_id: str
    message_id: str
    receipt_instance: str
    deadline_monotonic: float
    db_path: Path

    def __post_init__(self):
        if not isinstance(self.session_id, str) or not self.session_id:
            raise ValueError("Managed attempt requires a native session")
        for value in (self.message_id, self.receipt_instance):
            if not isinstance(value, str) or str(UUID(value)) != value:
                raise ValueError("Managed attempt requires canonical host UUIDs")
        if type(self.deadline_monotonic) not in (int, float) or not math.isfinite(
            self.deadline_monotonic
        ):
            raise ValueError("Managed attempt requires a finite monotonic deadline")
        if not isinstance(self.db_path, Path) or not self.db_path.is_absolute():
            raise ValueError(
                "Managed attempt requires an absolute native database path"
            )


def current_attempt(agent=None):
    if agent is not None:
        return vars(agent).get("_managed_chat_attempt") or _attempt.get()
    return _attempt.get()


@contextmanager
def bind_managed_attempt(attempt, *, db=None):
    if not isinstance(attempt, Attempt):
        raise PermissionError("Host-issued managed attempt required")
    if db is not None:
        previous = getattr(db, "_managed_chat_attempt", None)
        if previous is not None and previous != attempt:
            raise PermissionError("Managed worker database cannot change attempts")
        _check_db_path(db, attempt)
        db._managed_chat_attempt = attempt
    token = _attempt.set(attempt)
    try:
        yield attempt
    finally:
        _attempt.reset(token)


def _check_db_path(db, attempt):
    if Path(db.db_path).resolve() != attempt.db_path.resolve():
        raise PermissionError("Managed attempt native database does not match")


def _check_deadline(attempt):
    if time.monotonic() >= attempt.deadline_monotonic:
        raise PermissionError("Managed conversation deadline expired")


def _check_receipt(conn, attempt, session_id):
    _check_deadline(attempt)
    if session_id != attempt.session_id:
        raise PermissionError("Managed attempt session cannot be reassigned")

    def load(key):
        row = conn.execute(
            "SELECT value FROM state_meta WHERE key = ?", (key,)
        ).fetchone()
        try:
            return json.loads(row[0]) if row is not None else None
        except (TypeError, ValueError) as exc:
            raise PermissionError("Managed attempt receipt is invalid") from exc

    receipt = load(f"managed_prompt:{session_id}:{attempt.message_id}")
    active = load(f"managed_prompt_active:{session_id}")
    if (
        not isinstance(receipt, dict)
        or receipt.get("id") != attempt.message_id
        or receipt.get("instance") != attempt.receipt_instance
        or receipt.get("deadline_monotonic") != attempt.deadline_monotonic
        or receipt.get("status") not in ("accepted", "running")
        or active != attempt.message_id
    ):
        raise PermissionError("Managed conversation attempt is no longer active")
    _check_deadline(attempt)


def assert_active(agent=None):
    attempt = current_attempt(agent)
    if attempt is None:
        return None
    _check_deadline(attempt)
    if agent is not None:
        db = getattr(agent, "_session_db", None)
        if db is None:
            raise PermissionError("Managed attempt requires native durable storage")
        _check_db_path(db, attempt)
        with db._read_ctx() as conn:
            _check_receipt(conn, attempt, agent.session_id)
    return attempt


def assert_write_allowed(db, conn, session_id):
    attempt = getattr(db, "_managed_chat_attempt", None) or current_attempt()
    if attempt is None:
        return
    ambient = current_attempt()
    if ambient is not None and ambient != attempt:
        raise PermissionError("Managed database belongs to another attempt")
    _check_db_path(db, attempt)
    if not conn.in_transaction:
        raise PermissionError("Managed write guard requires the native transaction")
    _check_receipt(conn, attempt, session_id)
