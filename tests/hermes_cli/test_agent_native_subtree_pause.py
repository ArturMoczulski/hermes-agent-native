"""Owner Pause is a durable, atomic subtree lifecycle operation."""
import pytest

from agent_native import cadence
from agent_native.identity import OWNER, ConflictError, create_root, get_root
from agent_native.work_retry import retry_failed
from agent_native.work_state import configure as configure_work, request_pause, request_resume
from tests.hermes_cli.test_agent_native_api import BODY, URL, client  # noqa: F401
from tests.hermes_cli.test_agent_native_work_effects import broker  # noqa: F401


def create_child(conn, parent, request_id, name):
    return create_root(
        conn, actor=OWNER, request_id=request_id, name=name,
        purpose=f'Continue {name} work.', parent_id=parent['id'],
        work={'timeout_seconds': 120, 'max_iterations': 16},
    )


def test_pause_atomically_marks_and_stops_entire_descendant_subtree(broker):
    s = broker
    child = create_child(s.conn, s.root, 'pause-child', 'Child')
    grandchild = create_child(s.conn, child, 'pause-grandchild', 'Grandchild')
    for agent in (s.root, child, grandchild):
        cadence.configure(
            s.conn, actor=OWNER, agent_id=agent['id'], expected_revision=1,
            interval_seconds=60, enabled=True,
        )

    paused = request_pause(s.conn, actor=OWNER, agent_id=s.root['id'])

    assert paused['affected_agent_ids'] == [s.root['id'], child['id'], grandchild['id']]
    assert paused['stopping_agent_ids'] == [s.root['id']]
    for agent_id, expected_attempt in (
        (s.root['id'], 'stopping'), (child['id'], 'paused'),
        (grandchild['id'], 'paused'),
    ):
        current = get_root(s.conn, actor=OWNER, agent_id=agent_id)
        assert current['pause']['paused'] is True
        assert current['pause']['sources'][0]['source_agent_id'] == s.root['id']
        assert current['execution'] == 'paused'
        assert current['work']['state'] == expected_attempt
        assert current['cadence']['enabled'] is False

    repeated = request_pause(s.conn, actor=OWNER, agent_id=s.root['id'])
    assert repeated['affected_agent_ids'] == paused['affected_agent_ids']
    assert repeated['stopping_agent_ids'] == paused['stopping_agent_ids']
    assert repeated['sources'] == paused['sources']
    assert repeated['newly_paused_agent_ids'] == []


def test_subtree_pause_does_not_pause_ancestors_or_siblings(broker):
    s = broker
    child = create_child(s.conn, s.root, 'isolated-child', 'Child')
    grandchild = create_child(s.conn, child, 'isolated-grandchild', 'Grandchild')
    sibling = create_child(s.conn, s.root, 'isolated-sibling', 'Sibling')

    paused = request_pause(s.conn, actor=OWNER, agent_id=child['id'])

    assert paused['affected_agent_ids'] == [child['id'], grandchild['id']]
    assert get_root(s.conn, actor=OWNER, agent_id=s.root['id'])['pause']['paused'] is False
    assert get_root(s.conn, actor=OWNER, agent_id=sibling['id'])['pause']['paused'] is False


def test_paused_agent_rejects_new_work_cadence_and_children(broker):
    s = broker
    child = create_child(s.conn, s.root, 'guard-child', 'Child')
    request_pause(s.conn, actor=OWNER, agent_id=child['id'])

    with pytest.raises(ConflictError, match='paused'):
        cadence.configure(
            s.conn, actor=OWNER, agent_id=child['id'], expected_revision=1,
            interval_seconds=60, enabled=True,
        )
    with pytest.raises(ConflictError, match='paused'):
        create_child(s.conn, child, 'guard-grandchild', 'Grandchild')
    with pytest.raises(ConflictError, match='paused'):
        configure_work(
            s.conn, actor=OWNER, agent_id=child['id'], expected_revision=1,
            limits={'timeout_seconds': 60, 'max_iterations': 4},
        )


def test_paused_agent_rejects_retrying_failed_work(broker):
    s = broker
    child = create_child(s.conn, s.root, 'retry-child', 'Child')
    run_id = get_root(s.conn, actor=OWNER, agent_id=child['id'])['work']['id']
    s.conn.execute(
        "UPDATE agent_native_work_runs SET state='failed' WHERE id=?", (run_id,),
    )
    s.conn.commit()
    request_pause(s.conn, actor=OWNER, agent_id=child['id'])

    with pytest.raises(ConflictError, match='paused'):
        retry_failed(
            s.conn, actor=OWNER, agent_id=child['id'], expected_revision=1,
            expected_run_id=run_id,
        )


