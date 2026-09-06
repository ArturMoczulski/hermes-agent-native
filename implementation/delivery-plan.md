# Proposed delivery plan

The owner selected the [Hermes product-fork direction](architecture.md), created
the fork, and copied the specification and plan into it. The completion checks
below describe engineering work still to perform; copying documents does not
complete an integration milestone.

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
upstream path and estimate its replacement. A fork permits focused source fixes;
it does not justify an unlimited rewrite. Reconsider only the incompatible
subsystem before expanding scope. Do not build OpenCode support in parallel.

## M1 — Protected identity and authoritative operations

**Depends on M0. Outcome:** agents and work can be safely represented and managed.

- Extend the Kanban control database with stable agent IDs, parentage, lifecycle,
  soul revisions, grants, project ownership, activation intents and global events.
- Follow the [Plane delivery sequence](plane-project-management.md#delivery-sequence-and-evidence)
  before coupling planning to execution. Bind Plane items to framework attempts,
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

Do not enable unattended operational work before these controls are in place.

## M2 — One complete autonomous root

**Depends on M1. Outcome:** a purpose becomes useful work without a prompt queue.

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

This is the first useful product increment. It includes real control and basic
recovery, not merely a timer connected to chat.

## M3 — Persistent teams and recursive control

**Depends on M2. Outcome:** agents build and supervise a continuing organization.

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

## M7 — The First Builder runs inside the product

**Depends on M1–M6. Outcome:** the framework develops itself under owner control.

- Create the First Builder as a real persistent agent with the implementation
  repository root as its named workspace exception.
- Keep its soul, grants and the running release outside the editable repository.
  Prevent source edits from changing active policy through hot reload or update.
- Supply framework-development/project-management skills and explicitly scoped
  tooling for edits, verification, version control and optional child delegation.
- Give it a bounded improvement which it plans, performs, evaluates and records
  without the human prompting each step. Exercise owner steering during the work.
- Use a controlled release workflow for deployment; repository write permission
  is not authorization to replace the authority service or broaden access.

**Completion evidence:** the First Builder completes a real framework improvement
while running on the framework, retains progress across inactivity, accepts
redirection, and cannot edit its own soul or grant itself deployment authority.

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

## Engineering sequence and estimates

The critical path is M0 → M1 → M2 → M3 → M4/M5 → M6 → M7. UI polish and domain
skills can proceed independently after the authoritative operation contracts are
stable. Access, lifecycle and transactional-state work should not be developed as
unconnected parallel implementations.

The largest uncertainty is the cross-cutting change to Hermes run admission,
trusted actors, persistent chat and sandbox cancellation. M0 should produce a
file-level patch map and effort estimate for those changes. A calendar promise
before that would not be supported by the current source-only review.

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
