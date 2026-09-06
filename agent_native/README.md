# Agent-native control domain

First increment: inactive root identity in the existing Hermes Kanban database.
`identity.py` supplies owner-only creation, reads, purpose revisions and event
history. Every creation and revision commits with its event in one transaction.
Request IDs deduplicate creation; expected revisions protect against stale edits.
Names are display labels, not identifiers. Schema initialization runs through
Hermes' existing connection/migration path. No new task store or agent loop exists.

This is an internal host interface, not an authentication mechanism. `OWNER` is
an in-process capability for trusted host code; it must never be selected from
request content or exposed in an agent tool. Any process with database write
access can bypass these operations. Managed workers are not launched yet.

Roots deliberately remain `not_started`. The existing dashboard now exposes creation and listing at `/agents`, through
owner-session authenticated `/api/agent-native/agents` endpoints. Request data
cannot choose the actor. Parent/grant rules, protected soul projections, workspace
isolation, activation intents and cadence remain to be implemented.
At that point creation must record an immediate activation atomically, as required
by the product specification. Do not present this interim record as a working agent.

Verification:

```sh
scripts/run_tests.sh tests/hermes_cli/test_agent_native_identity.py tests/hermes_cli/test_kanban_db_init.py
```

Tests use real isolated SQLite databases, including concurrent duplicate requests
and failed-event rollback. No model subscription, personal profile or browser is
used. The first dashboard flow must add Playwright coverage against the real API.

The Agents page is an interim inactive-record workflow and explicitly says work
has not started. Open it in the existing Hermes dashboard navigation. Browser
acceptance setup: [web/e2e/README.md](../web/e2e/README.md).

## Private profile provisioning

`provisioning.provision_root` publishes a complete host-owned directory for an
inactive root, keyed by its stable ID. It projects the database purpose and
revision into `profile/SOUL.md` and `profile/identity.json`, seeds an empty `.env`,
and creates separate workspace/practices, memories and skills directories.
Retries preserve mutable files and reject stale/tampered projections, symlinked
layout paths, and weakened protected permissions. No existing owner profile or
credential is copied. This currently uses POSIX filesystem permissions.

`sandbox_mounts` describes exactly four binds: read-only soul/identity files,
writable workspace, and writable memory. The profile root, `.env`, control
database and sibling directories are not included. This mount description is not
a worker launcher, and chmod alone does not isolate generated code from the host.

Real-container verification (local Alpine required; never pulls an image):

```sh
HERMES_TEST_IMAGE=alpine:latest scripts/run_tests.sh tests/hermes_cli/test_agent_native_provisioning.py
```

Without that explicit image setting, the Docker case skips and local filesystem
checks still run. The container test applies the emitted binds with no network,
read-only root filesystem, dropped capabilities and no-new-privileges. It verifies
failed soul writes/chmod, absent neighbor/control paths and persisted mutable work.

Before startup integration, Hermes' Docker backend must stop inheriting automatic
credential/skill/cache mounts, environment forwarding, container reuse and any
other options that widen these grants. That integration is still pending. The
current provisioning module is not exposed as a worker tool or a dashboard action,
and purpose changes require an explicit refresh workflow before startup.
