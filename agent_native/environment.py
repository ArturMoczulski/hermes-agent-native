"""Restricted Hermes tool environment, not an agent/model dispatcher.

Only trusted host code constructs this environment. The image is selected by the
owner and resolved locally to an immutable ID. No arbitrary Docker options or
host credentials can be supplied through this factory.
"""
import json
import os
import subprocess

from agent_native.provisioning import sandbox_mounts
from tools.environments.docker import DockerEnvironment, find_docker


class _ManagedEnvironment(DockerEnvironment):
    _profile_scoped_passthrough = False

    def __init__(self, *, image, mounts, agent_id):
        if not hasattr(os, 'getuid'):
            raise RuntimeError('Managed worker currently requires a POSIX host')
        self._managed_mounts = mounts
        self._managed_uid = f'{os.getuid()}:{os.getgid()}'
        try:
            super().__init__(image=image, cwd='/workspace', task_id=agent_id,
                             network=False, persistent_filesystem=False,
                             persist_across_processes=False, run_as_host_user=True)
            if not self._snapshot_ready:
                raise RuntimeError('Managed image could not initialize a Bash session')
        except BaseException:
            if getattr(self, '_container_id', None):
                self.cleanup(force_remove=True)
                self.wait_for_cleanup(timeout=45)
            raise

    def _automatic_mount_args(self):
        return []

    def _mount_args(self, *args):
        # No implicit home/workspace binds or global sandbox directories.
        return [], []

    def _resource_args(self, *args):
        return []

    def _egress_and_env_args(self, extra_args):
        self._run_env_values = {}
        return 'managed-offline', [], [], [], []

    def _resolve_passthrough_env(self):
        # Covers snapshot initialization and every later docker exec.
        return {}, set()

    def _run_command(self, name, workdir):
        # Construct from a closed set: inherited _all_run_args cannot widen access.
        args = [self._docker_exe, 'run', '-d', '--pull=never', '--init', '--name', name,
                '--network=none', '--read-only', '--cap-drop=ALL',
                '--security-opt=no-new-privileges', '--user', self._managed_uid,
                '--pids-limit=128', '--memory=512m', '--cpus=1',
                '--tmpfs', '/tmp:rw,nosuid,nodev,size=128m,mode=1777',
                '--env', 'HOME=/tmp', '--workdir', '/workspace',
                '--label', 'hermes-agent=1', '--label', 'agent-native-managed=1']
        for mount in self._managed_mounts:
            source = mount['source']
            if ',' in source:
                raise ValueError('Docker bind source must not contain a comma')
            spec = f"type=bind,src={source},dst={mount['target']}"
            args += ['--mount', spec + (',readonly' if mount['readonly'] else '')]
        return args + ['--entrypoint', '/bin/sh', self._image, '-c', 'exec sleep infinity']

    def cleanup(self, *, force_remove=False):
        cid = getattr(self, '_container_id', None)
        if not cid:
            return
        try:
            result = subprocess.run([self._docker_exe, 'rm', '-f', cid],
                                    capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip())
        except (OSError, subprocess.TimeoutExpired, RuntimeError) as exc:
            # Keep the identity on both the environment and raised error.
            error = RuntimeError(f'Container cleanup unconfirmed for {cid}: {exc}')
            error.container_id = cid
            raise error from exc
        self._container_id = None

    def wait_for_cleanup(self, timeout=30):
        return getattr(self, '_container_id', None) is None

    def _recreate_container(self):
        # Recovery must return to host admission and revalidate soul/grants.
        return False


def open_environment(conn, *, actor, agent_id, storage_root, image):
    mounts = sandbox_mounts(conn, actor=actor, agent_id=agent_id, storage_root=storage_root)
    docker = find_docker()
    if not docker:
        raise RuntimeError('Docker is required for managed execution')
    result = subprocess.run([docker, 'image', 'inspect', image],
                            check=True, capture_output=True, text=True, timeout=15)
    metadata = json.loads(result.stdout)[0]
    if (metadata.get('Config') or {}).get('Volumes'):
        raise ValueError('Managed images must not declare implicit volumes')
    image_id = metadata.get('Id', '')
    if not image_id.startswith('sha256:'):
        raise RuntimeError('Could not resolve a local immutable image ID')
    return _ManagedEnvironment(image=image_id, mounts=mounts, agent_id=agent_id)
