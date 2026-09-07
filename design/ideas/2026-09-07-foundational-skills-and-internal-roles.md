# Foundational skills and parallel internal roles

Date: 2026-09-07. Source: the human owner's brainstorming conversation.
Status: **Loose idea, not adopted. No implementation requested.**

## A common foundation, with specialization on top

Almost every agent may need a common foundation of skills, regardless of its
profession or purpose. Plane project management is the owner's concrete example:
agents generally need to organize tasks, plan work and keep progress legible.
Other agents need additional specialized skills and access to specialized tools
for their particular work.

The idea is to distinguish a reusable foundation from purpose-specific additions,
instead of assembling every agent entirely from scratch. The exact shared set,
exceptions and way to obtain specialized skills remain open. A skill teaches a
method; actual tools and permissions remain separate, as in
[Workspaces and skills](../04-workspaces-and-skills.md#loadable-skills).

## The same pattern might apply to internal roles

An autonomous agent may also benefit from a reusable set of parallel roles or
workflows. One part performs the work while other parts remain responsive or
review what is happening. The owner's examples are:

- **Communication:** remain available to receive conversations, new information,
  instructions and other agents' messages while work continues.
- **Execution:** carry out the current work and pursue the agent's purpose.
- **Review:** periodically compare progress and results with expectations and
  acceptance criteria, deciding whether work is complete or still needed.

Many agents could share these roles, then add specialized roles for their domain.
This extends the foundational-versus-specialized idea from skills to the
organization of the agent itself. A reviewer might consider both the current
assignment and whether continuing responsibility still justifies more work;
finishing one task need not finish an ongoing purpose.

“Thread” here means an independently progressing activity, not a decision about
operating-system threads or a requirement for an always-running model call.
These roles might be internal sessions or workflows, child agents, framework
processes, or a combination. A child-agent implementation is one possibility,
not a requirement that every agent automatically spawn the same children.

## A more speculative example: a subconscious signal source

The owner used a human-mind analogy to explore how far this organization might go.
In that analogy, a conscious, interpreting process encounters internal feelings
that it did not deliberately choose. It receives those experiences and forms
interpretations or explanations afterward. This is an architectural inspiration,
not an established psychological model or a claim about machine experience.

A hypothetical agent version could contain a separate internal process that
produces signals independently of the main reasoning process. The main process
would handle inputs from both the outside world and inside the system. It might
receive a signal without direct access to the producer's internal state, without
knowing exactly how the signal arose, and without a direct way to question or
control that producer.

In the strongest version of the analogy, communication is asymmetric or one-way:
the internal process can inject a feeling-like or sensory-like signal, while the
main process can only receive it and decide what it means or how to respond. The
main process might be largely unaware that a child-like process produced it.
This is a possible way to explore a “subconscious” in a hypothetical human-like
agent, rather than treating all inputs as ordinary two-way conversations.

The owner is **unsure whether such one-way or partly hidden relationships are
desirable** in this framework. Preserve the example for exploration; it does not
request emotional simulation, hidden children, consciousness, or a runtime change.

## Questions for a future exploration

- Which skills and internal roles are common enough to supply by default, and
  which should an agent add only when its purpose needs them?
- When is a role another session of the same agent, and when does it need its own
  child identity, purpose, permissions, memory and lifecycle?
- How would concurrent communication, execution and review coordinate shared
  state and competing conclusions without duplicating work or creating an
  indefinitely expanding tree of helper agents?
- What could an internal signal contain, and how would the receiver distinguish
  a signal or suggestion from evidence, an instruction or an authorized decision?
- Could a recipient have limited insight into a signal's producer while the human
  owner and framework retain its origin and history? One-way communication need
  not mean untraceable communication.
- If the producer were an actual child, how would limited parent visibility fit
  parent accountability, interruption, subtree pause and retirement?

## Relationship to the current specification

The current design already requires [receiving inputs during work](../02-independent-work.md#events-and-continuity)
and [explicit evaluation](../03-projects-and-delegation.md#explicit-evaluation-of-results).
A separate reviewer agent is optional; the accountable parent retains responsibility.
The proposal above explores how those responsibilities could be organized.

Any later adoption must explicitly address the existing
[protected agent layers](../01-agents.md#four-layers) and
[observable, attributable communication](../09-observability.md#agent-communication-is-event-history).
Internal signals would not silently acquire human authority or permission to
rewrite the soul. These are connections to revisit, not decisions settling the
open questions in this note.
