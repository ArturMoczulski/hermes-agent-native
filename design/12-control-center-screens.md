# Control center: screen-by-screen specification

Status: **Recommended build specification for review**, 2026-09-05. This is the
textual design brief for the first browser control center. It replaces the need
for visual mockups; the incomplete Figma exploration is not a build reference.
No interface implementation is claimed.

Read this for what each screen contains and how its controls work. Read
[User experience](10-user-experience.md) for shared interaction rules,
[UX scenarios](11-ux-scenarios.md) for acceptance evidence, and
[UI implementation](../implementation/user-interface.md) for Hermes reuse.
Existing product requirements take precedence over layout recommendations here.
The final section identifies controls dependent on unresolved product policies.

## 1. Application shell

Use a persistent navigation sidebar on desktop. The main area shows one primary
view at a time. Details open beside it or on a linked detail page; do not force
chat, monitoring, decisions and project management onto one dashboard.

| Navigation | Contains |
| --- | --- |
| Chat | Agent selection and the selected agent's continuing conversation. |
| Monitor | The agent tree, current activity and attention needed. |
| Inbox | Requests currently requiring the human's decision, with a pending count. |
| Work | Projects, plans, assignments, results and evaluation. |
| Create agent | A creation form accessible from every primary view. |
| Settings | Secondary navigation near the owner identity: connections and configuration. |

The shell shows the signed-in human owner and a connection indicator. Show a
prominent last-known-state banner when disconnected. Every scoped view displays
its scope, such as “All agents” or “Metal Artist and descendants,” with a clear
way to change or remove it. Inbox starts global even when another view is scoped.

The first visit to an empty installation offers **Create your first agent** with
a short example purpose. Do not invent demo agents in a real installation. On
later visits, restore the last view unless an explicit link selects another record.
Every agent, assignment and decision must have a link that opens that exact record.

## 2. Create agent

Use a focused form, as a page on narrow screens or a large dialog on desktop.
Its primary question is: **What should this agent exist to do?**

| Field | Behavior |
| --- | --- |
| Purpose | Required multiline text. Example: “Develop an original metal music career: compose, produce and improve a body of work.” This is the main field, not an initial chat message. |
| Name | Suggested from the purpose, editable before submission. Names need not be unique. |
| Parent | Explicitly “No parent — root agent” or a selected agent with its ancestor path. Creating a child from an agent's details preselects that parent visibly. |
| Outcomes and continuing obligations | Optional details of what fulfillment means and what delivery, monitoring or growth should continue. Discovery clarifies missing details; no lifetime type is required. |
| Thinking cadence | Show the actual configured interval and allow editing. Explain that it is a review interval, not a deadline or a guarantee of continuous execution. No arbitrary hardcoded default. |
| Fundamental rules | Optional owner-defined rules, kept with the purpose in the soul. |
| Capabilities summary | Plain-language summary of the permissions and tools this agent will receive. A broad purpose does not expand permissions. |
| Advanced settings | Model/provider, skills, workspace and detailed permissions. Show inherited/configured values; technical configuration need not be entered again when usable defaults exist. |

Primary action: **Create and start**. Secondary action: **Cancel**. If essential
configuration is missing, identify it next to the field and link to the relevant
setting while preserving the draft.

On submit, disable duplicate submission and show **Creating…**. Once accepted,
open Chat for the new identity with its saved purpose and observed startup state:
**Queued for first review**, then **Planning** when execution is observed. The
first review starts immediately rather than waiting a full cadence interval.
Discovery and clarification are legitimate first work; do not require the human
to create tasks or send a second “start” message.

If creation fails, retain the form. If the response is uncertain, reconcile the
original request before retrying. A child created by an agent appears in the same
tree and conversation picker without requiring human creation of a separate chat.
Lifetime follows evaluation of the purpose and remaining obligations. Do not add
a mandatory temporary/permanent or bounded/ongoing selector.

## 3. Chat

Desktop layout: agent picker, conversation, optional agent-details panel. The
conversation gets most of the width. Closing details must leave chat fully usable.

**Agent picker:** search by name/purpose, expandable root/child relationships,
parent context, unread conversation count and compact own-activity labels.
Offer an explicit filter for paused/retired agents. Selecting a descendant opens
that agent directly. Remember a separate unsent draft for each agent.

