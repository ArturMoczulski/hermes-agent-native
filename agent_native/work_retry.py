"""Owner-requested fresh attempts after known failure, never effect redelivery."""
import json
from uuid import NAMESPACE_URL, uuid4, uuid5

from agent_native.identity import ConflictError, _now, _require_owner, require_active
from hermes_cli.kanban_db_connect import write_txn


def retry_failed(conn, *, actor, agent_id, expected_revision, expected_run_id):
    _require_owner(actor)
    from agent_native.work_state import event
    recovery_id = str(uuid5(NAMESPACE_URL, 'agent-native:failed-work-retry:' + expected_run_id))
    with write_txn(conn):
        require_active(conn, agent_id)
        from agent_native.subtree_lifecycle import require_not_paused
        require_not_paused(conn, agent_id)
        root = conn.execute('SELECT soul_revision FROM agent_native_agents WHERE id=?', (agent_id,)).fetchone()
        if not root:
            raise KeyError(agent_id)
        previous = conn.execute(
            'SELECT activation_id,soul_revision,limits,state FROM agent_native_work_runs WHERE id=? AND agent_id=?',
            (expected_run_id, agent_id),
        ).fetchone()
        if root[0] != expected_revision or (previous and previous[1] != expected_revision):
            raise ConflictError('Purpose changed; reload before retrying work')
        if not previous or previous[3] != 'failed':
            raise ConflictError('Only a failed attempt can be retried after owner review')
        # Stable identity makes a repeated owner request harmless even after the
        # recovery finishes or another scheduled attempt is subsequently created.
        recovered = conn.execute(
            'SELECT id,session_id,state,limits FROM agent_native_work_runs WHERE id=? AND agent_id=?',
            (recovery_id, agent_id),
        ).fetchone()
        if not recovered:
            latest = conn.execute('SELECT id FROM agent_native_work_runs WHERE agent_id=? ORDER BY rowid DESC LIMIT 1', (agent_id,)).fetchone()
            if latest[0] != expected_run_id:
                raise ConflictError('A newer work attempt exists; reload before retrying')
            if conn.execute("SELECT 1 FROM agent_native_work_runs WHERE agent_id=? AND state IN ('queued','preparing','running','stopping')", (agent_id,)).fetchone():
                raise ConflictError('An active work attempt already exists')
            from agent_native.delivery_barrier import unresolved_terminal_notices, record_notices
            notices = unresolved_terminal_notices(conn, agent_id)
            from agent_native.model_settings import get_selection
            from agent_native.model_runtime import validate_choice
            validate_choice(get_selection(conn, agent_id))
            session_id = 'an_work_' + uuid4().hex
            conn.execute(
                'INSERT INTO agent_native_work_runs(id,agent_id,activation_id,soul_revision,session_id,limits,state,created_at) VALUES(?,?,?,?,?,?,?,?)',
                (recovery_id, agent_id, previous[0], expected_revision, session_id, previous[2], 'queued', _now()),
            )
            event(conn, recovery_id, 'work.queued', 'Owner requested recovery of failed attempt ' + expected_run_id + '; inspect current work and continue without replaying prior effects.')
            record_notices(conn, recovery_id, notices)
            recovered = (recovery_id, session_id, 'queued', previous[2])
    return dict(id=recovered[0], session_id=recovered[1], state=recovered[2], limits=json.loads(recovered[3]))
