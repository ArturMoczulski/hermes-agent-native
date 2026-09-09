"""Writer planning through real private setup, SQLite grants and external HTTP."""
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from agent_native.identity import OWNER, create_root, revise_soul
from agent_native.plane_write_access import revoke_writes
from agent_native.plane_write_journal import MutationJournal, ReplayError
from agent_native.startup import prepare, read_setup
from hermes_cli.kanban_db_connect import connect_closing
from tests.hermes_cli.writer_plane_fixture import writer_plane_server


def uid():
    return str(uuid4())


@pytest.fixture
def writer(tmp_path):
    with writer_plane_server() as plane:
        home = tmp_path / 'agent-native'
        home.mkdir(mode=0o700)
        config = home / 'plane-setup.json'
        config.write_text(json.dumps(plane.config))
        config.chmod(0o600)
        db_path = tmp_path / 'control.db'
        with connect_closing(db_path) as conn:
            root = create_root(conn, actor=OWNER, request_id='writer', name='Writer',
                               purpose='Write a fantasy story about a glass dragon.')
            prepare(conn, actor=OWNER, agent_id=root['id'], home=home)
            setup = read_setup(conn, root['id'])
            assert setup['status'] == 'ready'
            yield SimpleNamespace(plane=plane, home=home, config=config, db_path=db_path,
                                  conn=conn, root=root, setup=setup)


def install(s):
    from agent_native.writer_planning import install_grants
    return install_grants(s.conn, actor=OWNER, agent_id=s.root['id'])


def open_session(s, binding_id, validate=lambda conn: None):
    from agent_native.writer_planning import open_planning
    return open_planning(db_path=s.db_path, home=s.home, agent_id=s.root['id'],
                         binding_id=binding_id, validate=validate)


def test_ready_setup_opens_fresh_scoped_snapshot_without_reprovisioning(writer):
    s = writer
    binding = install(s)
    before = len(s.plane.requests)
    checked = []
    def validate(conn):
        assert conn is not s.conn
        checked.append(conn.in_transaction)
    with open_session(s, binding, validate) as planning:
        result = planning.snapshot()
        assert result['project']['id'] == s.setup['project_id']
        assert result['discovery']['id'] == s.setup['discovery_item_id']
        assert result['items'][0]['id'] == s.setup['discovery_item_id']
        assert result['states'][0]['group'] == 'backlog'
        assert result['cycles'] == []
        s.plane.items[s.setup['discovery_item_id']]['name'] = 'Updated discovery'
        assert planning.snapshot()['discovery']['name'] == 'Updated discovery'
    assert checked
    assert all(r['method'] == 'GET' for r in s.plane.requests[before:])
    assert any(r['path'] == '/api/v1/users/me/' for r in s.plane.requests[before:])
    assert 'fixture-api-key' not in repr(result)
    assert 'fixture-password' not in repr(result)


def test_only_explicit_owner_installs_grants_and_open_never_regrants(writer):
    from agent_native.writer_planning import install_grants
    s = writer
    with pytest.raises(PermissionError):
        install_grants(s.conn, actor=object(), agent_id=s.root['id'])
    binding = install(s)
    revoke_writes(s.conn, actor=OWNER, binding_id=binding)
    before = len(s.plane.requests)
    with pytest.raises(PermissionError):
        with open_session(s, binding):
            pytest.fail('Revoked grants must not open')
    assert len(s.plane.requests) == before


@pytest.mark.parametrize('change', ['purpose', 'origin', 'principal', 'workspace'])
def test_stale_setup_or_changed_private_configuration_cannot_open(writer, change):
    s = writer
    binding = install(s)
    if change == 'purpose':
        revise_soul(s.conn, actor=OWNER, agent_id=s.root['id'], expected_revision=1,
                    purpose='Different purpose')
    elif change == 'workspace':
        path = s.home / 'agents' / s.root['id'] / 'workspace'
        path.rename(path.with_name('saved-workspace'))
        path.symlink_to(path.with_name('saved-workspace'), target_is_directory=True)
    else:
        config = json.loads(s.config.read_text())
        config['base_url' if change == 'origin' else 'expected_user_id'] = (
            'http://127.0.0.1:1' if change == 'origin' else uid())
        s.config.write_text(json.dumps(config))
    before = len(s.plane.requests)
    with pytest.raises((PermissionError, ValueError)):
        with open_session(s, binding):
            pytest.fail('Changed authority must not open')
    assert len(s.plane.requests) == before


