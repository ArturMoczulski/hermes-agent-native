"""Host-owned text outputs with stable identities and immutable versions.

Legacy story rows are copied without rewriting their files. Their original
checksums and evaluations remain verifiable; all new publications use this store.
"""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from uuid import UUID, uuid4

from agent_native import story_store as legacy

OUTPUT_SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_native_output_versions (
    output_id TEXT NOT NULL,
    version INTEGER NOT NULL CHECK(version > 0),
    agent_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    call_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    title TEXT NOT NULL,
    format TEXT NOT NULL CHECK(format IN ('markdown', 'text')),
    content TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    requested_output_id TEXT,
    origin TEXT NOT NULL CHECK(origin IN ('native', 'legacy_story')),
    evaluation_json TEXT,
    relative_path TEXT NOT NULL UNIQUE,
    byte_count INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY(output_id, version),
    UNIQUE(agent_id, run_id, call_id)
);
CREATE INDEX IF NOT EXISTS agent_native_output_agent
    ON agent_native_output_versions(agent_id, created_at);
"""
MAX_CONTENT_BYTES = legacy.MAX_CONTENT_BYTES
_PUBLIC = (
    "output_id", "version", "agent_id", "run_id", "call_id", "item_id", "title",
    "format", "relative_path", "content_sha256", "byte_count", "created_at",
)
_EXTENSIONS = {"markdown": "md", "text": "txt"}


class OutputIntegrityError(ValueError):
    """Canonical output or immutable file fails verification."""


def _payload(item_id, title, content, format, output_id):
    legacy._text(item_id, 255, "item identity")
    legacy._text(title, 255, "title")
    body = legacy._text(content, MAX_CONTENT_BYTES, "content")
    if type(format) is not str or format not in _EXTENSIONS:
        raise ValueError("Output format must be markdown or text")
    if output_id is not None and (
        type(output_id) is not str or str(UUID(output_id)) != output_id
    ):
        raise ValueError("Output identity must be a canonical UUID")
    payload = json.dumps([item_id, title, content, format, output_id], ensure_ascii=False)
    return body, sha256(payload.encode("utf-8")).hexdigest()


def _checked(row):
    try:
        if (str(UUID(row["output_id"])) != row["output_id"]
                or type(row["version"]) is not int or row["version"] < 1):
            raise ValueError
        if row["origin"] == "legacy_story":
            original = legacy._checked({**row, "story_id": row["output_id"]})
            if row["format"] != "markdown" or row["requested_output_id"] is not None:
                raise ValueError
            return {**{key: row[key] for key in _PUBLIC}, "evaluation": original["evaluation"]}
        if row["origin"] != "native" or row["evaluation_json"] is not None:
            raise ValueError
        body, digest = _payload(row["item_id"], row["title"], row["content"],
                                row["format"], row["requested_output_id"])
        path = f"outputs/{row['output_id']}/v{row['version']}.{_EXTENSIONS[row['format']]}"
        if (row["relative_path"] != path
                or row["content_sha256"] != sha256(body).hexdigest()
                or row["byte_count"] != len(body) or row["payload_sha256"] != digest
                or (row["version"] == 1 and row["requested_output_id"] is not None)
                or (row["version"] > 1 and row["requested_output_id"] != row["output_id"])):
            raise ValueError
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise OutputIntegrityError("Output version integrity verification failed") from exc
    return {key: row[key] for key in _PUBLIC}


def _directory(tree, workspace, row, *, create=False):
    collection, output_id, filename = row["relative_path"].split("/")
    directory = tree.output(workspace, output_id, collection=collection, create=create)
    return directory, filename


def publish(conn, *, validate, workspace: Path, agent_id, run_id, call_id,
            item_id, title, content, format, output_id=None, record_progress=None):
    """Publish atomically under live host authority; caller owns assignment scope.

    Omitting output_id creates a new output, including when this assignment has
    other outputs. Supplying it appends to that same agent/assignment/format.
    A repeated call identity must have exactly the original payload.
    """
    for value in (agent_id, run_id, call_id):
        legacy._text(value, 255, "host identity")
    body, digest = _payload(item_id, title, content, format, output_id)
    if not callable(validate):
        raise TypeError("Output publication requires a host authority validator")
    if conn.in_transaction:
        raise RuntimeError("Output publisher must own its control transaction")
    tree, commit_attempted = legacy._Tree(), False
    key = (agent_id, run_id, call_id)
    lookup = "SELECT * FROM agent_native_output_versions WHERE agent_id=? AND run_id=? AND call_id=?"
    conn.execute("BEGIN IMMEDIATE")
    try:
        validate(conn)
        row = legacy._row(conn.execute(lookup, key))
        if row is not None:
            result = _checked(row)
            if row["origin"] != "native" or row["payload_sha256"] != digest:
                raise ValueError("Output call was already used with a different payload")
            directory, filename = _directory(tree, workspace, row)
            tree.read(directory, filename, body)
        else:
            version, identity = 1, output_id or str(uuid4())
            if output_id is not None:
                latest = legacy._row(conn.execute(
                    "SELECT * FROM agent_native_output_versions WHERE agent_id=? AND output_id=? ORDER BY version DESC LIMIT 1",
                    (agent_id, output_id)))
                if latest is None:
                    raise LookupError("Output does not exist for this agent")
                _checked(latest)
                if latest["item_id"] != item_id or latest["format"] != format:
                    raise ValueError("Output assignment and format cannot change")
                version = latest["version"] + 1
            row = dict(output_id=identity, version=version, agent_id=agent_id,
                       run_id=run_id, call_id=call_id, item_id=item_id, title=title,
                       format=format, content=content, content_sha256=sha256(body).hexdigest(),
                       payload_sha256=digest, requested_output_id=output_id,
                       origin="native", evaluation_json=None,
                       relative_path=f"outputs/{identity}/v{version}.{_EXTENSIONS[format]}",
                       byte_count=len(body), created_at=datetime.now(timezone.utc).isoformat())
            result = _checked(row)
            directory, filename = _directory(tree, workspace, row, create=True)
            tree.publish(directory, filename, body)
            conn.execute(
                f"INSERT INTO agent_native_output_versions ({','.join(row)}) VALUES ({','.join('?' for _ in row)})",
                tuple(row.values()))
        validate(conn)
        tree.verify()
        if record_progress is not None:
            record_progress(conn, result)
            validate(conn)
        commit_attempted = True
        conn.commit()
        tree.keep = True
        return result
    except BaseException:
        if conn.in_transaction:
            conn.rollback()
        if commit_attempted:
            # Preserve a committed file when the acknowledgement was lost; the
            # next call reconciles against the canonical row before doing work.
            try:
                tree.keep = legacy._row(conn.execute(lookup, key)) is not None
            except Exception:
                tree.keep = True
        raise
    finally:
        tree.close()


def list_outputs(conn, agent_id):
    """Return canonical metadata scoped to one agent, newest versions first."""
    cursor = conn.execute(
        "SELECT * FROM agent_native_output_versions WHERE agent_id=? ORDER BY created_at DESC, output_id, version DESC",
        (agent_id,))
    columns = [col[0] for col in cursor.description]
    return [_checked(dict(zip(columns, row))) for row in cursor]


def read_output(conn, agent_id, output_id, version, *, workspace=None):
    """Read canonical content by scoped identity; optionally verify its file."""
    if type(version) is not int or version < 1:
        raise ValueError("Output version must be a positive integer")
    row = legacy._row(conn.execute(
        "SELECT * FROM agent_native_output_versions WHERE agent_id=? AND output_id=? AND version=?",
        (agent_id, output_id, version)))
    if row is None:
        raise LookupError("Output version does not exist")
    result = _checked(row)
    if workspace is not None:
        tree = legacy._Tree()
        try:
            directory, filename = _directory(tree, workspace, row)
            tree.read(directory, filename, row["content"].encode("utf-8"))
        finally:
            tree.close()
    return {**result, "content": row["content"]}


def migrate_stories(conn):
    """Copy verified legacy records atomically, preserving all original evidence.

    No files are opened or rewritten. Conflicting or corrupt rows abort the
    transaction instead of silently dropping data. Repeated initialization is safe.
    """
    if conn.in_transaction:
        raise RuntimeError("Output migration must own its control transaction")
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='agent_native_story_versions'").fetchone():
        return 0
    conn.execute("BEGIN IMMEDIATE")
    count = 0
    try:
        cursor = conn.execute("SELECT * FROM agent_native_story_versions ORDER BY story_id, version")
        columns = [col[0] for col in cursor.description]
        for values in cursor:
            row = dict(zip(columns, values))
            legacy._checked(row)
            row["output_id"] = row.pop("story_id")
            row.update(format="markdown", requested_output_id=None, origin="legacy_story")
            _checked(row)
            prior = legacy._row(conn.execute(
                "SELECT * FROM agent_native_output_versions WHERE output_id=? AND version=?",
                (row["output_id"], row["version"])))
            if prior is not None:
                _checked(prior)
                if prior != row:
                    raise OutputIntegrityError("Legacy story conflicts with its canonical output")
                continue
            conn.execute(
                f"INSERT INTO agent_native_output_versions ({','.join(row)}) VALUES ({','.join('?' for _ in row)})",
                tuple(row.values()))
            count += 1
        conn.commit()
        return count
    except BaseException:
        conn.rollback()
        raise