def test_pause_api_acknowledges_affected_subtree(client):
    parent = client.post(URL, json={
        **BODY, 'request_id': 'pause-api-parent',
        'work': {'timeout_seconds': 30, 'max_iterations': 2},
    }).json()
    child = client.post(URL, json={
        **BODY, 'request_id': 'pause-api-child', 'name': 'Child',
        'parent_id': parent['id'],
        'work': {'timeout_seconds': 30, 'max_iterations': 2},
    }).json()

    response = client.post(f"{URL}/{parent['id']}/work/pause")

    assert response.status_code == 200
    assert response.json()['pause']['paused'] is True
    assert response.json()['subtree_pause']['affected_agent_ids'] == [parent['id'], child['id']]
    assert client.get(f"{URL}/{child['id']}").json()['pause']['paused'] is True


def test_resume_removes_only_its_pause_cause_and_restores_original_cadence(broker):
    s = broker
    child = create_child(s.conn, s.root, 'resume-child', 'Child')
    grandchild = create_child(s.conn, child, 'resume-grandchild', 'Grandchild')
    # Created agents are gated on setup readiness; complete it so this test
    # isolates resume rather than the workspace-preparation gate.
    for agent in (child, grandchild):
        s.conn.execute(
            "UPDATE agent_native_setup SET status='ready', message='Ready.' WHERE agent_id=?",
            (agent['id'],),
        )
    for agent in (s.root, child, grandchild):
        cadence.configure(
            s.conn, actor=OWNER, agent_id=agent['id'], expected_revision=1,
            interval_seconds=60, enabled=True,
        )
    request_pause(s.conn, actor=OWNER, agent_id=s.root['id'])
    request_pause(s.conn, actor=OWNER, agent_id=child['id'])

    resumed = request_resume(s.conn, actor=OWNER, agent_id=s.root['id'])

    assert resumed['resumed_agent_ids'] == [s.root['id']]
    assert set(resumed['still_paused_agent_ids']) == {child['id'], grandchild['id']}
    assert resumed['cadence_restored_agent_ids'] == [s.root['id']]
    assert get_root(s.conn, actor=OWNER, agent_id=s.root['id'])['cadence']['enabled'] is True
    for agent_id in (child['id'], grandchild['id']):
        current = get_root(s.conn, actor=OWNER, agent_id=agent_id)
        assert current['pause']['sources'][0]['source_agent_id'] == child['id']
        assert current['cadence']['enabled'] is False

    child_resume = request_resume(s.conn, actor=OWNER, agent_id=child['id'])
    assert child_resume['resumed_agent_ids'] == [child['id'], grandchild['id']]
    assert child_resume['still_paused_agent_ids'] == []
    assert set(child_resume['cadence_restored_agent_ids']) == {child['id'], grandchild['id']}
    queued = cadence.queue_due(s.conn, now='2099-01-01T00:00:00+00:00')
    assert len(queued) == 2
    assert get_root(s.conn, actor=OWNER, agent_id=child['id'])['work']['state'] == 'queued'
    assert get_root(s.conn, actor=OWNER, agent_id=grandchild['id'])['work']['state'] == 'queued'
    assert request_resume(s.conn, actor=OWNER, agent_id=child['id'])['affected_agent_ids'] == []


def test_resume_keeps_cadence_off_when_it_was_off_before_pause(broker):
    s = broker
    child = create_child(s.conn, s.root, 'manual-child', 'Manual child')
    # create_root enables cadence by default; a manual child has it off.
    cadence.configure(
        s.conn, actor=OWNER, agent_id=child['id'], expected_revision=1,
        interval_seconds=60, enabled=False,
    )
    request_pause(s.conn, actor=OWNER, agent_id=child['id'])

    resumed = request_resume(s.conn, actor=OWNER, agent_id=child['id'])

    assert resumed['resumed_agent_ids'] == [child['id']]
    assert resumed['cadence_restored_agent_ids'] == []
    assert get_root(s.conn, actor=OWNER, agent_id=child['id'])['cadence']['enabled'] is False


def test_resume_api_returns_subtree_acknowledgment(client):
    parent = client.post(URL, json={
        **BODY, 'request_id': 'resume-api-parent',
        'work': {'timeout_seconds': 30, 'max_iterations': 2},
    }).json()
    child = client.post(URL, json={
        **BODY, 'request_id': 'resume-api-child', 'name': 'Child',
        'parent_id': parent['id'],
        'work': {'timeout_seconds': 30, 'max_iterations': 2},
    }).json()
    client.post(f"{URL}/{parent['id']}/work/pause")

    response = client.post(f"{URL}/{parent['id']}/work/resume")

    assert response.status_code == 200
    assert response.json()['pause']['paused'] is False
    assert response.json()['subtree_resume']['resumed_agent_ids'] == [parent['id'], child['id']]
    assert client.get(f"{URL}/{child['id']}").json()['pause']['paused'] is False
