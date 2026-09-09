"""Additive tables installed through the existing Kanban schema initializer."""
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS agent_native_agents (
    id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    initial_purpose TEXT NOT NULL,
    purpose TEXT NOT NULL,
    soul_revision INTEGER NOT NULL CHECK(soul_revision > 0),
    execution TEXT NOT NULL CHECK(execution = 'not_started'),
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS agent_native_agent_parents (
    agent_id TEXT PRIMARY KEY REFERENCES agent_native_agents(id),
    parent_id TEXT NOT NULL REFERENCES agent_native_agents(id),
    created_at TEXT NOT NULL,
    CHECK(agent_id <> parent_id)
);
CREATE INDEX IF NOT EXISTS agent_native_agent_parent_children
    ON agent_native_agent_parents(parent_id, agent_id);
CREATE TABLE IF NOT EXISTS agent_native_creation_work (
    agent_id TEXT PRIMARY KEY REFERENCES agent_native_agents(id),
    work_limits TEXT
);
CREATE TABLE IF NOT EXISTS agent_native_chat_sessions (
    agent_id TEXT NOT NULL REFERENCES agent_native_agents(id),
    soul_revision INTEGER NOT NULL CHECK(soul_revision > 0),
    session_id TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    PRIMARY KEY(agent_id, soul_revision)
);
CREATE TABLE IF NOT EXISTS agent_native_initial_activations (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL UNIQUE REFERENCES agent_native_agents(id),
    cause TEXT NOT NULL CHECK(cause = 'creation'),
    soul_revision INTEGER NOT NULL CHECK(soul_revision > 0),
    requested_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS agent_native_setup (
    activation_id TEXT PRIMARY KEY REFERENCES agent_native_initial_activations(id),
    agent_id TEXT NOT NULL UNIQUE REFERENCES agent_native_agents(id),
    status TEXT NOT NULL CHECK(status IN ('queued', 'preparing', 'blocked', 'failed', 'unresolved', 'ready', 'superseded')),
    phase TEXT NOT NULL CHECK(phase IN ('files', 'workspace', 'project', 'discovery', 'ready')),
    attempted INTEGER NOT NULL DEFAULT 0 CHECK(attempted IN (0, 1)),
    files_ready INTEGER NOT NULL DEFAULT 0 CHECK(files_ready IN (0, 1)),
    plane_origin TEXT,
    plane_user_id TEXT,
    workspace_slug TEXT,
    workspace_id TEXT,
    project_id TEXT,
    discovery_item_id TEXT,
    message TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS agent_native_setup_events (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    activation_id TEXT NOT NULL REFERENCES agent_native_setup(activation_id),
    status TEXT NOT NULL,
    phase TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS agent_native_setup_revisions (
    agent_id TEXT PRIMARY KEY REFERENCES agent_native_agents(id),
    soul_revision INTEGER NOT NULL CHECK(soul_revision > 0)
);
CREATE TABLE IF NOT EXISTS agent_native_plane_access (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL REFERENCES agent_native_agents(id),
    workspace_slug TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK(revision > 0),
    active INTEGER NOT NULL CHECK(active IN (0, 1)),
    UNIQUE(agent_id, workspace_slug, project_id)
);
CREATE TABLE IF NOT EXISTS agent_native_plane_write_access (
    binding_id TEXT PRIMARY KEY REFERENCES agent_native_plane_access(id),
    operations TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK(revision > 0),
    active INTEGER NOT NULL CHECK(active IN (0, 1))
);
CREATE TABLE IF NOT EXISTS agent_native_plane_resource_access (
    binding_id TEXT NOT NULL REFERENCES agent_native_plane_access(id),
    kind TEXT NOT NULL CHECK(kind IN ('project', 'item', 'cycle')),
    resource_id TEXT NOT NULL,
    fields TEXT NOT NULL,
    PRIMARY KEY(binding_id, kind, resource_id)
);
CREATE TABLE IF NOT EXISTS agent_native_plane_mutations (
    operation_id TEXT PRIMARY KEY,
    operation TEXT NOT NULL,
    binding_id TEXT NOT NULL REFERENCES agent_native_plane_access(id),
    agent_id TEXT NOT NULL REFERENCES agent_native_agents(id),
    workspace_slug TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    write_revision INTEGER NOT NULL,
    soul_revision INTEGER NOT NULL,
    arguments_sha256 TEXT NOT NULL,
    resource_ids TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending', 'confirmed', 'rejected', 'unknown')),
    resource_id TEXT,
    created_at TEXT NOT NULL,
    finished_at TEXT
);
CREATE TABLE IF NOT EXISTS agent_native_plane_preparations (
    operation_id TEXT PRIMARY KEY REFERENCES agent_native_plane_mutations(operation_id),
    arguments_json TEXT NOT NULL,
    prepared_json TEXT NOT NULL,
    prepared_sha256 TEXT NOT NULL,
    attempted INTEGER NOT NULL DEFAULT 0 CHECK(attempted IN (0, 1)),
    prepared_at TEXT NOT NULL,
    attempted_at TEXT
);
CREATE TABLE IF NOT EXISTS agent_native_plane_mutation_events (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_id TEXT NOT NULL,
    operation TEXT NOT NULL,
    binding_id TEXT,
    agent_id TEXT,
    workspace_slug TEXT,
    workspace_id TEXT,
    project_id TEXT,
    revision INTEGER,
    write_revision INTEGER,
    soul_revision INTEGER,
    status TEXT NOT NULL CHECK(status IN ('pending', 'confirmed', 'rejected', 'unknown', 'denied')),
    reason TEXT,
    resource_id TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS agent_native_plane_mutation_event_operation
    ON agent_native_plane_mutation_events(operation_id, sequence);
CREATE TABLE IF NOT EXISTS agent_native_events (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL REFERENCES agent_native_agents(id),
    kind TEXT NOT NULL,
    soul_revision INTEGER NOT NULL,
    purpose TEXT NOT NULL,
    actor TEXT NOT NULL CHECK(actor = 'owner'),
    created_at TEXT NOT NULL,
    UNIQUE(agent_id, soul_revision)
);
"""

from agent_native.work_state import WORK_SCHEMA
from agent_native.story_store import STORY_SCHEMA
from agent_native.output_store import OUTPUT_SCHEMA
SCHEMA_SQL += WORK_SCHEMA + STORY_SCHEMA + OUTPUT_SCHEMA

from agent_native.model_settings import MODEL_SCHEMA
SCHEMA_SQL += MODEL_SCHEMA

from agent_native.autonomy import AUTONOMY_SCHEMA
SCHEMA_SQL += AUTONOMY_SCHEMA

from agent_native.acceptance import ACCEPTANCE_SCHEMA
SCHEMA_SQL += ACCEPTANCE_SCHEMA

from agent_native.first_builder import SCHEMA as FIRST_BUILDER_SCHEMA
SCHEMA_SQL += FIRST_BUILDER_SCHEMA

SCHEMA_SQL += """
CREATE TABLE IF NOT EXISTS agent_native_removals (
 agent_id TEXT PRIMARY KEY REFERENCES agent_native_agents(id),
 removed_at TEXT NOT NULL
);
"""
