"""Owner-prepared First Builder identity with an explicit pre-launch hold."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile

from agent_native.identity import OWNER, _now, _require_owner, create_root, get_root
from hermes_cli.kanban_db_connect import write_txn


SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_native_first_builder (
 id INTEGER PRIMARY KEY CHECK(id=1),
 agent_id TEXT NOT NULL UNIQUE REFERENCES agent_native_agents(id),
 repository TEXT NOT NULL,
 protected_instructions TEXT NOT NULL,
 runtime_release TEXT NOT NULL,
 instruction_sha256 TEXT NOT NULL,
 launch_state TEXT NOT NULL CHECK(launch_state IN ('held_for_owner_test','ready_to_launch','active')),
 owner_test_evidence TEXT,
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL
);
"""

MODEL = {"provider": "openai-codex", "model": "gpt-5.6-sol", "reasoning_effort": "low"}
PURPOSE = "Build, maintain, and improve the agent-native framework in this repository under the human owner's direction."
WORK_LIMITS = {"timeout_seconds": 1800, "max_iterations": 200}
PLANE = {
    "origin": "http://localhost:19230",
    "workspace_slug": "agent-native",
    "workspace_id": "34f36591-6596-40c9-bf66-564529b2c4df",
    "project_id": "0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897",
    "item_id": "d1d913c7-0cc1-4965-9daf-5a419d43b978",
}
_FILES = ("SOUL.md", "INSTRUCTIONS.md", "PRACTICES.md", "PLANE.md")
_RUNTIME_PACKAGES = ("agent", "agent_native", "hermes_cli", "providers", "tools", "tui_gateway")


def _safe_directory(path):
    path = Path(path)
    if path.is_symlink():
        raise ValueError("Protected instruction directory must not be a symlink")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)
    if stat.S_IMODE(path.stat().st_mode) != 0o700:
        raise ValueError("Protected instruction directory must be private")
    return path.resolve()


def _deploy(source, destination):
    source, destination = Path(source).resolve(), Path(destination)
    contents = {}
    for name in _FILES:
        path = source / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("First Builder instruction source is incomplete")
        contents[name] = path.read_bytes()
    digest = hashlib.sha256(b"".join(name.encode() + b"\0" + contents[name] for name in _FILES)).hexdigest()
    parent = _safe_directory(destination.parent)
    if destination.exists():
        if destination.is_symlink() or not destination.is_dir():
            raise ValueError("Protected instruction deployment is unsafe")
        for name, body in contents.items():
            path = destination / name
            if path.is_symlink() or not path.is_file() or path.read_bytes() != body or stat.S_IMODE(path.stat().st_mode) != 0o400:
                raise ValueError("Protected First Builder instructions changed")
        return destination.resolve(), digest
    stage = Path(tempfile.mkdtemp(prefix=".first-builder-", dir=parent))
    try:
        stage.chmod(0o700)
        for name, body in contents.items():
            target = stage / name
            target.write_bytes(body)
            target.chmod(0o400)
        os.rename(stage, destination)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return destination.resolve(), digest


def _deploy_runtime(source, destination_root):
    source = Path(source).resolve()
    entries = []
    for package in _RUNTIME_PACKAGES:
        base = source / package
        if not base.is_dir() or base.is_symlink():
            raise ValueError("First Builder runtime source is incomplete")
        entries.extend(path for path in base.rglob("*.py") if "__pycache__" not in path.parts and not path.is_symlink())
    entries.extend(path for path in source.glob("*.py") if path.is_file() and not path.is_symlink())
    digest = hashlib.sha256()
    for path in sorted(entries):
        relative = path.relative_to(source)
        digest.update(str(relative).encode() + b"\0" + path.read_bytes())
    generation = digest.hexdigest()[:16]
    destination_root = _safe_directory(destination_root)
    destination = destination_root / generation
    if destination.exists():
        if destination.is_symlink() or not destination.is_dir():
            raise ValueError("Protected First Builder runtime changed")
        expected = {path.relative_to(source): path.read_bytes() for path in entries}
        actual = {path.relative_to(destination): path for path in destination.rglob("*.py")}
        if set(actual) != set(expected):
            raise ValueError("Protected First Builder runtime changed")
        for relative, body in expected.items():
            path = actual[relative]
            if (path.is_symlink() or not path.is_file() or path.read_bytes() != body
                    or stat.S_IMODE(path.stat().st_mode) != 0o400):
                raise ValueError("Protected First Builder runtime changed")
        return destination.resolve()
    stage = Path(tempfile.mkdtemp(prefix=".runtime-", dir=destination_root))
    try:
        for path in entries:
            target = stage / path.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())
            target.chmod(0o400)
        for directory in sorted((p for p in stage.rglob("*") if p.is_dir()), reverse=True):
            directory.chmod(0o500)
        stage.chmod(0o500)
        os.rename(stage, destination)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return destination.resolve()


