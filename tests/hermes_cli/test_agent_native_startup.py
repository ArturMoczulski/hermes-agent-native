"""Durable setup orchestration over real SQLite and private files."""
from contextlib import contextmanager
from uuid import uuid4

import pytest

from agent_native.identity import OWNER, create_root, get_root, revise_soul
from hermes_cli.kanban_db_connect import connect_closing


@pytest.fixture
def setup(tmp_path):
    with connect_closing(tmp_path / 'control.db') as conn:
        root = create_root(conn, actor=OWNER, request_id='writer', name='Writer', purpose='Write fantasy stories.')
        yield conn, root, tmp_path


class Planning:
    def __init__(self):
        self.calls = []
        self.workspace = {'id': str(uuid4()), 'slug': 'an-writer'}
        self.project = {'id': str(uuid4())}
        self.item = {'id': str(uuid4())}
        self.on_item = None

    @contextmanager
    def open(self):
        yield self

    def ensure_workspace(self, **kwargs):
        self.calls.append(('workspace', kwargs))
        return self.workspace

    def ensure_project(self, **kwargs):
        self.calls.append(('project', kwargs))
        return self.project

    def ensure_discovery(self, **kwargs):
        self.calls.append(('discovery', kwargs))
        if self.on_item:
            self.on_item()
        return self.item


def run(conn, root, home, planning):
    from agent_native.startup import prepare
    return prepare(conn, actor=OWNER, agent_id=root['id'], home=home,
                   open_plane=planning.open, plane_identity=('http://localhost:19230', 'host-owner'))


def test_creation_queues_one_setup_in_same_transaction(setup):
    conn, root, _ = setup
    assert root.get('setup') is not None, 'Creation must durably queue setup'
    assert root['setup']['status'] == 'queued'
    assert root['setup']['activation_id'] == root['startup']['id']
    assert create_root(conn, actor=OWNER, request_id='writer', name='Writer', purpose=root['purpose'])['setup'] == root['setup']


def test_setup_checkpoints_files_and_planning_without_starting_model(setup):
    conn, root, home = setup
    planning = Planning()
    run(conn, root, home, planning)
    current = get_root(conn, actor=OWNER, agent_id=root['id'])
    assert current['setup']['status'] == 'ready'
    assert current['setup']['discovery_item_id'] == planning.item['id']
    assert current['execution'] == 'not_started'
    assert (home / 'agents' / root['id'] / 'workspace' / 'PRACTICES.md').is_file()
    run(conn, root, home, planning)
    assert len(planning.calls) == 3


def test_unknown_item_result_is_reconciled_without_permission_to_resend(setup):
    from agent_native.startup import retry_setup
    from agent_native.plane_setup import SetupError
    conn, root, home = setup
    planning = Planning()
    def lost():
        raise SetupError('Plane response could not be confirmed', uncertain=True)
    planning.on_item = lost
    run(conn, root, home, planning)
    assert get_root(conn, actor=OWNER, agent_id=root['id'])['setup']['status'] == 'unresolved'
    planning.on_item = None
    retry_setup(conn, actor=OWNER, agent_id=root['id'])
    run(conn, root, home, planning)
    assert [name for name, _ in planning.calls] == ['workspace', 'project', 'discovery', 'workspace', 'project', 'discovery']
    assert planning.calls[-1][1]['allow_create'] is False
    assert get_root(conn, actor=OWNER, agent_id=root['id'])['setup']['status'] == 'ready'


def test_interrupted_host_recovers_attempt_marker_after_reopen(setup):
    conn, root, home = setup
    planning = Planning()
    def die():
        raise SystemExit('simulate host exit before receipt')
    planning.on_item = die
    with pytest.raises(SystemExit):
        run(conn, root, home, planning)
    planning.on_item = None
    with connect_closing(home / 'control.db') as fresh:
        run(fresh, root, home, planning)
    assert planning.calls[-1][1]['allow_create'] is False


