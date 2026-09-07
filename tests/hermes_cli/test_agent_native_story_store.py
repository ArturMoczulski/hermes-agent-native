"""Real SQLite/filesystem boundaries for versioned story publication."""

from hashlib import sha256
from pathlib import Path
import sqlite3
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from agent_native import story_store as store


@pytest.fixture
def setup(tmp_path):
    conn = sqlite3.connect(tmp_path / "control.db", isolation_level=None)
    conn.executescript(store.STORY_SCHEMA)
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

    args = dict(
        validate=validate,
        workspace=workspace,
        agent_id=str(uuid4()),
        run_id=str(uuid4()),
        call_id="call_first",
        item_id=str(uuid4()),
        title="The emerald dragon",
        content="# The emerald dragon\n\nŻółty moonlight.\n",
        evaluation={
            "summary": "A draft for review",
            "criteria": ["Has a dragon"],
            "accepted": False,
        },
    )
    try:
        yield SimpleNamespace(conn=conn, workspace=workspace, args=args, checks=checks)
    finally:
        conn.close()


def publish(s, **changes):
    return store.publish(s.conn, **{**s.args, **changes})


def files(s):
    return sorted(
        p.relative_to(s.workspace).as_posix()
        for p in s.workspace.rglob("*")
        if p.is_file()
    )


def test_exact_file_body_canonical_read_and_safe_metadata(setup):
    s = setup
    result = publish(s)
    assert str(UUID(result["story_id"])) == result["story_id"]
    assert result["relative_path"] == f"stories/{result['story_id']}/v1.md"
    assert result["version"] == 1
    assert not Path(result["relative_path"]).is_absolute()
    body = s.args["content"].encode("utf-8")
    path = s.workspace / result["relative_path"]
    assert path.read_bytes() == body
    assert path.stat().st_mode & 0o777 == 0o400
    assert path.stat().st_nlink == 1
    assert result["content_sha256"] == sha256(body).hexdigest()
    assert result["byte_count"] == len(body)
    assert result["evaluation"] == s.args["evaluation"]
    assert "content" not in result
    assert len(s.checks) >= 2
    read = store.read_story(
        s.conn, s.args["agent_id"], result["story_id"], 1, workspace=s.workspace
    )
    assert read == {**result, "content": s.args["content"]}
    assert store.list_stories(s.conn, s.args["agent_id"]) == [result]


def test_same_call_is_idempotent_and_changed_payload_is_rejected(setup):
    s = setup
    first = publish(s)
    assert publish(s) == first
    with pytest.raises(ValueError):
        publish(s, content="Different body")
    assert files(s) == [first["relative_path"]]
    assert store.list_stories(s.conn, s.args["agent_id"]) == [first]


def test_versions_follow_item_without_overwriting_prior_content(setup):
    s = setup
    first = publish(s)
    second = publish(s, call_id="call_second", content="The revised dragon story.")
    assert second["story_id"] == first["story_id"]
    assert second["version"] == 2
    assert (s.workspace / first["relative_path"]).read_text() == s.args["content"]
    assert (
        s.workspace / second["relative_path"]
    ).read_text() == "The revised dragon story."
    other = publish(s, call_id="call_other", item_id=str(uuid4()))
    assert other["story_id"] != first["story_id"] and other["version"] == 1


def test_paused_run_cannot_publish_or_replay(setup):
    s = setup
    s.conn.execute("UPDATE run_authority SET active=0")
    with pytest.raises(PermissionError):
        publish(s)
    assert list(s.workspace.iterdir()) == []
    assert store.list_stories(s.conn, s.args["agent_id"]) == []


def test_read_is_agent_scoped(setup):
    s = setup
    result = publish(s)
    assert store.list_stories(s.conn, str(uuid4())) == []
    with pytest.raises(LookupError):
        store.read_story(s.conn, str(uuid4()), result["story_id"], 1)


@pytest.mark.parametrize("where", ["workspace", "ancestor", "stories"])
def test_symlink_traversal_is_rejected_without_outside_writes(setup, tmp_path, where):
    s = setup
    outside = tmp_path / "outside"
    outside.mkdir()
    if where == "workspace":
        link = tmp_path / "workspace-link"
        link.symlink_to(outside, target_is_directory=True)
        workspace = link
    elif where == "ancestor":
        link = tmp_path / "ancestor-link"
        link.symlink_to(tmp_path, target_is_directory=True)
        workspace = link / "workspace"
    else:
        (s.workspace / "stories").symlink_to(outside, target_is_directory=True)
        workspace = s.workspace
    with pytest.raises((OSError, ValueError)):
        publish(s, workspace=workspace)
    assert list(outside.iterdir()) == []
    assert store.list_stories(s.conn, s.args["agent_id"]) == []


