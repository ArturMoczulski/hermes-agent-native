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
