"""Host-owned story content and immutable workspace publications."""

STORY_SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_native_story_versions (
    story_id TEXT NOT NULL,
    version INTEGER NOT NULL CHECK(version > 0),
    agent_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    call_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    evaluation_json TEXT NOT NULL,
    relative_path TEXT NOT NULL UNIQUE,
    byte_count INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY(story_id, version),
    UNIQUE(agent_id, item_id, version),
    UNIQUE(agent_id, run_id, call_id)
);
"""


from contextlib import suppress
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import stat
from uuid import UUID, uuid4

MAX_CONTENT_BYTES = 1024 * 1024
MAX_EVALUATION_BYTES = 16 * 1024
_PUBLIC = (
    "story_id",
    "version",
    "agent_id",
    "run_id",
    "call_id",
    "item_id",
    "title",
    "relative_path",
    "content_sha256",
    "byte_count",
    "created_at",
)


class StoryIntegrityError(ValueError):
    """Stored content or its immutable file no longer matches the publication."""


def _text(value, limit, label):
    if (
        type(value) is not str
        or not value.strip()
        or len(value) > limit
        or "\x00" in value
    ):
        raise ValueError(f"Invalid story {label}")
    try:
        encoded = value.encode("utf-8")
    except UnicodeError as exc:
        raise ValueError(f"Invalid story {label}") from exc
    if len(encoded) > limit:
        raise ValueError(f"Story {label} exceeds its size limit")
    return encoded


def _payload(item_id, title, content, evaluation):
    _text(item_id, 255, "item identity")
    _text(title, 255, "title")
    body = _text(content, MAX_CONTENT_BYTES, "content")
    if type(evaluation) is not dict:
        raise ValueError("Story evaluation must be a JSON object")
    try:
        report = json.dumps(
            evaluation, sort_keys=True, ensure_ascii=False, allow_nan=False
        )
        if len(report.encode("utf-8")) > MAX_EVALUATION_BYTES:
            raise ValueError("Story evaluation exceeds its size limit")
        payload = json.dumps(
            [item_id, title, content, json.loads(report)],
            ensure_ascii=False,
            sort_keys=True,
        )
    except (TypeError, UnicodeError, RecursionError) as exc:
        raise ValueError("Invalid story evaluation") from exc
    return body, report, sha256(payload.encode("utf-8")).hexdigest()


def _row(cursor):
    row = cursor.fetchone()
    return (
        dict(zip((col[0] for col in cursor.description), row))
        if row is not None
        else None
    )


def _checked(row):
    try:
        if (
            str(UUID(row["story_id"])) != row["story_id"]
            or type(row["version"]) is not int
            or row["version"] < 1
        ):
            raise ValueError
        evaluation = json.loads(row["evaluation_json"])
        body, _, digest = _payload(
            row["item_id"], row["title"], row["content"], evaluation
        )
        path = f"stories/{row['story_id']}/v{row['version']}.md"
        if (
            row["relative_path"] != path
            or row["content_sha256"] != sha256(body).hexdigest()
            or row["byte_count"] != len(body)
            or row["payload_sha256"] != digest
        ):
            raise ValueError
    except (KeyError, TypeError, ValueError) as exc:
        raise StoryIntegrityError(
            "Story version integrity verification failed"
        ) from exc
    return {**{key: row[key] for key in _PUBLIC}, "evaluation": evaluation}


def _same(info, other):
    return (info.st_dev, info.st_ino) == (other.st_dev, other.st_ino)


class _Tree:
    """Held no-follow directory handles; cleanup removes only our own inodes."""

    def __init__(self):
        self.fds, self.edges, self.created_dirs, self.created_files = [], [], [], []
        self.keep = False

    def _open_dir(self, parent, name, *, create=False):
        if create:
            try:
                os.mkdir(name, mode=0o700, dir_fd=parent)
                self.created_dirs.append((
                    parent,
                    name,
                    os.stat(name, dir_fd=parent, follow_symlinks=False),
                ))
            except FileExistsError:
                pass
        fd = os.open(
            name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=parent,
        )
        self.fds.append(fd)
        self.edges.append((parent, name, fd))
        info = os.fstat(fd)
        if create and (
            info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700
        ):
            raise PermissionError(
                "Story directories must remain private and host-owned"
            )
        return fd

    def story(self, workspace, story_id, *, create=False):
        if os.name != "posix":
            raise OSError(
                "Story publication requires POSIX no-follow directory operations"
            )
        if (
            not isinstance(workspace, Path)
            or not workspace.is_absolute()
            or ".." in workspace.parts
        ):
            raise ValueError(
                "Story workspace must be an absolute path without traversal"
            )
        root = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        self.fds.append(root)
        fd = root
        for name in workspace.parts[1:]:
            fd = self._open_dir(fd, name)
        info = os.fstat(fd)
        if info.st_uid != os.geteuid() or info.st_mode & 0o022:
            raise PermissionError(
                "Story workspace must be host-owned without shared write access"
            )
        fd = self._open_dir(fd, "stories", create=create)
        return self._open_dir(fd, story_id, create=create)

    def verify(self):
        for parent, name, fd in self.edges:
            if not _same(
                os.stat(name, dir_fd=parent, follow_symlinks=False), os.fstat(fd)
            ):
                raise PermissionError("Story directory changed during publication")

    def read(self, directory, name, body):
        fd = os.open(
            name,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK,
            dir_fd=directory,
        )
        try:
            info = os.fstat(fd)
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_nlink != 1
                or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) != 0o400
                or info.st_size != len(body)
            ):
                raise StoryIntegrityError(
                    "Story file is not the private immutable publication"
                )
            chunks, remaining = [], len(body) + 1
            while remaining:
                chunk = os.read(fd, min(remaining, 65536))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            after = os.fstat(fd)
            if (
                b"".join(chunks) != body
                or after.st_nlink != 1
                or after.st_size != len(body)
            ):
                raise StoryIntegrityError(
                    "Story file content does not match its canonical version"
                )
            if not _same(os.stat(name, dir_fd=directory, follow_symlinks=False), after):
                raise StoryIntegrityError(
                    "Story file entry changed during verification"
                )
            self.verify()
        finally:
            os.close(fd)

    def publish(self, directory, name, body):
        stage = ".story-" + uuid4().hex + ".tmp"
        fd = os.open(
            stage,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=directory,
        )
        info = os.fstat(fd)
        self.created_files.append((directory, stage, info))
        try:
            view = memoryview(body)
            while view:
                count = os.write(fd, view)
                if count <= 0:
                    raise OSError("Story file write made no progress")
                view = view[count:]
            os.fchmod(fd, 0o400)
            os.fsync(fd)
            self.verify()
            # link is atomic and refuses an existing target; rename/replace could overwrite it.
            os.link(
                stage,
                name,
                src_dir_fd=directory,
                dst_dir_fd=directory,
                follow_symlinks=False,
            )
            self.created_files.append((directory, name, info))
            os.unlink(stage, dir_fd=directory)
            os.fsync(directory)
            self.read(directory, name, body)
        finally:
            os.close(fd)

    def close(self):
        if not self.keep:
            for parent, name, info in reversed(self.created_files):
                with suppress(OSError):
                    if _same(os.stat(name, dir_fd=parent, follow_symlinks=False), info):
                        os.unlink(name, dir_fd=parent)
            for parent, name, info in reversed(self.created_dirs):
                with suppress(OSError):
                    if _same(os.stat(name, dir_fd=parent, follow_symlinks=False), info):
                        os.rmdir(name, dir_fd=parent)
        for fd in reversed(self.fds):
            with suppress(OSError):
                os.close(fd)


def publish(
    conn,
    *,
    validate,
    workspace: Path,
    agent_id,
    run_id,
    call_id,
    item_id,
    title,
    content,
    evaluation,
):
    """Validate and publish one version; the callback raises on inactive/stale authority.

    Owns the control transaction. Canonical rows become visible only after the
    complete file exists. Exceptions roll back and remove our files; abrupt host
    death can leave an unreferenced file, never an accepted incomplete DB row.
    The caller owns item scope and treats evaluation as an agent report only.
    """
    for value in (agent_id, run_id, call_id):
        _text(value, 255, "host identity")
    body, report, digest = _payload(item_id, title, content, evaluation)
    if not callable(validate):
        raise TypeError("Story publication requires a host authority validator")
    if conn.in_transaction:
        raise RuntimeError("Story publisher must own its control transaction")
    tree, commit_attempted = _Tree(), False
    key = (agent_id, run_id, call_id)
    lookup = "SELECT * FROM agent_native_story_versions WHERE agent_id=? AND run_id=? AND call_id=?"
    conn.execute("BEGIN IMMEDIATE")
    try:
        validate(conn)
        row = _row(conn.execute(lookup, key))
        if row is not None:
            result = _checked(row)
            if row["payload_sha256"] != digest:
                raise ValueError("Story call was already used with a different payload")
            directory = tree.story(workspace, row["story_id"])
            tree.read(directory, f"v{row['version']}.md", body)
        else:
            latest = _row(
                conn.execute(
                    "SELECT * FROM agent_native_story_versions WHERE agent_id=? AND item_id=? ORDER BY version DESC LIMIT 1",
                    (agent_id, item_id),
                )
            )
            if latest:
                _checked(latest)
            story_id, version = (
                (latest["story_id"], latest["version"] + 1)
                if latest
                else (str(uuid4()), 1)
            )
            directory = tree.story(workspace, story_id, create=True)
            tree.publish(directory, f"v{version}.md", body)
            row = dict(
                story_id=story_id,
                version=version,
                agent_id=agent_id,
                run_id=run_id,
                call_id=call_id,
                item_id=item_id,
                title=title,
                content=content,
                content_sha256=sha256(body).hexdigest(),
                payload_sha256=digest,
                evaluation_json=report,
                relative_path=f"stories/{story_id}/v{version}.md",
                byte_count=len(body),
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            conn.execute(
                f"INSERT INTO agent_native_story_versions ({','.join(row)}) VALUES ({','.join('?' for _ in row)})",
                tuple(row.values()),
            )
            result = _checked(row)
        validate(conn)
        tree.verify()
        commit_attempted = True
        conn.commit()
        tree.keep = True
        return result
    except BaseException:
        if conn.in_transaction:
            conn.rollback()
        if commit_attempted:
            # A lost COMMIT acknowledgement must not delete a file whose row did
            # commit. Retain it on an unreadable outcome; reads expose DB rows only.
            try:
                tree.keep = _row(conn.execute(lookup, key)) is not None
            except Exception:
                tree.keep = True
        raise
    finally:
        tree.close()


def list_stories(conn, agent_id):
    """All published versions, newest first. The caller enforces owner authority."""
    cursor = conn.execute(
        "SELECT * FROM agent_native_story_versions WHERE agent_id=? ORDER BY created_at DESC, version DESC",
        (agent_id,),
    )
    columns = [col[0] for col in cursor.description]
    return [_checked(dict(zip(columns, row))) for row in cursor]


def read_story(conn, agent_id, story_id, version, *, workspace=None):
    """Read canonical content by scoped IDs; optionally verify the file projection."""
    if type(version) is not int or version < 1:
        raise ValueError("Story version must be a positive integer")
    row = _row(
        conn.execute(
            "SELECT * FROM agent_native_story_versions WHERE agent_id=? AND story_id=? AND version=?",
            (agent_id, story_id, version),
        )
    )
    if row is None:
        raise LookupError("Story version does not exist")
    result = _checked(row)
    if workspace is not None:
        tree = _Tree()
        try:
            directory = tree.story(workspace, row["story_id"])
            tree.read(
                directory, f"v{row['version']}.md", row["content"].encode("utf-8")
            )
        finally:
            tree.close()
    return {**result, "content": row["content"]}
