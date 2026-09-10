import sqlite3

import pytest

from agent_native import media_store
from agent_native.identity import OWNER
from agent_native.project_workspace import grant
from agent_native.work_state import read_work
from tests.hermes_cli.test_agent_native_work_effects import broker, effect  # noqa: F401


PNG = b"\x89PNG\r\n\x1a\n" + b"agent-native-screenshot"


def test_media_output_is_copied_verified_and_reopened(tmp_path):
    conn = sqlite3.connect(":memory:")
    conn.executescript(media_store.MEDIA_SCHEMA)
    project = tmp_path / "project"
    output = tmp_path / "output"
    (project / "artifacts").mkdir(parents=True)
    (project / "artifacts" / "smoke.png").write_bytes(PNG)

    saved = media_store.publish(
        conn, validate=lambda _conn: None, project_workspace=project,
        output_workspace=output, agent_id="agent", run_id="run", call_id="call",
        item_id="item", title="Smoke screenshot", path="artifacts/smoke.png",
    )

    assert saved["mime_type"] == "image/png"
    assert saved["byte_count"] == len(PNG)
    assert saved["filename"] == "smoke.png"
    reopened, path = media_store.read(conn, "agent", saved["artifact_id"], workspace=output)
    assert reopened == saved
    assert path.read_bytes() == PNG


@pytest.mark.parametrize("path", ["../secret.png", "/tmp/secret.png"])
def test_media_output_rejects_paths_outside_project(tmp_path, path):
    conn = sqlite3.connect(":memory:")
    conn.executescript(media_store.MEDIA_SCHEMA)
    project = tmp_path / "project"
    project.mkdir()
    with pytest.raises(PermissionError):
        media_store.publish(
            conn, validate=lambda _conn: None, project_workspace=project,
            output_workspace=tmp_path / "output", agent_id="agent", run_id="run",
            call_id="call", item_id="item", title="Escape", path=path,
        )


def test_media_output_rejects_symlink_and_unsupported_type(tmp_path):
    conn = sqlite3.connect(":memory:")
    conn.executescript(media_store.MEDIA_SCHEMA)
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside.png"
    outside.write_bytes(PNG)
    (project / "linked.png").symlink_to(outside)
    (project / "script.js").write_text("alert(1)")
    for path in ("linked.png", "script.js"):
        with pytest.raises((PermissionError, ValueError)):
            media_store.publish(
                conn, validate=lambda _conn: None, project_workspace=project,
                output_workspace=tmp_path / "output", agent_id="agent", run_id="run",
                call_id=path, item_id="item", title="Rejected", path=path,
            )


def test_managed_agent_publishes_media_from_its_granted_project(broker, tmp_path):
    project = tmp_path / "game"
    (project / "artifacts").mkdir(parents=True)
    (project / "artifacts" / "smoke.png").write_bytes(PNG)
    grant(broker.conn, actor=OWNER, agent_id=broker.root["id"], expected_revision=1,
          root=str(project))

    saved = broker.run._effect(broker.conn, broker.planning, effect(
        broker, "media-one", "output_media_publish", {
            "item_id": broker.setup["discovery_item_id"],
            "title": "Playable smoke screenshot", "path": "artifacts/smoke.png",
        }))

    assert saved["mime_type"] == "image/png"
    assert read_work(broker.conn, broker.root["id"])["media_outputs"] == [saved]
