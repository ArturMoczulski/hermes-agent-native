"""Immutable media outputs copied from an agent's granted project workspace."""

from datetime import datetime, timezone
from hashlib import sha256
import os
from pathlib import Path
import shutil
import tempfile
from uuid import UUID, uuid4

from agent_native.builder_repository import _path


MEDIA_SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_native_media_outputs (
 artifact_id TEXT PRIMARY KEY,
 agent_id TEXT NOT NULL,
 run_id TEXT NOT NULL,
 call_id TEXT NOT NULL,
 item_id TEXT NOT NULL,
 title TEXT NOT NULL,
 filename TEXT NOT NULL,
 mime_type TEXT NOT NULL,
 content_sha256 TEXT NOT NULL,
 relative_path TEXT NOT NULL UNIQUE,
 byte_count INTEGER NOT NULL,
 created_at TEXT NOT NULL,
 UNIQUE(agent_id, run_id, call_id)
);
CREATE INDEX IF NOT EXISTS agent_native_media_agent
 ON agent_native_media_outputs(agent_id, created_at);
"""

MAX_MEDIA_BYTES = 100 * 1024 * 1024
_PUBLIC = ("artifact_id", "agent_id", "run_id", "call_id", "item_id", "title",
           "filename", "mime_type", "content_sha256", "byte_count", "created_at")


class MediaIntegrityError(ValueError):
    pass


def _text(value, label, maximum=255):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or "\x00" in value:
        raise ValueError(f"Media {label} must be nonblank text")
    return value.strip()


def _sniff(path, body):
    ext = path.suffix.lower()
    signatures = {
        ".png": ("image/png", body.startswith(b"\x89PNG\r\n\x1a\n")),
        ".jpg": ("image/jpeg", body.startswith(b"\xff\xd8\xff")),
        ".jpeg": ("image/jpeg", body.startswith(b"\xff\xd8\xff")),
        ".gif": ("image/gif", body.startswith((b"GIF87a", b"GIF89a"))),
        ".webp": ("image/webp", len(body) >= 12 and body[:4] == b"RIFF" and body[8:12] == b"WEBP"),
        ".wav": ("audio/wav", len(body) >= 12 and body[:4] == b"RIFF" and body[8:12] == b"WAVE"),
        ".mp3": ("audio/mpeg", body.startswith(b"ID3") or (len(body) >= 2 and body[0] == 0xff and body[1] & 0xe0 == 0xe0)),
        ".ogg": ("audio/ogg", body.startswith(b"OggS")),
        ".mp4": ("video/mp4", len(body) >= 12 and body[4:8] == b"ftyp"),
        ".webm": ("video/webm", body.startswith(b"\x1aE\xdf\xa3")),
    }
    mime, valid = signatures.get(ext, (None, False))
    if not valid:
        raise ValueError("Media file type is unsupported or does not match its content")
    return mime


def _row(cursor):
    value = cursor.fetchone()
    return None if value is None else dict(zip((column[0] for column in cursor.description), value))


def _checked(row):
    try:
        if str(UUID(row["artifact_id"])) != row["artifact_id"]:
            raise ValueError
        for field in ("agent_id", "run_id", "call_id", "item_id", "title", "filename", "mime_type"):
            _text(row[field], field)
        expected = f"artifacts/{row['artifact_id']}/{row['filename']}"
        if row["relative_path"] != expected or len(row["content_sha256"]) != 64 or row["byte_count"] < 1:
            raise ValueError
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise MediaIntegrityError("Media output integrity verification failed") from exc
    return {key: row[key] for key in _PUBLIC}


def _destination(workspace, row):
    root = Path(workspace).resolve()
    directory = root / "artifacts" / row["artifact_id"]
    return directory, directory / row["filename"]


def publish(conn, *, validate, project_workspace, output_workspace, agent_id, run_id,
            call_id, item_id, title, path):
    if not callable(validate):
        raise TypeError("Media publication requires a host authority validator")
    for value in (agent_id, run_id, call_id, item_id):
        _text(value, "identity")
    title = _text(title, "title")
    _, source = _path(project_workspace, path, existing=True)
    size = source.stat().st_size
    if not 1 <= size <= MAX_MEDIA_BYTES:
        raise ValueError("Media file is empty or exceeds the 100 MB limit")
    body = source.read_bytes()
    if len(body) != size:
        raise ValueError("Media file changed while it was read")
    mime = _sniff(source, body)
    digest = sha256(body).hexdigest()
    existing = _row(conn.execute(
        "SELECT * FROM agent_native_media_outputs WHERE agent_id=? AND run_id=? AND call_id=?",
        (agent_id, run_id, call_id)))
    if existing is not None:
        result = _checked(existing)
        if existing["content_sha256"] != digest or existing["item_id"] != item_id or existing["title"] != title:
            raise ValueError("Media call was already used with a different file")
        read(conn, agent_id, existing["artifact_id"], workspace=output_workspace)
        return result

    identity = str(uuid4())
    filename = source.name
    row = dict(artifact_id=identity, agent_id=agent_id, run_id=run_id, call_id=call_id,
               item_id=item_id, title=title, filename=filename, mime_type=mime,
               content_sha256=digest, relative_path=f"artifacts/{identity}/{filename}",
               byte_count=len(body), created_at=datetime.now(timezone.utc).isoformat())
    result = _checked(row)
    directory, destination = _destination(output_workspace, row)
    directory.mkdir(parents=True, exist_ok=False)
    temporary = None
    try:
        validate(conn)
        fd, temporary = tempfile.mkstemp(prefix=".media-", dir=directory)
        with os.fdopen(fd, "wb") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
        temporary = None
        validate(conn)
        conn.execute(
            f"INSERT INTO agent_native_media_outputs ({','.join(row)}) VALUES ({','.join('?' for _ in row)})",
            tuple(row.values()))
        conn.commit()
        return result
    except BaseException:
        if conn.in_transaction:
            conn.rollback()
        shutil.rmtree(directory, ignore_errors=True)
        raise
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def list_media(conn, agent_id):
    cursor = conn.execute(
        "SELECT * FROM agent_native_media_outputs WHERE agent_id=? ORDER BY created_at DESC, artifact_id",
        (agent_id,))
    columns = [column[0] for column in cursor.description]
    return [_checked(dict(zip(columns, values))) for values in cursor]


def read(conn, agent_id, artifact_id, *, workspace):
    row = _row(conn.execute(
        "SELECT * FROM agent_native_media_outputs WHERE agent_id=? AND artifact_id=?",
        (agent_id, artifact_id)))
    if row is None:
        raise LookupError("Media output does not exist")
    result = _checked(row)
    _, path = _destination(workspace, row)
    if path.is_symlink() or not path.is_file():
        raise MediaIntegrityError("Media output file is unavailable")
    body = path.read_bytes()
    if len(body) != row["byte_count"] or sha256(body).hexdigest() != row["content_sha256"]:
        raise MediaIntegrityError("Media output file does not match its record")
    return result, path
