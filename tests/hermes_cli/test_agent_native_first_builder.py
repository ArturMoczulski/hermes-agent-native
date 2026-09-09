"""Protected First Builder preparation remains inert until an explicit launch."""

from pathlib import Path

import pytest

from agent_native.first_builder import active_runtime, confirm_owner_test, launch, prepare, read
from agent_native.identity import OWNER
from agent_native.work_service import WorkService
from hermes_cli.kanban_db_connect import connect_closing
from tests.hermes_cli.test_agent_native_api import client  # noqa: F401


def test_prepare_registers_exact_model_and_cannot_be_dispatched(tmp_path, monkeypatch):
    home = tmp_path / "service-home"
    repository = tmp_path / "framework"
    repository.mkdir()
    source = Path(__file__).resolve().parents[2] / "first-builder"
    monkeypatch.setattr(
        "agent_native.model_runtime.validate_choice",
        lambda choice: {"provider": choice["provider"], "model": choice["model"]},
    )
    monkeypatch.setattr("agent_native.model_runtime.validate_reasoning", lambda choice: choice["reasoning_effort"])

    with connect_closing(tmp_path / "control.db") as conn:
        builder = prepare(
            conn,
            actor=OWNER,
            home=home,
            repository=repository,
            instruction_source=source,
        )

        assert builder["name"] == "First Builder"
        assert builder["model_selection"] == {
            "provider": "openai-codex",
            "model": "gpt-5.6-sol",
            "revision": 1,
            "source": "override",
            "updated_at": builder["model_selection"]["updated_at"],
            "reasoning_effort": "low",
        }
        registration = read(conn, actor=OWNER)
        assert registration["agent_id"] == builder["id"]
        assert registration["launch_state"] == "held_for_owner_test"
        assert registration["repository"] == str(repository.resolve())
        assert registration["protected_instructions"].startswith(str(home.resolve()))
        assert registration["runtime_release"].startswith(str(home.resolve()))
        assert Path(registration["protected_instructions"], "SOUL.md").read_text() == (source / "SOUL.md").read_text()
        assert Path(registration["protected_instructions"], "PLANE.md").is_file()
        assert not Path(registration["protected_instructions"], "MEMORY.md").exists()
        assert builder["purpose"] == "Build, maintain, and improve the agent-native framework in this repository under the human owner's direction."
        assert builder["work"]["state"] == "queued"

        service = WorkService(tmp_path / "control.db", home)
        monkeypatch.setattr(service, "runs", {})
        service.tick()
        assert service.runs == {}

        again = prepare(
            conn,
            actor=OWNER,
            home=home,
            repository=repository,
            instruction_source=source,
        )
        assert again["id"] == builder["id"]


def test_prepare_rejects_a_changed_protected_runtime_generation(tmp_path, monkeypatch):
    home = tmp_path / "service-home"
    repository = tmp_path / "framework"
    repository.mkdir()
    source = Path(__file__).resolve().parents[2] / "first-builder"
    monkeypatch.setattr("agent_native.model_runtime.validate_choice", lambda choice: {"provider": choice["provider"], "model": choice["model"]})
    monkeypatch.setattr("agent_native.model_runtime.validate_reasoning", lambda choice: choice["reasoning_effort"])
    with connect_closing(tmp_path / "control.db") as conn:
        prepare(conn, actor=OWNER, home=home, repository=repository, instruction_source=source)
        runtime = Path(read(conn, actor=OWNER)["runtime_release"])
        target = runtime / "agent_native" / "first_builder.py"
        target.chmod(0o600)
        target.write_text("changed\n")
        with pytest.raises(ValueError, match="runtime changed"):
            prepare(conn, actor=OWNER, home=home, repository=repository, instruction_source=source)


