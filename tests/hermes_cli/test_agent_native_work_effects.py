"""Run broker admission against real SQLite, scoped planning and external Plane HTTP."""

import json
from types import SimpleNamespace

import pytest

from agent_native import work_state
from agent_native.identity import OWNER, create_root
from agent_native.plane_write_journal import MutationJournal
from agent_native.plane_reads import PlaneReadError
from agent_native.plane_writes import PlaneWriteError
from agent_native.startup import prepare, read_setup
from agent_native.work_service import _Run, WorkService
from agent_native.writer_planning import install_grants, open_planning
from hermes_cli.kanban_db_connect import connect_closing, write_txn
from tests.hermes_cli.writer_plane_fixture import writer_plane_server


@pytest.fixture
def broker(tmp_path, monkeypatch):
    profile = tmp_path / 'native-profile'
    profile.mkdir()
    monkeypatch.setenv('HERMES_HOME', str(profile))
    # Broker tests never launch a worker, but admission still requires a real
    # configured selection. This endpoint has no service and incurs no model call.
    (profile / 'config.yaml').write_text(json.dumps({
        'model': {'provider': 'custom:broker-fixture', 'default': 'fixture-model'},
        'custom_providers': [{'name': 'broker-fixture',
                              'base_url': 'http://127.0.0.1:18883/v1',
                              'api_key': 'fixture-only'}],
    }))
    with writer_plane_server() as plane:
        home = tmp_path / 'agent-native'
        home.mkdir(mode=0o700)
        config = home / 'plane-setup.json'
        config.write_text(json.dumps(plane.config))
        config.chmod(0o600)
        db_path = tmp_path / 'control.db'
        with connect_closing(db_path) as conn:
            root = create_root(conn, actor=OWNER, request_id='work-effects',
                               name='Writer', purpose='Write a fantasy story.')
            prepare(conn, actor=OWNER, agent_id=root['id'], home=home)
            setup = read_setup(conn, root['id'])
            assert setup['status'] == 'ready'
            work = work_state.configure(conn, actor=OWNER, agent_id=root['id'],
                                        expected_revision=1,
                                        limits={'timeout_seconds': 120, 'max_iterations': 16})
            binding = install_grants(conn, actor=OWNER, agent_id=root['id'])
            with write_txn(conn):
                conn.execute("UPDATE agent_native_work_runs SET state='running',binding_id=? WHERE id=?",
                             (binding, work['id']))
            run = _Run(WorkService(db_path, home), work)
            run.workspace = home / 'agents' / root['id'] / 'workspace'
            with open_planning(db_path=db_path, home=home, agent_id=root['id'],
                               binding_id=binding, validate=run.validate) as planning:
                yield SimpleNamespace(plane=plane, home=home, db_path=db_path, conn=conn,
                                      root=root, setup=setup, work=work, run=run, planning=planning)
            run.ended.set()
            assert run.host.pid == 0, 'This test exercises the broker without launching a worker'


def effect(s, call_id, tool='plane_operation_execute', arguments=None):
    return {'run_id': s.work['id'], 'tool_call_id': call_id, 'tool': tool,
            'arguments': arguments or {'operation': 'item.create',
                                      'arguments': {'name': 'One durable story task'}}}


def test_lost_plane_write_preserves_unknown_and_blocks_all_later_admission(broker):
    s = broker
    path = (f"/api/v1/workspaces/{s.setup['workspace_slug']}/projects/"
            f"{s.setup['project_id']}/work-items/")
    s.plane.lose.add(('POST', path))
    before = len(s.plane.requests)
    with pytest.raises(PlaneWriteError) as error:
        s.run._effect(s.conn, s.planning, effect(s, 'first-create'))
    assert error.value.outcome == 'unknown'
    operation_id, result = s.conn.execute(
        'SELECT operation_id,result FROM agent_native_work_effects WHERE run_id=? AND call_id=?',
        (s.work['id'], 'first-create')).fetchone()
    assert operation_id == error.value.operation_id and result is None
    assert MutationJournal(s.conn).get(operation_id, actor=OWNER)['status'] == 'unknown'
    assert sum(request['method'] == 'POST' and request['path'] == path
               for request in s.plane.requests[before:]) == 1
    assert len([item for item in s.plane.items.values()
                if item['name'] == 'One durable story task']) == 1
    work = work_state.read_work(s.conn, s.root['id'])
    assert work['state'] == 'unknown'
    assert work['error'] and 'Plane' in work['error']
    assert any(event['kind'] == 'work.unknown' for event in work['events'])

    before = len(s.plane.requests)
    for params in (effect(s, 'first-create'), effect(s, 'second-create'),
                   effect(s, 'read-after-unknown', 'plane_resource_inspect', {'kind': 'project'})):
        with pytest.raises(PermissionError):
            s.run._effect(s.conn, s.planning, params)
    for boundary in ('model', 'persist'):
        with pytest.raises(PermissionError):
            s.run._admit(s.conn, {'run_id': s.work['id'], 'boundary': boundary})
    assert len(s.plane.requests) == before
    assert s.conn.execute('SELECT COUNT(*) FROM agent_native_work_effects WHERE run_id=?',
                          (s.work['id'],)).fetchone()[0] == 1
    assert work_state.read_work(s.conn, s.root['id'])['model_calls'] == 0
    s.run.fail('PlaneWriteError')
    with connect_closing(s.db_path) as reopened:
        assert work_state.read_work(reopened, s.root['id'])['state'] == 'unknown'
        assert MutationJournal(reopened).get(operation_id, actor=OWNER)['status'] == 'unknown'
        assert reopened.execute('SELECT stop_requested FROM agent_native_work_runs WHERE id=?',
                                (s.work['id'],)).fetchone()[0] == 1


def test_output_cannot_use_a_foreign_item_or_create_an_artifact(broker):
    s = broker
    other = create_root(s.conn, actor=OWNER, request_id='foreign-work',
                        name='Other writer', purpose='Write a different story.')
    prepare(s.conn, actor=OWNER, agent_id=other['id'], home=s.home)
    foreign = read_setup(s.conn, other['id'])
    assert foreign['status'] == 'ready'
    assert foreign['project_id'] != s.setup['project_id']
    params = effect(s, 'foreign-output', 'output_publish', {
        'title': 'Must not be saved', 'content': 'Foreign story text',
        'item_id': foreign['discovery_item_id'], 'format': 'markdown',
    })
    prior_files = set(s.run.workspace.rglob('*'))
    with pytest.raises(PlaneReadError) as error:
        s.run._effect(s.conn, s.planning, params)
    assert error.value.status == 404
    assert not (s.run.workspace / 'stories').exists()
    assert s.conn.execute('SELECT COUNT(*) FROM agent_native_output_versions').fetchone()[0] == 0
    assert work_state.read_work(s.conn, s.root['id'])['state'] == 'running'
    assert set(s.run.workspace.rglob('*')) == prior_files
