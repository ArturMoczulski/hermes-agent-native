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

An agent's lifespan follows the work its purpose still requires. The human or
parent defines that purpose, expected outcomes and continuing responsibilities;
creation does not require choosing a permanent “one-time” or “ongoing” agent type.
The same evaluation process applies to roots and children.

Agents are instruments for accomplishing their purposes. Continued existence is
not an objective: their instructions must make completion, replacement and
retirement normal outcomes, without a motive to fear or resist termination.
An agent must not invent busywork, conceal failures, weaken criteria, preserve
unnecessary children or oppose an authorized stop to keep itself running.

### Evaluate whether the purpose still needs an agent

At work reviews, the agent assesses its current protected purpose against accepted
results, remaining commitments and relevant changes. Assignment acceptance is
one input; it does not by itself establish fulfillment of the whole purpose.
Record the purpose and criteria revisions, evidence, ongoing obligations,
uncertainty, judgment and next action. Reconsider after accepted results, material
changes in purpose or circumstances, and regular planning reviews; a cadence
check can retain an applicable judgment rather than repeat a full review.

| Finding | Consequence |
| --- | --- |
| An outcome is not yet met and a useful authorized next step is clear | Continue or revise the plan; delegate when useful. |
| A service still needs delivery, maintenance or monitoring | Continue the required operating cycle; a healthy service is evidence of success, not evidence that the responsibility has ended. |
| Useful growth or improvement remains within the purpose | Plan evaluable improvements alongside existing commitments, without inventing a need for endless expansion. |
| The purpose is still relevant but work awaits a result, answer or next scheduled service | Wait with the dependency or next review recorded. Inactivity is not proof that the agent is unnecessary. |
| Whole-purpose completion is established, or the purpose clearly no longer needs pursuing, and no responsibilities remain unresolved | Initiate retirement through the framework, retaining the evidence and notifying the parent, or the human for a root. |
| Purpose relevance, acceptance or remaining responsibilities are uncertain | Ask through the parent chain; a root asks the human. Do not silently abandon an obligation or rewrite the purpose. |

A purpose can also cease to be relevant before its original criteria are met.
Retirement on that basis records the evidence and why the work is no longer
needed; it does not falsely mark unmet criteria accepted. The judgment must fit
current purpose and authority. If it depends on an unknown owner preference or
would abandon an unresolved commitment, escalate rather than decide silently.

Self-retirement does not require a new human approval for every completed purpose.
Applicable result acceptance and existing authority still apply: a delegated
result must have its accountable evaluation, and a worker's claim of completion
cannot bypass it. Before self-retirement, review the entire subtree, unresolved
questions, future service commitments, unfinished work and uncertain external
effects. Resolve or explicitly hand off obligations within authority first.
Where relevance depends on an owner's intention, ask that owner through the normal
chain. An empty board, a finished sprint, a progress warning or one failed attempt
is not sufficient evidence of purpose completion or irrelevance.

For example, a researcher whose purpose is one investigation can retire after
its parent accepts the result and no obligations remain. A marketing child whose
purpose includes growing and maintaining demand can finish a campaign, evaluate
performance, and plan another useful initiative without a new parent prompt.
A delivery agent may finish establishing a service and move to recurring operation;
it need not keep creating growth projects to justify its existence. If the owner
ends that service, evaluation can establish that the responsibility has ended.

Purpose evaluation interprets the existing soul; it never grants permission to
edit it. [Retirement](05-human-interaction.md#retirement) ends the entire subtree
and preserves its records. [Cancellation](05-human-interaction.md#assignment-cancellation)
stops the selected work and pauses its agent and subtree; it does not itself
establish that the agent's purpose has ended.

Changing a child's purpose and replacing it are different operations. Replacement
retires the old child and its descendants, preserves their records, and creates
a distinct agent with a selected explicit handoff of context, artifacts and
unfinished work. Follow [lifecycle control](05-human-interaction.md#steering-active-work).
