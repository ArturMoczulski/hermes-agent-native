"""Real file/SQLite/OS lock boundaries; no Plane or provider access."""
from contextlib import closing
import os
from pathlib import Path
import select
import sqlite3
import subprocess
import sys
from threading import Event, Thread
from uuid import uuid4

import pytest

from agent_native.plane_operation_lock import OperationBusy, OperationLockError, operation_lock

pytestmark = pytest.mark.skipif(os.name != 'posix', reason='Real POSIX lock acceptance')


@pytest.fixture
def database(tmp_path):
    path = tmp_path / 'control.db'
    with closing(sqlite3.connect(path)) as conn:
        conn.execute('CREATE TABLE access (revoked INTEGER NOT NULL)')
        conn.execute('INSERT INTO access VALUES (0)')
        conn.commit()
        yield conn, path


def test_independent_connections_exclude_same_operation_without_sqlite_transaction(database):
    first, path = database
    operation = str(uuid4())
    with closing(sqlite3.connect(path, timeout=0)) as second:
        with operation_lock(first, operation):
            assert not first.in_transaction
            with pytest.raises(OperationBusy):
                with operation_lock(second, operation):
                    pytest.fail('Concurrent operation admitted')
            second.execute('UPDATE access SET revoked = 1')
            second.commit()
            assert first.execute('SELECT revoked FROM access').fetchone()[0] == 1
            assert not first.in_transaction
        with operation_lock(second, operation):
            assert not second.in_transaction


def test_other_operation_and_other_database_do_not_block(database, tmp_path):
    first, path = database
    operation = str(uuid4())
    with closing(sqlite3.connect(tmp_path / 'second.db')) as other:
        other.execute('CREATE TABLE t (x)')
        with operation_lock(first, operation):
            with operation_lock(first, str(uuid4())):
                with operation_lock(other, operation):
                    pass


def test_independent_thread_cannot_enter_held_operation(database):
    first, path = database
    operation = str(uuid4())
    finished = Event()
    outcomes = []

    def contender():
        try:
            with closing(sqlite3.connect(path)) as second:
                with operation_lock(second, operation):
                    outcomes.append('entered')
        except Exception as exc:
            outcomes.append(exc)
        finally:
            finished.set()

    with operation_lock(first, operation):
        thread = Thread(target=contender, daemon=True)
        thread.start()
        assert finished.wait(5), 'Nonblocking contender failed to return'
        thread.join(timeout=5)
        assert len(outcomes) == 1 and isinstance(outcomes[0], OperationBusy)


def test_lock_files_are_private_and_persist_on_release(database):
    conn, path = database
    operation = str(uuid4())
    before_paths = set(path.parent.iterdir())
    with operation_lock(conn, operation):
        directories = [p for p in path.parent.iterdir() if p.is_dir() and p not in before_paths]
        assert len(directories) == 1
        directory = directories[0]
        assert directory.stat().st_mode & 0o7777 == 0o700
        files = list(directory.iterdir())
        assert len(files) == 1
        lock = files[0]
        before = lock.stat()
        assert before.st_mode & 0o7777 == 0o600
        assert before.st_nlink == 1
    assert lock.stat().st_ino == before.st_ino
    with operation_lock(conn, operation):
        assert lock.stat().st_ino == before.st_ino


def test_body_exception_releases_lock(database):
    conn, path = database
    operation = str(uuid4())
    with pytest.raises(LookupError):
        with operation_lock(conn, operation):
            raise LookupError('fixture')
    with operation_lock(conn, operation):
        pass


