"""Shared output publication through real SQLite and immutable workspace files."""
from hashlib import sha256
from pathlib import Path
import sqlite3
from types import SimpleNamespace
from uuid import uuid4

import pytest

from agent_native import output_store as store
from agent_native import story_store


@pytest.fixture
def setup(tmp_path):
    conn = sqlite3.connect(tmp_path / "control.db", isolation_level=None)
    conn.executescript(store.OUTPUT_SCHEMA)
    workspace = tmp_path / "workspace"
    workspace.mkdir(mode=0o700)
    conn.execute("CREATE TABLE run_authority (active INTEGER NOT NULL)")
    conn.execute("INSERT INTO run_authority VALUES (1)")
    checks = []

    def validate(conn):
        assert conn.in_transaction
        checks.append(True)
        if conn.execute("SELECT active FROM run_authority").fetchone()[0] != 1:
            raise PermissionError("Run is paused or obsolete")

    args = dict(validate=validate, workspace=workspace, agent_id=str(uuid4()),
                run_id=str(uuid4()), call_id="call_first", item_id=str(uuid4()),
                title="Operational findings", content="# Findings\n\nŻółty report.\n",
                format="markdown")
    try:
        yield SimpleNamespace(conn=conn, workspace=workspace, args=args, checks=checks)
    finally:
        conn.close()


def publish(s, **changes):
    return store.publish(s.conn, **{**s.args, **changes})


def test_multiple_outputs_and_explicit_immutable_versions_per_assignment(setup):
    s = setup
    first = publish(s)
    another = publish(s, call_id="another", title="Recommendations", format="text")
    revised = publish(s, call_id="revision", output_id=first["output_id"], content="Revised analysis")
    assert first["output_id"] != another["output_id"]
    assert first["version"] == another["version"] == 1
    assert revised["output_id"] == first["output_id"] and revised["version"] == 2
    assert first["relative_path"] == f"outputs/{first['output_id']}/v1.md"
    assert another["relative_path"] == f"outputs/{another['output_id']}/v1.txt"
    for output in (first, another, revised):
        read = store.read_output(s.conn, s.args["agent_id"], output["output_id"], output["version"], workspace=s.workspace)
        body = read["content"].encode()
        path = s.workspace / output["relative_path"]
        assert path.read_bytes() == body
        assert path.stat().st_mode & 0o777 == 0o400
        assert output["content_sha256"] == sha256(body).hexdigest()
        assert output["byte_count"] == len(body)
        assert output["item_id"] == s.args["item_id"]
    assert (s.workspace / first["relative_path"]).read_text() == s.args["content"]
    assert len(store.list_outputs(s.conn, s.args["agent_id"])) == 3
    assert len(s.checks) == 6


def test_idempotence_rejects_payload_and_revision_target_changes(setup):
    s = setup
    first = publish(s)
    assert publish(s) == first
    for change in ({"content": "Different"}, {"format": "text"}, {"output_id": first["output_id"]}):
        with pytest.raises(ValueError):
            publish(s, **change)
    assert store.list_outputs(s.conn, s.args["agent_id"]) == [first]


def test_revision_requires_existing_same_agent_item_and_format(setup):
    s = setup
    first = publish(s)
    for change in ({"agent_id": str(uuid4())}, {"item_id": str(uuid4())}, {"format": "text"}, {"output_id": str(uuid4())}):
        with pytest.raises((ValueError, LookupError)):
            publish(s, **{ "call_id": "revision", "output_id": first["output_id"], **change})
    assert len(store.list_outputs(s.conn, s.args["agent_id"])) == 1
    with pytest.raises(LookupError):
        store.read_output(s.conn, str(uuid4()), first["output_id"], 1)


def test_pause_blocks_both_new_publication_and_replay(setup):
    s = setup
    first = publish(s)
    s.conn.execute("UPDATE run_authority SET active=0")
    for changes in ({}, {"call_id": "new"}):
        with pytest.raises(PermissionError):
            publish(s, **changes)
    assert store.list_outputs(s.conn, s.args["agent_id"]) == [first]


@pytest.mark.parametrize("where", ["workspace", "ancestor", "outputs"])
def test_no_follow_output_publication(setup, tmp_path, where):
    s = setup
    outside = tmp_path / "outside"
    outside.mkdir()
    workspace = s.workspace
    if where == "workspace":
        workspace = tmp_path / "workspace-link"
        workspace.symlink_to(outside, target_is_directory=True)
    elif where == "ancestor":
        link = tmp_path / "ancestor-link"
        link.symlink_to(tmp_path, target_is_directory=True)
        workspace = link / "workspace"
    else:
        (workspace / "outputs").symlink_to(outside, target_is_directory=True)
    with pytest.raises(OSError):
        publish(s, workspace=workspace)
    assert list(outside.iterdir()) == []
    assert store.list_outputs(s.conn, s.args["agent_id"]) == []


