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


def test_renderer_state_is_private_and_scoped_to_agent_revision_and_client(tmp_path, monkeypatch):
    from pathlib import Path
    from agent_native.chat import issue_binding
    from hermes_cli.web_server_agent_chat import bind_chat_renderer
    from hermes_cli import web_server_chat
    home = tmp_path / 'home'
    monkeypatch.setenv('HERMES_HOME', str(home))
    monkeypatch.setenv('HERMES_KANBAN_DB', str(tmp_path / 'control.db'))
    monkeypatch.setattr(web_server_chat, '_server_internal_ws_url', lambda path, **params: 'ws://127.0.0.1:19219' + path)
    with connect_closing(board='default') as conn:
        a = identity.create_root(conn, actor=identity.OWNER, request_id='a', name='Writer', purpose='Write fantasy')
        b = identity.create_root(conn, actor=identity.OWNER, request_id='b', name='Composer', purpose='Compose music')
    first = issue_binding(actor=identity.OWNER, agent_id=a['id'])
    second = issue_binding(actor=identity.OWNER, agent_id=b['id'])
    def state(binding, client='browser-a'):
        return Path(bind_chat_renderer({}, binding, attachment=client)['HERMES_TUI_CHAT_STATE'])
    path = state(first)
    assert path == state(first)
    assert path != state(second)
    assert path != state(first, 'browser-b')
    assert path.is_relative_to(home) and not path.is_relative_to(Path(first.workspace))
    assert path.parent.stat().st_mode & 0o777 == 0o700
    with connect_closing(board='default') as conn:
        identity.revise_soul(conn, actor=identity.OWNER, agent_id=a['id'], expected_revision=1, purpose='Write mysteries')
    revised = issue_binding(actor=identity.OWNER, agent_id=a['id'])
    assert state(revised) != path