def test_subprocess_lock_is_released_after_abrupt_exit(database):
    conn, path = database
    operation = str(uuid4())
    script = '''
import os, sqlite3, sys
from agent_native.plane_operation_lock import operation_lock
conn = sqlite3.connect(sys.argv[1])
with operation_lock(conn, sys.argv[2]):
    os.write(sys.stdout.fileno(), b'READY\\n')
    sys.stdin.buffer.read(1)
    os._exit(17)
'''
    child = subprocess.Popen(
        [sys.executable, '-c', script, str(path), operation],
        cwd=Path(__file__).resolve().parents[2],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    try:
        ready, _, _ = select.select([child.stdout], [], [], 5)
        assert ready, 'Child did not signal readiness'
        assert child.stdout.readline() == b'READY\n'
        with pytest.raises(OperationBusy):
            with operation_lock(conn, operation):
                pytest.fail('Subprocess lock not respected')
        child.stdin.write(b'x')
        child.stdin.flush()
        assert child.wait(timeout=5) == 17
        with operation_lock(conn, operation):
            pass
    finally:
        if child.poll() is None:
            child.kill()
        child.communicate(timeout=5)


@pytest.mark.parametrize('operation', [None, True, 1, str(uuid4()).upper(), 'not-a-uuid', '../escape', str(uuid4()) + '\n'])
def test_operation_uuid_must_be_canonical(database, operation):
    conn, path = database
    before = set(path.parent.iterdir())
    with pytest.raises(OperationLockError):
        with operation_lock(conn, operation):
            pytest.fail('Invalid lock identity accepted')
    assert set(path.parent.iterdir()) == before


@pytest.mark.parametrize('database_name', [':memory:', ''])
def test_memory_and_temporary_database_have_no_file_lock_guarantee(database_name):
    with closing(sqlite3.connect(database_name)) as conn:
        with pytest.raises(OperationLockError):
            with operation_lock(conn, str(uuid4())):
                pytest.fail('Non-file database admitted')


def test_non_posix_host_fails_explicitly(database, monkeypatch):
    import agent_native.plane_operation_lock as locks
    monkeypatch.setattr(locks, '_POSIX', False, raising=False)
    with pytest.raises(OperationLockError):
        with operation_lock(database[0], str(uuid4())):
            pytest.fail('Unsupported host admitted')


def _seed_lock(database):
    conn, path = database
    operation = str(uuid4())
    before = set(path.parent.iterdir())
    with operation_lock(conn, operation):
        directory = next(p for p in path.parent.iterdir() if p not in before and p.is_dir())
        lock = next(directory.iterdir())
    return operation, directory, lock


@pytest.mark.parametrize('mode', [0o755, 0o770, 0o777, 0o1700])
def test_permissive_or_special_directory_mode_is_not_repaired(database, mode):
    operation, directory, lock = _seed_lock(database)
    directory.chmod(mode)
    with pytest.raises(OperationLockError):
        with operation_lock(database[0], operation):
            pytest.fail('Unsafe directory accepted')
    assert directory.stat().st_mode & 0o7777 == mode


@pytest.mark.parametrize('mode', [0o644, 0o660, 0o666, 0o1600])
def test_permissive_or_special_file_mode_is_not_repaired(database, mode):
    operation, directory, lock = _seed_lock(database)
    lock.chmod(mode)
    with pytest.raises(OperationLockError):
        with operation_lock(database[0], operation):
            pytest.fail('Unsafe file accepted')
    assert lock.stat().st_mode & 0o7777 == mode


@pytest.mark.parametrize('kind', ['symlink', 'hardlink', 'fifo', 'directory'])
def test_lock_path_rejects_aliases_and_special_files(database, kind):
    operation, directory, lock = _seed_lock(database)
    lock.unlink()
    target = directory.parent / 'target'
    if kind in ('symlink', 'hardlink'):
        target.write_text('Must remain untouched')
        target.chmod(0o600)
    if kind == 'symlink':
        lock.symlink_to(target)
    elif kind == 'hardlink':
        os.link(target, lock)
    elif kind == 'fifo':
        os.mkfifo(lock, 0o600)
    else:
        lock.mkdir(mode=0o600)
    with pytest.raises(OperationLockError):
        with operation_lock(database[0], operation):
            pytest.fail('Non-private regular lock accepted')
    if target.exists():
        assert target.read_text() == 'Must remain untouched'


def test_lock_directory_cannot_be_replaced_by_symlink(database):
    operation, directory, lock = _seed_lock(database)
    original = directory.with_name('original-locks')
    directory.rename(original)
    directory.symlink_to(original, target_is_directory=True)
    with pytest.raises(OperationLockError):
        with operation_lock(database[0], operation):
            pytest.fail('Symlinked lock directory accepted')


def test_current_database_path_cannot_be_replaced_by_symlink(database):
    conn, path = database
    original = path.with_name('original.db')
    path.rename(original)
    path.symlink_to(original)
    with pytest.raises(OperationLockError):
        with operation_lock(conn, str(uuid4())):
            pytest.fail('Symlinked current database path accepted')


def test_hardlinked_database_cannot_get_independent_lock_namespace(database):
    conn, path = database
    os.link(path, path.with_name('alias.db'))
    with pytest.raises(OperationLockError):
        with operation_lock(conn, str(uuid4())):
            pytest.fail('Hard-linked database admitted')


def test_missing_or_special_main_file_rejected(database):
    conn, path = database
    path.unlink()
    with pytest.raises(OperationLockError):
        with operation_lock(conn, str(uuid4())):
            pytest.fail('Missing main file admitted')
    os.mkfifo(path, 0o600)
    with pytest.raises(OperationLockError):
        with operation_lock(conn, str(uuid4())):
            pytest.fail('Special main file admitted')


def test_database_permissions_unchanged_but_writable_parent_rejected(database):
    conn, path = database
    path.chmod(0o644)
    with operation_lock(conn, str(uuid4())):
        assert path.stat().st_mode & 0o777 == 0o644
    parent_mode = path.parent.stat().st_mode & 0o7777
    path.parent.chmod(0o777)
    try:
        with pytest.raises(OperationLockError):
            with operation_lock(conn, str(uuid4())):
                pytest.fail('Replaceable lock namespace accepted')
    finally:
        path.parent.chmod(parent_mode)


def test_sqlite_resolved_alias_uses_same_operation_namespace(database):
    conn, path = database
    alias = path.with_name('alias.db')
    alias.symlink_to(path)
    operation = str(uuid4())
    with closing(sqlite3.connect(alias)) as second:
        with operation_lock(conn, operation):
            # Some SQLite builds report the resolved target; others retain the alias.
            with pytest.raises((OperationBusy, OperationLockError)):
                with operation_lock(second, operation):
                    pytest.fail('Alias bypassed active operation')


def test_first_lock_creation_race_has_one_winner(database):
    from queue import Queue
    from threading import Barrier

    _, path = database
    operation = str(uuid4())
    start = Barrier(3)
    release = Event()
    outcomes = Queue()

    def contender():
        try:
            with closing(sqlite3.connect(path)) as conn:
                start.wait(timeout=5)
                with operation_lock(conn, operation):
                    outcomes.put('entered')
                    if not release.wait(5):
                        outcomes.put('release timed out')
        except OperationBusy:
            outcomes.put('busy')
        except Exception as error:
            outcomes.put(error)

    threads = [Thread(target=contender, daemon=True) for _ in range(2)]
    try:
        for thread in threads:
            thread.start()
        start.wait(timeout=5)
        results = [outcomes.get(timeout=5), outcomes.get(timeout=5)]
        assert set(results) == {'busy', 'entered'}
    finally:
        release.set()
        for thread in threads:
            thread.join(timeout=5)
    assert all(not thread.is_alive() for thread in threads)
    assert outcomes.empty()
