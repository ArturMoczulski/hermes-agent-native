# Implementation plan: a product fork of Hermes

Status: **Hermes fork selected by the owner**, 2026-09-05. This repository is the
framework's implementation home and the First Builder's workspace. The detailed
engineering plan still requires implementation and validation; it is not a claim
of completed work. The [product specification](../design/README.md) remains
authoritative, and proposed defaults do not silently resolve its open decisions.

Development follows the [First Builder startup instructions](../first-builder/INSTRUCTIONS.md)
and [continuous TDD practices](../first-builder/PRACTICES.md). Keep current work
and verification evidence in [STATE.md](../first-builder/STATE.md).

## Recommendation

Build agent-native as a focused fork of Hermes Agent. Reuse its agent engine,
profiles, memory, skills, tools, sandbox backends, dispatcher, and web
interface. Add the persistent organization and human-control rules that make
agent-native a distinct product.

Start with Hermes as the only agent engine. OpenCode is optional future tooling
for a demonstrated specialist need. Use one always-on Linux host, SQLite on local
disk, and Docker workspaces initially. The human's browser is a client; closing it
must not stop work.

Allowing a fork makes this simpler than the earlier external-supervisor proposal:
we can change Hermes's execution boundaries directly. Plane supplies planning;
the framework links its records to execution without duplicating the task board. This is still substantial product
work, not a configuration-only setup or a promise of a tiny patch.

## What to read

| Document | Purpose |
| --- | --- |
| [Specification coverage in Plane](plane-roadmap-coverage.md) | Milestone modules, rolling cycle policy and specification/scenario-to-work links; live Plane owns status. |
| [Plane project management](plane-project-management.md) | Selected planning service, source ownership, provisioning and integration sequence. |
| [User interface](user-interface.md) | Browser console, Hermes reuse, shared state and incremental UX delivery. |
| [Architecture](architecture.md) | Components, authoritative state, execution, permissions, communication, and recovery. |
| [Delivery plan](delivery-plan.md) | Ordered milestones, deliverables, completion evidence, and all 24 product scenarios. |
| [Decisions and evidence](decisions-and-evidence.md) | Reuse choices, proposed product defaults, source references, and fork maintenance. |

## The application we would build

```mermaid
flowchart TD
    H[Human owner] --> UI[Extended Hermes web interface]
    UI --> C[Agent-native control module]
    C <--> DB[Framework control database and event record]
    C <--> P[Plane planning service]
    UI --> P
    C --> D[One managed dispatcher]
    D --> A[Hermes agent processes and persistent profiles]
    A --> T[Authorized framework tools]
    T --> C
    A --> S[Private Docker workspaces]
    A --> E[Recorded model and tool activity]
    E --> DB
    DB --> UI
```

The control module is ordinary application code within the fork. It checks who
may act and keeps records consistent; it does not choose artistic or commercial
strategy. Agents make those judgments through Hermes's model/tool loop.

## Reuse and custom work

| Capability | Starting point | Our change |
| --- | --- | --- |
| Model calls, tool loop, retries, context management | Hermes engine | Supply trusted agent/run context and enforce run admission. |
| Memory, skills, transcripts | Hermes profiles | Map profiles to stable agent IDs; protect soul and configuration separately. |
| File, shell, browser, domain tools | Hermes and approved MCP integrations | Scope access and credentials; track consequential actions. |
| Sandboxes | Hermes Docker backend | Bind lifetime to framework work, including actual stopping of background processes. |
| Projects, backlog, cycles and board | Plane Community Edition | Provision scoped workspaces and integrate planning operations. |
| Claims, runs, results and evaluations | Framework control module; reuse suitable Hermes primitives | Link Plane items, enforce authority and distinguish submission from acceptance. |
| Recurring activation and dispatch | Hermes gateway and scheduling machinery | Add purpose check-ins; send every activation through one eligibility check. |
| Chat, profile/settings views, task-board UI | Hermes web application | Add agent tree, purpose editor, decision inbox, and connected activity views. |
| Agent ownership and lifecycle | Custom control module | Parent tree, soul revisions, permissions, pause, retirement, replacement. |
| Clarification and decision routing | Custom records and workflow using existing transports | Parent-by-parent escalation, human-origin authentication, durable returning answers. |
| Observability and progress assessment | Existing execution/task events plus custom records | Unified history, delivery states, freshness, evaluations, and progress concerns. |

Reuse means keeping an existing implementation where it fits, not retaining every
Hermes default. Its peer task access, direct completion, independent activation
paths, and persistent-container cleanup need deliberate changes for this product.
The [evidence review](decisions-and-evidence.md#evidence-and-version-boundaries)
separates documented features from the proposed additions.

## The shortest useful delivery sequence

1. Establish the fork and prove its integration and access boundaries.
2. Add protected identity, authoritative operations, work records, and events.
3. Deliver one complete autonomous root: create, plan, act, ask, evaluate, continue.
4. Add persistent children, escalation, and recursive lifecycle controls.
5. Complete the human inbox, system observability, and progress review.
6. Complete restart recovery, deployment, and operation away from the laptop.
7. Run the First Builder inside the framework against its repository workspace.

Basic owner chat, pending decisions, stopping, recovery, and result evaluation
belong in the first autonomous-root milestone. Later milestones complete breadth
and robustness; they are not permission to postpone the control foundations.

## Keep the initial installation small

- One human owner and one trusted web channel.
- One authoritative task store for all projects, with enforced access boundaries.
- One dispatcher; multiple agents and isolated workers as capacity allows.
- Existing Hermes Python and frontend tooling, rather than another backend stack.
- Existing model providers; no custom provider SDK or agent execution loop.
- Standard Docker and service supervision; no Kubernetes or distributed framework
  workflow platform initially. Plane retains its own required service dependencies.
- Plane is the planning store and board. Bundle the project-management skill and
  integrate it with framework control records; do not duplicate a Hermes board.

Multiple roots, recursive teams, different models, and authorized communication
between separately isolated workers are part of the initial product. Multiple
physical worker hosts can follow; the first release must not depend on them.

## Repository and First Builder workspace

The owner selected `ArturMoczulski/hermes-agent-native` as the implementation home.
The specification and plan now live here. Make active design and implementation
updates in this fork; the old agent-native implementation is reference material.
Do not maintain a compatibility layer for its runtime state, event protocol or
Next.js/NestJS/agentd/OpenCode service chain.

The [First Builder](../first-builder/INSTRUCTIONS.md) develops the framework from
this repository root, following its owner-defined soul and continuous TDD workflow.
It works through the current coding environment now and will run inside the
framework once that capability is implemented. No deployed Builder or scheduler
is established by creating these documents.
