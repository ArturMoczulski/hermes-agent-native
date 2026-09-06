"""Nonblocking exclusion for one host-local SQLite/Plane operation.

Use on local POSIX filesystems with a protected database parent. No SQLite
transaction spans the caller's work. Persistent 0700/0600 lock paths must not be
replaced or removed, even on release. An OS lock ends when its last descriptor
closes, including process death; descriptors are close-on-exec. Do not fork while
holding it. This is not a lease, distributed lock, or run-authentication boundary.
SQLite may resolve an opening alias before reporting the main database filename;
that canonical target shares one lock namespace. Never replace an open database.
"""
from contextlib import ExitStack, contextmanager
import errno
import os
from pathlib import Path
import sqlite3
import stat
from uuid import UUID

_POSIX = os.name == 'posix'


class OperationBusy(RuntimeError):
    """Another host execution/recovery call currently owns this operation."""


class OperationLockError(RuntimeError):
    """Operation exclusion cannot be safely established on this host."""


def _private(info, directory=False):
    valid_type = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    mode = 0o700 if directory else 0o600
    if (not valid_type or stat.S_IMODE(info.st_mode) != mode
            or info.st_uid != os.geteuid() or (not directory and info.st_nlink != 1)):
        raise OperationLockError('Unsafe Plane operation lock path')


def _same(left, right):
    return (left.st_dev, left.st_ino) == (right.st_dev, right.st_ino)


@contextmanager
def operation_lock(conn, operation_id):
    """Acquire once or raise OperationBusy; yield no transferable capability."""
    if not _POSIX:
        raise OperationLockError('Plane operation locks require a local POSIX host')
    with ExitStack() as handles:
        def open_fd(path, flags, mode=0o600, **kwargs):
            fd = os.open(path, flags | os.O_CLOEXEC | os.O_NOFOLLOW, mode, **kwargs)
            handles.callback(os.close, fd)
            return fd

        try:
            import fcntl

            if type(operation_id) is not str or str(UUID(operation_id)) != operation_id:
                raise OperationLockError('A canonical operation UUID is required')
            if not isinstance(conn, sqlite3.Connection):
                raise OperationLockError('A file-backed SQLite connection is required')
            filename = next((r[2] for r in conn.execute('PRAGMA database_list') if r[1] == 'main'), '')
            if not filename or not Path(filename).is_absolute():
                raise OperationLockError('A file-backed SQLite connection is required')
            db_info = Path(filename).lstat()
            if not stat.S_ISREG(db_info.st_mode) or db_info.st_nlink != 1 or db_info.st_uid != os.geteuid():
                raise OperationLockError('A private unaliased SQLite main file is required')
            db = Path(filename).resolve(strict=True)
            parent_fd = open_fd(db.parent, os.O_RDONLY | os.O_DIRECTORY)
            parent = os.fstat(parent_fd)
            if parent.st_uid != os.geteuid() or parent.st_mode & 0o022:
                raise OperationLockError('SQLite parent must be protected from other writers')
            directory = db.name + '.plane-operation-locks'
            try:
                os.mkdir(directory, mode=0o700, dir_fd=parent_fd)
            except FileExistsError:
                pass
            directory_fd = open_fd(directory, os.O_RDONLY | os.O_DIRECTORY, dir_fd=parent_fd)
            _private(os.fstat(directory_fd), directory=True)
            name = operation_id + '.lock'
            try:
                fd = open_fd(name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NONBLOCK, dir_fd=directory_fd)
            except FileExistsError:
                fd = open_fd(name, os.O_RDWR | os.O_NONBLOCK, dir_fd=directory_fd)
            _private(os.fstat(fd))
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as error:
                if error.errno in (errno.EACCES, errno.EAGAIN):
                    raise OperationBusy('Plane operation is already active') from None
                raise
            current = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            current_dir = os.stat(directory, dir_fd=parent_fd, follow_symlinks=False)
            _private(current)
            _private(current_dir, directory=True)
            if (not _same(os.fstat(fd), current) or not _same(os.fstat(directory_fd), current_dir)
                    or not _same(db_info, os.stat(db.name, dir_fd=parent_fd, follow_symlinks=False))):
                raise OperationLockError('Plane operation lock path changed during acquisition')
        except OperationBusy:
            raise
        except (OSError, ValueError, ImportError, sqlite3.Error):
            raise OperationLockError('Plane operation lock could not be established') from None
        yield