def test_revised_ready_setup_opens_new_discovery_with_existing_project_grant(writer):
    s = writer
    binding = install(s)
    old_discovery = s.setup['discovery_item_id']
    revise_soul(s.conn, actor=OWNER, agent_id=s.root['id'], expected_revision=1,
                purpose='Write a different fantasy story.')
    prepare(s.conn, actor=OWNER, agent_id=s.root['id'], home=s.home)
    revised = read_setup(s.conn, s.root['id'])

    assert revised['discovery_item_id'] != old_discovery
    assert install(s) == binding
    with open_session(s, binding) as planning:
        snapshot = planning.snapshot()
    assert snapshot['discovery']['id'] == revised['discovery_item_id']


def test_actual_api_principal_must_match_the_provisioned_identity(writer):
    s = writer
    binding = install(s)
    s.plane.overrides['GET', '/api/v1/users/me/'] = lambda _: (200, {}, {'id': uid()})
    before = len(s.plane.requests)
    with pytest.raises(PermissionError):
        with open_session(s, binding):
            pytest.fail('Different remote principal must not open')
    assert [r['path'] for r in s.plane.requests[before:]] == ['/api/v1/users/me/']


def test_writer_authors_brief_cycle_task_and_records_version_reference(writer):
    s = writer
    binding = install(s)
    transactions = []
    def validate(conn):
        transactions.append(conn.in_transaction)
    with open_session(s, binding, validate) as planning:
        brief = planning.inspect({'kind': 'project'})
        result = planning.execute(uid(), 'project.update', {
            'description': 'Write one glass-dragon story. Criteria: a complete ending.',
            'expected_fingerprint': brief['fingerprint']})
        assert result['resource']['description'].startswith('Write one')
        cycle = planning.execute(uid(), 'cycle.create', {
            'name': '01 — First story', 'description': 'WIP 1. Exit: readable draft and evaluation.'})
        cycle_id = cycle['resource']['id']
        assert cycle['resource']['start_date'] is None
        assert cycle['resource']['end_date'] is None
        task = planning.execute(uid(), 'item.create', {
            'name': 'Draft the glass dragon', 'description': 'Acceptance: complete story with an ending.',
            'priority': 'high'})
        task_id = task['resource']['id']
        observed = planning.inspect({'kind': 'item', 'resource_id': task_id})
        membership = planning.execute(uid(), 'cycle.assign', {
            'cycle_id': cycle_id, 'item_id': task_id,
            'expected_item_fingerprint': observed['fingerprint'], 'expected_cycle_id': None})
        assert membership['resource']['issue'] == task_id
        reference = planning.execute(uid(), 'artifact.record', {
            'item_id': task_id, 'reference': 'stories/glass-dragon/v1.md',
            'description': 'Saved story version; awaiting acceptance.'})
        assert reference['resource']['issue'] == task_id
        assert 'stories/glass-dragon/v1.md' in reference['resource']['comment_html']
        assert s.root['id'] in reference['resource']['comment_html']
        assert planning.inspect({'kind': 'item', 'resource_id': task_id})['cycle_id'] == cycle_id
    assert True in transactions, 'Run validity must be checked in real mutation admission transactions'
    assert len(s.plane.cycles) == 1
    assert len(s.plane.items) == 2
    assert s.plane.items[task_id]['created_by'] == s.plane.user
    events = MutationJournal(s.conn).events(actor=OWNER)
    assert {event['agent_id'] for event in events} == {s.root['id']}
    assert len([event for event in events if event['status'] == 'confirmed']) == 5


def test_project_brief_canonicalizes_trailing_newlines_before_delivery(writer):
    s = writer
    binding = install(s)
    with open_session(s, binding) as planning:
        brief = planning.inspect({'kind': 'project'})
        result = planning.execute(uid(), 'project.update', {
            'description': 'A complete project brief.\n\n',
            'expected_fingerprint': brief['fingerprint'],
        })
    assert result['status'] == 'confirmed'
    assert result['resource']['description'] == 'A complete project brief.'
    assert s.plane.projects[s.setup['project_id']]['description'] == 'A complete project brief.'


def test_uncertain_create_after_reopen_recovers_original_without_resending(writer):
    from agent_native.plane_writes import PlaneWriteError
    s = writer
    binding, operation_id = install(s), uid()
    path = f"/api/v1/workspaces/{s.setup['workspace_slug']}/projects/{s.setup['project_id']}/work-items/"
    s.plane.lose.add(('POST', path))
    with open_session(s, binding) as planning:
        with pytest.raises(PlaneWriteError):
            planning.execute(operation_id, 'item.create', {'name': 'One durable task'})
    assert MutationJournal(s.conn).get(operation_id, actor=OWNER)['status'] == 'unknown'
    before = len(s.plane.requests)
    with open_session(s, binding) as resumed:
        result = resumed.recover(operation_id)
        assert result['status'] == 'confirmed'
        assert s.plane.items[result['resource']['id']]['name'] == 'One durable task'
        with pytest.raises(ReplayError):
            resumed.execute(operation_id, 'item.create', {'name': 'One durable task'})
    assert all(r['method'] == 'GET' for r in s.plane.requests[before:])
    assert len([r for r in s.plane.requests if r['method'] == 'POST' and r['path'] == path]) == 2  # discovery + one task