def test_purpose_change_during_setup_prevents_ready_and_next_effect(setup):
    conn, root, home = setup
    planning = Planning()
    original = planning.ensure_workspace
    def changed(**kwargs):
        result = original(**kwargs)
        revise_soul(conn, actor=OWNER, agent_id=root['id'], expected_revision=1, purpose='New purpose')
        return result
    planning.ensure_workspace = changed
    run(conn, root, home, planning)
    current = get_root(conn, actor=OWNER, agent_id=root['id'])
    assert current['setup']['status'] == 'superseded'
    assert [name for name, _ in planning.calls] == ['workspace']


def test_missing_config_reports_blocker_and_preserves_files(setup):
    from agent_native.startup import prepare, retry_setup
    conn, root, home = setup
    prepare(conn, actor=OWNER, agent_id=root['id'], home=home)
    current = get_root(conn, actor=OWNER, agent_id=root['id'])
    assert current['setup']['status'] == 'blocked'
    assert current['setup']['files_ready']
    note = home / 'agents' / root['id'] / 'workspace' / 'note.md'
    note.write_text('keep this')
    retry_setup(conn, actor=OWNER, agent_id=root['id'])
    prepare(conn, actor=OWNER, agent_id=root['id'], home=home)
    assert note.read_text() == 'keep this'


def test_untrusted_retry_cannot_queue_setup(setup):
    from agent_native.startup import retry_setup
    conn, root, _ = setup
    with pytest.raises(PermissionError):
        retry_setup(conn, actor='owner', agent_id=root['id'])


def test_other_host_cannot_process_same_setup_while_lock_is_held(setup):
    from agent_native.plane_operation_lock import operation_lock, OperationBusy
    conn, root, home = setup
    planning = Planning()
    with operation_lock(conn, root['startup']['id']):
        with connect_closing(home / 'control.db') as other:
            with pytest.raises(OperationBusy):
                run(other, root, home, planning)
    assert planning.calls == []
    assert not (home / 'agents').exists()


def test_correcting_first_login_identity_after_no_effects_is_retryable(setup):
    from agent_native.startup import prepare, retry_setup
    from agent_native.plane_setup import SetupError
    conn, root, home = setup
    @contextmanager
    def wrong_account():
        raise SetupError('Unexpected host account', uncertain=False)
        yield
    prepare(conn, actor=OWNER, agent_id=root['id'], home=home,
            open_plane=wrong_account, plane_identity=('http://localhost:19230', 'wrong-owner'))
    retry_setup(conn, actor=OWNER, agent_id=root['id'])
    planning = Planning()
    run(conn, root, home, planning)
    assert get_root(conn, actor=OWNER, agent_id=root['id'])['setup']['status'] == 'ready'


def test_purpose_edit_immediately_supersedes_ready_setup(setup):
    conn, root, home = setup
    run(conn, root, home, Planning())
    updated = revise_soul(conn, actor=OWNER, agent_id=root['id'], expected_revision=1, purpose='Write poetry')
    assert updated['setup']['status'] == 'superseded'


def test_shutdown_guard_before_first_write_allows_safe_resume(setup):
    from agent_native.startup import prepare
    conn, root, home = setup
    planning = Planning()
    stopping = [False]
    original = planning.ensure_workspace
    def shutdown_before_post(**kwargs):
        stopping[0] = True
        planning.before_write()
        return original(**kwargs)
    planning.ensure_workspace = shutdown_before_post
    prepare(conn, actor=OWNER, agent_id=root['id'], home=home,
            open_plane=planning.open, plane_identity=('http://localhost:19230', 'host-owner'),
            stopped=lambda: stopping[0])
    planning.ensure_workspace = original
    run(conn, root, home, planning)
    assert planning.calls[0][1]['allow_create'] is True


def test_late_setup_receipt_cannot_revive_superseded_request(setup):
    from agent_native.startup import _update
    conn, root, home = setup
    run(conn, root, home, Planning())
    revise_soul(conn, actor=OWNER, agent_id=root['id'], expected_revision=1, purpose='Changed purpose')
    # A delayed host checkpoint must retain its resource receipt without
    # overwriting the owner's newer terminal state.
    _update(conn, root['id'], status='ready', message='Late successful receipt')
    assert get_root(conn, actor=OWNER, agent_id=root['id'])['setup']['status'] == 'superseded'
