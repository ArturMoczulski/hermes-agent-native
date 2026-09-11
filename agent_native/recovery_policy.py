"""Bounded, deterministic retry policy for temporary managed-work failures."""

from datetime import datetime, timedelta, timezone
from uuid import NAMESPACE_URL, uuid5


# A retry loop is allowed to recover quickly, but it must not turn a short
# cadence into an unbounded model-spending loop. These are execution controls,
# not product estimates or cycle dates.
RECOVERY_WINDOW_SECONDS = 15 * 60
RECOVERY_BACKOFF_SECONDS = (5, 30, 120)
MAX_AUTOMATIC_RETRIES = len(RECOVERY_BACKOFF_SECONDS)


def _at(value):
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def recovery_identity(agent_id, previous_run_id):
    """Return the idempotency key for recovery after one failed attempt."""
    return str(uuid5(
        NAMESPACE_URL,
        'agent-native:automatic-recovery:' + agent_id + ':' + previous_run_id,
    ))


def recent_retry_attempts(conn, agent_id, *, now):
    """Return consecutive retryable failures inside the active recovery window."""
    now_value = _at(now)
    cutoff = now_value - timedelta(seconds=RECOVERY_WINDOW_SECONDS)
    attempts = []
    for row in conn.execute(
        'SELECT id,state,created_at,finished_at FROM agent_native_work_runs '
        'WHERE agent_id=? ORDER BY rowid DESC', (agent_id,),
    ).fetchall():
        run_id, state, created_at, finished_at = row
        if state != 'retryable_failure':
            break
        timestamp = _at(finished_at or created_at)
        if timestamp < cutoff:
            break
        # A useful result, output or purpose evaluation means the preceding
        # failure did not create an unproductive retry loop. Start a fresh
        # recovery window after that evidence.
        if (
            conn.execute(
                'SELECT 1 FROM agent_native_work_results WHERE run_id=?',
                (run_id,),
            ).fetchone()
            or conn.execute(
                'SELECT 1 FROM agent_native_output_versions WHERE run_id=?',
                (run_id,),
            ).fetchone()
            or conn.execute(
                'SELECT 1 FROM agent_native_purpose_evaluations WHERE run_id=?',
                (run_id,),
            ).fetchone()
        ):
            break
        attempts.append(row)
        if len(attempts) >= MAX_AUTOMATIC_RETRIES:
            break
    return attempts


def enforce_backoff(conn, agent_id, *, now):
    """Return whether retry admission is allowed, extending cadence when needed."""
    previous = conn.execute(
        'SELECT id,state,finished_at,created_at FROM agent_native_work_runs '
        'WHERE agent_id=? ORDER BY rowid DESC LIMIT 1', (agent_id,),
    ).fetchone()
    if not previous or previous[1] != 'retryable_failure':
        return True
    attempts = recent_retry_attempts(conn, agent_id, now=now)
    if not attempts:
        return True
    retry_number = len(attempts)
    delay = RECOVERY_BACKOFF_SECONDS[min(retry_number - 1, len(RECOVERY_BACKOFF_SECONDS) - 1)]
    finished = _at(previous[2] or previous[3])
    minimum_due = (finished + timedelta(seconds=delay)).isoformat()
    current = conn.execute(
        'SELECT next_due FROM agent_native_cadence WHERE agent_id=?',
        (agent_id,),
    ).fetchone()
    if not current:
        return True
    current_due = _at(current[0])
    due = max(current_due, _at(minimum_due))
    if due != current_due:
        conn.execute(
            'UPDATE agent_native_cadence SET next_due=? WHERE agent_id=?',
            (due.isoformat(), agent_id),
        )
    return _at(now) >= due