**Conversation header:** agent name, ancestor breadcrumb, short purpose, current
assignment and own activity. Show descendant activity separately when relevant.
Include **View work**, **Agent details**, and **Pause agent and children**. Replace
pause with the appropriate paused/stopping state and eligible resume control.
Put retirement and purpose editing in details, away from routine message sending.

**Conversation body:**

- Human messages and agent replies, with sender and timestamp.
- Useful progress updates and links to resulting work, without a stream of routine tool output.
- Result cards with title, artifact type, version, assignment and review state.
- Decision cards linked to the same request shown in Inbox. A question still being considered by a parent is not a human decision card.
- Clearly attributed system observations and forwarded agent communication. Quoted human text is not itself a trusted owner message.
- Collapsed work-event groups that open the relevant history. Do not expose or invent private reasoning as a status report.

**Composer:** multiline **Message [agent name]** field and **Send**. Support
Shift+Enter for a newline and make the send shortcut discoverable. General file
upload is not required for the first slice; links to existing artifacts must work.
Show sending, accepted/awaiting handling, handled and failure states only when
known. Acknowledging new direction is separate from receiving a message.

Sending context does not implicitly pause work. A paused agent's conversation
remains readable and accepts owner input, visibly awaiting handling where no
execution is eligible; it must not resume work merely to service a new message.
Preserve older scroll position and offer **New messages** rather than jumping to
the bottom. An empty conversation shows the purpose and startup state, not a
fabricated agent greeting. A failed send retains text and offers safe retry.

## 4. Monitor

This is the operational overview. Start with an expandable tree table; a graph
canvas is unnecessary. Use a flat-list toggle for sorting and large searches.

**Toolbar:** search, root/subtree filter, project filter, own-activity filter,
**Needs attention**, and **Include retired**. Show active filters and **Clear
filters**. Preserve ancestor rows around matching descendants. In tree mode,
updates must not continuously reorder rows.

| Column | Required content |
| --- | --- |
| Agent | Name, expand/collapse control, parent hierarchy; stable identifier in details. |
| Own activity | Planning, working, waiting or idle; lifecycle restrictions and stopping/unknown displayed distinctly. |
| Current work | Assignment and observed stage; “+2 other assignments” opens details rather than hiding parallel work. |
| Descendants | Separate counts of working, waiting and attention-needed descendants. Name this column “Descendants” if counts include more than direct children. |
| Cadence | Configured interval and next eligible review, or why reviews are suspended. |
| Last work | Last actual work time or “Never worked.” A check-in that chooses to wait does not update this as productive work. |
| Freshness | Last observation and explicit stale/unknown warning when current activity cannot be established. |

Clicking a row opens Agent details. Provide direct **Open chat**, **View work**
and **View history** actions. **Pause agent and children** must be reachable
without navigating through configuration screens. Do not add bulk actions or
drag-to-reparent in the initial interface.

Show attention items with reasons: awaiting human decision, failed execution,
unconfirmed stopping, or a progress concern. Link each to its evidence. Waiting
for a dependency is not automatically failure. Overall counts must not imply
that every parent is executing when only descendants are active.

Example: Metal Artist has no own execution and waits for compositions. Composer
is arranging a song; Researcher is gathering references; Producer waits for the
arrangement. Show two working descendants under Metal Artist and the specific
blocked branch, rather than one misleading status for the entire organization.

## 5. Agent details

Use the same inspector from Chat and Monitor, with an expanded page when needed.
The header always identifies the agent and parent path. This is one shared
interface for all agents. Name the work area **Work** and its content collection
**Saved outputs**; use **Results** for the wider outcome and evaluation view.
A story is an output title/type within those views, not a separate agent screen.
Sections:

