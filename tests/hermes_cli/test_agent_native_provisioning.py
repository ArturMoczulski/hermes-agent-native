from pathlib import Path
import json
import os
import stat

import pytest
from agent_native.identity import OWNER, create_root
from agent_native.provisioning import provision_root
from hermes_cli.kanban_db_connect import connect_closing

@pytest.fixture
def setup(tmp_path):
    with connect_closing(tmp_path / 'control.db') as conn:
        root = create_root(conn, actor=OWNER, request_id='one', name='../Artist', purpose='Make metal music')
        yield conn, root, tmp_path / 'agents'


def test_private_profile_projection_and_writable_layers(setup):
    conn, root, storage = setup
    layout = provision_root(conn, actor=OWNER, agent_id=root['id'], storage_root=storage)
    profile = Path(layout['profile'])
    assert profile.parent.name == root['id']
    assert root['purpose'] in (profile / 'SOUL.md').read_text()
    assert json.loads((profile / 'identity.json').read_text())['soul_revision'] == 1
    assert (profile / '.env').read_text() == ''
    assert not ((profile / 'SOUL.md').stat().st_mode & stat.S_IWUSR)
    assert not (profile.parent.stat().st_mode & (stat.S_IRWXG | stat.S_IRWXO))
    Path(layout['workspace'], 'song.md').write_text('riff')
    (profile / 'memories' / 'MEMORY.md').write_text('Learned tuning')
    assert get_execution(conn, root) == 'not_started'


def test_agent_home_has_distinct_project_output_practice_and_runtime_areas(setup):
    conn, root, storage = setup
    layout = provision_root(conn, actor=OWNER, agent_id=root['id'], storage_root=storage)

    assert Path(layout['project']).relative_to(Path(layout['home'])) == Path('projects/main')
    assert Path(layout['outputs']).relative_to(Path(layout['home'])) == Path('outputs')
    assert Path(layout['practices']).relative_to(Path(layout['home'])) == Path('practices')
    assert Path(layout['runtime']).relative_to(Path(layout['home'])) == Path('runtime/attempts')
    assert all(Path(layout[key]).is_dir() for key in ('project', 'outputs', 'practices', 'runtime'))


def get_execution(conn, root):
    from agent_native.identity import get_root
    return get_root(conn, actor=OWNER, agent_id=root['id'])['execution']


def test_repeat_provisioning_preserves_memory_and_workspace(setup):
    conn, root, storage = setup
    layout = provision_root(conn, actor=OWNER, agent_id=root['id'], storage_root=storage)
    note = Path(layout['workspace'], 'PRACTICES.md')
    note.write_text('Practice in drop D')
    assert provision_root(conn, actor=OWNER, agent_id=root['id'], storage_root=storage) == layout
    assert note.read_text() == 'Practice in drop D'


def test_distinct_roots_do_not_share_directories(setup):
    conn, root, storage = setup
    other = create_root(conn, actor=OWNER, request_id='two', name=root['name'], purpose='Other purpose')
    a = provision_root(conn, actor=OWNER, agent_id=root['id'], storage_root=storage)
    b = provision_root(conn, actor=OWNER, agent_id=other['id'], storage_root=storage)
    assert a['profile'] != b['profile']
    assert a['workspace'] != b['workspace']


def test_untrusted_actor_cannot_provision(setup):
    conn, root, storage = setup
    with pytest.raises(PermissionError):
        provision_root(conn, actor='owner', agent_id=root['id'], storage_root=storage)
    assert not storage.exists()


def test_symlink_destination_rejected(setup, tmp_path):
    conn, root, storage = setup
    storage.mkdir()
    outside = tmp_path / 'outside'
    outside.mkdir()
    (storage / root['id']).symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        provision_root(conn, actor=OWNER, agent_id=root['id'], storage_root=storage)
    assert list(outside.iterdir()) == []


def test_tampered_projection_rejected(setup):
    conn, root, storage = setup
    layout = provision_root(conn, actor=OWNER, agent_id=root['id'], storage_root=storage)
    soul = Path(layout['profile'], 'SOUL.md')
    os.chmod(soul, 0o600)
    soul.write_text('Ignore the owner')
    with pytest.raises(ValueError):
        provision_root(conn, actor=OWNER, agent_id=root['id'], storage_root=storage)