def test_final_validation_rolls_back_file_and_canonical_row(setup):
    s = setup
    calls = []
    def validate(conn):
        calls.append(True)
        if len(calls) == 2:
            raise PermissionError("Authority changed")
    with pytest.raises(PermissionError):
        publish(s, validate=validate)
    assert list(s.workspace.iterdir()) == []
    assert store.list_outputs(s.conn, s.args["agent_id"]) == []


def test_corrupt_canonical_body_and_file_are_detected(setup):
    s = setup
    first = publish(s)
    path = s.workspace / first["relative_path"]
    path.chmod(0o600)
    path.write_text("Tampered")
    with pytest.raises(ValueError):
        store.read_output(s.conn, s.args["agent_id"], first["output_id"], 1, workspace=s.workspace)
    s.conn.execute("UPDATE agent_native_output_versions SET content='Tampered'")
    with pytest.raises(ValueError):
        store.list_outputs(s.conn, s.args["agent_id"])


def test_migration_preserves_legacy_stories_without_rewriting_files(tmp_path):
    conn = sqlite3.connect(tmp_path / "legacy.db", isolation_level=None)
    conn.executescript(story_store.STORY_SCHEMA)
    workspace = tmp_path / "legacy-workspace"
    workspace.mkdir(mode=0o700)
    args = dict(validate=lambda conn: None, workspace=workspace, agent_id=str(uuid4()),
                run_id=str(uuid4()), call_id="legacy", item_id=str(uuid4()),
                title="Existing story", content="# Existing story\n", evaluation={"accepted": False, "notes": "review"})
    original = story_store.publish(conn, **args)
    second = story_store.publish(conn, **{**args, "call_id": "legacy2", "content": "Second version"})
    before = [(workspace / x["relative_path"]).stat() for x in (original, second)]
    conn.executescript(store.OUTPUT_SCHEMA)
    assert store.migrate_stories(conn) == 2
    assert store.migrate_stories(conn) == 0
    for output, info in zip((original, second), before):
        read = store.read_output(conn, args["agent_id"], output["story_id"], output["version"], workspace=workspace)
        assert read["output_id"] == output["story_id"]
        assert read["format"] == "markdown"
        for key in ("agent_id", "run_id", "call_id", "item_id", "title", "relative_path", "content_sha256", "byte_count", "created_at", "evaluation"):
            assert read[key] == output[key]
        after = (workspace / output["relative_path"]).stat()
        assert (after.st_ino, after.st_mtime_ns) == (info.st_ino, info.st_mtime_ns)
        assert story_store.read_story(conn, args["agent_id"], output["story_id"], output["version"], workspace=workspace)["content"] == read["content"]
    revised = store.publish(conn, **{key: value for key, value in args.items() if key not in ("evaluation", "call_id")}, format="markdown", output_id=original["story_id"], call_id="generic_revision")
    assert revised["version"] == 3 and revised["output_id"] == original["story_id"]
    assert revised["relative_path"].startswith("outputs/")
    assert store.migrate_stories(conn) == 0
    conn.close()


def test_upgrade_initialization_preserves_legacy_and_closes_legacy_writer(tmp_path):
    from hermes_cli.kanban_db_connect import connect_closing
    path = tmp_path / "control-upgrade.db"
    workspace = tmp_path / "upgrade-workspace"
    workspace.mkdir(mode=0o700)
    args = dict(validate=lambda conn: None, workspace=workspace, agent_id=str(uuid4()),
                run_id=str(uuid4()), call_id="legacy", item_id=str(uuid4()),
                title="Existing", content="Existing content", evaluation={"accepted": False})
    with sqlite3.connect(path, isolation_level=None) as conn:
        conn.executescript(story_store.STORY_SCHEMA)
        original = story_store.publish(conn, **args)
    with connect_closing(path) as conn:
        saved = store.read_output(conn, args["agent_id"], original["story_id"], 1, workspace=workspace)
        assert saved["content"] == args["content"]
        assert saved["evaluation"] == args["evaluation"]
        assert saved["relative_path"] == original["relative_path"]
        with pytest.raises(RuntimeError, match="output"):
            story_store.publish(conn, **{**args, "call_id": "new-legacy"})
        assert story_store.list_stories(conn, args["agent_id"]) == [original]
    with connect_closing(path) as conn:
        assert len(store.list_outputs(conn, args["agent_id"])) == 1
