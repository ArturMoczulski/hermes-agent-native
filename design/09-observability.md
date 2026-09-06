# Observability

The framework provides a way for the human owner to observe the whole system:
what is happening now, what happened previously, and why an agent is active or
inactive. Observation must not require asking every agent to write a status
report. The framework's own activity records support these views.

This is a product requirement. It does not prescribe a dashboard technology,
monitoring service, storage format, or interface layout.

## System overview

The human can see all agents and their parent–child relationships, including
paused and retired agents. The overview identifies which agents are working,
thinking, waiting, blocked, paused, retired, or experiencing a failure. These
are meaningful distinctions rather than mandatory labels or mutually exclusive
states: an agent can have active work and another blocked assignment.

The human can narrow the view to an agent, subtree, project, time period, or
kind of event, and move from an overview to the work and events behind it.
Activity in a child must not be confused with the parent's own activity.
An idle coordinator with busy children should be distinguishable from an
entirely idle subtree.

## Each agent's current state

For any agent, the human can inspect:

| Information | What it should explain |
| --- | --- |
| Identity and responsibility | Which agent this is, its parent, purpose, and children. |
| Current work | The project and assignment it is advancing, the current action or stage, when it started, and available progress or results. |
| Delegated work | What its children are doing, who owns each assignment, and what results it is waiting for. |
| Purpose evaluation | Latest review of whether the agent is still needed: accepted outcomes, remaining obligations, useful growth, recurring delivery or monitoring, relevant evidence, uncertainty, and the decision to continue, wait, clarify, pause or retire. |
| Last activity | When it last checked in, performed work, and completed work; these are distinct facts. An agent that has never worked is identified as such. |
| Thinking cadence | Its configured cadence, most recent check-in, and next scheduled check-in when applicable. |
| Reason for inactivity | Whether it has no useful next action, is waiting for an answer or result, is paused, is retired, or has failed. |
| Conditions for continuation | What answer, event, scheduled check-in, or owner action would allow it to proceed. |
| Pending questions | What is being asked, which work depends on it, and where the question is in the parent escalation chain. |

A check-in that decides to wait must not appear as completed project work.
Cadence changes and suspended schedules must be visible. Paused or retired
agents must not appear to have an ordinary upcoming work activation.

Accepting an assignment is distinct from fulfilling the agent's whole purpose.
Show why recurring operations or monitoring remain necessary even when no action
is due now. Retirement records identify the initiator and affected subtree and
link the purpose evaluation and accountable acceptance where applicable;
a self-assessment is distinguishable
from the framework completing retirement. Agent survival or activity volume is
not a measure of success.

## Events across the system

The framework tracks all system events it observes and produces, including:

- Agent creation, parent relationships, changes of purpose or permissions,
  replacement, pause, continuation, and retirement.
- Scheduled check-ins, other activations, their causes, and their recorded
  decisions or outcomes.
- Work creation, assignment, progress, completion, cancellation, and failure.
- Concerns about activity without progress, their supporting evidence, and the
  response to review; explicit result evaluations and acceptance outcomes.
- Purpose evaluations, remaining obligations, continued relevance, retirement
  decisions and related escalation. Cancellation records link the abandoned
  assignment to the resulting agent/subtree pause and retained independent work.
- Delegation, child results, questions, escalation, and answers.
- Human-owner and agent messages, keeping their origins distinguishable.
- Permission requests, approvals, denials, and actions taken under them, including
  the lifecycle of requests in the unified human decision inbox.
- Model and tool activity, external work started through the framework, known
  outcomes, interruptions, and recovery attempts.

Each event identifies what happened, when, the relevant agent or system
component, related work, and its known outcome. Related events can be followed
as a sequence: for example, a child asks a question, two parents escalate it,
the human answers, and the original work continues.

The activity record includes failures and unsuccessful actions, not just an
agent's summary of accomplishments. Event content must not expose credentials
or secrets; any omitted or redacted content is identified as such.

## Agent communication is event history

All agent-to-agent communication through the framework is recorded as events,
including parent–child messages, sibling messages, and permitted communication
between trees. This includes work requests, progress updates, results, questions,
escalations, answers, and control messages. Recording does not depend on an
agent voluntarily summarizing the conversation afterward.

The human can inspect the sender, intended recipient, time, message content or
referenced artifact, related work, and the request or conversation being answered.
The record preserves agent origin even when a message quotes human instructions.
The same content-access and redaction rules as other system events apply.

Sending, delivery, handling, and replying are distinct observations. Record each
when known, along with delivery failures or repeated attempts. A sent message
must not be presented as received or acted upon without evidence. An unknown
state remains visibly unknown.

The human can follow a conversation across multiple agents and relate it to the
work it caused. If a question is escalated through several parents, the full
route and returning answer remain inspectable rather than appearing as unrelated
messages or losing the original sender.

## History, freshness, and uncertainty

The human can review the history behind the current state, including the
direction and authorization associated with significant actions. History
survives inactivity and restart. Updating a plan or summarizing memory must not
silently erase the evidence needed to understand earlier behavior.

Views distinguish current observations from the last known state and show when
information was last updated. If an agent becomes unreachable or an action's
outcome is uncertain, the system must show that uncertainty rather than report
successful completion or a confidently current status.

Observability covers recorded activity, available outputs, and decision
summaries. It must not invent progress, explanations, or activity that the
framework cannot observe. External work with limited visibility is shown with
its last known progress and available evidence.

The human owner can inspect the whole system. Agent access to these views
follows granted permissions; observation does not create a new way for an agent
to read another agent's private context. Retention periods, export formats, and
notification defaults remain separate design decisions.