def test_stop_at_admission_transaction_prevents_http_effect(writer):
    s = writer
    binding, operation_id = install(s), uid()
    def validate(conn):
        if conn.in_transaction:
            raise PermissionError('Run stopped')
    before = len(s.plane.requests)
    with open_session(s, binding, validate) as planning:
        with pytest.raises(PermissionError, match='Run stopped'):
            planning.execute(operation_id, 'item.create', {'name': 'Must never be sent'})
    assert all(r['method'] == 'GET' for r in s.plane.requests[before:])
    assert MutationJournal(s.conn).get(operation_id, actor=OWNER)['status'] == 'rejected'


def test_late_read_after_stop_is_discarded_and_closed_session_cannot_reuse(writer):
    s = writer
    binding = install(s)
    stopped = False
    def validate(conn):
        if stopped:
            raise PermissionError('Run stopped')
    path = f"/api/v1/workspaces/{s.setup['workspace_slug']}/projects/{s.setup['project_id']}/"
    def stop_before_reply(request):
        nonlocal stopped
        stopped = True
        return 200, {}, s.plane.projects[s.setup['project_id']]
    s.plane.overrides['GET', path] = stop_before_reply
    with open_session(s, binding, validate) as planning:
        before = len(s.plane.requests)
        with pytest.raises(PermissionError, match='Run stopped'):
            planning.snapshot()
        assert len(s.plane.requests) == before + 1
    stopped = False
    before = len(s.plane.requests)
    with pytest.raises(PermissionError, match='ended'):
        planning.snapshot()
    assert len(s.plane.requests) == before


def test_existing_field_restriction_is_not_widened_on_install_or_open(writer):
    from agent_native.plane_write_access import allow_resource
    s = writer
    binding = install(s)
    allow_resource(s.conn, actor=OWNER, binding_id=binding, kind='project',
                   resource_id=s.setup['project_id'], fields=set())
    assert install(s) == binding
    with open_session(s, binding) as planning:
        observed = planning.inspect({'kind': 'project'})
        before = len(s.plane.requests)
        with pytest.raises(PermissionError):
            planning.execute(uid(), 'project.update', {'description': 'Forbidden rewrite',
                                                       'expected_fingerprint': observed['fingerprint']})
    assert len(s.plane.requests) == before


def test_ungranted_existing_item_edit_and_forged_scope_arguments_are_denied(writer):
    s = writer
    binding = install(s)
    iid = uid()
    s.plane.items[iid] = {**s.plane.items[s.setup['discovery_item_id']], 'id': iid, 'name': 'Owner item'}
    with open_session(s, binding) as planning:
        observed = planning.inspect({'kind': 'item', 'resource_id': iid})
        before = len(s.plane.requests)
        with pytest.raises(PermissionError):
            planning.execute(uid(), 'item.update', {'item_id': iid, 'name': 'Forbidden rewrite',
                                                   'expected_fingerprint': observed['fingerprint']})
        with pytest.raises(ValueError):
            planning.execute(uid(), 'item.create', {'name': 'Forged scope', 'project_id': uid()})
        with pytest.raises(ValueError):
            planning.inspect({'kind': 'project', 'base_url': 'http://127.0.0.1:1'})
    assert len(s.plane.requests) == before


def test_bad_create_authorship_remains_unknown_without_edit_permission(writer):
    from agent_native.plane_writes import PlaneWriteError
    s = writer
    binding, operation_id, iid = install(s), uid(), uid()
    path = f"/api/v1/workspaces/{s.setup['workspace_slug']}/projects/{s.setup['project_id']}/work-items/"
    s.plane.overrides['POST', path] = lambda request: (201, {}, {
        **s.plane.items[s.setup['discovery_item_id']], **request['body'],
        'id': iid, 'created_by': uid()})
    with open_session(s, binding) as planning:
        with pytest.raises(PlaneWriteError, match='attribution'):
            planning.execute(operation_id, 'item.create', {'name': 'Wrong service author'})
    assert MutationJournal(s.conn).get(operation_id, actor=OWNER)['status'] == 'unknown'
    assert s.conn.execute('SELECT 1 FROM agent_native_plane_resource_access WHERE resource_id = ?',
                          (iid,)).fetchone() is None
