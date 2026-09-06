# Human interaction and authority

## Conversation in both directions

The human can address any agent, including a descendant, to ask for status,
provide information, discuss results, change direction, or interrupt work.
Each agent is clearly identifiable in conversation.

Agents can proactively report progress and results. Questions arising from
confusion, uncertainty, or a blocker follow the escalation route below. The
human can still initiate conversation with any descendant directly.

## Questions move up the parent chain

When an agent cannot decide what to do, it consults its direct parent. That
parent decides whether it can answer within its authority. If it cannot, it
escalates to its own parent. This repeats until an agent can resolve the question
or the question reaches a root. A root that cannot resolve it asks the human.
A parentless agent asks the human directly when owner input is needed.

Children do not bypass this chain for their own unresolved questions. Human
input to any agent remains authoritative regardless of where it enters the tree.
An agent relaying an answer preserves who supplied it; forwarding does not turn
an agent answer into a human instruction.

The pending question identifies the originating agent, affected work, and who
is currently expected to answer. Its resolution returns to the affected work
without requiring the human to relay messages manually. Questions and answers
survive inactivity and restart. If a parent is unavailable, the question remains
visibly blocked; automatic recovery or reassignment is a lifecycle decision,
not implicit permission to skip the chain.

## Trusted human-owner and agent communication

The framework designates trusted communication channels for the human owner.
Messages recognized as coming from that owner carry the highest authority over
all agents, their purposes, rules, permissions, and work. A parent cannot veto
owner direction to a descendant. The human can revise earlier restrictions or
change any agent's soul, including a root's.

Agents communicate through a separate designated agent-to-agent path that
identifies the sending agent. The framework must distinguish owner communication
from agent communication by trusted origin, not by wording, a display name, or
an agent's claim that “the human said so.” This is a product trust boundary,
not a prescription for a particular chat application or transport.

Quoting or forwarding an owner's words does not by itself give an agent message
owner authority. The original owner instruction must remain independently
attributable if it is relied upon as authorization. Skills, work artifacts, and
other encountered text are not trusted owner channels.

Human input takes precedence over agent plans and conflicting agent instructions.
The agent still identifies what the owner actually requested: a narrow instruction
is not permission for unrelated work. Ambiguous directions can require
clarification; the owner must not need an agent's consent to exercise control.

## Questions, proposals, and permission

These interactions have different meanings:

| Interaction | Example | What it provides |
| --- | --- | --- |
| Clarification | “Which audience should this album be aimed at?” | Missing information |
| Proposal | “The next useful step would be a live recording.” | A suggested direction for consideration |
| Permission request | “May I publish these tracks?” | Authorization for a particular action |
| Progress report | “The compositions are ready; recording is underway.” | Visibility into work |

An answer to a question does not automatically authorize every action related
to it. An agent can independently take clear next steps already within its
purpose and permissions. Whether a new-direction proposal requires a reply
is an [open decision](07-open-decisions.md).

**Proposed:** a required approval waits for explicit authorization. Silence leaves
the request pending; denial leads to replanning or continued waiting. Requests
identify the action and scope so the same answer is not reused as permission for
an unrelated action. Notification alone does not count as approval.

Permission policies must support different levels of human involvement and
different rules for different actions or milestones. Their exact labels and
defaults remain open. The framework enforces applicable restrictions independently
of whether the agent remembers to mention them in its reasoning.

## Unified human decision inbox

The human owner has one inbox for questions, decisions, and approval requests
that require their input across all root agents. It aggregates requests that
reach the human through the established escalation chain; it does not give
children a way to bypass their parents.

Each item identifies the originating agent, escalation path, affected work,
question or proposed action, relevant context, and recommended response when
available. It shows what is blocked, what can continue, and any known urgency.
The human can inspect the supporting conversation and artifacts without asking
agents to reconstruct them.

A response in the designated trusted owner inbox resolves the corresponding
request and reaches the affected work through the recorded communication flow.
An unanswered item remains pending across inactivity and restart. Repeated
check-ins do not create duplicate items for the same unresolved request.

