# Agents and their layers

## Persistent identity

An agent is a persistent entity with a name, a purpose, accumulated experience,
working practices, capabilities, and current work. It remains the same agent when
it finishes an action, waits for an answer, or resumes after an interruption.

A root agent has no parent. A child has one parent and can have children of its
own. These relationships form trees without cycles or a fixed depth limit.
Agents must remain distinguishable even when different parents give children
the same name.

## Ownership and responsibility

The human owner is the ultimate authority over the framework and every agent.
A root agent is owned by the human and has no agent owner above it. A child has both the human owner and its direct parent as its agent owner;
the parent acts under the human's ultimate authority. Each agent's area of
responsibility includes itself and all its descendants, within its granted
agent authority. The human's authority covers all such areas.

The human can change any agent's purpose, fundamental rules, operating
permissions, or other state. Human authority is recognized through designated
trusted owner communication channels, not a claim made in message text.

## Four layers

| Layer | Contents | Change rule |
| --- | --- | --- |
| Soul | Why the agent exists: purpose, motivation, and fundamental behavioral rules | The human owner can change any soul. An agent cannot change its own soul; its direct parent can change it within the parent's authority. No agent can change a root's soul. |
| Working practices | Conventions, methods, preferences for carrying out work, and lessons about effective approaches | The agent can develop these within its soul and granted authority. |
| Memory | Learned facts, experience, decisions, and relevant context | The agent can maintain and refine its understanding. |
| Runtime state | Active work, progress, dependencies, pending questions, and results | Changes as work proceeds. |

An artist's soul might say that it exists to develop a metal music career and
must obtain permission before public release. Its practices might describe how
it evaluates a composition. Its memory might contain feedback on earlier songs.
Its runtime state might say that a recording is underway and artwork is waiting
for a decision.

The layers are distinctions in meaning and ownership. They do not require a
particular number of files or a particular storage format.

## Ownership is enforced

An agent may read its soul but cannot overwrite it, replace it indirectly, or
use editable practices or memory to contradict it. Writing “release automatically”
into a work note does not override a fundamental rule requiring release approval.
Loading a skill does not change that boundary either.

A parent's permission to change a child's soul does not give the child permission
to change its own soul. A grandparent or project coordinator does not automatically
gain the direct parent's ownership rights. Changes must follow the parent
relationship and applicable authority.

Root souls are defined at creation and protected from modification by agents.
They are editable by the human owner. Likewise, a human can revise a child's soul
without needing permission from its parent. The framework must distinguish an
owner-directed change from an agent attempting to rewrite its own purpose.
Understanding or interpreting a purpose during work does not itself authorize
an agent to change that purpose.

## Lifetime and work assignment

Parentage and role duration are separate. A child may be an ongoing autonomous
specialist or be created for a bounded assignment. The role is explicit at creation;
being a child does not make an agent temporary or dependent on a new parent prompt
for every piece of work.

| Role | After an assignment is accepted as complete |
| --- | --- |
| Ongoing specialist | Keeps its purpose and cadence; identifies useful next work, starts clear authorized projects, asks about uncertainty, or proposes a direction. Finishing a project does not end its responsibility. |
| Bounded-assignment child | Becomes idle with its identity, memory, results and history retained. Its parent can explicitly reassign or retire it. It does not invent a new ongoing purpose for itself. |

For example, a business-leader agent can create ongoing marketing and sales
children. After one campaign, marketing can investigate new audiences, propose
another campaign and start clear permitted work within its marketing purpose.
Sales can likewise develop new initiatives within its sales purpose. A researcher
created only to answer one question becomes idle after its accepted result.

An ongoing child's new projects develop its existing purpose; they do not grant
permission to rewrite its soul or escape parent supervision. Both roles follow
the same ownership, permission and evaluation rules. An ongoing agent may choose
to wait when no useful work is ready, but assignment completion does not force it
into an idle role awaiting another assignment.

If either kind of child's parent retires, the child also retires under the
[subtree retirement rule](05-human-interaction.md#retirement).
The disposition after cancellation of a bounded assignment remains a separate
[open choice](07-open-decisions.md); completion does not resolve that question.

Changing a child's purpose and replacing it are different operations. Replacement
retires the old child and its descendants, preserves their records, and creates
a distinct agent with a selected explicit handoff of context, artifacts and
unfinished work. Follow [lifecycle control](05-human-interaction.md#steering-active-work).
