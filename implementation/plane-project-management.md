# Plane integration and delivery plan

Status: selected planning direction by the owner, 2026-09-06. Plane replaces the
earlier Hermes-only task-board recommendation. The [product contract](../design/13-project-management.md)
is authoritative. The owner subsequently authorized local setup: Plane Community v1.4.2 is now
running in Docker, with a [live Builder workspace](../first-builder/PLANE.md).
The managed-agent adapter remains unimplemented. Existing identity and sandbox
increments remain useful.

## Reuse and boundary

Use self-hosted Plane Community Edition for project/backlog/cycle management and
its planning UI. Keep Hermes as the model/tool engine and the framework as the
owner of agent identity, permissions, run admission, cancellation and evaluation.
Do not maintain an independently editable Hermes Kanban copy of Plane work items
or allow its native dispatcher to start a second run for them.

| Record | Authority | Framework integration |
| --- | --- | --- |
| Project brief, backlog, priority, cycle, item description and planning state | Plane | Scoped reads/writes; stable external IDs and version/fingerprint observations. |
| Agent tree, soul, grants and lifecycle | Framework control database | Plane membership is never a substitute for these checks. |
| Assignment binding, execution claim, attempt and stop state | Framework | Bind to Plane item ID and admitted brief/dependency revision. |
| Criteria and result evaluation | Plane brief is the planning source; framework preserves the evaluated revision and judgment | Changes invalidate applicability of stale acceptance; no silent criteria replacement. |
| Human decisions and agent communications | Framework decision/message/event records | Link comments to durable records and retain verified sender provenance. |
| Artifacts | Approved artifact storage | Stable versioned references from both systems; Plane attachments may supplement these. |

Keep the namespaced control tables already added through Hermes's SQLite schema
initializer. Database location does not make inherited Hermes tasks authoritative
for managed projects. The records listed in architecture.md must follow the field
ownership above rather than create competing writable project/assignment copies.

## Smallest useful integration

One operator-managed Compose deployment, one workspace per root portfolio, shared
scoped projects for its descendants. Reuse native Plane work items, cycles, states
and project UI. Use links and framework metadata for deeper logical relationships;
do not depend on paid epics, approval workflows or custom properties.

Implement one narrow Plane adapter behind framework work operations. Agents receive
only scoped operations; installation credentials stay in the trusted service.
Derive agent identity from the run, never from caller-supplied owner/agent labels.
Do not grant workers broad Plane tokens, native bypass tools or network access
that bypasses this adapter. Read filtering must be enforced as well as writes.
Whether dedicated Plane identities are useful is an adapter choice to validate;
one service credential does not justify exposing its full access to an agent.

Expose actual available operations and resource IDs in the managed agent context.
The bundled skill describes the workflow without inventing tool names. Root creation
must publish planning-setup state and initiate discovery once ready. Provision
projects only when useful; setup retries recover prior IDs rather than duplicating.

## Reliable updates and owner edits

Persist external mutation intent and correlation before delivery. After timeouts,
reconcile before retrying creation. Use supported API capabilities for deduplication
where verified; do not assume Plane provides universal idempotency or atomic CAS.
Validate webhook origin, deduplicate delivery, and re-fetch current source records;
reconcile periodically to cover missing notifications. Serialize local mutations
and detect changes using available revisions/fingerprints. Prove race behavior in
the pinned release before claiming an admission guarantee for direct Plane edits.

Only framework operations authorize execution or satisfy dependencies. Preserve
the admitted brief, revalidate fresh planning state before new work, and stop or
replan obsolete active assignments when a material change is observed. Immediate
owner stops and purpose changes use the framework, not eventual webhook delivery.
A native Plane edit may be visible before reconciliation; show that freshness gap.

Human project edits require a verified Plane-user-to-owner mapping. Imported text
and service-account comments remain data, not authority. Pending questions and
binding approvals belong to the existing framework inbox. Project comment messages
must be captured with source identity, correlation, delivery and event history.
Do not mistake Plane's own activity feed for the complete framework event ledger.

## Service operations

Pin and record a tested Community release and deployment configuration. Verify its
actual dependencies and provision persistent storage, health checks, owner access,
secrets, backups and a tested restore path. Plane's required services are distinct
from the deliberately small framework control process; the previous blanket
exclusion of additional databases/queues does not apply to Plane's own stack.
Do not put service credentials in agent workspaces, repository files or snapshots.

Back up Plane data/attachments and framework mappings/events consistently enough
to reconcile them. A restore must suspend admission until references, pending
operations and active attempts have been reconciled. Report provisioning and
connection failures in the control center. No automatic destructive recreation
of a workspace whose identity cannot be resolved.

## Delivery sequence and evidence

1. **Capability check against a pinned Community release.** Verify workspace/project
   provisioning, credentials and scoped reads/writes, states, dependencies, cycles,
   comments, pagination, rate limits, deletion, webhook verification and conflict
   behavior. Record supported operations and gaps from actual API/source evidence.
   Confirm that no required feature silently needs Commercial Edition. Resolve a
   material gap before expanding custom work or changing the selected product.
2. **Provision and reconnect.** In isolated service data, establish one root workspace
   and project, restart, and retry setup without duplicates. Demonstrate failure and
   recovery plus backups/restore. No live owner workspace used as a test fixture.
3. **One vertical planning slice.** Through scoped work operations and the skill,
   create a brief, item and cycle; show links and freshness in Work. Start with a
   failing Playwright flow against the real adapter/service and focused unit checks.
4. **Execution and evaluation.** Bind one item to durable run admission; deliver,
   review and accept evidence, then choose the next item. Test duplicate triggers,
   stale criteria, unauthorized reads/writes and premature completed-state edits.
5. **Children and continuous planning.** Delegate scoped work, escalate a blocker,
   close/replan a cycle and resume after restart. Verify subtree stopping even with
   Plane unavailable. Exercise the skill's planning judgment separately from scripted
   model fixtures, which only prove integration.

Each step uses small test-first increments, not a large implementation followed by
tests. Use the existing cached Playwright Chromium; no browser download is required.
The external First Builder now uses this skill and its live Plane project through
a separate local API account. The one-time repository backlog import is complete;
repository files retain evidence and connection pointers. Managed agents still
require the scoped integration, and this local API account must not be copied
into their workers.

## Official evidence reviewed 2026-09-06

- [Plane Community overview](https://plane.so/open-source): projects, work items,
  cycles, modules, pages, views, REST API and webhooks. It separates commercial
  governance/approval features from the open-source offering. This supports reuse
  for planning, not a claim that Plane enforces our agent hierarchy.
- [Edition documentation](https://developers.plane.so/self-hosting/editions-and-versions):
  Community is AGPLv3 and editions have separate release/feature boundaries.
  Validate the selected release and distribution requirements before packaging it.
- [API introduction](https://developers.plane.so/api-reference/introduction):
  JSON REST API and API-key authentication with a self-hosted base URL. Use current
  work-item endpoints, not the deprecated issues API.

These references establish feasibility; the pinned-release checks above remain
unperformed. No arbitrary-depth project tree, per-agent authorization scheme,
transactional integration or automatic approvals are assumed from marketing pages.
