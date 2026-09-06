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

An agent independently takes clear next steps within its purpose and permissions.
It asks through the parent chain when material direction is missing, and proposes
a useful direction when no next step is apparent. A proposal waits for a reply
when choosing it requires missing direction or additional authority. Describing
an already authorized next step does not create a new approval gate.

The owner can grant standing permission for a class of actions within explicit
scope and limits, or approve a particular action. Publishing, spending, contacting
people and deployment require one of those permissions. Actions within a standing
permission can proceed without asking again for each occurrence. For example,
permission to publish finished tracks to a specified account applies to that
publication activity; it does not authorize spending on promotion. These external
action permissions do not add an approval step for the framework's trusted owner
conversation or already permitted agent-to-agent communication.

When required permission is absent, the action waits for explicit authorization.
Silence, elapsed time and notification do not grant approval. Requests identify
the action and scope; an answer to a clarification does not authorize unrelated
actions. Denial leads to replanning or continued waiting. Other clear, permitted
work can proceed independently.

The framework enforces the current permissions and applicable fundamental rules
at the operation that causes the effect, independently of the agent's reasoning.
The owner can change or withdraw permissions. A standing permission cannot be
reused outside its scope or after it no longer applies. The initial capability
template is specified in [Workspaces and skills](04-workspaces-and-skills.md#default-capabilities).

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
this a stop. It checks the outcomes of prior actions before starting conflicting
new work; an uncertain previous effect remains visible and blocks conflicting
actions until reconciled.

After that reconciliation, an agent with a changed purpose automatically replans
and starts clear authorized work under the new purpose when it is not paused.
Missing direction or permission follows the normal clarification route. A purpose
edit does not remove a pause or require a second human "start" message once the
agent is otherwise eligible. This specific rule does not settle the remaining
subtree-resume policy.

Replacing a child retires the old child and all its descendants. Their identity,
history, artifacts and unfinished-work records remain available. The replacement
has a new identity and receives an explicit parent-selected handoff of relevant
context, artifacts and unfinished assignments; it is not the old worker continuing
unnoticed. Descendants are not automatically reparented and private memory is not
copied wholesale. Handover remains within the recipient's authorized access.

The direct parent is informed when human direction changes delegated work so it
does not rely on the old plan. This notification never gives the parent a veto
or delays obeying the human.

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

Retirement preserves results, history and the record of unfinished work without
keeping the retired subtree active. Replacement uses the explicit selected
handoff described above. No automatic reassignment or erasure occurs. General
retention periods, export/deletion and transfer outside that replacement workflow
remain separate operational choices.

## Observing the system

The human can inspect current agent activity, thinking cadence, last work, and
system-wide history without asking each agent to produce a report. The
[observability specification](09-observability.md) defines these views and the
record of actions, decisions, approvals, and failures that supports them.

## Applying ownership to permissions

[Agent ownership](01-agents.md) defines who can change an agent. A parent can
give a child a selected subset of its own delegable permissions and can narrow
that subset. It cannot grant powers it does not hold or is not allowed to delegate.
The owner can mark particular permissions non-delegable. Additional authority
follows the parent escalation chain to the owner where necessary.

Authorized child creation and delegation within these limits do not require
human approval for every child. Child creation, skills and editable practices
cannot bypass restrictions. Permission administration does not change soul
ownership: no agent can edit its own soul or a root's soul, and the human remains
the ultimate owner of every agent.

## Terms for ending or continuing work

These terms describe distinct user intentions. They are not a requirement to
expose separate commands with these names.

| Term | Plain meaning | Example | What is settled or still open |
| --- | --- | --- | --- |
| Pause | Stop working for now, keeping the possibility of continuing. | “Put composition on hold while I review the direction.” | Agent pause includes its subtree; questions and work are retained. |
| Resume | Let paused work continue. | “You can continue composing now.” | Recheck new direction first; handling children separately paused beforehand is still proposed. |
| Cancel an assignment | Abandon this piece of work rather than resume it later. | “We are dropping this song.” | Cancellation of a bounded assignment still needs a disposition decision; finishing an assignment follows the role-duration rule. |
| Retire an agent | End its ongoing role, rather than temporarily pause it. | “We no longer need a dedicated artwork agent.” | All descendants retire; retain history, results and unfinished-work records without automatic reassignment. |
| Replace an agent | Put a new agent in charge of an existing responsibility. | “Use a new producer for this album.” | Stop and retire the old subtree; preserve its records and create a distinct replacement with a selected explicit handoff. |

These remaining choices concern what happens after work stops. They do not
weaken immediate interruption on purpose changes or replacement.