| Section | Contents and controls |
| --- | --- |
| Overview | Purpose, expected outcomes, continuing obligations, direct parent, human ownership, lifecycle, own activity, descendant summary, current assignments and blockers. **Open chat**, **View work**, **Create child**. |
| Purpose evaluation | Latest review, evidence and applicable accountable acceptance; remaining obligations and the reason to continue, wait, clarify, pause or retire. Distinguish growth from recurring delivery/monitoring and assignment completion from whole-purpose fulfillment. Link related work, escalations and any retirement operation. |
| Cadence | Interval, last check-in and its recorded outcome, next eligible check-in, last actual work and last accepted result as separate facts. **Edit cadence**. Show suspension causes; a paused agent has no ordinary upcoming activation. |
| Plane progress updates | Owner-controlled **Concise**, **Standard** (default), or **Detailed**, with a short explanation of each level, **Save** and **Cancel**. Show the saved value and when it applies. Link the [reporting rules](13-project-management.md#continuous-work-item-updates-and-outputs); required events remain visible at every level. |
| Soul | Purpose and fundamental rules, current revision and change history. **Edit purpose and rules** for the owner; never describe agent-authored memory as a soul change. |
| Practices and memory | Separate readable sections, with last-change attribution, owner **Edit**, **Save** and **Cancel**. Preserve revisions and warn of concurrent changes. These edits cannot grant capabilities or override the soul. |
| Capabilities | Configured model/provider, skills, workspace and effective permissions, including where a restriction comes from. Owner **Edit** controls with explicit changes and their effective status. |
| Children | Direct children with purpose, latest purpose-evaluation outcome, activity and work links; expand into deeper levels through Monitor. |
| History | Agent-scoped event history and related communication. |

Runtime state is an observed record with named actions, not a generic editable
JSON box. Owner control is expressed through purpose edits, work updates and
lifecycle operations; historical evidence must not be rewritten by changing a badge.
Changing model preserves identity and accumulated work. Show when a saved setting
will take effect; do not imply that an in-flight operation already uses it.

The compact agent Work area shows the actual Plane project/cycle, current
assignment and criteria, current attempt and limits, recent results and
**Open planning project**. Saved outputs show title, format, version, producing
agent/work and evaluation links. Use **Open output**, **Download** where available,
and format-appropriate controls such as audio playback. The result detail below
owns the complete review interaction; do not maintain duplicate result records.

A current work item must come from an explicit assignment/selection record,
not an inference from Plane priority, status or cycle order. When work stops,
label the retained record as last selected work. Preserve the requirements and
cycle observed when the agent selected it; distinguish them from later planning
observations. Show when each was observed, and do not imply that the agent has
adopted a human edit just because the refreshed view can see it. Missing selection
and temporarily unavailable planning are distinct states.

Planning freshness is independent of live execution status. Provide **Refresh
planning**, the last successful check time, and a visible stale state after an
outage. An older snapshot cannot explain a newer selection. Changing agent,
purpose or project discards incompatible cached data. Owner inspection must not
start work or reinstate revoked agent permissions; stopping remains available
while the planning service is unavailable.

Show whether recent progress and output links reached the Plane item, with
**Open work item** and pending, failed, unknown or description-conflict details
when present. A saved output and its delivery to Plane have distinct states.
Use the same versions and evaluations in both surfaces; a pending delivery must
not obscure a saved output or disable stopping.

Link **Decisions** to the same requests used by Chat and Inbox, and **Children**
to the same parentage used by Monitor. A feature not yet supplied by the backend
must be described as unavailable, not as an empty successful list. Do not add
working-looking child creation or decision controls before their operations exist.
A supported feature with no records has a genuine empty state.

## 6. Inbox

Desktop layout: request list and selected request detail. On narrow screens use
the list followed by a detail page with Back. Default to **Pending**, across all
roots. Other views: **Answered**, **Declined**, and **Obsolete**. Filter by root,
originating agent, project and request type; default ordering is oldest first,
with explicit urgency displayed and an optional urgency sort.

Each list entry shows type, concise question/action, originating agent, responsible
root, age, declared urgency and affected work. Repeated check-ins do not create
new copies. The pending badge counts requests, not reminders or messages.

**Request detail contains:**

- The exact question, proposal or action awaiting authorization.
- Why human input is needed and any suggested answer with its rationale.
- Originating agent and escalation route, for example Researcher → Composer → Metal Artist → You.
- Affected assignments, what is blocked and what can continue independently.
- Relevant conversation, artifacts and request history; **Open conversation** and **View work** links.
- Request state, revision/applicability and the current responder, including the recorded answer after resolution.

| Request type | Response controls |
| --- | --- |
| Clarification | Free-text answer, optional suggested choices, **Send answer**. Choosing a suggestion alone does not submit it. |
| Direction proposal | Proposed next work and scope; **Proceed with this proposal**, **Give different direction**, or **Decline**. Acceptance applies to the stated proposal, not unrelated permissions. |
| Approval | Exact action, target and relevant limits, with **Approve this action** and **Decline**; optional explanatory comment. Required approval is never inferred from silence. |

After responding, show **Answer recorded**, then known delivery/handling state.
Keep the response visible instead of immediately jumping to the next item. Provide
**Next pending request**. Answering a paused agent does not resume it.

If the request changes or is resolved elsewhere, show **This request has changed**
and its current state before accepting a response. An obsolete answer cannot
authorize new work. A dismissed detail panel leaves the item pending. Unavailable
parents remain visible in routing history; the UI must not silently bypass them.

## 7. Work: projects and plans

Plane supplies detailed backlog, board and cycle editing under
[Project management with Plane](13-project-management.md). The control center
provides a connected overview with **Open in Plane** links and source freshness;
it need not duplicate Plane’s full editor. Add assignment and Edit plan route to
the appropriate Plane surface or the same scoped integration operations. Show
cycle order, goal, exit criteria, remaining work and the last cycle review
alongside run state. Do not require planned dates or display invented duration
estimates; current focus follows accepted outcomes and the recorded sequence.
Framework evaluation and stop controls remain authoritative. A completed cycle
or empty board does not establish whole-purpose completion or end a continuing
service. Link the coordinating agent's purpose evaluation and remaining obligations.

The default is a project list with outcome, coordinating agent, current stage,
active assignments, blocked assignments, pending reviews and latest accepted
result. Use evidence and stages; avoid decorative completion percentages.
Filters: agent/subtree, project state and attention needed.

Selecting a project opens its overview with:

- Purpose/outcome and coordinating agent, including its actual parent context.
- The current plan: milestones or ordered assignments, dependencies and latest revision.
- Assignments in a list, with an optional board toggle.
- Pending decisions, progress concerns, results and evaluations.
- **Talk to coordinator**, **Add assignment**, **Edit plan**, and links to history.

Agents create and maintain plans themselves; owner editing is optional control,
not a prerequisite for progress. Project membership does not move an agent in
the tree or create a new ownership boundary. Keep any cross-project conflicts
visible rather than silently assigning a new coordinator's authority.

Recommended board columns: **Planned**, **Working**, **Waiting**, **In review**,
**Accepted**. Show **Needs revision** as an explicit assignment state in its
applicable work column. Keep cancelled assignments in an explicit history/filter.
Native Plane board changes update planning state; no drag-to-done shortcut can
bypass framework evaluation. Show a discrepancy until premature completion is
reconciled. Native board labels map to the richer states in the planning chapter.

## 8. Assignment and result detail

This is a linked detail page or a sufficiently wide panel, not another primary
navigation destination. It contains:

| Area | Contents and controls |
| --- | --- |
| Assignment header | Title, project, current state, implementer and accountable evaluator. **Talk to implementer**, **Talk to coordinator**. |
| Expected outcome | Description, acceptance criteria and constraints; owner **Edit assignment** with a change summary and revision. |
| Dependencies | Required results, unanswered questions and waiting actions; each links to the actual record. |
| Attempts | Current and prior attempts, reported stage, timestamps and evidence. Preserve failed and interrupted attempts. |
| Results | Artifacts with title, type, version, producing agent and time. **Preview**, **Open**, **Download** where applicable. |
| Evaluation | Submitted version, evaluator, criteria-by-criteria findings and outcome: awaiting review, accepted, or needs revision. |
| Progress concern | Repetition evidence, last meaningful progress, responsible agent's assessment and planned response. **Discuss with coordinator** and links to the affected attempts. |

Preview text, images and audio initially. Unsupported types get a useful download
or open action. Missing or denied artifacts show that state explicitly.

The owner can **Accept result** or **Request revision** with feedback against the
displayed version. Routine evaluation remains with the accountable agent; it does
not create a mandatory human approval for every task. A new result version or
changed criteria invalidates a stale review submission. Editing criteria preserves
their history and does not silently turn an old result into accepted work.

**Cancel assignment and pause agent** identifies the work being abandoned, its
performing agent and descendant subtree, dependent work and retained results.
Submitting immediately stops the assignment and durably pauses that subtree.
Independent assignments remain recorded but paused, rather than being cancelled;
the agent is not automatically retired. Show stopping and unknown effects honestly,
and do not let a later cadence or answer remove the pause.

Link the agent's whole-purpose evaluation separately from this assignment's
acceptance. When whole-purpose completion is established with applicable
accountable acceptance and no unresolved obligations, the agent can initiate
framework retirement. Show the evidence and affected subtree without an extra
blanket owner approval. Uncertain relevance or commitments follow the existing
parent escalation chain; unresolved root questions appear in Inbox. Retirement
is a normal outcome, not a failure or a reason to invent further assignments.

## 9. Event history

Reach Activity/History from Monitor, an agent, an assignment or a decision. Use
one shared paginated table for all agent purposes, separate from the chat feed.
Support all-system, agent/subtree, project, assignment, time-range and event-type
filters as their underlying records become available.

Owner-selected activity presentation, 2026-09-07:

- Show newest recorded activity first, with a stable tie-breaker for equal times.
- Default to **20 rows per page**, with **20 / 50 / 100** in a **Rows per page**
  selector. One hundred is the maximum page size, not a history retention limit.
- Show **Previous**, **Next**, current page, and **Latest**. Disable unavailable
  directions based on actual data; do not invent a total page/event count.
- Use compact columns for time, event type, readable summary and related work/run.
  Show actor, target and outcome when recorded; otherwise identify missing details
  honestly. Expand a row for its recorded details and links, rather than rendering
  every tool result in full in the table. Narrow screens retain pagination and
  readable summaries with details on demand.
- Keep a loaded page stable as new events arrive. Show **New activity available**;
  selecting it or **Latest** loads the newest page. Do not silently shift rows,
  reset scroll, duplicate entries or skip older entries during navigation.
- Changing agent, filters or page size starts at the newest page in the new scope.
  Preserve the chosen page size while moving between agents. Delayed responses
  from a previous selection must not overwrite the current view.
- Preserve loading, empty, error and disconnected/last-known states. Provide a
  safe retry for a failed page request. Reading older history never starts work.

Pagination bounds both the displayed rows and the fetched history. The browser
must not download every event just to display the first twenty. The selected
agent and its live status stay visible independently of the current history page.

Every event shows time, actor, readable action, target, outcome and related
records. Include agent creation and lifecycle changes, cadence reviews and their
outcomes, work changes, artifacts, assignment acceptance, whole-purpose
evaluations, progress concerns, human decisions, and all agent-to-agent
communication. Cancellation links the abandoned work to the resulting subtree
pause. Retirement identifies its initiator and affected subtree, linking purpose
evaluation and acceptance where applicable. A request is distinct from observed
retirement. Expand an event for recorded details.

Message details show actual sender, recipient, content or linked artifact,
origin attribution, correlation to the exchange and observed delivery stages.
Follow related messages and escalation hops without manually searching logs.
Redactions, absent content, unknown delivery and gaps are labeled explicitly.
Routine events may be grouped but must remain inspectable. Paused and retired
agents' records are still available. This is history inspection, not replay.

## 10. Settings

Keep daily work separate from technical configuration. Reuse existing Hermes
settings where appropriate, with framework meanings made explicit.

| Section | Required controls |
| --- | --- |
| Owner and trusted channel | Identify the authenticated owner and the trusted web communication channel. Session/sign-out controls. Do not label an arbitrary integration as an owner channel. |
| Models and providers | Configure available providers/credentials and defaults; show availability and useful connection errors. Per-agent overrides live in Agent details. |
| Integrations and tools | Inspect configured connections, configure/disconnect them, and show which agents are affected. Connection existence and permission to use it are separate facts. |
| Skills | Inspect available skills and descriptions; assign/remove them for agents. Show provenance; loading a skill never expands authority by itself. |
| Agent defaults | Cadence, model, workspace and capability defaults for new agents. Clearly state that changing defaults does not silently rewrite existing agents. |

Use **Save** and **Cancel**, readable validation, unsaved-change protection and
explicit saved/effective states. Never echo stored secrets into messages or event
content. Show credential presence using masked indicators. Do not add billing,
multiple-owner administration or a separate infrastructure dashboard to v1.

## 11. Shared control dialogs and operation states

| Control | Exact experience |
| --- | --- |
| Pause agent and children | Begin interruption immediately, without a confirmation delay. Show **Stopping**, the affected subtree and any execution still stopping. Show **Paused** only when supported by observed state. Conversation and inspection stay available. |
| Resume agent and children | Show affected agents and outstanding independent pause causes according to the adopted policy. Show the recorded resume operation, then actual eligibility/execution; do not label everything working as soon as the button is pressed. |
| Edit purpose and rules | Show current and proposed soul, affected work and the consequence of saving. Label the submit action **Save and stop affected work**. Saving starts interruption immediately; show stopping and pending replanning distinctly. |
| Retire agent and children | For an owner action, confirm with the named agent, descendant count/tree and unfinished work. **Retire this agent and its children** ends the whole subtree's roles; history/results remain inspectable. Agent-initiated retirement follows purpose evaluation without a new blanket confirmation gate. Both show unconfirmed stopping honestly. |
| Replace agent | No ambiguous one-click action in v1. Show the old subtree that will retire and the selected context, artifacts and unfinished work for handoff. Use the approved lifecycle policy: immediate stopping, retained records and a distinct replacement identity. |

Show **Requested**, **In progress**, **Completed**, **Failed**, or **Outcome
unknown** as applicable to the operation, separately from agent/work status.
An interruption does not undo an already completed external action. Failed or
unknown operations retain their details and offer reconciliation/retry where safe.
Owner-directed changes from another trusted entry point must become visible in
these same views, not create a second competing version of state.

## 12. Shared usability and state requirements

Use readable text labels, restrained status colors, consistent spacing and one
obvious primary action per form. Optimize dense information in Monitor and a
calmer reading experience in Chat. No profession-specific visual branding is
required: a metal artist and a business agent use the same control center.

Every view distinguishes loading, genuinely empty, no filter matches, failure,
permission denied and disconnected/last known. Keep drafts during recoverable
errors. Provide **Retry**, **Clear filters** or configuration links appropriate to
the actual problem. Do not show an empty list as if failed loading succeeded.

On narrow screens collapse navigation and pickers into panels, and show detail
pages one at a time. Preserve selected identity, context, filters and drafts when
returning. All primary workflows need keyboard navigation, labeled fields, visible
focus, sensible dialog focus return and text equivalents for status colors.
Live updates must not steal focus or flood assistive announcements.

Closing the browser does not stop agents. A disconnected browser cannot confirm
that a command was applied. Reconnect refreshes current state, reconciles pending
operations and deduplicates messages and decisions.

## Build order and unresolved policy dependencies

The current delivery target is the [fantasy-writer milestone](14-first-writer-milestone.md):
one root using shared Chat, Work, Activity and Saved outputs before the complete
organization console. Following the first story demonstration, generalize its
work/result contract and show a nonwriter using the same controls before adding
further domain-specific behavior. [Shared-work delivery](../implementation/shared-agent-work.md)
sets the engineering sequence; full child supervision and the global Inbox retain
their existing delivery dependencies.

Build complete small workflows, following [continuous TDD](../first-builder/PRACTICES.md):

1. Create one root, retain its purpose, show its startup state and basic Monitor row.
2. Deliver continuing Chat, one real human request/answer and subtree pause for that root.
3. Show its plan, assignment, result and accountable evaluation.
4. Add children, recursive navigation, escalation and lifecycle scope.
5. Complete global Inbox, history, filters and progress-concern details.
6. Harden concurrent edits, obsolete answers, worker loss, reconnection and accessibility alongside the relevant features.

Use [UX-01–UX-20](11-ux-scenarios.md) as acceptance targets for those increments.
Do not build every screen as an empty shell and defer functional verification.

The [open decisions](07-open-decisions.md) still govern general resume handling,
timing and progress thresholds. Purpose-based lifespan evaluation, cancellation
with agent/subtree pause, purpose-change restart and replacement handoff follow
the approved [lifecycle rules](05-human-interaction.md#steering-active-work).
Do not invent these in frontend code. Parent permission
administration follows the approved [permission rules](05-human-interaction.md#applying-ownership-to-permissions).
Project-wide pause, automatic request expiry, reminder timing, graph editing and
history replay are not required controls for this first interface. Their absence
does not remove immediate agent/subtree interruption or the owner's authority.
