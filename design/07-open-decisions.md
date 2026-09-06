# Open product decisions

The product's central behavior is established: persistent purpose, independent
thinking cadence, structured work, skills, recursive delegation, proactive
questions, human steering, layered agent state, and subtree pause. Human ownership
of everything, agent responsibility for their subtrees, trusted owner channels,
and immediate work on creation are also established. Questions escalate through
parents to the human only if no agent can resolve them. Purpose changes and child
replacement stop affected active work immediately. The First Builder is intended
to run within the framework with this repository as its privileged workspace.

Detection of activity without progress, explicit evaluation of results, and a
unified human decision inbox are required capabilities. Their inclusion is
settled; detailed defaults can be specified during implementation design.

The following choices still need agreement. Recommendations are labeled as
proposals in the relevant documents. This list does not defer the established
behavior or introduce implementation choices.

| Decision | Question to settle | Current proposal |
| --- | --- | --- |
| Participation across projects | Can an agent work on unrelated projects concurrently, and who resolves competing priorities? | No default adopted. |
| Retained-work operations (AN-68) | What retention periods, export/deletion controls and deliberate transfers outside replacement should be supported? | Retain history/results/unfinished-work records; no automatic reassignment or erasure. Operational choices remain open separately from the accepted lifespan and cancellation rules. |
| Resume and project pause | How does subtree resume treat separately paused descendants? Does project pause stop only work belonging to that project? | Preserve separate descendant pauses; project pause scope remains open. |
| Timing and interruptions | Which events prompt immediate reconsideration? How are missed check-ins and reminders handled? | Answers and results can enable prompt reconsideration; redundant timer reviews can be combined without losing messages. |
| Capacity limits and progress detection settings | What existing resource controls apply, and what evidence and timing identify activity without progress? | Progress detection and review are required; exact thresholds and resource defaults remain open. |

The earlier writer milestone and subsequent Builder handoff use **AN-70** for
explicit local runtime limits, required before real managed admission. This now
includes the writer path; default values remain unapproved. Broad multi-agent
capacity and progress thresholds remain AN-67. Root timing choices in AN-66 also
remain open and move forward for the writer cadence. AN-65 governs the later descendant/project-pause extension; ordinary
authorized root resume must preserve its own pause causes and reconcile work.
Reprioritizing delivery does not adopt proposed defaults.

The meanings of pause, resume, cancel, retire, and replace are explained with
examples in [Human interaction](05-human-interaction.md). Their open questions
concern work and children after stopping, not whether stopping happens.

Retirement is settled: retiring an agent retires every descendant. They do not
automatically remain active or get reassigned.

## Resolved: autonomy and permissions

The owner approved AN-60, AN-61 and AN-62 in the decision discussion following the
Plane roadmap review: "Yes, this all sounds good." Approval applies to the three
presented defaults, not the remaining lifecycle or timing proposals above.

- **AN-60 — Next work:** clear authorized steps proceed; missing direction prompts
  clarification, and no apparent next step prompts a proposal. A proposal needs a
  response when direction or authority is missing, not merely because it was stated.
- **AN-61 — Permission policy:** ordinary root defaults support private work, Plane,
  public research and child creation within configured limits. Scoped standing permission or explicit
  approval is required for publication, spending, contacting people and deployment.
  Silence and timeouts never approve an action.
- **AN-62 — Parent administration:** a parent can select and narrow a subset of its
  own delegable permissions for a child. It cannot grant additional powers; the
  owner can mark permissions non-delegable.

Canonical behavior lives in [Human interaction](05-human-interaction.md#questions-proposals-and-permission)
and [Default capabilities](04-workspaces-and-skills.md#default-capabilities).
These are settled product rules; their enforcement still needs implementation.

## Resolved: purpose-based lifespan, cancellation and replacement

The owner's latest clarification replaces the earlier creation-time distinction
between ongoing specialists and bounded children. AN-64 now records this policy:

- Every root and child evaluates whether its purpose still requires work, using
  accepted results, continuing obligations, relevant changes and subtree commitments.
- Useful growth, recurring operations and legitimate waiting can all justify
  continuing. Clear whole-purpose fulfillment or established irrelevance permits
  self-retirement without pretending unmet criteria were accepted; uncertain
  relevance or outstanding obligations follow normal escalation and acceptance.
- Agents have no self-preservation objective. They must not create unnecessary work,
  resist authorized termination or change their soul to justify a lifecycle outcome.
- Cancelling an assignment stops that work and pauses its performing agent and
  descendants. Independent assignments remain recorded under the pause. Retirement
  is a separate evaluated or owner/parent-directed action.

The earlier “completed bounded child becomes idle” default is superseded. The
owner's marketing/sales example remains valid: continuing responsibility can lead
to new authorized initiatives without another parent prompt. Retention/export/
deletion and transfer outside replacement remain separately open above.

AN-63 remains accepted: purpose changes stop affected work immediately; reconcile
prior effects, then automatically replan when clear and not paused. Inform the
direct parent of human redirection without a veto. Replacement retires the old
child and its descendants, retains history, and gives a distinct new agent a
selected explicit handoff of context, artifacts and unfinished work.

Canonical behavior is in [purpose evaluation](01-agents.md#lifetime-and-work-assignment)
and [lifecycle control](05-human-interaction.md#steering-active-work). These decisions
do not approve general resume, project participation, wakeup timing, or capacity
and progress thresholds. Runtime enforcement remains implementation work.

## Optional scope to decide explicitly

The following capabilities are not required by the current core specification.
They must be deliberately accepted or excluded rather than assumed from an
example or an implementation choice.

| Capability | Product decision |
| --- | --- |
| Manual-only agents | Should an agent be configurable to act only when explicitly invoked, with no automatic thinking cadence? |
| Replay or branching of past work | Should a human be able to revisit a previous state or explore an alternative continuation, in addition to inspecting history and recovering interrupted work? |
| Multiple human communication channels | Must the same agent support several chat surfaces with coordinated context, or is one sufficient initially? |

Plane is the selected planning application; the default workflow and workspace
mapping are in [Project management](13-project-management.md). Its pinned release,
API integration and deployment validation belong to implementation design. The
remaining storage, messaging and model choices do not change product authority.
