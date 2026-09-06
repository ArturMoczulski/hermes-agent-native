"""Real Hermes dispatch and HTTP/SQLite scope checks for host-bound Plane reads."""
from contextlib import contextmanager
import json

import pytest

from agent_native.identity import OWNER, revise_soul
from agent_native.plane_access import revoke_project
from tests.hermes_cli import test_agent_native_plane_writes as fixtures

setup = fixtures.setup
upstream = fixtures.upstream


@pytest.fixture
def open_service(setup, upstream):
    @contextmanager
    def factory():
        with fixtures.connect_closing(setup.db_path) as conn:
            authority = fixtures.WriteAuthority(conn)
            context = authority.issue_context(actor=OWNER, binding_id=setup.binding['id'])
            service = fixtures.PlaneWrites(authority, fixtures.MutationJournal(conn),
                base_url=upstream.url, api_key='private-fixture-key', service_user_id=setup.user)
            yield service, context
    return factory


@pytest.mark.parametrize('entry', ['registry', 'model'])
def test_host_bound_inspection_uses_only_its_granted_project(setup, upstream, open_service, entry):
    from agent_native import plane_tools
    from model_tools import handle_function_call
    from tools.registry import registry

    dispatch = registry.dispatch if entry == 'registry' else handle_function_call
    with plane_tools.bind_plane_tools(actor=OWNER, open_service=open_service):
        result = json.loads(dispatch('plane_resource_inspect', {'kind': 'project'},
                                     task_id='another-agent', session_id='owner'))
    assert result['resource']['id'] == setup.project
    assert result['resource']['description'] == setup.project_record['description']
    assert result['fingerprint']
    assert [r['path'] for r in upstream.requests] == [setup.path]
    assert all(r['method'] == 'GET' for r in upstream.requests)
    assert 'private-fixture-key' not in json.dumps(result)


@pytest.mark.parametrize('change', ['project', 'purpose'])
def test_bound_context_rechecks_current_authority_before_each_call(setup, upstream, open_service, change):
    from agent_native import plane_tools
    from tools.registry import registry

    with plane_tools.bind_plane_tools(actor=OWNER, open_service=open_service):
        first = json.loads(registry.dispatch('plane_resource_inspect', {'kind': 'project'}))
        assert first['resource']['id'] == setup.project
        if change == 'project':
            revoke_project(setup.conn, actor=OWNER, binding_id=setup.binding['id'])
        else:
            revise_soul(setup.conn, actor=OWNER, agent_id=setup.root['id'],
                        expected_revision=1, purpose='Changed direction')
        before = list(upstream.requests)
        assert 'error' in json.loads(registry.dispatch('plane_resource_inspect', {'kind': 'project'}))
    assert upstream.requests == before


@pytest.mark.parametrize('extra', [
    {'actor': 'owner'}, {'context': {'role': 'owner'}}, {'binding_id': 'elsewhere'},
    {'project_id': fixtures.uid()}, {'task_id': 'another-agent'},
])
def test_arguments_cannot_override_host_authority(setup, upstream, open_service, extra):
    from agent_native import plane_tools
    from model_tools import handle_function_call

    with plane_tools.bind_plane_tools(actor=OWNER, open_service=open_service):
        assert 'error' in json.loads(handle_function_call('plane_resource_inspect',
                                    {'kind': 'project', **extra}))
    assert upstream.requests == []


@pytest.mark.parametrize('actor,context', [(None, None), ('owner', None), (OWNER, object()),
                                          (OWNER, {'role': 'owner'})])
def test_only_host_can_bind_an_issued_context(setup, upstream, open_service, actor, context):
    from agent_native import plane_tools

    @contextmanager
    def invalid_service():
        with open_service() as (service, _):
            yield service, context

    with pytest.raises(PermissionError):
        with plane_tools.bind_plane_tools(actor=actor, open_service=invalid_service):
            pytest.fail('Untrusted binding succeeded')
    assert upstream.requests == []


def test_nested_socket_rpc_keeps_scope_and_rechecks_revocation(setup, upstream, open_service):
    import socket
    from threading import Event, Thread
    from agent_native import plane_tools
    from tools.code_execution_rpc import _rpc_server_loop
    from tools.code_kernel import CellAuthority

    server = socket.socket()
    server.bind(('127.0.0.1', 0))
    server.listen(1)
    stop = Event()
    thread = None
    try:
        with plane_tools.bind_plane_tools(actor=OWNER, open_service=open_service):
            cell = CellAuthority('caller-controlled-task-id')
            thread = Thread(target=_rpc_server_loop, daemon=True,
                args=(server, 'another-task-id', [], [0], 8,
                      frozenset({'plane_resource_inspect'}), stop, 'fixture-rpc-token'),
                kwargs={'dispatch': cell.dispatch})
            thread.start()
            with socket.create_connection(server.getsockname(), timeout=5) as client:
                with client.makefile('rwb') as channel:
                    def inspect():
                        channel.write(json.dumps({'token': 'fixture-rpc-token',
                            'tool': 'plane_resource_inspect', 'args': {'kind': 'project'}}).encode() + b'\n')
                        channel.flush()
                        return json.loads(channel.readline())
                    result = inspect()
                    assert result.get('resource', {}).get('id') == setup.project, result
                    before = list(upstream.requests)
                    revoke_project(setup.conn, actor=OWNER, binding_id=setup.binding['id'])
                    assert 'error' in inspect()
                    cell.retire()
                    assert 'error' in inspect()
                    assert upstream.requests == before
    finally:
        stop.set()
        server.close()
        if thread:
            thread.join(timeout=5)
            assert not thread.is_alive()


def test_bare_thread_and_expired_copied_context_have_no_plane_authority(setup, upstream, open_service):
    from concurrent.futures import ThreadPoolExecutor
    from contextvars import copy_context
    from agent_native import plane_tools
    from model_tools import handle_function_call

    def inspect():
        return json.loads(handle_function_call('plane_resource_inspect', {'kind': 'project'}))

    with plane_tools.bind_plane_tools(actor=OWNER, open_service=open_service):
        stale = copy_context()
        with ThreadPoolExecutor(max_workers=1) as executor:
            assert 'error' in executor.submit(inspect).result(timeout=5)
    assert 'error' in stale.run(inspect)
    assert upstream.requests == []


def test_binding_reclaims_its_worker_even_when_adapter_close_fails(open_service, monkeypatch):
    from agent_native import plane_tools

    pools = []
    executor = plane_tools.ThreadPoolExecutor

    def record_executor(**kwargs):
        pool = executor(**kwargs)
        pools.append(pool)
        return pool

    monkeypatch.setattr(plane_tools, 'ThreadPoolExecutor', record_executor)

    @contextmanager
    def broken_close():
        with open_service() as pair:
            yield pair
        raise RuntimeError('Fixture close failed')

    try:
        with pytest.raises(RuntimeError, match='Fixture close failed'):
            with plane_tools.bind_plane_tools(actor=OWNER, open_service=broken_close):
                pass
        with pytest.raises(RuntimeError):
            pools[0].submit(lambda: None)
    finally:
        for pool in pools:
            pool.shutdown(wait=True)
