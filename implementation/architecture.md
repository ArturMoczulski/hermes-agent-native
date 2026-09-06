# Proposed architecture

The owner selected a Hermes fork as the implementation foundation. Detailed
choices below remain the engineering plan to validate. Product behavior comes
from [design/](../design/README.md); unsettled defaults are identified in
[Decisions and evidence](decisions-and-evidence.md#proposed-product-defaults).

## 1. A control module within a Hermes fork

Put the new domain code in a distinct package, provisionally `agent_native/`,
inside the fork. Reuse Hermes's existing server, engine, and frontend. Use Plane
for planning under [the integration plan](plane-project-management.md).
Avoid replacing upstream modules wholesale or creating a second application
which mirrors the same task state.

The package should have a few clear responsibilities:

| Module | Responsibility |
| --- | --- |
| Identity and authority | Stable agent IDs, parentage, souls, grants, lifecycle rules. |
| Work | Projects, assignment ownership, dependencies, progress, review and acceptance. |
| Coordination | Cadence, pending activations, admission, scheduling, stop and recovery. |
| Communication | Authenticated origin, message delivery, escalation and decisions. |
| Activity | Durable events, projections, evaluations and progress concerns. |

These are modules in one product, not separate microservices. Introduce interfaces
at the existing Hermes entry points, and keep the actual rules in this package.

### One operation boundary

Every relevant read or mutation must carry a trusted actor: human owner, a
particular agent/run, or a scoped system operation. Derive that identity from an
authenticated session or the trusted worker launch context. Never accept a tool
argument such as `actor="human"` as proof of authority.

Route agent tools, dashboard/API requests, chat commands, operator CLI commands,
cron callbacks, Kanban dispatch, and recovery through the same domain operations.
Missing actor context denies an operation; it must not silently mean owner.
Cover reads as well as writes, including artifacts, memory, and event views.

Existing bypass paths must either use this boundary or be disabled in the
managed product mode. This includes profile deletion, direct board mutation,
native agent messaging, arbitrary background activation, and framework updates.
Environment variables describing a worker are metadata; the trusted launcher
binds them to the actual run and protects them from generated code.

Native delegation must create a recorded child/assignment through this boundary,
or be disabled for managed agents. An untracked native subagent would otherwise
bypass the parent tree, resource grants, message history and subtree stopping.

The basic mutation transaction is:

1. Authenticate actor and verify current authority and relevant revisions.
2. Check the work/lifecycle transition and update authoritative records.
3. Append the corresponding event and any pending delivery/dispatch intent.
4. Commit, then perform external delivery or launch work.

External calls cannot participate in a SQLite transaction. A durable pending
operation and reconciliation connect the database decision to its actual effect.

## 2. State and identity

Use the existing Hermes Kanban database as the basis of the authoritative control
database, retaining the namespaced identity/control tables already implemented.
Plane owns project planning and work items; it is not a second editable copy of
Hermes tasks. Follow the field ownership and linked IDs in the
[Plane integration plan](plane-project-management.md). Enforce access per operation;
a board filter is not a permission boundary.
Hermes's per-profile session databases remain transcript storage, not competing
sources of task ownership or completion.

Extend the existing schema/migration mechanism rather than adding another ORM or
database server solely for the new module. Keep new tables clearly namespaced.

| Record | Required information |
| --- | --- |
| Agent | Immutable ID, display name, parent ID, ongoing/bounded role, lifecycle, profile mapping, model configuration, cadence and last activity. |
| Soul revision | Purpose, fundamental rules, authorizing actor, revision and effective time. |
| Grant | Who can perform/delegate which operation on which resource, with conditions. |
| Project binding | Plane project ID, coordinator/responsibility boundary and observed planning revision; planning content stays in Plane. |
| Assignment binding | Plane item ID, responsible/performing agent, admitted brief and criteria revision, dependency observations and current attempt. |
| Run and external job | Managed run plus agent, purpose/assignment revision, engine session, worker/sandbox identity, observations and outcome. |
| Message and delivery | Sender, recipient, content/reference, request/work correlation and distinct delivery/handling observations. |
| Decision and escalation hop | Origin, current responder, affected work, request type, scope, response provenance and applicability. |
| Evaluation and progress concern | Criteria, evidence, judgment, uncertainty, response and related attempts. |
| Activation and event | Cause, deduplication key, scheduling/processing state, monotonic event sequence and correlation IDs. |

Human-readable names may repeat. Use a generated stable profile identifier for
Hermes; do not use a display name as an access-control key. Store agent parentage
separately from task dependencies. Validate cycles and walk descendants iteratively
without a fixed product depth limit.

Agent state must not be one overloaded status field. An agent can be enabled,
have one task waiting for an answer, another child working, and no active model
turn. Show lifecycle, execution, work dependencies and observation freshness
separately. Record last check-in, last work activity and last completed work as
distinct facts.

### Files and the four layers

- **Soul:** the control database owns the current revision; the trusted service
  generates a protected `SOUL.md` projection for Hermes to read.
- **Practices:** agent-writable Markdown and approved skills describe methods.
- **Memory:** reuse the profile's memory and transcript-search facilities within
  its access scope.
- **Runtime state:** task/decision/run records are authoritative. Generate
  readable Markdown/JSON snapshots and event exports for agents and humans.

Generated snapshots identify their source and revision. Agents update structured
state through tools, not by editing exported snapshots. Refresh a snapshot before
its use, or mark it stale and supply the authoritative tool view. File exports do
not create a second writable task store.

The human changes any soul. A parent can change its direct child's soul only
within its grant; a grandparent's supervisory responsibility is not direct soul
ownership. An agent never changes its own soul. A revision invalidates old work
authority and starts a fresh engine session after interruption is reconciled.
Memory and relevant context may be carried forward explicitly; an old cached
prompt must not become the new authority.

Keep the creation experience simple: installation setup establishes an
owner-approved default capability template, so creating a root can begin with
its purpose. Apply the owner-approved
[default capabilities](../design/04-workspaces-and-skills.md#default-capabilities)
and [permission policy](../design/05-human-interaction.md#questions-proposals-and-permission).
Standing scoped permissions allow recurring actions within their limits; otherwise
required approval is explicit. Personal-resource access remains separately granted. Show the inherited capabilities to the owner; do not ask the
model to invent its own permissions from the purpose text.

## 3. Execution and environments

Use Hermes's own model/tool loop. Start a dedicated engine process for each active
agent profile rather than repeatedly switching process-global profile state.
Persist the profile independently of process lifetime. Reuse the engine's session
history; persist our mapping from framework agent/activation to engine session/run.

Within the fork, reuse the existing managed worker launch and session machinery,
with a shared admission check in front of every launch path. Do not nest an
OpenCode loop inside each agent or make internal task dispatch unnecessarily
round-trip through a second HTTP server. Existing public Hermes APIs can remain
for integrations after their operations obey the same authority rules.

### Separate the engine from generated code

Use Hermes's Docker tool backend for terminal, file and code execution. The Hermes
engine reads protected prompt/configuration and runs its trusted tools outside
the generated-code sandbox. Give each agent an explicitly assigned private
workspace and sandbox identity. Reuse persistent workspace storage; an agent's
existence does not depend on a container staying up.

The workspace container receives no control database, host home directory,
owner credentials, engine-management credentials, deployment configuration or
Docker socket. Protect the engine installation, managed settings and enabled
plugin code from agent edits. Maintain an immutable deny list for forwarding
operator secrets, including through skills, environment declarations or credential
files. Only deliberately granted task credentials may cross this boundary.

Use default-denied resource access. Restrict container egress and tool/MCP
capabilities to granted resources; a shell with unrestricted network and publishing
credentials would bypass a publishing approval tool. Prefer existing network
controls and authenticated service adapters. Grant read access separately from
write, publish, spend, or deployment capabilities.

Encode mechanically enforceable fundamental rules as structured action policy.
Natural-language purpose and taste guide the model; no design should claim that
filesystem protection can prove compliance with every sentence of a soul.
Draft policy interpretation visibly at creation; ambiguity must not create a
new grant. Apply policy at the operation that causes the effect, not only in an
agent's prompt or a confirmation dialog.

For approved external actions, persist a scoped action intent and bind permission
to that intent, relevant revisions, resource, and parameters. A capability adapter
executes it with credentials kept outside the sandbox, rechecks authorization at
execution time, and records the result. Reuse established SDKs/MCP integrations
inside that boundary. Provider support itself stays in Hermes.

### Capacity and simultaneous work

Allow one active model turn that mutates a given persistent profile at a time in
the first release. This prevents competing memory/session writers. It does not
mean one unfinished assignment per agent.

Different agents run concurrently. Long external operations return tracked job
handles, and delegated work belongs to separately managed child agents. These
operations can remain active while the coordinator performs a new check-in.
A tool that requires a long synchronous wait should become a tracked background
job or delegated assignment so it does not indefinitely monopolize coordination.

During a bounded active turn, redundant cadence ticks coalesce into a pending
review. Messages and results remain individually retained. Deliver human steering
at the engine's supported boundary, with queued versus consumed state visible;
explicit interruption goes directly to control and does not wait for a model turn.
After the current turn yields, consider independent branches before continuing a
long assignment. Never solve contention by dropping a message or starting duplicate
work in a second writer for the same profile.

Use configurable global worker slots and fair queuing across roots. Idle profiles
need not keep a model request or a warm process. Record resource waiting separately
from waiting for a human. More physical worker hosts and shared distributed storage
are later deployment extensions, not prerequisites for separate agent environments.

## 4. Autonomous work and one dispatcher

Extend the existing gateway/dispatcher to handle two kinds of work: coordination
activations and assignment execution. Reuse its task claim/run tracking primitives;
add current agent lifecycle, grant, revision and capacity checks to eligibility.

Cadence, new owner input, child results and answered dependencies all create
durable activation intents. A timer determines when a review is due; it does not
directly start an unrestricted agent process. There is one dispatch owner. Native
cron, heartbeat, goal continuation, review automation and manual chat execution
must use the same admission mechanism or remain disabled for managed agents.

Initially support interval cadences such as every minute or every 24 hours.
Creation schedules an immediate activation regardless of interval. Calendar/DST
schedules can reuse Hermes's scheduler later; they are not needed for the first
purpose-cadence demonstration. Display actual next eligible review, including
capacity delays, rather than promise a model always begins at an exact instant.

At each activation, assemble current soul, practices, relevant memory, grants,
work snapshot, unanswered requests and newly delivered messages. Supply a bundled
[Plane project-management skill](../skills/productivity/plane-project-management/SKILL.md)
which directs the agent to:

1. Assess purpose and uncertainty; create or revise a plan with useful outcomes.
2. Inspect existing assignments and evidence before creating more work.
3. Start authorized independent work or delegate when useful.
4. Ask a focused question about a blocked branch; keep other branches eligible.
5. Submit results with evidence, evaluate them, and choose the next useful step.
6. Record a wait reason when there is no useful action.

The skill teaches judgment; the control module enforces mutations. A cadence
review is not a completed project task. An enduring purpose stays open across
milestones. A bounded child does not invent unrelated work when its assignment ends.

## 5. Tasks, evaluation and progress

Use Plane work items, dependencies and cycles through scoped operations. Keep
claims, attempts and evaluations in the framework, reusing suitable Hermes
primitives without a competing native board/dispatcher. A worker submits a result; the
responsible agent accepts it against the recorded criteria. An authorized human
can make that decision directly. Self-performed work still requires a recorded
evaluation, without forcing an extra reviewer agent for every small task.

Store implementer, accountable parent, reviewer and evaluation independently;
upstream review reassignment must not erase who performed or owns the assignment.
Do not automatically use a coding-review skill for music or business work. Keep
criteria and their revisions in the brief, including subjective criteria and
uncertainty. A successful process exit is an execution observation, not acceptance.

Reuse existing repeated-failure and blocked-loop signals as evidence. Add linked
concerns for repeated attempts, plan changes and delegation without new outcomes
or learning. Start with configurable heuristics and explicit agent review; avoid
a separate always-running evaluation model. Create one concern per recurring
pattern, then update it with evidence and the responsible agent's response.

Do not automatically retire an agent or change its soul because a heuristic fires.
Known external waiting and useful investigation are not failures. Upstream
automatic routing to human triage must follow our escalation rules instead.

## 6. Messages, decisions and owner control

Use one designated web owner channel initially. Reuse Hermes's authentication
and chat UI, with an explicit trusted-owner actor at the server. Keep ordinary
worker credentials distinct and incapable of invoking owner operations. Secure
all alternate API/CLI/PTY entry paths; origin labels must survive quoting and
forwarding. No owner password or management token belongs in a public frontend
environment variable or worker sandbox.

The checked-out dashboard has reconnectable TUI/PTY sessions with retention,
alongside a legacy disconnect-and-kill path. That is not the required framework
lifecycle: managed-agent conversation connects to service-owned runs and durable
messages. Leaving a page, switching agents or losing a WebSocket must not terminate
work or create another writer. The [UI implementation plan](user-interface.md)
describes structured chat, component reuse and the terminal-lifetime distinction.

Build messages and decisions into the same control database. The model-facing
tools identify their authenticated sender automatically. Native peer messaging
must call these operations or be disabled. Sibling and cross-tree communication
is allowed when granted, without ownership or private-memory access being implied.

A question has one stable request ID and an ordered escalation history. It moves
to the direct parent, which answers or passes it to its own parent. Only an
unresolved root question enters the human inbox. An unavailable parent leaves
the request visibly pending at that parent; it does not authorize a shortcut.

Distinguish accepted-for-delivery, delivered-to-agent-inbox, supplied-to-a-run,
acknowledged/handled, and replied. Only claim a state supported by an observation.
An answer preserves its origin, records returning delivery, resolves the relevant
dependency, and makes eligible work ready for review. Retries use the same message
and request identities.

Reuse Hermes's clarification/approval UI elements where useful. Convert long-lived
waiting interactions into durable pending requests and end the blocked activation
so other work can proceed. On an answer, launch an eligible continuation with the
recorded decision; do not rely on keeping a Python callback alive for days.

The human inbox aggregates questions, proposals needing decisions, and approvals.
It shows scope, originating work, route, suggested response, what is blocked and
what continues. Responses to obsolete requests are recorded as inapplicable and
cannot start revised, paused or retired work.

Chat can convey context without stopping work. Explicit owner lifecycle commands
and purpose edits are applied by control, independently of the agent's consent.
For ambiguous prose, the UI presents the interpreted operation for clarification;
never wait for an LLM to execute an unambiguous Stop button. Inform the responsible
parent of direct owner redirection without giving the parent a veto.

## 7. Pause, purpose change and retirement

The stop path first blocks new dispatch and capability use in a transaction, then
immediately signals relevant engine runs, background processes and external jobs.
Record `stopping` until execution is known to have ended. Killing an engine alone
is insufficient: persistent Docker containers can retain background work.

Track sandboxes and jobs by owning agent/run. Reuse Docker process/container
controls to stop the relevant local execution while preserving durable volumes.
After a bounded grace period, escalate termination of framework-owned processes;
if an external service cannot confirm cancellation, retain an unknown/stopping
record and block conflicting replacement work. Already completed effects remain.

- **Agent pause:** add a durable pause cause to that agent and its descendants.
  Timers and answers cannot remove it. Read-only owner conversation/inspection
  remains possible without activating operational tools.
- **Resume:** remove only the selected pause cause, retaining independent child
  pauses. Reconcile outcomes and pending instructions before new execution.
- **Purpose change:** increment the purpose revision; stop that agent's obsolete
  runs and dependent descendant assignments. Follow recorded assignment provenance
  to determine scope. Preserve unrelated work and descendants' souls.
- **Assignment cancellation:** stop that assignment and dependent execution;
  retain results and records. It does not automatically retire an ongoing worker.
- **Retirement:** disable the entire agent subtree permanently for dispatch,
  withdraw obsolete pending requests, and stop every owned run/job recursively.
- **Replacement:** use a new agent ID and an explicit brief/artifact handoff.
  Retire the old subtree under the owner-approved replacement policy; never
  silently reparent descendants. Ongoing and bounded children follow the distinct
  [role-duration rules](../design/01-agents.md#lifetime-and-work-assignment).

Late results from obsolete runs can be retained as historical evidence but cannot
complete the successor assignment or authorize new actions. Purpose and assignment
revisions supplement, rather than replace, Hermes's existing run-ownership guards.

## 8. Events, recovery and operation

Extend existing task/run events into a unified system history with a monotonic
sequence. Keep task events and the global event projection linked without allowing
them to become independently authoritative. The state transition and its global
event must commit together in the control database.

Record all framework messages and known delivery outcomes, owner commands, soul
and grant revisions, activations, task transitions, decisions, evaluations, model
calls, tool starts/results/errors, stops and recovery attempts. Correlate agent,
project, task, run, cause and request IDs. Redact secrets before persistence and
show that content was redacted.

Use the engine's existing event callbacks and transports. Add a durable event sink
at model/tool boundaries in the fork, including a local spool if the central sink
is temporarily unavailable. Record an action intent before executing a controlled
effect; inability to record or authorize it blocks that action. If recording a
result fails after the effect, preserve uncertainty and reconcile it rather than
claim success. Ordinary optional observer hooks are insufficient for this contract.

The dashboard reads a snapshot plus events after its sequence. Reconnect with a
cursor and deduplicate IDs; do not depend on live SSE buffers as the only history.
Keep last observation time separate from current display time. Missing events or
expired engine history create a visible gap, not invented completion.

At service startup, acquire the single-dispatcher lease, recover pending intents,
reconcile known workers/jobs and expired claims, and perform one current review
for missed intervals. Never replay every missed tick or blindly reissue an action
whose outcome is unknown. Use engine idempotency where available, while keeping
durable framework operation IDs beyond the engine's retention window.

Deploy initially on one always-on Linux host with existing service supervision,
Docker and an authenticated HTTPS front door. SQLite WAL remains on local disk.
Back up the control database, souls, profiles and artifacts consistently; exclude
or separately protect secrets. A restored installation reconciles work before
dispatch. There is no initial high-availability or multi-controller promise.

## 9. First Builder

The Builder's current repository role is defined by its
[soul](../first-builder/SOUL.md) and [startup instructions](../first-builder/INSTRUCTIONS.md).
Follow the [continuous TDD practices](../first-builder/PRACTICES.md) now and when
the role runs inside the framework; persist work in [STATE.md](../first-builder/STATE.md).
The following describes the runtime isolation still to implement.

Give the First Builder an explicit workspace mount of the new implementation
repository root. Its plan and development artifacts live there. Its canonical
soul, grants, owner credentials and the running authority service live outside
that writable checkout.

Run the framework from a protected installed release, with no hot reload from
the Builder's edits. The Builder can propose and verify code changes; deployment
goes through the owner's scoped release authorization. Repository access does not
grant a Docker socket, service-manager access or permission to broaden its grants.
Existing tooling is used for code checks and version control under those grants.

The product is self-bootstrapped when this agent can plan and finish a bounded
framework improvement, retain its progress, and accept human steering while
running inside the framework. The external contributor remains necessary until
that boundary is actually demonstrated.
