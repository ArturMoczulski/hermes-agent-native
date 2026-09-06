# Projects and delegation

## Structured work

The framework provides project and task management. Work must remain organized
across check-ins, delegated assignments, and human conversations. A project has
an intended outcome and a boundary that makes progress meaningful. A task is a
piece of work contributing to an outcome.

An agent may have an ongoing purpose that spans successive projects. Developing
a music career can involve many albums; finishing an album does not finish the
artist's purpose.

## Ownership boundaries follow the agent tree

The human owns all agents and projects. For agent supervision, the boundary of
an agent's responsibility is itself and its descendants. A root has no other
agent above it; a child also answers to its direct parent. These boundaries nest:
the composer's area sits inside the artist's area, and the researcher's area
sits inside the composer's.

Projects and tasks organize outcomes within those responsibility boundaries.
They do not establish a competing ownership structure or move an agent outside
its parent's supervision. The agent coordinating a project manages its plan,
assignments, results, and blockers within its area of responsibility. The human
can intervene anywhere.

```text
Human owner — ultimate authority over every agent
└── Metal artist — responsible for itself and its descendants
    └── Composer — responsible for itself and its descendants
        ├── Metal music researcher
        └── Producer
```

The artist can coordinate an album and the composer its composition work.
Research and production can be tasks or subprojects as useful for planning.
These work divisions do not change ownership. An agent can coordinate multiple
successive projects while retaining its identity and parent.

Changes to agents follow [the ownership rules](01-agents.md). Communication with another tree does not
extend an agent's ownership boundary into that tree.

## Information needed to manage work

The workspace must make these facts clear:

- The intended outcome, constraints, and what counts as completion.
- Who is responsible for the work and who is performing each assignment.
- Current plans, priorities, active work, dependencies, and blockers.
- Questions awaiting answers and the party expected to answer them.
- Results, artifacts, feedback, and reasons for material changes of direction.

Active, waiting, finished, failed, and cancelled work must be distinguishable.
These are meaningful distinctions, not a required vocabulary for a task board.
Reporting a result and accepting it as meeting the objective are also distinct.

## Delegating to children

An agent can create children within its authority. Each child can create children
in turn, allowing arbitrary conceptual depth. An assignment must communicate the
objective, relevant context, constraints, expected result, and when to report
progress or request help.

The responsible agent evaluates the result and integrates it into the wider
work. Delegating an assignment does not eliminate responsibility for its outcome.
A child reports blockers and failures as well as successes. Unresolved questions
follow [the parent escalation chain](05-human-interaction.md); delegation does
not require the human to answer questions that an ancestor can resolve.

A child's purpose can describe a finite outcome, continuing responsibilities, or
both. Its evaluated purpose determines how long it is needed; no fixed lifetime
category is required. Creating more agents is a planning choice; it is not the required
response to every task or every cadence tick.

## Explicit evaluation of results

Work has stated completion expectations appropriate to its outcome. Producing
an artifact or reporting “done” does not by itself establish that those
expectations were met. The responsible agent reviews the result against the
brief, available evidence, and relevant quality criteria before treating the
assignment as successfully completed.

The evaluation records what was reviewed, which expectations were met, what
remains uncertain, and whether the result is accepted, needs revision, or does
not meet the objective. Those outcomes are visible in the work record and event
history. Criteria must not be silently weakened just to mark work complete.

For delegated work, the parent remains accountable for evaluating and integrating
the child's result. It may use an authorized reviewer or suitable tools to help;
a separate reviewer agent is not mandatory for every assignment. An agent also
evaluates its own work, and seeks parent or human involvement through the normal
escalation chain when it cannot resolve a material question.

Human approval is required where the applicable rules require it, not for every
routine evaluation. For subjective work, the evaluation explains the basis of
its judgment and relevant uncertainty instead of claiming objective proof of
quality. For example, a playable audio file still needs review against the
musical brief before it counts as a satisfactory composition.

## From result acceptance to purpose evaluation

Result evaluation answers whether a particular outcome met its criteria.
[Purpose evaluation](01-agents.md#lifetime-and-work-assignment) answers whether
the agent is still needed. Accepted milestones feed that wider review; they do
not automatically retire an agent or require it to invent another project.
Continuing work has service expectations and review periods, as well as criteria
for individual deliveries. Meeting this period's expectations does not discharge
future monitoring or delivery obligations. Growth and established operation may
coexist or succeed one another within the same protected purpose.

## Communication beyond parentage

Authorized agents can communicate directly with siblings and agents in other
trees, including agents running in different environments. Parent–child
relationships define supervision; they do not limit all communication to tree
edges. Communication does not change parentage, soul ownership, or permission to
access another agent's private context. An agent must know which agent it is
addressing and whether the requested interaction is permitted.

All agent-to-agent communication is recorded as system events under the
[observability requirements](09-observability.md), including messages beyond
parent–child relationships.

## Changing direction

The agent responsible for a project decides whether to adapt an existing child
or create a new one when the project's direction changes. This decision remains
subject to soul ownership and granted permissions.

For an album changing direction, the artist coordinates the changed album brief.
The composer decides how the composition work should respond and whether its
research and production children still fit. The framework does not automatically
rewrite the entire tree.

Purpose changes and child replacement follow the
[immediate-stop rule](05-human-interaction.md). The new direction must not leave
the old worker continuing an obsolete assignment. Results already produced
remain distinguishable from work under the revised brief. Replacement retires
the old child's subtree and gives a distinct new child an explicit selected
handoff, following [lifecycle control](05-human-interaction.md#steering-active-work).
Completing one delegated project does not necessarily end the child's wider
responsibility; [purpose evaluation](01-agents.md#lifetime-and-work-assignment)
determines whether useful responsibilities remain or retirement is appropriate.

Concurrent participation in unrelated projects, transfer of work responsibility,
and the relationship between project pause and agent pause are
[open decisions](07-open-decisions.md).

## Working method

[Project management with Plane](13-project-management.md) specifies the default
backlog, cycle, board and review workflow. Its project structure implements these
ownership and evaluation rules; it does not replace them.
