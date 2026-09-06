# Delivery plan

The owner selected the [Hermes product-fork direction](architecture.md), created
the fork, and copied the specification and plan into it. The completion checks
below describe engineering work still to perform; copying documents does not
complete an integration milestone.

The owner's first usable milestone is an [autonomous fantasy writer](fantasy-writer-milestone.md)
with creation, continuing chat, visible sessions/actions/stories and cadence.
The First Builder handoff follows, adding protected repository development.
M0–M7 are retained as capability-group identifiers and Plane references, not a
mandatory numerical delivery order. M7 is the subsequent self-bootstrap handoff gate: it draws
on root-relevant M0/M1/M2 work and its own Builder isolation requirements. Full
M3–M6 delivery follows that handoff. This changes delivery priority without
marking any unfinished capability complete.

Every milestone uses the [First Builder's continuous TDD workflow](../first-builder/PRACTICES.md):
choose one behavior, write and observe a failing test, implement the minimum,
verify, refactor and repeat. Use Playwright end-to-end acceptance tests for user
flows with supporting unit/integration tests. Tests accompany each small increment;
they are not a phase after milestone implementation. Keep current evidence and
the next step in [STATE.md](../first-builder/STATE.md).

The [UX specification](../design/10-user-experience.md), [UX scenarios](../design/11-ux-scenarios.md)
and [UI reuse plan](user-interface.md) guide the interface work in these milestones.

Each milestone ends in visible behavior, reviewable code, appropriate automated
checks, and updated operator documentation. Passing upstream tests alone does
not establish the agent-native product rules.

## M0 — Establish the fork and validate the reuse boundary

**Outcome:** an exact source baseline and a concrete, bounded change map.

[AN-17 audit and inventory](hermes-execution-audit.md) records the selected source
snapshot and required native-path dispositions. It completes that discovery
slice; the controlled integration proof and actual denial/enforcement remain
required below.

- Select and record an immutable Hermes release/commit after checking the features
  used by this plan. Live documentation and moving `main` are research references,
  not a dependency lock.
- Fork creation and copying the product/implementation documents are complete.
  Preserve license/attribution and keep old implementation history as reference.
  Establish the repeatable test setup for the first behavior before adding it;
  reuse existing tooling without treating desktop Playwright coverage as proof
  of the new framework's web workflows.
- Keep Hermes's Python/frontend/package tooling. Inventory the minimal places to
  attach actor checks, agent/run identity, event persistence and lifecycle control.
- Trace all run entry points: web chat/PTY, API, CLI, Kanban, cron, goal continuation,
  native delegation, reviews and recovery. Identify which will be integrated and
  which disabled for managed agents.
- Inspect sandbox mounts, network controls, credential forwarding, persistent
  container cleanup, profile memory writers, and protected configuration.
- Build a narrow integration proof through the chosen execution path: persistent
  profile, observed tool action, recorded run, explicit interruption and sandbox
  process inspection. Include a restart and a failed/unknown outcome.
- Decide the web chat integration: reuse UI components, but route conversation to
  persistent service-owned sessions rather than a browser-owned process.

**Completion evidence:** a recorded baseline, patch inventory, reproducible local
setup, and evidence that the proposed authority and lifecycle boundaries can be
inserted without replacing the agent loop or duplicating task storage. Provider
calls use an explicitly configured test account; they are not required for every
local check.

**Decision gate:** if a required boundary cannot be enforced, name the exact
upstream path and describe its replacement scope. A fork permits focused source fixes;
it does not justify an unlimited rewrite. Reconsider only the incompatible
subsystem before expanding scope. Do not build OpenCode support in parallel.

## M1 — Protected identity and authoritative operations

**Uses M0 integration evidence. Outcome:** agents and work can be safely
represented and managed. Deliver the single-Builder identity, grants, scoped
operations and event boundary before M7; multiple-root and parent-specific
completion cases remain part of full M1 coverage.

- Extend the Kanban control database with stable agent IDs, parentage, lifecycle,
  soul revisions, grants, project ownership, activation intents and global events.
- Complete the root-relevant [Plane delivery sequence](plane-project-management.md#delivery-sequence-and-evidence)
  needed by the Builder before coupling its planning to execution. Full multi-agent
  onboarding can follow. Source freshness and reconciliation needed for safe
  admission remain on the Builder path. Bind Plane items to framework attempts,
  evaluations and artifacts; add actor, purpose revision and expected-run checks.
  Do not adopt inherited Hermes tasks as a competing planning store.
- Add trusted owner authentication and scoped agent actors. Cover read access,
  UI/API/CLI mutations and worker tools; unknown actors fail closed.
- Generate protected soul/configuration and readable state projections. Scope
  mutable practices, memory and skill directories without allowing policy changes.
- Establish safe workspace provisioning, private profiles, explicit grants, and
  protected operator-secret filtering across all forwarding paths.
- Define the owner-approved default capability template during installation,
  so ordinary root creation needs a purpose rather than a permission inventory.
- Add a basic agent creation/editor view and work/record inspector using the
  existing web shell. Set up the always-on service and persistent storage layout.

**Completion evidence:** two roots with different model selections and duplicate
display names remain distinct; a child can be represented without cycles; owner
and parent soul edits obey their different rights; unauthorized reads/writes and
owner impersonation are rejected through every exposed path. Each accepted
mutation has a durable event and agent-readable representation.

Do not enable unattended Builder work before its exposed operations and execution
paths enforce these controls. Disable unsupported managed entry paths; narrowing
the first handoff to one root is not permission to bypass authority checks.

## M2 — One complete autonomous root

**Depends on the M1 authority and operation boundaries for enabled root work.
Outcome:** a purpose becomes useful work without a prompt queue. The fantasy writer
is the first root used to prove the selected behavior; the First Builder reuses
that foundation for its subsequent M7 handoff.

- Creation atomically records an immediate coordination activation. Add interval
  cadence and one managed dispatcher with per-profile turn admission and global
  capacity limits.
- Load the bundled [Plane project-management skill](../skills/productivity/plane-project-management/SKILL.md)
  using the scoped planning and framework work operations. Include
  purpose discovery, clear briefs, dependencies, evidence, review, next-step choice,
  focused questions and explicit wait reasons.
- Keep durable assignment state across bounded engine turns. Add tracked external
  jobs for long operations so coordination can continue while a job is active.
- Connect basic owner chat, steering, Stop, pause/resume, root questions and a
  simple durable human decision list. A blocker affects its dependent work only.
- Require explicit result evaluation before task acceptance, then a distinct
  assessment of whole-purpose fulfillment. Include finite criteria, continuing
  delivery/monitoring obligations, useful growth and established operations.
- Implement the basic lifecycle decision for the root: continue useful work,
  wait, ask about uncertainty, or initiate controlled retirement when the whole
  purpose is fulfilled with applicable acceptance and no unresolved obligations.
  Do not require human approval for every retirement or generate work for self-preservation.
- Assignment cancellation stops selected work and durably pauses its performing
  root; independent assignments are preserved but paused. A ready backlog item
  or cadence tick cannot remove that pause.
- Persist agent/session/run mappings, messages and pending dispatch. Reconcile
  restart during launch, execution and result recording without blind replay.

**Completion evidence:** create a root with a broad purpose and daily cadence;
it immediately plans, performs one authorized branch while another awaits an
answer, evaluates an artifact, and chooses a next step. A minute cadence does
not duplicate active work or unanswered questions. Closing the browser does not
stop work. Pause blocks subsequent actions; the owner can still communicate.
An accepted finite-purpose result permits recorded controlled retirement when no
obligations remain. An established service with monitoring duties continues even
without new growth work; uncertainty routes to the human for this root. Cancelling
one assignment preserves but pauses independent work. None of these outcomes may
weaken criteria, rewrite the soul or mistake a Done item for whole-purpose fulfillment.

Deliver the selected root capabilities first in the fantasy-writer milestone,
then reuse and complete remaining root coverage for the M7 Builder handoff.
Actual control, evaluation and basic recovery belong in the writer experience;
a timer connected to chat does not meet it.

## M3 — Persistent teams and recursive control

**Follows the M7 handoff and builds on M2. Outcome:** agents build and supervise
a continuing organization. Full recursive teams do not gate the first Builder.

- Add scoped child creation with purpose, capabilities, model, workspace and
  cadence, without a fixed lifetime classification. A parent can delegate only grants
  it is authorized to delegate.
- Create the child's initial work automatically; reuse admission and discovery
  rather than requiring a separate human bootstrap for every child.
- Add assignment delegation with accountable parent, implementer, criteria,
  reporting expectations and result/revision handoffs.
- Add durable parent-by-parent escalation with one request ID, route history and
  returning answer provenance. Keep an unavailable-parent question pending.
- Implement subtree pause/resume/retirement, purpose revisions and replacement.
  Stop obsolete work promptly, including relevant sandbox processes and external
  jobs; do not claim an uncertain action has stopped.
- Add authorized sibling and cross-tree messaging across separately isolated
  workspaces. Give projects scope within the tree without reparenting agents.
- Extend M2 purpose evaluation to the whole team: inspect child obligations and
  handoffs, preserve accountable parent acceptance, and route uncertainty up the
  parent chain. Retain retired records and avoid purposeless continuation.
- Cancellation durably pauses the performing child and its entire subtree while
  retaining independent assignments. Keep separately proposed resume handling
  distinct from this approved cancellation behavior.

**Completion evidence:** an artist creates a composer, which creates researcher
and producer children; a descendant delegates again. The parent reviews active
child work and starts an independent branch. A question travels upward and an
answer returns without human relaying. A subtree retirement stops all its
descendants and cannot be reversed by a timer or stale answer. Other roots keep
working. A child with fully accepted purpose fulfillment and no unresolved
obligations can initiate retirement of itself and its descendants; an accepted
campaign alone does not retire an agent that still has marketing responsibilities.
Uncertain handoffs escalate instead of abandoning work. Cancellation pauses the
performing child subtree, preserving its independent assignments. A grandparent
cannot directly acquire a grandchild's soul-edit rights.

## M4 — Complete the owner experience and event views

**Depends on M3; basic UI/events began in M1–M2. Outcome:** one place to understand
and direct the whole organization.

- Extend existing Hermes profile/task pages with a stable agent tree, purpose
  and grants editor, project/task views and direct conversation with any agent.
- Complete the unified decision inbox across all roots: clarification, proposal
  and permission types; context, route, urgency, affected work, recommendations,
  answers, denial and obsolescence.
- Show current assignment and stage, delegated work, cadence, last check-in,
  last work/completion, pending questions and reasons for inactivity.
- Add filters by agent, subtree, project, time and event type, with a connected
  view of messages, decisions, actions, results and evaluations.
- Complete durable model/tool event ingestion, secret redaction, stream cursor
  recovery and last-known/unknown presentation. Preserve source event references.
- Distinguish message sending, delivery, handling and reply. Retrying delivery
  must not invent receipt or produce duplicate decision items.
- Ensure owner direction takes precedence anywhere in the tree and is relayed to
  responsible coordinators as information, not an approval request to the parent.

**Completion evidence:** the owner can trace a research question through two
ancestors to an inbox response and resumed work; inspect a denial and a failed
action; refresh during work without losing identity or duplicating output; and
see a disconnected worker as unknown rather than completed.

Retain Hermes's existing styles and useful components. Add the structured
managed-agent conversation within the same web application, as described in the
[UI plan](user-interface.md). It shares the control service and durable history;
there is no second independent frontend application or chat state store.

## M5 — Progress concerns and complete result review

**Depends on M3–M4. Outcome:** activity is assessed against outcomes and learning.

- Extend existing failure/recurrence signals into evidence-linked concerns for
  repeated failed attempts, repeated planning and unresolved delegation.
- Have the responsible agent review each concern and record a justified
  continuation, changed approach, investigation or escalation.
- Deduplicate recurring concerns and exclude known waiting states from simple
  failure rules. Make timing and thresholds configurable.
- Deepen the assignment and purpose evaluation introduced in M2–M3 with
  domain-appropriate evidence: accepted, needs revision, or not met; criteria
  revisions, artifact references, ongoing obligations and uncertainty remain
  inspectable. Test growth opportunities separately from established operations.
  This milestone improves evaluation quality; it does not defer the basic
  purpose-fulfillment and lifecycle decision until after the first root.
- Route upstream automatic human-triage/review behavior through the ownership and
  escalation rules. Do not mechanically apply software-review criteria to music.

**Completion evidence:** repeated unproductive research produces one linked
concern and a response; a legitimate long recording job does not automatically
fail. A composition missing a required section returns for revision, and later
acceptance records the evidence. Purpose review distinguishes a fulfilled finite
objective, useful ongoing operations, unsupported busywork and an uncertain handoff.
No progress heuristic alone retires an agent or changes its soul.

## M6 — Recovery and operation that can be relied on

**Depends on M2–M5; basic deployment/recovery began earlier. Outcome:** unattended
operation has documented, observable behavior through failures and upgrades.

- Complete recovery for crashes around claims, dispatch, messages, approvals,
  external effects, task acceptance and purpose changes.
- Recover from lost event subscriptions, expired engine histories and unknown
  jobs. Quarantine conflicting work until its prior outcome is reconciled.
- Verify pause/retirement during tools and background commands, persistent
  container cleanup, service restarts, full disks and unavailable providers.
- Add consistent database/profile/artifact backup and restore procedures,
  credential rotation and an owner-operated emergency stop path.
- Check fair capacity allocation across multiple roots, repeated agent creation,
  missed cadence coalescing and worker cleanup. Publish practical host limits.
- Ship one documented always-on Linux deployment with HTTPS authentication and
  default resource isolation. Avoid introducing a hosted service requirement.
- Record the pinned upstream/runtime/image versions; disable automatic upstream
  updates and document deliberate upgrade/rollback procedures.

**Completion evidence:** after closing the browser and restarting the service,
agents retain purpose, tasks, questions and memory; work with unknown effects is
not duplicated. A restored backup resumes through reconciliation. Engine stop and
sandbox stop are distinguishable in records. No UI connection owns the cadence.

## M7 — First major handoff: the autonomous First Builder with chat

**Depends on root-relevant M0/M1/M2 behavior and the Builder isolation below,
not full M3–M6 completion. Outcome:** the owner continues framework development
through a persistent Builder agent and its web conversation. The external coding
conversation is no longer needed to prompt each development step.

Deliver the following outcomes in small test-driven increments. These are scope
and evidence gates, not duration estimates or calendar windows.

1. **Scoped planning and retry handling.** Complete the Builder's scoped Plane
   reads/writes and durable uncertain-write handling; connect its existing project,
   current cycle and project-management skill. Preserve work, evidence and decisions
   across turns, and reconcile failures before retrying an effect. Complete the
   applicable planning recovery checks before unattended planning depends on them.
2. **One managed Builder turn.** Admit a real Hermes model/tool run under the current
   Builder identity, soul revision and grants. Provide explicitly scoped repository
   editing, test execution and version-control tools. Persist run/session/assignment
   identity and relevant model/tool events; enforce authenticated operations, owner
   Stop and purpose/permission changes. Verify actual sandbox process stopping and
   keep unknown outcomes visible. Keep the canonical soul, grants, credentials and
   protected installed running release outside the editable repository; no hot reload
   or source edit may change active authority. Repository access does not grant a
   Docker socket, arbitrary host access or permission to deploy.
3. **Durable chat, questions and steering.** Connect the trusted owner channel to
   that persistent Builder in the existing web application. Retain messages,
   proactive questions and answers; show queued versus handled input and current
   work, waiting and uncertain status. Support direct conversation, redirection,
   Stop and pause/resume while work is running. Closing, reopening or refreshing
   the browser must neither terminate work nor duplicate a run or lose history.
4. **Cadence, evaluation and basic recovery.** Use one dispatcher and durable
   activation intents, including immediate start and interval review, with one
   mutating turn per Builder profile. Load the current purpose, memory and Plane
   work; choose useful authorized work, record explicit result evaluation, and
   separately assess whole-purpose fulfillment and continuing obligations. Continue,
   wait, ask or retire through the applicable lifecycle controls. Cancellation
   pauses the performing agent; cadence cannot clear that pause. Reconcile restart
   during launch, tool execution and result recording without blindly replaying
   effects, dropping owner input or falsely claiming completion.
5. **Proven self-bootstrap.** Give the hosted Builder a real bounded framework
   improvement. Observe it choose the work, demonstrate the relevant test failing,
   implement the change, pass appropriate checks and record result/evaluation
   evidence in Plane. Exercise owner chat and steering during the work, browser
   closure, service restart and later independent next-step selection. The owner
   does not supply each development step. Missing direction or authorization causes
   a focused question; an explicit pause remains in force.

**Completion evidence:** a recorded end-to-end run through all five outcomes,
including real model-driven coding and verification, owner conversation, actual
interruption, continued work without an open browser, restart reconciliation and
an unprompted next authorized step. Pair deterministic Playwright and process/
storage checks with this live acceptance; scripted model responses alone do not
prove autonomous development. Demonstrate that the Builder cannot edit its own
soul, grant itself authority or activate repository changes as the running release.
Deployment remains an owner-authorized controlled operation.

Keep the first handoff to one Builder without child delegation if necessary.
Full recursive teams and cross-tree communication, the complete organization
monitor and global inbox, advanced progress-concern analysis, multi-root capacity
fairness, and the packaged Linux release remain subsequent M3–M6 work. Basic
visibility, decisions, control, evaluation, isolation and recovery listed above
are not deferred. Completing M7 does not automatically complete those groups or
all multi-agent cases in M0–M2.

## Coverage of the full product specification

The numbered references below are [product scenarios](../design/06-product-scenarios.md).
Milestones establish capabilities; the final release record must attach actual
evidence rather than marking a requirement done because a page or function exists.

| Scenario | Primary milestone(s) |
| --- | --- |
| 1. Start from an ongoing purpose | M2 |
| 2. Continue after a milestone | M2, M5 |
| 3. Review while work is active | M2, M3 |
| 4. Ask proactively and track answers | M2, M3, M4 |
| 5. Delegate through a persistent tree | M3 |
| 6. Protect soul while learning | M1, M3 |
| 7. Skills for structured work | M1, M2 |
| 8. Steer and pause through chat | M2, M3, M4 |
| 9. Recover continuity | M2, M6 |
| 10. Nest responsibility within the tree | M1, M3 |
| 11. Operate offline with different models | M1, M2, M6 |
| 12. Collaborate without changing ownership | M3 |
| 13. Enforce access and explain actions | M1, M4, M6 |
| 14. Recognize human authority; reject impersonation | M1, M3, M4 |
| 15. Build an ongoing team from a purpose | M3 |
| 16. Framework develops itself | M7 |
| 17. Retire the entire subtree | M3, M6 |
| 18. See current work and cadence | M4 |
| 19. Follow events across agents | M3, M4 |
| 20. Distinguish current state from missing information | M4, M6 |
| 21. Inspect communication and delivery outcomes | M3, M4 |
| 22. Notice activity without progress | M5 |
| 23. Evaluate results before accepting them | M2, M5 |
| 24. Resolve human decisions in one place | M2, M4 |

## Engineering sequence and evidence

The current path is the [fantasy-writer cycle](fantasy-writer-milestone.md):
create and observe a managed story run with actual stopping → durable owner chat
and steering → detailed activity/artifacts → cadence, evaluation and recovery →
real owner acceptance. Deliver UI and backend together through small tested slices.
The service provisions the ordinary writer's planning home; Builder-specific
repository privileges do not gate this path.

Then reuse those foundations for the M7 Builder handoff, adding protected deployed
soul/grants/running release and repository tools before its first development run.
Full M3 teams, M4/M5 organization experience and progress assessment, and M6 broader
operation follow. M0–M7 preserve capability coverage; their numbers do not dictate
chronological completion. The [execution audit](hermes-execution-audit.md) remains
the source map: enforce every enabled writer path and leave unused paths disabled.
No requirement to integrate every inherited native feature before proving one root.

Use ordered outcome-based cycles without planned date ranges or duration estimates.
Advance on accepted evidence. Root timing and runtime-limit defaults remain open;
select explicit trusted settings before dependent real activation.

Use deterministic local checks for authority, scheduling and state transitions;
real isolated processes/containers for lifecycle and recovery; and a small set of
explicitly configured model-driven scenarios for autonomous behavior. Do not turn
every UI or documentation change into a full model run. None of these checks has
been run as part of preparing this proposal.

## First-release exclusions

Do not initially build OpenCode coupling, a provider SDK, custom memory research,
a new skill marketplace, Kubernetes,
multi-controller consensus, a mobile/desktop client, or a new chat-platform
integration for every messenger. Multiple owner chat channels and historical
execution replay/branching remain optional product decisions. Detailed financial
budgets and the other unselected brainstorm features are not added by this plan.

General-purpose agents use granted skills and integrations. The framework does
not promise that installing it alone supplies every business service or music
production capability; a missing capability becomes visible work or an escalated
request. The core supports arbitrary purposes and recursive children whose
lifespans follow purpose evaluation, without a fixed catalog of professions or
creation-time lifetime types.
