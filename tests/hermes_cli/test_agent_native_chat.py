"""Managed chat bindings use real isolated control storage, not caller-selected identity."""
from concurrent.futures import ThreadPoolExecutor

import pytest

from agent_native import identity
from hermes_cli.kanban_db_connect import connect_closing


def test_concurrent_reconnects_share_binding_and_revision_revokes_it(tmp_path):
    from agent_native.chat import issue_binding, lookup_session
    db_path = tmp_path / 'control.db'
    storage = tmp_path / 'agents'
    with connect_closing(db_path) as conn:
        root = identity.create_root(conn, actor=identity.OWNER, request_id='a', name='Writer', purpose='Write fantasy')
        other = identity.create_root(conn, actor=identity.OWNER, request_id='b', name='Composer', purpose='Compose music')
    def connect(_):
        return issue_binding(actor=identity.OWNER, agent_id=root['id'], db_path=db_path, storage_root=storage)
    with ThreadPoolExecutor(max_workers=3) as workers:
        bindings = list(workers.map(connect, range(3)))
    binding = bindings[0]
    assert len({b.session_id for b in bindings}) == 1
    assert binding.purpose == root['purpose']
    assert lookup_session(binding.session_id, db_path=db_path)
    assert not lookup_session('unmanaged-session', db_path=db_path)
    binding.validate()
    second = issue_binding(actor=identity.OWNER, agent_id=other['id'], db_path=db_path, storage_root=storage)
    assert second.session_id != binding.session_id
    with connect_closing(db_path) as conn:
        assert identity.get_root(conn, actor=identity.OWNER, agent_id=root['id'])['execution'] == 'not_started'
        identity.revise_soul(conn, actor=identity.OWNER, agent_id=root['id'], expected_revision=1, purpose='Write mysteries')
    with pytest.raises((PermissionError, identity.ConflictError)):
        binding.validate()
    second.validate()
    # The old native history remains recognizable as managed after purpose edits.
    assert lookup_session(binding.session_id, db_path=db_path)


@pytest.mark.parametrize('actor', [None, 'owner', {'role': 'owner'}])
def test_caller_data_cannot_issue_binding(tmp_path, actor):
    from agent_native.chat import issue_binding
    with pytest.raises(PermissionError):
        issue_binding(actor=actor, agent_id='anything', db_path=tmp_path / 'absent.db', storage_root=tmp_path / 'agents')
    assert not (tmp_path / 'absent.db').exists()
