import hashlib
import time
from types import SimpleNamespace
from uuid import uuid4

import pytest

from agent_native.builder_repository import command, read_file, write_file
from agent.work_policy import BUILDER_TOOL_NAMES, TOOL_NAMES, WorkContext, tool_schemas
from tests.hermes_cli.test_agent_native_api import client  # noqa: F401


def test_builder_repository_reads_and_compare_and_swap_writes(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    path = root / "module.py"
    path.write_text("old\n")
    observed = read_file(root, {"path": "module.py"})
    assert observed == {
        "path": "module.py", "content": "old\n", "sha256": hashlib.sha256(b"old\n").hexdigest(),
    }

    changed = write_file(root, {"path": "module.py", "content": "new\n", "expected_sha256": observed["sha256"]})
    assert changed["sha256"] == hashlib.sha256(b"new\n").hexdigest()
    assert path.read_text() == "new\n"
    with pytest.raises(ValueError, match="changed"):
        write_file(root, {"path": "module.py", "content": "stale\n", "expected_sha256": observed["sha256"]})


def test_builder_repository_rejects_escape_symlinks_and_dangerous_commands(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    outside = tmp_path / "secret"
    outside.write_text("private")
    (root / "escape").symlink_to(outside)
    for path in ("../secret", "/etc/passwd", "escape"):
        with pytest.raises((ValueError, PermissionError)):
            read_file(root, {"path": path})
    with pytest.raises(PermissionError, match="command"):
        command(root, {"argv": ["rm", "-rf", "."]})
    with pytest.raises(PermissionError, match="command"):
        command(root, {"argv": ["git", "push"]})


def test_builder_repository_runs_bounded_non_shell_commands(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "needle.txt").write_text("needle\n")
    result = command(root, {"argv": ["rg", "-n", "needle", "needle.txt"], "timeout_seconds": 5})
    assert result["returncode"] == 0
    assert "1:needle" in result["output"]
    assert result["truncated"] is False


def test_repository_tools_are_absent_from_ordinary_managed_work():
    common = dict(run_id=str(uuid4()), agent_id=str(uuid4()), soul_revision=1, name="Agent",
                  purpose="Work", workspace="/workspace", session_id="session", native_db="/state.db",
                  deadline_monotonic=time.monotonic() + 30, max_iterations=5, max_tokens=1000,
                  initial_context="context", skill_text="skill", request=lambda *_: {})
    ordinary = WorkContext(**common, authorized_tools=sorted(TOOL_NAMES))
    builder = WorkContext(**common, authorized_tools=sorted(TOOL_NAMES | BUILDER_TOOL_NAMES))
    assert not BUILDER_TOOL_NAMES & {row["function"]["name"] for row in tool_schemas(ordinary)}
    assert BUILDER_TOOL_NAMES <= {row["function"]["name"] for row in tool_schemas(builder)}
    with pytest.raises(PermissionError):
        ordinary.tool(None, "repository_file_read", {"path": "README.md"}, "call")


def test_repository_tool_descriptions_apply_to_an_agents_granted_project_workspace():
    context = SimpleNamespace(authorized_tools=sorted(TOOL_NAMES | BUILDER_TOOL_NAMES))
    schemas = {row['function']['name']: row['function'] for row in tool_schemas(context)}

    assert 'granted project workspace' in schemas['repository_file_read']['description']
    assert 'expected_sha256 to missing' in schemas['repository_file_write']['description']
    assert 'rg --files' in schemas['repository_command']['description']


def test_owner_grants_one_ordinary_agent_an_isolated_repository(client, tmp_path):
    from agent_native.first_builder import active_repository
    from agent_native.project_workspace import active_repository as active_project_repository
    from hermes_cli.kanban_db_connect import connect_closing

    granted = client.post('/api/agent-native/agents', json={
        'request_id': 'ordinary-coder', 'name': 'Game builder', 'purpose': 'Build a game',
    }).json()
    ordinary = client.post('/api/agent-native/agents', json={
        'request_id': 'ordinary-reader', 'name': 'Reader', 'purpose': 'Read stories',
    }).json()
    project = tmp_path / 'fantasy-game'
    project.mkdir()

    response = client.post(f"/api/agent-native/agents/{granted['id']}/workspace", json={
        'expected_revision': 1, 'root': str(project),
    })
    assert response.status_code == 201
    assert response.json() == {'root': str(project.resolve()), 'active': True, 'revision': 1}

    with connect_closing(tmp_path / 'control.db') as conn:
        assert active_project_repository(conn, granted['id']) == project.resolve()
        with pytest.raises(PermissionError):
            active_project_repository(conn, ordinary['id'])
        with pytest.raises(PermissionError):
            active_repository(conn, granted['id'])


def test_granted_agent_publishes_a_stable_isolated_preview(client, tmp_path):
    from agent_native.identity import OWNER
    from agent_native.project_preview import publish
    from hermes_cli.kanban_db_connect import connect_closing

    agent = client.post('/api/agent-native/agents', json={
        'request_id': 'preview-coder', 'name': 'Site builder', 'purpose': 'Build a site',
    }).json()
    project = tmp_path / 'site'
    (project / 'dist').mkdir(parents=True)
    (project / 'dist' / 'index.html').write_text('<link rel="stylesheet" href="game.css"><h1>Playable increment</h1>')
    (project / 'dist' / 'game.css').write_text('h1 { color: green; }')
    assert client.post(f"/api/agent-native/agents/{agent['id']}/workspace", json={
        'expected_revision': 1, 'root': str(project),
    }).status_code == 201

    with connect_closing(tmp_path / 'control.db') as conn:
        preview = publish(conn, actor=OWNER, agent_id=agent['id'], path='dist')
    assert preview['url'] == f"/api/agent-native/agents/{agent['id']}/preview/"
    response = client.get(preview['url'])
    assert response.status_code == 200
    assert 'Playable increment' in response.text
    assert client.get(preview['url'] + '../secret').status_code == 404

    launch = client.post(f"/api/agent-native/agents/{agent['id']}/preview-launch")
    assert launch.status_code == 200
    launch_url = launch.json()['url']
    assert 'ticket=' in launch_url and 'X-Hermes' not in launch_url
    assert launch_url.startswith('http://localhost')
    client.headers.pop('X-Hermes-Session-Token')
    exchange = client.get(launch_url, follow_redirects=False)
    assert exchange.status_code == 303
    assert 'ticket=' not in exchange.headers['location']
    assert 'HttpOnly' in exchange.headers['set-cookie']
    assert client.get(exchange.headers['location']).status_code == 200
    assert client.get(exchange.headers['location'] + 'game.css').text == 'h1 { color: green; }'
    assert client.get(launch_url, follow_redirects=False).status_code == 401