@pytest.mark.parametrize("kind", ["symlink", "hardlink", "regular"])
def test_existing_version_target_is_never_followed_or_overwritten(
    setup, tmp_path, kind
):
    import os

    s = setup
    first = publish(s)
    target = (s.workspace / first["relative_path"]).parent / "v2.md"
    outside = tmp_path / "outside.md"
    outside.write_text("preserve this")
    if kind == "symlink":
        target.symlink_to(outside)
    elif kind == "hardlink":
        os.link(outside, target)
    else:
        target.write_text("preserve this")
    with pytest.raises((OSError, ValueError)):
        publish(s, call_id="next-call", content="new content")
    assert outside.read_text() == "preserve this"
    assert target.read_text() == "preserve this"
    assert store.list_stories(s.conn, s.args["agent_id"]) == [first]


def test_idempotent_replay_and_file_read_reject_hardlinked_publication(setup, tmp_path):
    import os

    s = setup
    first = publish(s)
    os.link(s.workspace / first["relative_path"], tmp_path / "aliased.md")
    with pytest.raises((OSError, ValueError)):
        publish(s)
    with pytest.raises((OSError, ValueError)):
        store.read_story(
            s.conn, s.args["agent_id"], first["story_id"], 1, workspace=s.workspace
        )
    # The canonical DB read remains safe and does not traverse the tampered file.
    assert (
        store.read_story(s.conn, s.args["agent_id"], first["story_id"], 1)["content"]
        == s.args["content"]
    )


def test_title_is_data_and_cannot_choose_a_path(setup):
    s = setup
    result = publish(s, title="../../outside.md")
    assert result["relative_path"] == f"stories/{result['story_id']}/v1.md"
    assert files(s) == [result["relative_path"]]


def test_second_authority_check_rolls_back_published_file(setup):
    s = setup
    checks = []

    def validate(conn):
        assert conn.in_transaction
        checks.append(True)
        if len(checks) == 2:
            assert len(files(s)) == 1
            raise PermissionError("Deadline passed while saving the story")

    with pytest.raises(PermissionError):
        publish(s, validate=validate)
    assert len(checks) == 2
    assert list(s.workspace.iterdir()) == []
    assert store.list_stories(s.conn, s.args["agent_id"]) == []


def test_real_sqlite_commit_failure_removes_uncommitted_file(setup):
    s = setup
    s.conn.execute("PRAGMA foreign_keys=ON")
    s.conn.executescript("""
        CREATE TABLE required_parent(id INTEGER PRIMARY KEY);
        CREATE TABLE deferred_guard(parent INTEGER REFERENCES required_parent(id) DEFERRABLE INITIALLY DEFERRED);
        CREATE TRIGGER fail_story_commit AFTER INSERT ON agent_native_story_versions
        BEGIN INSERT INTO deferred_guard VALUES(1); END;
    """)
    with pytest.raises(sqlite3.IntegrityError):
        publish(s)
    assert not s.conn.in_transaction
    assert list(s.workspace.iterdir()) == []
    assert store.list_stories(s.conn, s.args["agent_id"]) == []


def test_failed_atomic_file_publication_rolls_back_and_cleans_stage(setup, monkeypatch):
    import os

    s = setup

    def fail_link(*args, **kwargs):
        raise OSError("Injected atomic publication failure")

    monkeypatch.setattr(os, "link", fail_link)
    with pytest.raises(OSError):
        publish(s)
    assert list(s.workspace.iterdir()) == []
    assert store.list_stories(s.conn, s.args["agent_id"]) == []


def test_canonical_database_content_hash_is_verified_on_read(setup):
    s = setup
    first = publish(s)
    s.conn.execute("UPDATE agent_native_story_versions SET content=?", ("corrupted",))
    with pytest.raises(ValueError):
        store.read_story(s.conn, s.args["agent_id"], first["story_id"], 1)


def test_outer_transaction_is_refused_before_any_publication(setup):
    s = setup
    s.conn.execute("BEGIN IMMEDIATE")
    try:
        with pytest.raises(RuntimeError):
            publish(s)
        assert s.conn.in_transaction
        assert list(s.workspace.iterdir()) == []
    finally:
        s.conn.rollback()


