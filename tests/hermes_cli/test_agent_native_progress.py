"""Progress delivery uses real scoped Plane HTTP and durable native receipts."""
from agent_native import work_state
from hermes_cli.kanban_db_connect import connect_closing, write_txn
from tests.hermes_cli.test_agent_native_work_effects import broker  # noqa: F401
from tests.hermes_cli.test_agent_native_work_focus import select


def test_selection_comment_is_attributed_and_replay_does_not_duplicate(broker):
    s = broker
    focus = select(s)
    comments = list(s.plane.comments.values())
    assert len(comments) == 1
    assert comments[0]['issue'] == focus['item_id']
    assert s.work['id'] in comments[0]['comment_html']
    assert s.root['id'] in comments[0]['comment_html']
    with connect_closing(s.db_path) as conn:
        report = work_state.read_work(conn, s.root['id'])['progress'][0]
    assert report['status'] == 'confirmed'
    assert report['comment_id'] == comments[0]['id']
    # A lost broker receipt must neither duplicate a comment nor rewind focus.
    with write_txn(s.conn):
        s.conn.execute('UPDATE agent_native_work_effects SET result=NULL WHERE run_id=? AND call_id=?', (s.work['id'], 'select-one'))
    assert select(s) == focus
    assert len(s.plane.comments) == 1


def test_lost_progress_response_stays_unknown_without_redelivery(broker):
    s = broker
    path = f"/api/v1/workspaces/{s.setup['workspace_slug']}/projects/{s.setup['project_id']}/work-items/{s.setup['discovery_item_id']}/comments/"
    s.plane.lose.add(('POST', path))
    focus = select(s)
    assert len(s.plane.comments) == 1
    report = work_state.read_work(s.conn, s.root['id'])['progress'][0]
    assert report['status'] == 'unknown'
    assert report['comment_id'] is None
    assert select(s) == focus
    assert sum(r['method'] == 'POST' and r['path'] == path for r in s.plane.requests) == 1
    # Reporting failure does not invent a work failure or success.
    assert work_state.read_work(s.conn, s.root['id'])['state'] == 'running'


def test_checkpoint_verbosity_filters_detail_but_never_blockers(broker):
    from agent_native.progress import get_settings, change_settings
    from agent_native.identity import OWNER
    from tests.hermes_cli.test_agent_native_work_effects import effect
    s = broker
    select(s)
    setting = get_settings(s.conn, s.root['id'])
    assert setting['verbosity'] == 'standard'
    def report(call, kind):
        return s.run._effect(s.conn, s.planning, effect(s, call, 'progress_report', {
            'item_id': s.setup['discovery_item_id'], 'kind': kind,
            'summary': 'Outline prepared', 'evidence': 'Three scenes outlined.', 'next_action': 'Draft the opening.'}))
    assert report('checkpoint', 'checkpoint')['status'] == 'confirmed'
    assert report('detail', 'detail')['status'] == 'suppressed'
    setting = change_settings(s.conn, actor=OWNER, agent_id=s.root['id'], verbosity='concise', expected_revision=setting['revision'])
    assert report('concise-check', 'checkpoint')['status'] == 'suppressed'
    assert report('blocker', 'blocker')['status'] == 'confirmed'
    setting = change_settings(s.conn, actor=OWNER, agent_id=s.root['id'], verbosity='detailed', expected_revision=setting['revision'])
    assert report('new-detail', 'detail')['status'] == 'confirmed'
    assert report('detail', 'detail')['status'] == 'suppressed'  # stable receipt, not reinterpreted
    assert len(s.plane.comments) == 4


def test_progress_cannot_target_unselected_items_or_bypass_verbosity(broker):
    import pytest
    from tests.hermes_cli.test_agent_native_work_effects import effect
    s = broker
    select(s)
    count = len(s.plane.requests)
    denied = s.run._effect(s.conn, s.planning, effect(
        s, 'foreign-progress', 'progress_report', {
            'item_id': '00000000-0000-4000-8000-000000000000',
            'kind': 'checkpoint', 'summary': 'Work', 'evidence': 'Evidence',
            'next_action': 'Next',
        }))
    assert denied['status'] == 'rejected'
    assert denied['error'] == 'PermissionError'
    rejected = s.run._effect(s.conn, s.planning, effect(s, 'raw-comment', arguments={
        'operation': 'comment.create',
        'arguments': {'item_id': s.setup['discovery_item_id'], 'text': 'Bypass'},
    }))
    assert rejected['status'] == 'rejected'
    assert rejected['tool'] == 'plane_operation_execute'
    assert len(s.plane.requests) == count
