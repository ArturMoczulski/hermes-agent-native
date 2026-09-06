"""Real Hermes Docker backend acceptance; requires a preinstalled Bash image."""
import json
import os
import subprocess
from pathlib import Path

import pytest
from agent_native.environment import open_environment
from agent_native.identity import OWNER, create_root
from hermes_cli.kanban_db_connect import connect_closing

@pytest.mark.skipif(os.environ.get('HERMES_TEST_IMAGE') != 'agent-native/dev:latest', reason='Opt in with existing Bash development image')
def test_hermes_worker_is_private_and_stops(tmp_path, monkeypatch):
    from tools.environments import docker as upstream
    def forbidden(*args, **kwargs):
        raise AssertionError('Managed worker consulted inherited host access')
    monkeypatch.setattr(upstream, '_readonly_skill_mount_args', forbidden)
    monkeypatch.setattr(upstream, '_egress_proxy_args_for_docker', forbidden)
    monkeypatch.setattr(upstream, 'resolve_passthrough_env', forbidden)
    monkeypatch.setenv('OWNER_PRIVATE_TOKEN', 'must-not-enter-worker')
    with connect_closing(tmp_path / 'control.db') as conn:
        root = create_root(conn, actor=OWNER, request_id='one', name='Artist', purpose='Make metal music')
        env = open_environment(conn, actor=OWNER, agent_id=root['id'], storage_root=tmp_path / 'agents', image='agent-native/dev:latest')
        cid = env._container_id
        try:
            info = json.loads(subprocess.check_output(['docker', 'inspect', cid], text=True))[0]
            assert info['HostConfig']['NetworkMode'] == 'none'
            assert info['HostConfig']['ReadonlyRootfs'] is True
            assert info['HostConfig']['CapDrop'] == ['ALL']
            assert info['HostConfig']['CapAdd'] is None
            assert 'no-new-privileges' in info['HostConfig']['SecurityOpt']
            assert info['Config']['User'] == f'{os.getuid()}:{os.getgid()}'
            assert set(m['Destination'] for m in info['Mounts']) == {'/agent/SOUL.md', '/agent/identity.json', '/workspace', '/memory'}
            result = env.execute('test -z "${OWNER_PRIVATE_TOKEN:-}" && test ! -e /var/run/docker.sock && cat /agent/SOUL.md && echo riff > /workspace/song.md && echo learned > /memory/MEMORY.md')
            assert result['returncode'] == 0, result
            assert 'Make metal music' in result['output']
            assert env.execute('echo overwrite > /agent/SOUL.md')['returncode'] != 0
            assert env.execute('chmod 600 /agent/SOUL.md')['returncode'] != 0
            second = open_environment(conn, actor=OWNER, agent_id=root['id'], storage_root=tmp_path / 'agents', image='agent-native/dev:latest')
            try:
                assert second._container_id != cid
                assert second.execute('cat /workspace/song.md')['returncode'] == 0
            finally:
                second.cleanup()
                assert second.wait_for_cleanup(timeout=45)
            subprocess.run(['docker', 'rm', '-f', cid], check=True, capture_output=True)
            assert env.execute('echo must-not-recreate')['returncode'] != 0
            assert subprocess.run(['docker', 'inspect', cid], capture_output=True).returncode != 0
            assert Path(tmp_path / 'agents' / root['id'] / 'workspace' / 'song.md').read_text().strip() == 'riff'
        finally:
            env.cleanup()
            assert env.wait_for_cleanup(timeout=45)
        assert subprocess.run(['docker', 'inspect', cid], capture_output=True).returncode != 0


def test_unknown_actor_cannot_start_worker(tmp_path):
    with connect_closing(tmp_path / 'control.db') as conn:
        with pytest.raises(PermissionError):
            open_environment(conn, actor='owner', agent_id='anything', storage_root=tmp_path / 'agents', image='any')


def test_cleanup_failure_retains_container_identity(monkeypatch):
    from agent_native.environment import _ManagedEnvironment
    env = _ManagedEnvironment.__new__(_ManagedEnvironment)
    env._container_id = 'owned-worker'
    env._docker_exe = 'docker'
    env._persistent = True
    env._persist_across_processes = False
    monkeypatch.setattr(subprocess, 'run', lambda *a, **k: subprocess.CompletedProcess(a[0], 1, '', 'daemon unavailable'))
    try:
        with pytest.raises(RuntimeError, match='owned-worker'):
            env.cleanup()
    finally:
        env.wait_for_cleanup(timeout=1)
    assert env._container_id == 'owned-worker'


def test_images_with_implicit_volumes_rejected(tmp_path, monkeypatch):
    import agent_native.environment as module
    monkeypatch.setattr(module, 'find_docker', lambda: 'docker')
    data = [{'Id': 'sha256:local', 'Config': {'Volumes': {'/extra': {}}}}]
    monkeypatch.setattr(subprocess, 'run', lambda *a, **k: subprocess.CompletedProcess(a[0], 0, json.dumps(data), ''))
    with connect_closing(tmp_path / 'control.db') as conn:
        root = create_root(conn, actor=OWNER, request_id='one', name='Artist', purpose='Music')
        with pytest.raises(ValueError, match='volume'):
            open_environment(conn, actor=OWNER, agent_id=root['id'], storage_root=tmp_path / 'agents', image='image')
