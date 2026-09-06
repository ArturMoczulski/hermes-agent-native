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

## Restricted Hermes execution environment

`environment.open_environment` now constructs a restricted subclass of Hermes'
Docker environment from the validated mount plan. It reuses Hermes' Bash session
and command execution, but does not accept caller-selected Docker flags, mounts,
environment forwarding or container reuse. Inherited credential/skills/cache and
egress proxy hooks are excluded. Upstream behavior is unchanged for ordinary
Hermes environments.

The owner-selected image must already exist locally, is resolved to its immutable
image ID, and must not declare extra volumes. The container uses no network, a
read-only root, no Linux capabilities, no-new-privileges, host UID/GID, bounded
resources and a private temporary directory. Its image remains trusted software;
the host engine and database must stay outside generated-code access.

Every instance gets a fresh container. A missing container fails instead of being
silently recreated. Cleanup checks removal synchronously; failure retains the
container ID on the environment and raised exception for host reconciliation.

```sh
HERMES_TEST_IMAGE=agent-native/dev:latest scripts/run_tests.sh tests/hermes_cli/test_agent_native_environment.py tests/tools/test_docker_environment.py
```

On the development machine, 69 checks passed, including real execution, exact
mount inspection, blocked soul writes/chmod, absent host credentials, distinct
containers, failure after removal, and confirmed cleanup. No image was downloaded.
The real-container case is opt-in; the fixture image must contain Bash.

This is the tool environment only. Managed run admission, cancellation records,
purpose-revision revalidation at launch, model-loop integration and scheduling are
still pending. Creating an agent in the dashboard does not start this environment.

## Scoped Plane reads

`plane_access` stores owner-managed project read bindings in the existing control
schema. A trusted host issues an opaque context for one agent and project;
`plane_reads.PlaneReads` derives the workspace/project from that context. Caller
text cannot select an actor, substitute a context, or expand the project scope.
Each use rechecks the current grant and purpose revision, including while reading
multiple pages. Revocation survives restart, and regranting does not revive old
contexts. Identical repeated grants preserve a valid context.

The host supplies the Plane service credential directly. It is not stored in the
control binding, agent workspace, returned records or context. The existing
restricted Docker environment retains its no-network and explicit-mount boundary.
The read service must never be handed to generated code as a Python object.

The read surface covers bound project details, work items, comments, attachment
metadata, cycles and states. Attachment downloads and signed storage URLs are not
part of this increment. Reads use fixed resource paths and validate returned
workspace/project/item identities. HTTP errors, pagination and external responses
must remain distinct from accepted work or valid owner direction.

These are trusted-host operations, like the initial identity operations. A context
is not a serialized agent token or proof of an admitted run. The future managed
launch/transport boundary must associate it with the authenticated invoking run,
keep it private, and enforce run lifecycle. No new dashboard endpoint, worker tool,
model loop, managed launch or planning write is introduced by this slice. General
parent-grant policy and unified authorization events remain separate work.

Focused internal checks:

```sh
scripts/run_tests.sh tests/hermes_cli/test_agent_native_plane_access.py tests/hermes_cli/test_agent_native_plane_reads.py
```

The tests use isolated SQLite and a real loopback HTTP server. They require no
browser, model credential or existing Plane account. The separate live Plane
probe uses its own disposable accounts and workspace; see the scoped-read
[validation report](../implementation/plane-scoped-reads.md) for observed results.
