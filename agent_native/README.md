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

Roots remain `not_started`: a saved startup request is not observed execution.
Creation now atomically records identity, its creation event and exactly one
`agent_native_initial_activations` row bound to the original purpose revision.
Owner reads include `startup` (ID, cause, purpose revision and request time).
Existing inactive records without one return null; reads and retried old creation
requests do not silently activate them. Retrying after a purpose edit retains the
original intent revision. Future admission must verify current purpose, grants,
configured limits/model and fresh planning before acting on any intent.

The owner-authenticated `/agents` UI now opens `/agents/:agentId` after confirmed
creation; roster links and direct/reloaded detail URLs show purpose, startup
request and truthful not-started activity. Pending creation envelopes survive
reload in tab session storage until confirmation, including a lost POST response.
No write is sent if that envelope cannot be retained. The detail page shows
unknown/loading/error states and identifies a superseded request revision.

Private provisioning, restricted tool environments and host Plane grants are
not yet connected to startup. No dispatcher, managed run, chat, cadence, story
artifact or Pause control is enabled by this increment.

Verification:

```sh
scripts/run_tests.sh tests/hermes_cli/test_agent_native_identity.py tests/hermes_cli/test_kanban_db_init.py
```

Tests use real isolated SQLite databases, including concurrent duplicate requests
and failed-event rollback. No model subscription, personal profile or browser is
used by these identity checks. Dashboard browser acceptance uses the real API;
its setup is linked below.

The Agents/detail pages explicitly distinguish recorded startup from work that
has not started. Open them in the existing Hermes dashboard navigation. Browser
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

The restricted Hermes environment below excludes automatic credential/skill/cache
mounts, environment forwarding and container reuse that would widen these grants.
Managed startup integration remains pending. The provisioning module is not exposed
as a worker tool or a dashboard action, and purpose changes still require an
explicit refresh workflow before startup.

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

## Scoped Plane writes

`plane_writes.PlaneWrites` adds a trusted-host dispatcher for ten planning
mutations and read-only source inspection. `tool_schemas(context)` exposes the
fixed schema subset granted to the binding. `execute(context, operation_id,
operation, arguments)` keeps the opaque authority context and operation UUID
outside model arguments; the host supplies the Plane credential and service-user
identity. This is not yet a registered managed-agent tool or a dashboard route.

`plane_write_access` layers explicit operation grants over the existing project
read binding. Existing resource edits also need owner-selected fields. Confirmed
item/cycle creation records the created resource's fixed field rights without
expanding the operation grant. Current scope, purpose and field rights are checked
around execution. Direct control-database access remains privileged host access,
not something a worker receives.

The operations cover project descriptions, work-item creation/updates, appended
comments, undated cycles and memberships, dependencies, and unverified artifact
references. Plain text is escaped; artifact references are not fetched or converted
into native crawler-triggering links. This surface rejects terminal Plane states;
it cannot replace framework result acceptance or cancellation controls. Source
fingerprints detect observed changes but do not provide atomic remote writes.

`plane_write_journal` durably records a one-shot operation intent before sending,
then its confirmed/rejected/unknown outcome. Stored receipts contain hashes and
identifiers, not work text or credentials. Reusing an operation UUID is denied;
using a new UUID does not deduplicate an earlier semantic request. Missing final
receipts remain pending, including after journal-write failure. Pending or unknown
effects require reconciliation, not automatic replay.

`PlaneWrites.recover` now investigates the original operation using protected
prepared arguments and scoped reads. A durable attempt marker survives crashes;
a local operation lock prevents overlapping delivery and recovery. Matching
results preserve their observation provenance, and recovered creates acquire no
editable-field grants. Ambiguous evidence remains unresolved without resending.
The separate preparation table contains planning text and must remain protected
with the control database; public receipts/events still contain only hashes and
identifiers. See [recovery semantics and evidence](../implementation/plane-write-recovery.md).
AN-23 source reconciliation and managed-run integration remain separate.

Read the [operation boundary and evidence](../implementation/plane-scoped-writes.md)
for the supported surface, focused checks and remaining runtime integration.
Neither these contexts nor the journal authenticate an admitted run. Existing
sandbox restrictions remain in force; no managed Builder or cadence is activated.

## Hermes Plane tool boundary (AN-24, first increment)

`plane_tools.bind_plane_tools(actor=OWNER, open_service=...)` connects
`plane_resource_inspect` to the real Hermes `model_tools.handle_function_call`
and `ToolRegistry.dispatch` paths. Every `plane_` name is reserved: missing,
expired or forged authority cannot fall through to a native/plugin handler.
The early model dispatch branch precedes argument coercion, tool-search bridges
and native middleware; skip flags and caller task/session IDs cannot select
scope. Existing ordinary native tools retain their behavior.

The trusted host supplies a context-manager factory yielding a fresh
`(PlaneWrites, opaque_context)` pair. That factory creates and closes its private
control connection on one host-owned thread. Calls from other Hermes threads,
including `execute_code` socket RPC with `CellAuthority`, are serialized onto
that thread; SQLite thread checks remain enabled. The issued context selects
the project and agent. Model arguments only select the supported resource and
cannot supply actors, bindings, credentials or alternative projects.

The existing adapter rechecks current grants and soul revision before and after
HTTP. Binding lifetime joins those checks: ending a binding revokes copied and
queued contexts before waiting for in-flight I/O cleanup. A late response is
discarded, and item inspection cannot start subsequent membership/dependency
reads. Ending a binding does not revoke the durable grant or implement agent
retirement. The host keeps its factory, services, credentials and capabilities
out of generated code; these Python objects are not a worker transport.

Only resource inspection is connected in this increment. The other reserved
Plane tools return an unavailable-operation error here. Existing trusted-host
writes remain available through `PlaneWrites`; exposing them to models needs
host-owned durable operation correlation. The schema/context assembly, managed
run admission, native/auxiliary tool gates and real Builder launch remain open.
No tool is added to the ordinary core model catalog, and no dashboard workflow
or background agent is activated by this connection.

The same increment closes a concrete write race: current resource-field rights
are now checked inside the transaction that records a delivery attempt. A field
revoked before that transaction commits produces no HTTP mutation and a rejected
receipt. Revocation after admission cannot retract an already in-flight remote
request; unknown-outcome reconciliation and no-resend rules still apply.

Focused real HTTP/SQLite and socket-RPC checks:

```sh
scripts/run_tests.sh tests/tools/test_agent_native_dispatch.py tests/hermes_cli/test_agent_native_plane_tools.py tests/hermes_cli/test_agent_native_plane_tool_lifetime.py tests/hermes_cli/test_agent_native_plane_attempt_authority.py
```

These use isolated fixture services, not live Plane accounts or model calls.
The [Builder state](../first-builder/STATE.md) records red/green and regression
evidence. AN-24's broad remainder is now in backlog; its writer-specific integration
is part of AN-72. The accepted increment is not full managed-operation acceptance.