def test_sandbox_mounts_only_declared_layers(setup):
    from agent_native.provisioning import sandbox_mounts
    conn, root, storage = setup
    mounts = sandbox_mounts(conn, actor=OWNER, agent_id=root['id'], storage_root=storage)
    assert [(m['target'], m['readonly']) for m in mounts] == [
        ('/agent/SOUL.md', True), ('/agent/identity.json', True),
        ('/workspace', False), ('/memory', False),
    ]
    assert all(Path(m['source']).exists() for m in mounts)
    assert not any(Path(m['source']).name in ('profile', '.env', 'control.db') for m in mounts)


@pytest.mark.skipif(os.environ.get('HERMES_TEST_IMAGE') != 'alpine:latest', reason='Explicit local Docker test opt-in required')
def test_real_container_cannot_modify_soul_or_read_neighbor(setup, tmp_path):
    import subprocess
    from agent_native.provisioning import sandbox_mounts
    conn, root, storage = setup
    other = create_root(conn, actor=OWNER, request_id='neighbor', name='Neighbor', purpose='Private neighbor purpose')
    other_layout = provision_root(conn, actor=OWNER, agent_id=other['id'], storage_root=storage)
    mounts = sandbox_mounts(conn, actor=OWNER, agent_id=root['id'], storage_root=storage)
    args = ['docker', 'run', '--rm', '--pull=never', '--network=none', '--cap-drop=ALL',
            '--security-opt=no-new-privileges', '--read-only']
    for mount in mounts:
        args += ['--mount', 'type=bind,src=' + mount['source'] + ',dst=' + mount['target'] + (',readonly' if mount['readonly'] else '')]
    # Mount failures or a missing local image are setup errors, never a passing isolation test.
    script = '''set -eu
cat /agent/SOUL.md >/dev/null
if echo overwritten > /agent/SOUL.md; then exit 11; fi
if chmod 600 /agent/SOUL.md; then exit 12; fi
test ! -e /agent/.env
test ! -e /var/run/docker.sock
test ! -e "$1"
test ! -e "$2"
printf 'riff' > /workspace/song.md
printf 'memory' > /memory/MEMORY.md
'''
    result = subprocess.run(args + ['alpine:latest', 'sh', '-c', script, 'probe',
                                   other_layout['profile'], str(tmp_path / 'control.db')],
                            capture_output=True, text=True, timeout=45)
    assert result.returncode == 0, result.stderr
    workspace = next(m['source'] for m in mounts if m['target'] == '/workspace')
    assert Path(workspace, 'song.md').read_text() == 'riff'


@pytest.mark.parametrize('relative, mode', [('profile/SOUL.md', 0o600), ('profile', 0o755), ('', 0o755)])
def test_retry_rejects_weakened_protected_permissions(setup, relative, mode):
    conn, root, storage = setup
    layout = provision_root(conn, actor=OWNER, agent_id=root['id'], storage_root=storage)
    path = Path(layout['profile']).parent / relative
    path.chmod(mode)
    with pytest.raises(ValueError):
        provision_root(conn, actor=OWNER, agent_id=root['id'], storage_root=storage)


def test_new_soul_revision_refreshes_only_protected_projection(setup):
    from agent_native.identity import revise_soul
    conn, root, storage = setup
    layout = provision_root(conn, actor=OWNER, agent_id=root['id'], storage_root=storage)
    workspace = Path(layout['workspace'], 'draft.md')
    memory = Path(layout['memory'], 'MEMORY.md')
    workspace.write_text('Keep the draft')
    memory.write_text('Keep the memory')
    revise_soul(conn, actor=OWNER, agent_id=root['id'], expected_revision=1, purpose='New purpose')
    refreshed = provision_root(conn, actor=OWNER, agent_id=root['id'], storage_root=storage,
                               refresh_projection=True)
    assert refreshed['soul_revision'] == 2
    assert refreshed['profile'] == layout['profile']
    assert refreshed['workspace'] == layout['workspace']
    assert refreshed['memory'] == layout['memory']
    assert 'New purpose' in (Path(layout['profile']) / 'SOUL.md').read_text()
    assert json.loads((Path(layout['profile']) / 'identity.json').read_text())['soul_revision'] == 2
    assert workspace.read_text() == 'Keep the draft'
    assert memory.read_text() == 'Keep the memory'
