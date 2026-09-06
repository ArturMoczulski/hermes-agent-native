# User experience: the agent console

Status: **UX design for review**, 2026-09-05. Chat, monitoring and human decisions
are established requirements. The navigation, layouts and interaction defaults
below are the proposed first experience; they do not settle the separate
[open product decisions](07-open-decisions.md). No screen is claimed implemented.

Behavioral authority remains in [Agents](01-agents.md),
[Human interaction](05-human-interaction.md), [Work and delegation](03-projects-and-delegation.md),
and [Observability](09-observability.md). This document explains how the human
experiences those rules. Technology and reuse belong in
[UI implementation](../implementation/user-interface.md).

The [screen-by-screen specification](12-control-center-screens.md) gives the
concrete build brief: fields, controls, panels, navigation and operation states.
Use it instead of the incomplete Figma exploration; visual mockups are not needed.

## What the human should be able to do

Create an agent from a purpose, have an ongoing conversation with it, see what
it and its descendants are doing, answer requests, inspect results, and redirect
or stop work. Monitoring must be useful without asking agents to narrate status.
The interface must be understandable without knowing profiles, model sessions,
worker processes or event transport details.

## Navigation and context

| View | Primary question | Main content |
| --- | --- | --- |
| Chat | What do I want to discuss with this agent? | Agent picker, continuing conversation, current-work summary, optional details. |
| Monitor | What is happening across my agents? | Searchable agent tree/list, activity, work, blockers, cadence and freshness. |
| Inbox | What needs my decision? | Pending human requests with context, response controls and resolution history. |
| Work | What are we trying to achieve and what are the results? | Projects, assignments, dependencies, artifacts and evaluations. |

Settings is a secondary destination for owner configuration, models, integrations
and defaults. Detailed logs and events open from an agent or work item rather
than competing with the primary navigation. Inbox has a persistent pending count.
The initial empty installation offers Create agent; returning users can reopen
their last view. An explicit link to a particular agent or request takes priority.

Use stable agent identity for selection and links. Names may repeat: show the
parent path and a short identifier when needed. Switching Chat/Monitor/Work
preserves the selected agent or subtree scope. A global Inbox remains global;
an agent filter is explicit and removable. Back navigation restores context.
Opening a view never creates an agent, changes ownership or starts work.

## Creating an agent

1. Choose Create agent and describe its purpose. A suggested editable display
   name is enough; no task backlog or technical manifest is required.
2. Show the intended parent (none for a root), the configured thinking cadence,
   and a concise summary of available capabilities. Advanced settings expose
   model, skills and permissions without making them mandatory form fields.
3. Submit once. Show creation pending until the system accepts it; retain the
   draft on failure and prevent a repeated click/retry from creating duplicates.
4. Open the new agent's conversation. Show its purpose and actual startup state,
   such as queued or planning. Do not invent a greeting or show it working before
   execution is observed. Creation initiates the first work review immediately.
5. The agent performs discovery and plans work, asking a focused question if
   needed. The human can inspect the plan in Work while independent work continues.

Capability defaults are owner-configured; describing a purpose does not grant
new permissions. Child creation always makes the parent explicit. The same agent
appears in Chat and Monitor once created, including children created by agents.

## Chat view

Conceptual layout, not a fixed visual style:

```text
Chat | Monitor | Inbox (2) | Work                         Settings
Agent search      Composer / Metal Artist       [Pause agent & children]
Agent list        Purpose and current-work summary       [Details]
                  Continuing conversation
                  Results and decision cards
                  [Message Composer ...] [Send]
```

The picker includes roots and descendants, search, readable parent context,
unread conversation indicators and compact activity labels. Selecting an agent
opens its continuing human conversation. That conversation belongs to the agent
identity; execution sessions, context compression and restarts are internal.
Do not equate a continuing conversation with an unlimited model context window.

The header identifies who receives the message and links to purpose, parent,
current work and lifecycle controls. Details reveal assignments, children, cadence
and related events on demand. Keep the conversation usable when details are closed.
Switching agents preserves each draft and does not send it to the next selection.

Human messages, agent replies, system observations and forwarded agent messages
have distinct origins. Use durable structured attribution; text claiming to be
from the owner is not proof. Link artifacts and decision cards to their underlying
records. Routine tool details are expandable; meaningful progress, results and
questions stay readable. An activity summary is a recorded observation or agent
report, not a fabricated explanation or private reasoning transcript.

Sending a message while work is active does not implicitly stop it. Show accepted,
awaiting handling, handled or failed only when supported by delivery observations.
An explicit acknowledgement of changed direction is separate from receipt.
Retry uses the same message identity; preserve unsent text on failure. An uncertain
send after disconnection is reconciled rather than blindly sent again.

New activity does not steal scroll position while the human reads older messages.
Offer a new-messages indicator. Inactive conversations retain unread indicators;
routine tool events do not each create an unread human-conversation notification.
Proactive questions appear as linked decision cards and in Inbox only when routed
to the human. A child question still waiting at its parent is not a human request.

## Monitor view

Start with an expandable tree table, with a flat list option and filters for root,
subtree, project, activity and attention needed. Keep the tree's order stable as
updates arrive; explicitly selected sorts may reorder the flat list. Filtered tree
results preserve ancestor context and show that rows are hidden. Parentage is a
responsibility relationship, not a drag-and-drop folder organization operation.

