# Project management with Plane

## Default way of working

Agents use Plane workspaces, projects, backlogs and planning cycles to organize
most substantive work, including short assignments as well as long-term endeavors.
This is the owner's selected product direction. Plane is the shared planning
application; Hermes remains the agent engine. Provisioning and integration are
planned capabilities, not capabilities established by these documents.

Use a Scrum-like loop: choose a useful outcome, plan a small cycle, deliver and
evaluate increments, review the outcome, improve the approach, and plan again.
This applies to software, research, music and business work. It does not require
meetings, a dedicated Scrum-master agent, story points, or human approval at each
ceremony. The agent performs planning and review as part of its own work. Cycles
are ordered by intended outcome and dependencies, without calendar estimates,
date ranges or durations in days or weeks.

A direct answer or trivial action need not create a new project or sprint. Record
meaningful changes to existing work on the relevant item. Small substantive tasks
normally join an existing cycle; creating a new project for every request is not
the default. Continuous operational work can use a rolling Kanban backlog with
regular review when a finite sprint would be artificial.

## Planning structure

| Level | Purpose and required information |
| --- | --- |
| Agent purpose | Enduring reason for working; remains in the protected soul, never owned by Plane. |
| Workspace | Shared planning area for a root agent and its tree, visible to the human owner. |
| Project | Outcome, coordinating agent, constraints, success criteria, scope and current plan. |
| Milestone or workstream | Useful grouping of outcomes; optional, not another agent ownership boundary. |
| Cycle / sprint | Goal, sequence/order, scoped work, dependencies, accepted exit criteria and evidence, work-in-progress limit and review. |
| Work item | Deliverable or discovery question, acceptance criteria, priority, dependencies, implementer, accountable evaluator, state and next action. |
| Attempt and result | Actual execution, versioned evidence, evaluation and follow-up linked to the item. |

Distant plans stay coarse; upcoming work becomes specific enough to perform and
evaluate. Discovery is legitimate work with an explicit question and evidence of
what was learned. A project can end while its agent continues pursuing its purpose
through other projects. Active work and unanswered questions survive new sessions.

## Workspaces and recursive teams

Default to one shared Plane installation and one Plane workspace per root agent's
portfolio. Children use authorized projects within that workspace. A child may
coordinate a separate project when its responsibility merits it; it does not
receive an entire new installation or workspace merely because it exists.
An agent's private filesystem workspace is distinct from a Plane workspace.

The agent tree defines supervision; Plane project membership never reparents an
agent or expands its authority. Every project identifies its coordinating agent,
and every item identifies its implementer and accountable evaluator through stable
framework IDs. Names, labels, filters and board membership are not permissions.
Access is enforced for reads and writes, including comments and artifacts.

Example: the metal artist's workspace contains an album project. Composition may
be a workstream or a linked project coordinated by the composer. Its researchers
and producers receive scoped items and context. The artist can inspect the overall
plan without a duplicate copy of each child's task. The human can inspect all work.
Logical project relationships must remain expressible even where Plane lacks a
matching nested-project feature. Existing open cross-project authority questions
are not resolved by assigning a Plane role.

## Planning and delivery loop

1. **Orient.** Read current purpose, authority, project, cycle, active attempts,
   blockers, pending decisions and recent results. Recover existing work before
   creating new records. On first use, establish a brief and initial backlog.
2. **Refine.** Turn the next useful outcomes into small, evaluable items. Record
   uncertainty, dependencies and explicit non-goals where needed. Prioritize by
   contribution to the purpose and what must be learned next.
3. **Plan a cycle.** Choose a goal, its place in the sequence, a small feasible set
   of items, dependencies and a work-in-progress limit appropriate to actual
   capacity. Define exit criteria and the evidence needed to accept the outcome.
   Do not add calendar estimates, start/end date ranges or duration estimates.
4. **Deliver incrementally.** Pull ready work, verify authority and dependencies,
   delegate where useful, and produce evidence. Keep state and next actions current.
   Inspect active work before admitting more; avoid duplicate execution. A blocker
   on one item need not prevent independent authorized work.
5. **Evaluate.** Submit results against the brief, then record acceptance, revision
   needed, or failure and the reasons. Parent accountability and human approval
   rules follow [Projects and delegation](03-projects-and-delegation.md).
6. **Review and improve.** Advance when the cycle outcome meets its accepted exit
   criteria, or explicitly re-scope when new evidence or direction changes the
   plan. Do not wait for a date or claim an unmet goal complete. Carry unfinished
   work forward, return it to backlog, split it with traceable links, or cancel it
   with a reason under the lifecycle rules. Preserve the earlier goal, evidence
   and disposition. Record a useful process adjustment when supported by evidence.
