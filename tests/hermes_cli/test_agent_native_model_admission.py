"""Work admission captures its model before any preparation or worker startup."""
from types import SimpleNamespace
from threading import Event

from tests.hermes_cli.test_agent_native_model_runtime import configured_profile  # noqa: F401


def test_preparing_work_captures_selection_before_worker_start(configured_profile, tmp_path, monkeypatch):
    from agent_native import identity, model_settings, work_service
    from hermes_cli.kanban_db_connect import connect_closing

    db_path = tmp_path / 'control.db'
    with connect_closing(db_path) as conn:
        root = identity.create_root(conn, actor=identity.OWNER, request_id='model-admission',
            name='Analyst', purpose='Analyze the supplied material.',
            work={'timeout_seconds': 120, 'max_iterations': 10})
        conn.execute("UPDATE agent_native_setup SET status='ready',phase='ready' WHERE agent_id=?", (root['id'],))
    captured = []
    class BeforeWorker:
        def __init__(self, service, work):
            self.work = work
            self.ended = Event()
            self.thread = SimpleNamespace(start=lambda: captured.append(dict(work)))
    monkeypatch.setattr(work_service, '_Run', BeforeWorker)
    service = work_service.WorkService(db_path, tmp_path / 'profile' / 'agent-native')
    service.tick()
    assert len(captured) == 1
    work = captured[0]
    with connect_closing(db_path) as conn:
        snapshot = model_settings.read_attempt(conn, 'work', work['id'])
        assert snapshot is not None, 'Preparing work must persist model selection before starting a worker'
        assert work['model_selection'] == snapshot
        assert snapshot['provider'] == 'custom:first-fixture'
        assert snapshot['model'] == 'fixture-small'
        current = model_settings.get_selection(conn, root['id'])
        model_settings.change_selection(conn, actor=identity.OWNER, agent_id=root['id'],
            expected_revision=current['revision'],
            choice={'provider': 'custom:second-fixture', 'model': 'fixture-other'})
        assert model_settings.read_attempt(conn, 'work', work['id']) == snapshot
        assert work['model_selection'] == snapshot
