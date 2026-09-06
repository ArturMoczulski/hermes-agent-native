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

Children may be ongoing specialists with their own thinking cadence or agents
assigned bounded work. Both have the same identity and ownership rules.

Completing an assignment is distinct from ending an agent's existence. An ongoing
composer can finish one album and later work on another. A child assigned only
to research one question can report its result without being required to invent
an ongoing purpose. Whether such a child is retired automatically after assignment completion
remains to be specified; completion must not silently discard its results.
If its parent retires, it also retires under the
[subtree retirement rule](05-human-interaction.md).

Changing a child's purpose and replacing it with a new child are different
decisions. A replacement must be identifiable as a different agent; its inherited
context and unfinished assignments must be made explicit.