@pytest.mark.parametrize("same_call", [True, False])
def test_independent_connections_serialize_publication_and_idempotency(
    setup, same_call
):
    import threading

    s = setup
    path = Path(s.conn.execute("PRAGMA database_list").fetchone()[2])
    barrier = threading.Barrier(2)
    results, errors = [], []

    def write(index):
        conn = sqlite3.connect(path, isolation_level=None)
        try:
            barrier.wait(timeout=5)
            call = "same_call" if same_call else f"call_{index}"
            results.append(store.publish(conn, **{**s.args, "call_id": call}))
        except BaseException as exc:
            errors.append(exc)
        finally:
            conn.close()

    threads = [threading.Thread(target=write, args=(index,)) for index in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert all(not thread.is_alive() for thread in threads)
    assert errors == [] and len(results) == 2
    assert len({row["story_id"] for row in results}) == 1
    assert sorted(row["version"] for row in results) == (
        [1, 1] if same_call else [1, 2]
    )
    assert len(files(s)) == (1 if same_call else 2)


@pytest.mark.parametrize(
    "changes",
    [
        {"content": ""},
        {"content": "x" * (store.MAX_CONTENT_BYTES + 1)},
        {"content": "\ud800"},
        {"evaluation": []},
        {"evaluation": {"summary": "x" * store.MAX_EVALUATION_BYTES}},
        {"evaluation": {"score": float("nan")}},
    ],
)
def test_invalid_or_oversized_payload_has_no_effect(setup, changes):
    s = setup
    with pytest.raises(ValueError):
        publish(s, **changes)
    assert list(s.workspace.iterdir()) == []
    assert store.list_stories(s.conn, s.args["agent_id"]) == []


def test_paused_run_cannot_replay_an_existing_call(setup):
    s = setup
    first = publish(s)
    s.conn.execute("UPDATE run_authority SET active=0")
    with pytest.raises(PermissionError):
        publish(s)
    assert store.list_stories(s.conn, s.args["agent_id"]) == [first]
    assert files(s) == [first["relative_path"]]


def test_swapped_file_entry_during_read_fails_projection_verification(
    setup, tmp_path, monkeypatch
):
    import os

    s = setup
    first = publish(s)
    target = s.workspace / first["relative_path"]
    outside = tmp_path / "outside.md"
    outside.write_text("unrelated outside text")
    identity = target.stat().st_ino
    original_read, swapped = os.read, []

    def swap(fd, amount):
        data = original_read(fd, amount)
        if not swapped and os.fstat(fd).st_ino == identity:
            swapped.append(True)
            target.rename(target.with_suffix(".moved"))
            target.symlink_to(outside)
        return data

    monkeypatch.setattr(os, "read", swap)
    with pytest.raises((OSError, ValueError)):
        store.read_story(
            s.conn, s.args["agent_id"], first["story_id"], 1, workspace=s.workspace
        )
    assert swapped == [True]
    assert outside.read_text() == "unrelated outside text"


def test_directory_fsync_failure_preserves_previous_version_only(setup, monkeypatch):
    import os
    import stat

    s = setup
    first = publish(s)
    original = os.fsync

    def fail_directory(fd):
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            raise OSError("Directory durability failure")
        return original(fd)

    monkeypatch.setattr(os, "fsync", fail_directory)
    with pytest.raises(OSError):
        publish(s, call_id="second", content="A revised story")
    assert files(s) == [first["relative_path"]]
    assert store.list_stories(s.conn, s.args["agent_id"]) == [first]


def test_lost_commit_acknowledgement_preserves_committed_publication(setup):
    s = setup
    path = Path(s.conn.execute("PRAGMA database_list").fetchone()[2])

    class LoseAck(sqlite3.Connection):
        lost = False

        def commit(self):
            super().commit()
            if not self.lost:
                self.lost = True
                raise OSError("Commit succeeded but acknowledgement was lost")

    conn = sqlite3.connect(path, isolation_level=None, factory=LoseAck)
    try:
        with pytest.raises(OSError):
            store.publish(conn, **s.args)
        published = store.list_stories(s.conn, s.args["agent_id"])
        assert len(published) == 1
        assert files(s) == [published[0]["relative_path"]]
        assert store.publish(conn, **s.args) == published[0]
    finally:
        conn.close()