def _registration(conn):
    row = conn.execute(
        "SELECT agent_id,repository,protected_instructions,runtime_release,instruction_sha256,launch_state,owner_test_evidence,created_at,updated_at "
        "FROM agent_native_first_builder WHERE id=1"
    ).fetchone()
    if not row:
        return None
    return dict(zip(("agent_id", "repository", "protected_instructions", "runtime_release", "instruction_sha256",
                     "launch_state", "owner_test_evidence", "created_at", "updated_at"), row))


def read(conn, *, actor):
    _require_owner(actor)
    result = _registration(conn)
    if result is None:
        raise KeyError("First Builder is not prepared")
    return result


def prepare(conn, *, actor, home, repository, instruction_source):
    """Atomically register a held Builder; this never starts its queued run."""
    _require_owner(actor)
    repository = Path(repository)
    if repository.is_symlink() or not repository.is_dir():
        raise ValueError("First Builder repository must be an existing directory")
    repository = repository.resolve()
    deployed, digest = _deploy(
        instruction_source,
        Path(home).resolve() / "protected" / "first-builder" / digest_path(instruction_source),
    )
    runtime_release = _deploy_runtime(Path(instruction_source).resolve().parent,
                                      Path(home).resolve() / "protected" / "runtime")
    with write_txn(conn):
        previous = _registration(conn)
        if previous:
            if (previous["repository"], previous["protected_instructions"], previous["runtime_release"], previous["instruction_sha256"]) != (
                    str(repository), str(deployed), str(runtime_release), digest):
                raise ValueError("First Builder is already prepared from different protected inputs")
            return get_root(conn, actor=OWNER, agent_id=previous["agent_id"])
        root = create_root(
            conn, actor=OWNER, request_id="agent-native:first-builder:v1", name="First Builder",
            purpose=PURPOSE, work=WORK_LIMITS,
            model_selection=MODEL, autonomy_level=3, _allow_nested=True,
        )
        now = _now()
        conn.execute(
            "INSERT INTO agent_native_first_builder VALUES(1,?,?,?,?,?,?,?,?,?)",
            (root["id"], str(repository), str(deployed), str(runtime_release), digest,
             "held_for_owner_test", None, now, now),
        )
        conn.execute(
            "UPDATE agent_native_setup SET status='ready',phase='ready',attempted=0,files_ready=1,"
            "plane_origin=?,plane_user_id=?,workspace_slug=?,workspace_id=?,project_id=?,discovery_item_id=?,"
            "message='First Builder protected inputs and existing Plane project are prepared; launch is held for owner test.',updated_at=? "
            "WHERE agent_id=?",
            (PLANE["origin"], "be4115f9-e7c5-47fb-863d-daeae60347cd", PLANE["workspace_slug"], PLANE["workspace_id"], PLANE["project_id"],
             PLANE["item_id"], now, root["id"]),
        )
        return get_root(conn, actor=OWNER, agent_id=root["id"])


def digest_path(source):
    """Stable deployment generation without disclosing source path details."""
    source = Path(source).resolve()
    payload = []
    for name in _FILES:
        payload.append(name.encode() + b"\0" + (source / name).read_bytes())
    return hashlib.sha256(b"".join(payload)).hexdigest()[:16]


