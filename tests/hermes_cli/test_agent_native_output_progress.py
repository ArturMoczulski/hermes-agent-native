"""Saved evidence and reporting stay atomic; scoped Plane delivery stays one-shot."""
import sqlite3
import pytest
from agent_native import work_state
from tests.hermes_cli.test_agent_native_work_effects import broker, effect  # noqa: F401
from tests.hermes_cli.test_agent_native_work_focus import select


def publish(s, call='output-one', **changes):
    args = {'item_id': s.setup['discovery_item_id'], 'title': 'Findings <draft>',
            'content': '# Findings\nA saved result.', 'format': 'markdown', **changes}
    return s.run._effect(s.conn, s.planning, effect(s, call, 'output_publish', args))


def test_output_comments_keep_exact_versions_and_survive_receipt_replay(broker, monkeypatch):
    s = broker
    monkeypatch.setenv('HERMES_DASHBOARD_PUBLIC_URL', 'http://127.0.0.1:19221')
    first = publish(s)
    second = publish(s, 'output-two', output_id=first['output_id'], content='Revision two')
    comments = list(s.plane.comments.values())
    assert len(comments) == 2
    for version, comment in enumerate(comments, 1):
        assert f'output={first["output_id"]}&amp;version={version}' in comment['comment_html']
        assert 'Findings &lt;draft&gt;' in comment['comment_html']
        assert 'Open saved output' in comment['comment_html']
    assert publish(s) == first
    assert publish(s, 'output-two', output_id=first['output_id'], content='Revision two') == second
    assert len(s.plane.comments) == 2
    progress = work_state.read_work(s.conn, s.root['id'])['progress']
    assert len(progress) == 2 and all(r['status'] == 'confirmed' for r in progress)


def test_output_and_report_intent_roll_back_together(broker):
    s = broker
    s.conn.execute("CREATE TRIGGER reject_output_report BEFORE INSERT ON agent_native_progress WHEN NEW.source_id LIKE 'output:%' BEGIN SELECT RAISE(ABORT,'report unavailable'); END")
    with pytest.raises(sqlite3.IntegrityError):
        publish(s)
    assert work_state.read_work(s.conn, s.root['id'])['outputs'] == []
    assert not list(s.run.workspace.glob('outputs/*/v*.md'))
    assert not s.plane.comments


def test_file_free_result_is_reported_without_manufacturing_an_output(broker):
    s = broker
    result = s.run._effect(s.conn, s.planning, effect(s, 'waiting-result', 'result_record', {
        'item_id': s.setup['discovery_item_id'], 'summary': 'Need a comparison period.',
        'outcome': 'waiting', 'evaluation': 'Insufficient evidence for a trend.', 'outputs': []}))
    comments = list(s.plane.comments.values())
    assert len(comments) == 1
    assert 'Result recorded: waiting' in comments[0]['comment_html']
    assert 'not owner acceptance' in comments[0]['comment_html']
    assert result['id'] in comments[0]['comment_html']
    assert work_state.read_work(s.conn, s.root['id'])['outputs'] == []


def test_paused_outcome_is_queued_before_reporting_and_never_resends(broker):
    s = broker
    select(s)
    before = len(s.plane.requests)
    s.run.stop()
    assert len(s.plane.requests) == before  # process stop cannot wait for Plane
    assert work_state.read_work(s.conn, s.root['id'])['state'] == 'paused'
    reports = work_state.read_work(s.conn, s.root['id'])['progress']
    assert any(r['summary'] == 'Attempt paused' and r['status'] == 'pending' for r in reports)
    s.run._report_terminal()
    assert any('Attempt paused' in c['comment_html'] for c in s.plane.comments.values())
    count = len(s.plane.comments)
    s.run._report_terminal()
    assert len(s.plane.comments) == count


def test_comment_link_verification_rejects_rewritten_destination():
    from agent_native.plane_writes import _verify_applied, PlaneWriteError
    original = {'comment_html': '<p><a href="https://example.test/output?version=1">Open output</a></p>'}
    _verify_applied(original, original)
    with pytest.raises(PlaneWriteError):
        _verify_applied({'comment_html': original['comment_html'].replace('version=1', 'version=2')}, original)


def test_lost_output_notification_retains_saved_content_and_does_not_resend(broker):
    s = broker
    path = f"/api/v1/workspaces/{s.setup['workspace_slug']}/projects/{s.setup['project_id']}/work-items/{s.setup['discovery_item_id']}/comments/"
    s.plane.lose.add(('POST', path))
    output = publish(s)
    assert len(s.plane.comments) == 1
    report = work_state.read_work(s.conn, s.root['id'])['progress'][0]
    assert report['status'] == 'unknown'
    assert work_state.read_work(s.conn, s.root['id'])['outputs'][0]['output_id'] == output['output_id']
    assert publish(s) == output
    assert len(s.plane.comments) == 1


def test_link_column_upgrade_preserves_existing_delivery_records(broker):
    from hermes_cli.kanban_db_connect import _INITIALIZED_PATHS, connect_closing
    s = broker
    select(s)
    before = work_state.read_work(s.conn, s.root['id'])['progress']
    for column in ('link_url', 'link_label'):
        s.conn.execute(f'ALTER TABLE agent_native_progress DROP COLUMN {column}')
    path = s.conn.execute('PRAGMA database_list').fetchone()[2]
    _INITIALIZED_PATHS.discard(path)
    with connect_closing(s.db_path) as conn:
        assert work_state.read_work(conn, s.root['id'])['progress'] == before
    assert len(s.plane.comments) == 1


def test_terminal_reporting_cannot_outlive_its_purpose_revision(broker):
    s = broker
    select(s)
    s.run.stop()
    s.conn.execute('UPDATE agent_native_agents SET soul_revision=2 WHERE id=?', (s.root['id'],))
    before = len(s.plane.requests)
    s.run._report_terminal()
    assert len(s.plane.requests) == before
    assert any(r['status'] == 'pending' and r['summary'] == 'Attempt paused'
               for r in work_state.read_work(s.conn, s.root['id'])['progress'])