def test_launch_requires_the_owner_test_checkpoint(tmp_path, monkeypatch):
    home = tmp_path / "service-home"
    repository = tmp_path / "framework"
    repository.mkdir()
    source = Path(__file__).resolve().parents[2] / "first-builder"
    monkeypatch.setattr("agent_native.model_runtime.validate_choice", lambda choice: {"provider": choice["provider"], "model": choice["model"]})
    monkeypatch.setattr("agent_native.model_runtime.validate_reasoning", lambda choice: choice["reasoning_effort"])
    with connect_closing(tmp_path / "control.db") as conn:
        builder = prepare(conn, actor=OWNER, home=home, repository=repository, instruction_source=source)
        with pytest.raises(ValueError, match="test agent"):
            launch(conn, actor=OWNER, agent_id=builder["id"])
        confirmed = confirm_owner_test(conn, actor=OWNER, agent_id=builder["id"], evidence="Ordinary agent passed final bounded test.")
        assert confirmed["launch_state"] == "ready_to_launch"
        active = launch(conn, actor=OWNER, agent_id=builder["id"])
        assert active["launch_state"] == "active"


def test_protected_runtime_starts_without_mutable_checkout_imports(tmp_path, monkeypatch):
    from tui_gateway.host_supervisor import HostSupervisor

    home = tmp_path / "service-home"
    repository = tmp_path / "framework"
    repository.mkdir()
    source = Path(__file__).resolve().parents[2] / "first-builder"
    monkeypatch.setattr("agent_native.model_runtime.validate_choice", lambda choice: {"provider": choice["provider"], "model": choice["model"]})
    monkeypatch.setattr("agent_native.model_runtime.validate_reasoning", lambda choice: choice["reasoning_effort"])
    with connect_closing(tmp_path / "control.db") as conn:
        builder = prepare(conn, actor=OWNER, home=home, repository=repository, instruction_source=source)
        confirm_owner_test(conn, actor=OWNER, agent_id=builder["id"], evidence="isolated runtime test")
        launch(conn, actor=OWNER, agent_id=builder["id"])
        runtime = active_runtime(conn, builder["id"])
    host = HostSupervisor(
        registry_path=tmp_path / "protected-host.json",
        env={"HERMES_HOME": str(tmp_path / "hermes")},
        expected_hermes_home=str(tmp_path / "hermes"),
        source_root=runtime,
    )
    try:
        assert host.is_running()
        assert host._hello["build_sha"] == "unknown"
    finally:
        host.shutdown()


def test_owner_can_prepare_and_inspect_but_not_launch_from_http(client, monkeypatch):
    monkeypatch.setattr(
        "agent_native.model_runtime.validate_choice",
        lambda choice: {"provider": choice["provider"], "model": choice["model"]},
    )
    monkeypatch.setattr("agent_native.model_runtime.validate_reasoning", lambda choice: choice["reasoning_effort"])
    endpoint = "/api/agent-native/first-builder"
    assert client.get(endpoint).status_code == 404
    response = client.post(endpoint + "/prepare")
    assert response.status_code == 201, response.text
    prepared = response.json()
    assert prepared["registration"]["launch_state"] == "held_for_owner_test"
    assert prepared["agent"]["model_selection"]["model"] == "gpt-5.6-sol"
    assert prepared["agent"]["model_selection"]["reasoning_effort"] == "low"
    assert client.post(endpoint + "/prepare").json()["agent"]["id"] == prepared["agent"]["id"]
    assert client.get(endpoint).json()["registration"]["agent_id"] == prepared["agent"]["id"]
    assert client.post(endpoint + "/launch", json={"agent_id": prepared["agent"]["id"]}).status_code == 409
    confirmed = client.post(endpoint + "/confirm-test", json={
        "agent_id": prepared["agent"]["id"], "evidence": "Final ordinary test agent passed."
    })
    assert confirmed.status_code == 200
    assert confirmed.json()["registration"]["launch_state"] == "ready_to_launch"
    launched = client.post(endpoint + "/launch", json={"agent_id": prepared["agent"]["id"]})
    assert launched.status_code == 200
    assert launched.json()["registration"]["launch_state"] == "active"
    client.headers.pop("X-Hermes-Session-Token")
    assert client.get(endpoint).status_code == 401
