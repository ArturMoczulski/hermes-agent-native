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
| Proposals for new direction | When does an agent wait for a reply to a proposal, and when may it proceed within existing authority? | Clear, already authorized next steps can proceed; the proposal boundary needs definition. |
| Approval policy | Which levels of involvement exist, and does any policy permit a timed opportunity to veto? | Required approval means explicit authorization; notification is separate. |
| Parent permission administration | Which capabilities and permissions may a parent grant or change without further human involvement? | The human has ultimate control; agents remain within the authority granted to them. |
| After a purpose change or replacement | When does new work start after the immediate stop, and what context and unfinished work are handed over? | Stop affected active work immediately; retain existing results and replan or hand over explicitly. |
| Cancelled or finished assignments and retained work | Does a child become idle or retire after a bounded assignment ends? How are records and unfinished work retained or deliberately transferred after retirement? | Parent retirement retires all descendants. Assignment completion is separate, and results are preserved. |
| Resume and project pause | How does subtree resume treat separately paused descendants? Does project pause stop only work belonging to that project? | Preserve separate descendant pauses; project pause scope remains open. |
| Timing and interruptions | Which events prompt immediate reconsideration? How are missed check-ins and reminders handled? | Answers and results can enable prompt reconsideration; redundant timer reviews can be combined without losing messages. |
| Capacity limits and progress detection settings | What existing resource controls apply, and what evidence and timing identify activity without progress? | Progress detection and review are required; exact thresholds and resource defaults remain open. |

The meanings of pause, resume, cancel, retire, and replace are explained with
examples in [Human interaction](05-human-interaction.md). Their open questions
concern work and children after stopping, not whether stopping happens.

Retirement is settled: retiring an agent retires every descendant. They do not
automatically remain active or get reassigned.

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
