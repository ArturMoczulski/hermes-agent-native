"""Host-owned profile snapshots for inactive agents.

The owner-controlled storage root must never be mounted into a worker. Only its
specific mutable subdirectories may be granted to generated code. Read-only mode
bits prevent accidents, not attacks by a process running as the host user.
"""
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile

from agent_native.identity import get_root


def _projection(root):
    identity = json.dumps({
        'source': 'agent-native control database',
        'agent_id': root['id'], 'soul_revision': root['soul_revision'],
        'execution': 'not_started',
    }, indent=2) + '\n'
    soul = (f"# Agent purpose\n\nSource: agent-native control database\n"
            f"Agent ID: {root['id']}\nSoul revision: {root['soul_revision']}\n\n"
            f"{root['purpose']}\n\n"
            "This file is a host-owned projection. Memory and practices cannot change its authority.\n")
    return {'SOUL.md': soul, 'identity.json': identity, '.env': ''}


def _verify(base, expected):
    for relative in ('', 'profile', 'workspace', 'profile/memories', 'profile/skills'):
        path = base / relative
        if path.is_symlink() or not path.is_dir():
            raise ValueError(f'Unsafe or incomplete agent directory: {path}')
        if relative in ('', 'profile') and stat.S_IMODE(path.stat().st_mode) != 0o700:
            raise ValueError(f'Protected directory permissions changed: {path}')
    for name, contents in expected.items():
        path = base / 'profile' / name
        if path.is_symlink() or not path.is_file() or path.read_text() != contents:
            raise ValueError(f'Stale or modified protected projection: {name}')
        if stat.S_IMODE(path.stat().st_mode) != 0o400:
            raise ValueError(f'Protected file permissions changed: {name}')


def provision_root(conn, *, actor, agent_id, storage_root):
    """Publish one complete layout; retries validate it without erasing mutable work.

    Only inactive roots are supported. Soul revisions invalidate an existing
    projection until an explicit refresh workflow is implemented. No engine starts.
    """
    root = get_root(conn, actor=actor, agent_id=agent_id)
    storage = Path(storage_root)
    if storage.is_symlink():
        raise ValueError('Storage root must not be a symlink')
    storage = storage.resolve()
    storage.mkdir(parents=True, exist_ok=True, mode=0o700)
    base = storage / root['id']
    expected = _projection(root)
    if not base.exists() and not base.is_symlink():
        stage = Path(tempfile.mkdtemp(prefix='.provision-', dir=storage))
        try:
            profile = stage / 'profile'
            for directory in (profile, stage / 'workspace', profile / 'memories', profile / 'skills'):
                directory.mkdir(mode=0o700)
            for name, contents in expected.items():
                path = profile / name
                path.write_text(contents)
                path.chmod(0o400)
            (stage / 'workspace' / 'PRACTICES.md').write_text('# Working practices\n')
            (profile / 'memories' / 'MEMORY.md').write_text('')
            try:
                os.rename(stage, base)
            except OSError:
                # A concurrent successful provision may have won publication.
                # Validate below; never replace or delete the published directory.
                if not base.exists():
                    raise
        finally:
            if stage.exists():
                shutil.rmtree(stage)
    _verify(base, expected)
    return {'agent_id': root['id'], 'soul_revision': root['soul_revision'],
            'profile': str(base / 'profile'), 'workspace': str(base / 'workspace'),
            'memory': str(base / 'profile' / 'memories')}


def sandbox_mounts(conn, *, actor, agent_id, storage_root):
    """Explicit data mounts for the future managed execution boundary."""
    layout = provision_root(conn, actor=actor, agent_id=agent_id, storage_root=storage_root)
    profile = Path(layout['profile'])
    return [
        {'source': str(profile / 'SOUL.md'), 'target': '/agent/SOUL.md', 'readonly': True},
        {'source': str(profile / 'identity.json'), 'target': '/agent/identity.json', 'readonly': True},
        {'source': layout['workspace'], 'target': '/workspace', 'readonly': False},
        {'source': layout['memory'], 'target': '/memory', 'readonly': False},
    ]