def launch_is_held(conn, agent_id):
    row = conn.execute("SELECT launch_state FROM agent_native_first_builder WHERE agent_id=?", (agent_id,)).fetchone()
    return bool(row and row[0] != "active")


def active_repository(conn, agent_id):
    row = conn.execute(
        "SELECT repository FROM agent_native_first_builder WHERE agent_id=? AND launch_state='active'",
        (agent_id,),
    ).fetchone()
    if not row:
        raise PermissionError("First Builder repository tools are not active")
    repository = Path(row[0])
    if repository.is_symlink() or not repository.is_dir() or str(repository.resolve()) != row[0]:
        raise PermissionError("First Builder repository grant changed")
    return repository


def active_runtime(conn, agent_id):
    row = conn.execute(
        "SELECT runtime_release FROM agent_native_first_builder WHERE agent_id=? AND launch_state='active'",
        (agent_id,),
    ).fetchone()
    if not row:
        raise PermissionError("First Builder runtime is not active")
    runtime = Path(row[0])
    if runtime.is_symlink() or not runtime.is_dir() or str(runtime.resolve()) != row[0]:
        raise PermissionError("Protected First Builder runtime changed")
    entries = sorted(path for path in runtime.rglob("*.py") if not path.is_symlink())
    digest = hashlib.sha256()
    for path in entries:
        if not path.is_file() or stat.S_IMODE(path.stat().st_mode) != 0o400:
            raise PermissionError("Protected First Builder runtime changed")
        digest.update(str(path.relative_to(runtime)).encode() + b"\0" + path.read_bytes())
    if not entries or digest.hexdigest()[:16] != runtime.name:
        raise PermissionError("Protected First Builder runtime changed")
    return runtime


def active_instructions(conn, agent_id):
    row = conn.execute(
        "SELECT protected_instructions,instruction_sha256 FROM agent_native_first_builder WHERE agent_id=? AND launch_state='active'",
        (agent_id,),
    ).fetchone()
    if not row:
        raise PermissionError("First Builder protected instructions are not active")
    directory = Path(row[0])
    if directory.is_symlink() or not directory.is_dir() or str(directory.resolve()) != row[0]:
        raise PermissionError("Protected First Builder instructions changed")
    contents = {}
    for name in _FILES:
        path = directory / name
        if path.is_symlink() or not path.is_file() or stat.S_IMODE(path.stat().st_mode) != 0o400:
            raise PermissionError("Protected First Builder instructions changed")
        contents[name] = path.read_bytes()
    digest = hashlib.sha256(b"".join(name.encode() + b"\0" + contents[name] for name in _FILES)).hexdigest()
    if digest != row[1]:
        raise PermissionError("Protected First Builder instructions changed")
    return directory


def confirm_owner_test(conn, *, actor, agent_id, evidence):
    _require_owner(actor)
    if not isinstance(evidence, str) or not evidence.strip() or len(evidence) > 4000:
        raise ValueError("Final test evidence is required")
    with write_txn(conn):
        current = read(conn, actor=OWNER)
        if current["agent_id"] != agent_id:
            raise PermissionError("First Builder identity does not match")
        if current["launch_state"] == "active":
            raise ValueError("First Builder is already active")
        conn.execute(
            "UPDATE agent_native_first_builder SET launch_state='ready_to_launch',owner_test_evidence=?,updated_at=? WHERE id=1",
            (evidence.strip(), _now()),
        )
        return read(conn, actor=OWNER)


def launch(conn, *, actor, agent_id):
    _require_owner(actor)
    with write_txn(conn):
        current = read(conn, actor=OWNER)
        if current["agent_id"] != agent_id:
            raise PermissionError("First Builder identity does not match")
        if current["launch_state"] == "held_for_owner_test":
            raise ValueError("Run and record the final ordinary test agent before launching the First Builder")
        if current["launch_state"] == "ready_to_launch":
            conn.execute("UPDATE agent_native_first_builder SET launch_state='active',updated_at=? WHERE id=1", (_now(),))
        return read(conn, actor=OWNER)
