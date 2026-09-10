"""One host-derived answer to whether an agent may perform automatic work."""
from datetime import datetime, timedelta, timezone


def _decision(state, *, may_start=False, blocker=None, release=None, actor=None):
    return {
        'state': state,
        'may_start': may_start,
        'blocker': blocker,
        'release_condition': release,
        'responsible_actor': actor,
    }


def automatic_work(conn, agent_id, *, now=None, busy=False):
    """Return the authoritative, read-only automatic-work readiness decision."""
    agent = conn.execute(
        'SELECT soul_revision FROM agent_native_agents WHERE id=?', (agent_id,),
    ).fetchone()
    if not agent:
        raise KeyError(agent_id)
    if conn.execute('SELECT 1 FROM agent_native_removals WHERE agent_id=?', (agent_id,)).fetchone():
        return _decision('removed', blocker='Agent was removed.')
    if conn.execute('SELECT 1 FROM agent_native_retirements WHERE agent_id=?', (agent_id,)).fetchone():
        return _decision('retired', blocker='Agent was retired.')
    pause = conn.execute(
        'SELECT source_agent_id FROM agent_native_agent_pauses WHERE agent_id=? '
        'ORDER BY requested_at,source_agent_id LIMIT 1', (agent_id,),
    ).fetchone()
    if pause:
        return _decision('owner_paused', blocker='Automatic work is paused.',
                         release='Resume the applicable pause.', actor='owner')
    setup = conn.execute(
        'SELECT status,message FROM agent_native_setup WHERE agent_id=?', (agent_id,),
    ).fetchone()
    if setup and setup[0] != 'ready':
        return _decision('setup', blocker=setup[1] or 'Agent setup is not ready.',
                         release='Complete or repair agent setup.', actor='framework')
    work = conn.execute(
        'SELECT id,state,finished_at FROM agent_native_work_runs WHERE agent_id=? '
        'ORDER BY rowid DESC LIMIT 1', (agent_id,),
    ).fetchone()
    if not work:
        return _decision('not_configured', blocker='Bounded work is not configured.',
                         release='Configure work for this agent.', actor='owner')
    if busy or work[1] in ('queued', 'preparing', 'running', 'stopping'):
        return _decision('working')
    concern = conn.execute(
        "SELECT summary FROM agent_native_progress_concerns WHERE agent_id=? AND status='open' "
        'ORDER BY created_at DESC,id DESC LIMIT 1', (agent_id,),
    ).fetchone()
    if concern:
        return _decision('owner_attention', blocker=concern[0],
                         release='Review the progress concern and provide direction.', actor='owner')
    if work[1] == 'unknown':
        return _decision('framework_reconciliation', blocker='A work outcome is uncertain.',
                         release='Reconcile the uncertain effect before continuing.', actor='framework')
    if work[1] == 'failed':
        return _decision('owner_attention', blocker='The latest attempt failed.',
                         release='Review the failure and retry the work.', actor='owner')
    cadence = conn.execute(
        'SELECT enabled,interval_seconds,next_due FROM agent_native_cadence WHERE agent_id=?',
        (agent_id,),
    ).fetchone()
    if not cadence or not cadence[0]:
        return _decision('automatic_off', blocker='Automatic work is disabled.',
                         release='Enable automatic work.', actor='owner')
    from agent_native.acceptance import pending_required
    reviews = pending_required(conn, agent_id)
    if reviews:
        return _decision('waiting_owner_review', blocker='A required output review is unanswered.',
                         release='Accept the output or request a revision.', actor='owner')
    evaluation = conn.execute(
        'SELECT record_json FROM agent_native_purpose_evaluations WHERE agent_id=? '
        'ORDER BY created_at DESC,id DESC LIMIT 1', (agent_id,),
    ).fetchone()
    if evaluation:
        import json
        record = json.loads(evaluation[0])
        if record.get('judgment') == 'clarify':
            question_id = record.get('question_id')
            question = conn.execute(
                'SELECT question,answer FROM agent_native_questions WHERE id=? AND agent_id=?',
                (question_id, agent_id),
            ).fetchone()
            if question and question[1] is None:
                return _decision('waiting_owner_answer', blocker=question[0],
                                 release='Answer the agent question.', actor='owner')
    from agent_native.delivery_barrier import unresolved_terminal_notices
    try:
        unresolved_terminal_notices(conn, agent_id)
    except Exception as exc:
        from agent_native.identity import ConflictError
        if not isinstance(exc, ConflictError):
            raise
        return _decision('framework_reconciliation', blocker=str(exc),
                         release='Reconcile the unresolved delivery before continuing.', actor='framework')
    now_value = datetime.fromisoformat(now) if now else datetime.now(timezone.utc)
    due = datetime.fromisoformat(cadence[2])
    wake = conn.execute(
        'SELECT 1 FROM agent_native_cadence_wakes WHERE agent_id=?', (agent_id,),
    ).fetchone()
    if not wake and work[2]:
        due = max(due, datetime.fromisoformat(work[2]) + timedelta(seconds=cadence[1]))
    if now_value < due:
        return _decision('scheduled', blocker='Waiting for the next configured check-in.',
                         release='The cadence becomes due at ' + cadence[2] + '.', actor='framework')
    return _decision('ready', may_start=True)