| Column/detail | What it conveys |
| --- | --- |
| Agent | Name, parentage and durable identity. |
| Own activity | Planning, performing work, waiting, idle, stopping, or a known failure. |
| Current work | Assignment and current observed stage; show additional active/blocked work in details. |
| Children | Separate count/summary of active, waiting or blocked descendants. |
| Cadence | Configured interval, last check-in, next eligible review or a suspension reason. |
| Last work | Last actual work activity; distinguish never worked and last completion in details. |
| Freshness | Last observation and stale/unknown indication when current state cannot be established. |

Lifecycle, execution and dependencies are separate facts. A coordinator can be
idle with busy children, or working on one branch while another is blocked.
Do not compress that into one misleading red/green dot. A scheduled check-in that
chooses to wait is not completed project work. No made-up percentage progress:
show criteria, stage and evidence unless a meaningful measured total exists.

Example: Metal Artist is waiting for compositions, Composer is arranging a song,
Researcher is gathering references, and Producer is waiting on an arrangement.
The artist row shows no own execution and active descendants; it is not presented
as an entirely idle organization or as personally running the children's tools.

Selecting a row opens an inspector with Chat, Work and History links. History
supports agent/subtree/project/time/event filters and follows related messages,
escalation hops, actions and outcomes. Show sender, recipient, content or artifact,
time and known delivery state. Mark redactions, failures and gaps explicitly.

Paused and retired agents remain inspectable through explicit filters. Hiding a
row is presentation only and never stops work. Unreachable is not retired or done.
A node graph is optional later; arbitrary-depth trees, keyboard expansion and
search must already work without needing a graph canvas.

## Inbox view

Use one queue for clarification, direction proposals needing a decision, and
approval requests across roots. Distinguish pending, answered, denied and obsolete.
Allow filters and history; default to pending, with declared urgency and age
visible. Do not infer urgency simply because an agent repeatedly posts updates.

Each item shows the originating agent, responsible root, escalation route,
affected assignment, request, suggested answer if available, supporting artifacts,
what is blocked and what may continue. Open related chat without losing the item.
Use the same request identity when showing a card in Chat or Work.

Clarifications support free text and optional suggested answers. Required approvals
show the exact action and scope with explicit approve/decline controls. Merely
opening or dismissing an item is not a response. Do not add approval by timeout.
If the same request changes or is resolved in another tab, refresh its applicability
before accepting a response. Record an obsolete response without authorizing work.

After submission, show the recorded response and its delivery state; do not claim
work resumed merely because the response was accepted. A paused agent stays paused
unless the owner separately directs resumption. Repeated check-ins update an
existing request rather than producing duplicate items. Children use the established
parent escalation chain; opening an inbox does not change that route.

## Work and results

Provide project and assignment lists and a board where useful. Each item has a
purpose/outcome, coordinator, implementer, criteria, dependencies, status and
evidence. Project grouping does not redefine the agent tree or confer authority.
Show a useful plan even if some branches are waiting for answers.

An assignment detail links its conversation, relevant agents, attempts, decisions,
artifacts and evaluation. Distinguish producing a result, submitting it for review,
accepting it, and requesting revision. Preserve prior attempts and criteria history.
The accountable evaluator follows the delegation rules; do not send every routine
result to the human. An explicit human decision can be made from the same record.

Preview supported artifacts; provide a usable download/open action when preview is
unavailable. Start with common text, image and audio results so the interface is
not coding-only. Show unavailable or access-denied artifacts honestly. A progress
concern links the repetition evidence and the responsible agent's response; it is
not a red failure badge based only on elapsed waiting time.

## Control and editing

Use explicit labels that identify scope. Avoid one ambiguous Stop button that
sometimes cancels a task and sometimes retires an organization.

| Control | Interaction |
| --- | --- |
| Pause agent and children | Acts immediately; show stopping until affected execution is known to end. Keep conversation/inspection available. Do not insert a confirmation delay. |
| Resume agent and children | Show remaining independent pause causes according to the adopted resume policy; reconsider pending direction before execution. |
| Cancel assignment | Identify the assignment and dependent work being cancelled, keeping independent assignments distinct. |
| Edit purpose | Show current/proposed purpose and affected work; Save applies the explicit owner change and starts interruption immediately. Do not silently edit purpose from routine discussion. |
| Retire agent and children | Preview the subtree and preserve records. Confirm this deliberate retirement operation; it is separate from immediate pause. |

Do not report stopped while external work is still stopping or uncertain. Identify
the unresolved action and conflicting work that cannot proceed. Purpose changes,
replacement and stale decisions use the existing lifecycle rules, including the
open handoff details in the product specification. Show operation failures rather
than optimistically leaving a false completed state on screen.

## Usability and failure states

On a narrow screen, show one main view with pickers/details in dismissible panels.
Keep the selected agent and scope visible near the composer and control actions.
All primary flows work with keyboard navigation, labeled inputs, sensible focus
return and text status labels; color alone is insufficient. Streaming updates
must not repeatedly steal focus or overwhelm assistive announcements.

Distinguish loading, empty, filtered-empty, unavailable and permission-denied states.
A disconnected client keeps cached information labeled last known; it cannot
confirm a stop, grant or response. Reconnection refreshes authoritative state and
deduplicates updates. Persisted conversations and tasks survive closing the client;
their agents continue according to lifecycle and authority, not page visibility.

Creation defaults, permissions, reminder timing, project pause and resume semantics
remain governed by [open decisions](07-open-decisions.md). This UX does not settle
them through an implicit button behavior. Multiple owner channels, group-chat rooms,
historical replay, a graph canvas and native clients are outside this first UX.
