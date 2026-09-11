# agent-native — product specification

agent-native is a framework for creating persistent agents that take responsibility
for purposes with finite outcomes, continuing responsibilities, or both. A human
gives an agent a purpose, equips it to work, and can
then guide it through conversation while it independently plans, acts, delegates,
and revisits what to do next.

An artist agent might develop a body of music over years. Another agent might
explore and develop a source of income. Each maintains its own identity and work,
and each can create a hierarchy of agents to help.

## Reading this specification

This directory is the canonical product specification for agent-native. It describes intended behavior,
not a particular implementation or a claim that capabilities already exist.
It generally separates product behavior from engineering choices. The owner has
selected Plane as the shared project-management application; its workflow is
specified here, with deployment and integration details in implementation/.

Unmarked requirements describe the intended product. Sections marked **Proposed**
are concrete recommendations awaiting a decision. The outstanding product choices
are collected in [Open decisions](07-open-decisions.md). Examples illustrate
behavior; they do not require a particular profession, workflow, or application.

| Document | What it answers |
| --- | --- |
| [Secrets and credential authority](18-secrets-and-credential-authority.md) | How are framework, instance and agent secrets scoped while the owner retains administration and recovery? |
| [Models and providers](15-model-selection.md) | How are defaults, per-agent choices, effective changes and test costs controlled? |
| [Agents and their layers](01-agents.md) | What is an agent, what can it change, and when is it no longer needed? |
| [Independent work and thinking cadence](02-independent-work.md) | How does an agent keep making useful progress without repeated prompts? |
| [Projects and delegation](03-projects-and-delegation.md) | How is work organized, and how do agent relationships differ from project boundaries? |
| [Project management with Plane](13-project-management.md) | How do agents organize most work through shared backlogs, boards and planning cycles? |
| [Workspaces and skills](04-workspaces-and-skills.md) | What support does the framework provide for doing and managing work? |
| [Output feedback and demonstrations](16-output-feedback-and-demonstrations.md) | How do owners respond to exact outputs, and how do agents communicate demonstrable work? |
| [Human interaction and authority](05-human-interaction.md) | How do people talk to, steer, pause, and authorize agents? |
| [User experience](10-user-experience.md) | How do Chat, Monitor, Inbox and Work fit together? |
| [Control center screens](12-control-center-screens.md) | What does each screen contain, and what do its controls do? |
| [UX acceptance scenarios](11-ux-scenarios.md) | Which interactions and failure states must the interface demonstrate? |
| [Observability](09-observability.md) | How can the human see current activity, cadence, and system history? |
| [Independent security review](17-independent-security-review.md) | Future milestone: how do independent reviewers assess actions and behavior, contain risks, and involve the owner? |
| [Product scenarios](06-product-scenarios.md) | What observable behavior demonstrates the product? |
| [First writer milestone](14-first-writer-milestone.md) | What is the first usable create, chat, observe and continue experience? |
| [The First Builder](08-first-builder.md) | How does the framework eventually develop itself? |
| [Open decisions](07-open-decisions.md) | Which product choices still need agreement? |

## Loose ideas

[Brainstorming notes](ideas/README.md) preserve possible future directions separately
from the specification chapters. They are non-normative, even where their wording
is unmarked: recording an idea does not adopt it or schedule implementation.

## The product promise

Creating an agent with a purpose starts its work immediately, including any
necessary discovery and planning. The human does not need to maintain a queue
of prompts to keep an agent moving.
The agent periodically considers its purpose and circumstances, looks for useful
work, and takes the next clear step within its authority. It asks when it needs
clarification, proposes a direction when none is apparent, and waits when waiting
is appropriate. It also evaluates whether its purpose still requires an agent
and can retire when that purpose is fulfilled; continued existence is not a goal.

The human owner has ultimate authority over every agent and can change any
agent's direction, purpose, or rules through designated trusted owner channels. The agent also initiates
conversation when it needs help, a decision, or permission.

The framework supports multiple independent root agents and parent–child trees
of arbitrary conceptual depth. Actual work is bounded by available resources and
granted authority; the product does not promise unlimited simultaneous execution.

## Independent operation and model choice

Agents can continue operating while the human is offline and their personal
computer is turned off. Their existence and thinking cadence do not depend on
an open chat or an active human session. The environment running the framework
must remain available; no particular hosting arrangement is prescribed.

Model choice is independent for each agent. Different agents can use different
supported models and providers at the same time. Changing an agent's model must
not require replacing its identity, purpose, memory, or project relationships.
The product must not tie the agent definition to a single model provider.

## What the framework is responsible for

The framework provides persistent agent identity and state, thinking cadence,
structured workspaces, loadable skills, communication, delegation, system-wide
observability, detection of activity without progress, explicit result evaluation,
a unified human decision inbox, and enforced
boundaries on what each agent may change or do. The agents use judgment and
skills to choose plans, methods, and next actions. The intended
[First Builder](08-first-builder.md) eventually runs inside the framework to
develop it from this repository.

Success means an agent can advance an ongoing purpose across interruptions and
completed tasks, make its progress understandable, and involve the human where
needed. A timer that repeatedly produces a message is insufficient. Commercial
success or artistic quality is an outcome to pursue and evaluate, not something
the framework can guarantee.