Pending, answered, denied, and no-longer-applicable requests remain
distinguishable. If a purpose change, replacement, or retirement makes a request
obsolete, that is visible; an old answer must not silently authorize a different
or obsolete action. An inbox response enables appropriate reconsideration of
work but does not override an existing pause or retirement unless the human
actually directs that change.

The inbox is a product capability, not a requirement for a particular application
or visual layout. It complements the human's ability to talk to any agent.

## Steering active work

Giving context, changing direction, pausing, and cancelling are distinct actions.
Receiving a chat message does not inherently cancel work. The agent should
acknowledge material direction and make clear how it affects the current plan.

The human can steer a project or revise an agent's fundamental purpose. The
framework distinguishes those requests and applies an explicit owner-directed
soul change when requested. An agent cannot use ordinary planning as a pretext
for changing its own soul.

When the human changes an agent's purpose, or a parent replaces a child, the
affected active work stops immediately. Stop does not wait for another check-in
or allow the obsolete assignment to run to its normal completion. The affected
agent must not continue issuing actions under the old purpose or assignment.
Dependent descendant work carrying out that assignment must also stop; unrelated
work in other responsibility areas is not implicitly cancelled.

The framework initiates interruption immediately and makes any action that has
not yet stopped visible. Already completed effects are not undone by calling
this a stop. A revised agent replans against the new purpose; a replacement
receives an explicit handoff rather than continuing the old worker unnoticed.
Exactly when new work starts after that interruption remains to be specified.

**Proposed:** the responsible parent is informed when direct human direction
changes delegated work, so it does not rely on the old plan. This notification
is not a request for the parent's permission to obey the human.

## Pause and continuation

Pausing an agent pauses its entire descendant subtree by default. Scheduled
check-ins must not restart paused work. Paused agents remain addressable and
their state remains inspectable; a pause must not erase unanswered questions or
unfinished work.

The framework must acknowledge the pause and identify any work that is still
stopping. It must not imply that interruption reverses already completed actions.

**Proposed:** resuming a subtree first rechecks pending instructions, results,
and dependencies. It does not blindly repeat interrupted work, and descendants
that were separately paused remain paused. Cancellation is distinct from pause.
Retirement follows the subtree rule below.

## Retirement

Retiring an agent ends its ongoing role and retires all its descendants,
recursively. Children do not remain active or get reassigned automatically when
their parent retires. Retired agents cease autonomous work; later scheduled
check-ins do not reactivate them. This is distinct from a temporary pause.

Retirement must not silently discard results or the record of unfinished work.
Retention of those records and any later deliberate transfer of unfinished work
remain separate decisions; they do not keep the retired subtree active.

## Observing the system

The human can inspect current agent activity, thinking cadence, last work, and
system-wide history without asking each agent to produce a report. The
[observability specification](09-observability.md) defines these views and the
record of actions, decisions, approvals, and failures that supports them.

## Applying ownership to permissions

[Agent ownership](01-agents.md) defines who can change an agent. An agent cannot
use child creation, skills, or editable practices to bypass a restriction, or
delegate more authority than it is allowed to grant. Which permissions a parent
may change without additional human involvement remains an open decision.

## Terms for ending or continuing work

These terms describe distinct user intentions. They are not a requirement to
expose separate commands with these names.

| Term | Plain meaning | Example | What is settled or still open |
| --- | --- | --- | --- |
| Pause | Stop working for now, keeping the possibility of continuing. | “Put composition on hold while I review the direction.” | Agent pause includes its subtree; questions and work are retained. |
| Resume | Let paused work continue. | “You can continue composing now.” | Recheck new direction first; handling children separately paused beforehand is still proposed. |
| Cancel an assignment | Abandon this piece of work rather than resume it later. | “We are dropping this song.” | Whether a child assigned only to that song becomes idle or is retired needs agreement. |
| Retire an agent | End its ongoing role, rather than temporarily pause it. | “We no longer need a dedicated artwork agent.” | All descendants retire as well. Handling retained records and unfinished work remains to be specified. |
| Replace an agent | Put a new agent in charge of an existing responsibility. | “Use a new producer for this album.” | The old active work stops immediately; handoff and disposition of its children need agreement. |

These remaining choices concern what happens after work stops. They do not
weaken immediate interruption on purpose changes or replacement.
