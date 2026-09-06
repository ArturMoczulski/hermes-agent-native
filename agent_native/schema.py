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
