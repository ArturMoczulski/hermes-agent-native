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