7. **Review continued need.** Use accepted results to evaluate the whole purpose,
   including growth opportunities, recurring delivery, monitoring and descendant
   obligations. Record whether to continue, operate, wait, ask or retire under
   [purpose evaluation](01-agents.md#lifetime-and-work-assignment). Select clear
   authorized work when useful; do not fabricate a new cycle to keep an agent alive.
   Ask the parent about unresolved relevance or direction; roots ask the human.

Scope can change during a cycle. Record the source, reason and displaced work;
re-evaluate affected active attempts rather than blindly continuing an obsolete
brief. Human purpose changes, replacement, subtree pause and retirement retain
their immediate-stop behavior independently of the board or cycle sequence.

Cancelling an assigned item follows [assignment cancellation](05-human-interaction.md#assignment-cancellation):
stop the selected work and pause its agent/subtree. A cycle review cannot bypass
that pause by immediately pulling another item. Unassigned backlog cancellation has no direct performer to pause; still stop
invalid dependent execution. Only work without affected dependencies is a record-only
cancellation.

Thinking cadence determines when an agent reviews work; it does not estimate
cycle duration. Preserve actual activity and acceptance timestamps. A genuine
externally required deadline belongs to the affected work with its source and
constraint, separately from cycle order; it does not create an estimated sprint
duration. Cycle transition does not accept unfinished results, kill valid active
work, retire children or terminate a purpose. Review active work before proceeding.

Use native Plane cycles without planned start/end dates. Their goals, order,
items and exit evidence define progression; do not fabricate calendar values.

## Board, evidence and progress

The board distinguishes backlog, ready, working, blocked/waiting, review,
revision needed, accepted, failed and cancelled work. These may be represented
by mapped states plus explicit outcome/blocker fields; a single native state
must not erase these distinctions. Agent pause and run state are separate.

A Plane completed column is a planning signal, not sufficient evidence of
framework acceptance. Accepted work requires a recorded evaluation of the current
result against the applicable criteria. A premature completed-state edit is shown
as a discrepancy and reconciled; it does not unlock dependent execution.

Count progress through accepted outcomes, delivered evidence and useful learning.
Repeated board edits, new children, or successful check-ins alone are not progress.
A repeated no-progress pattern prompts assessment and a change of approach or
escalation; it must not generate an endless stream of identical questions.

## Human experience and communication

The control center's Work view shows project/cycle goals, sequence, exit criteria,
current assignments, blockers, reviews, last meaningful progress and links into
the relevant Plane workspace, project and board. Plane supplies detailed backlog and cycle editing.
Chat, agent tree, execution monitoring, stopping and the unified decision inbox
remain framework surfaces, linked to the same work IDs.

Agents maintain the board; the human is free to inspect or edit it without having
to run sprint ceremonies. Verified human planning edits can steer work, but Plane
comments are not automatically trusted owner commands. Identity must be verified
through designated channels. Service-account activity cannot impersonate the
human. Purpose, grants, stop commands and binding decisions use the framework's
trusted operations; a comment or board state cannot bypass them.

Questions follow the parent escalation chain and link to their work item. Plane
may show a reference to the pending question and its resolution; it must not
create a second independent human decision inbox. Agent communications through
project comments are also recorded as framework communication events.

## Provisioning, recovery and readable state

The framework provides the planning service, establishes workspace/project access
and supplies agents with a [project-management skill](../skills/productivity/plane-project-management/SKILL.md).
Agents primarily use Plane through API-backed planning operations; the web UI
is the human planning surface. Agents use scoped capabilities; they do not receive installation administrator
credentials or direct database access. Workspace setup is retry-safe and exposes
pending, ready and failed states, including a recoverable explanation.

Plane owns planning content. The framework owns agent authority, execution claims,
runs, decisions, evaluations and the event ledger. Views and file representations
identify their source and freshness; they are not competing editable task stores.
Each external update carries enough correlation to reconcile partial failures
without duplicating projects, items, messages or execution.

If Plane is unavailable, show stale/unavailable state and preserve pending writes.
Do not select new work or expand scope from stale plans. Previously admitted,
bounded work can continue only while its authority and stop controls remain valid;
retain evidence for later reconciliation. Cancellation must work without Plane.
The operator can restore planning data, artifacts and framework records together
and reconcile their mappings before resuming dispatch. Retiring an agent preserves
its work history while revoking active access; parent retirement retires descendants.

## First Builder before provisioning

The externally hosted First Builder applies the same planning and evaluation
workflow using repository PLAN.md and first-builder/STATE.md until Plane is ready.
It can perform human-authorized development through its coding environment;
framework run admission does not yet exist for that contributor. Record tests,
evidence and next actions there, then reconcile outstanding work into Plane once.
This bootstrap exception does not permit managed agents to bypass control during
a planning-service outage.

## Acceptance examples

| Situation | Required behavior |
| --- | --- |
| New artist purpose | Establish album/discovery plan and small first cycle; start authorized work without a human-maintained queue. |
| Small substantive request | Add a clear item to the appropriate existing project/cycle rather than inventing a new portfolio. |
| Child team | Parent sees linked progress; child cannot read or mutate unrelated projects through shared credentials. |
| Blocked item | Record linked question, escalate through parents, and find independent ready work within capacity. |
| Sprint ends mid-task | Review and deliberately carry work forward without losing history or duplicating the active attempt. |
| Worker says done | Keep result in review until an applicable evaluation accepts it; board movement alone cannot satisfy dependencies. |
| Human redirects or pauses | Apply the trusted instruction immediately; reconcile the planning view afterward. |
| Restart or duplicate delivery | Recover the same work and pending updates; create no duplicate assignment or run. |
| Planning outage | Show freshness and pending operations; retain stop controls and reconcile before selecting new work. |
| Activity without outcomes | Surface a progress concern supported by evidence and revise the approach. |
