# Proposed decisions and supporting evidence

Prepared on 2026-09-05. These recommendations support the
[implementation proposal](README.md); the initial review did not approve product changes. Later owner decisions are
identified and linked below.
The review used documentation and source inspection. It did not validate a
working Hermes integration or execute tests.

## Why a Hermes product fork

| Approach | What it saves | What we would still build or maintain | Recommendation |
| --- | --- | --- | --- |
| Configure stock Hermes | Existing engine, tools, memory, scheduling and UI | Our protected hierarchy, authority, lifecycle, decision routing and unified history remain unsupported as a coherent product contract. | Useful starting software, insufficient by configuration alone. |
| Extend Hermes only through plugins and an external supervisor | Keeps upstream updates relatively independent | A supervisor, task/identity synchronization, additional UI, and enforcement across native paths that may bypass plugins. | Fallback if a maintained fork becomes impractical. |
| Fork Hermes and extend its shared operations | Keeps the engine, dispatch primitives, profiles and web application together; Plane now supplies planning | Our domain rules and deliberate patches at every relevant native entry point; ongoing upstream integration. | Preferred starting point. |
| Hermes coordinating OpenCode workers | Adds a second established execution engine | Two session, configuration, permission, cancellation and tool systems to connect and observe. | Add only for a demonstrated specialist advantage. |
| Rebuild around the current prototype or a minimal engine SDK | Maximum freedom in architecture | More custom task, UI, memory, skill, execution and operations work. | Preserve useful code as reference; do not make it the new foundation. |

The fork recommendation is an engineering judgment about total work saved, not
an upstream promise that our product is already implemented. Forking lets us
enforce the new rules inside existing services; it does not eliminate the need
to understand all their alternate execution paths.

Hermes and OpenCode overlap as agent execution systems. OpenCode can be called
as a tool by Hermes, but stacking them is not necessary to obtain a model/tool
loop. OpenCode already provides server-based sessions, streaming and cancellation;
those are useful capabilities, not unique reasons to add it here.
[OpenCode server documentation](https://opencode.ai/docs/server/).

Use Hermes's existing coding tools and skills for the initial First Builder.
An OpenCode worker becomes worthwhile only if later evidence shows a particular
workflow materially benefits and its results, resources and stopping can be
integrated into the same control records. No such comparative benchmark was
performed in this review.

## What the existing code contributes

The earlier source review compared the documentation branch's prototype with
the newer repository snapshot at
`f67ddd5205d1344b5745dfa28946aa44bc9e5cb1`. That snapshot was inspected separately;
it was not merged into this branch. The preserved
technical documentation in the [old repository](https://github.com/ArturMoczulski/agent-native) includes older
states and plans, so it is not a verified description of every newer file.

| Finding from source inspection | Implication for this plan |
| --- | --- |
| The newer implementation has a web HQ, proxy/backend services, agentd, and per-agent OpenCode servers. | Reusing a headless agent engine was a sound direction; the entire service chain is not needed when the chosen base already has a web application and task dispatcher. |
| There are useful chat, streaming, history and agent-tree concepts. | Consult or selectively port them when they save work. Preserve source and documentation for reference. |
| The inspected code does not provide the required ongoing-purpose cadence or a complete dynamic persistent-child lifecycle. | These central product behaviors still require implementation, whichever engine is chosen. |
| Pause/status paths do not consistently prevent new execution or stop active work throughout a subtree. | Lifecycle control needs an authoritative shared boundary, rather than more UI status flags. |
| Soul/context loading and concurrent task launches do not implement the specified protected layers and durable work ownership. | Rebuild these domain rules against the current specification. |
| Stream and status observations do not constitute the complete durable system and communication history the specification requires. | Treat existing presentation code as a reference, not proof of observability coverage. |

This supports replacing the implementation foundation, not deleting the previous
work. No runtime-state migration or backward compatibility is required. Historical
research, including the OpenClaw comparison, remains historical evidence; its
external claims are not used as current benchmarks or as reasons to reject an
alternative today.

Source locations in that snapshot include
`packages/core/agent_native_runtime/host.py` (`pause`, `invoke`),
`packages/core/agent_native/gateway.py` (invocation and status paths), and
`packages/core/agent_native_runtime/opencode_http.py` (session/event handling).
Use the recorded commit when inspecting these findings; this branch's versions
can differ.

## Evidence and version boundaries

The following primary sources were reviewed on 2026-09-05. Documentation and
`main` links can change. The release tag below is a reference point, not proof
that every feature seen on `main` shipped in that release. M0 must select and
record an exact commit, verify the required feature set there, and preserve
source permalinks in the fork's decision record.

| Area | Evidence | Consequence for the proposal |
| --- | --- | --- |
| Engine reuse | [Architecture](https://hermes-agent.nousresearch.com/docs/developer-guide/architecture/) and [programmatic integration](https://hermes-agent.nousresearch.com/docs/developer-guide/programmatic-integration/) describe Hermes's execution components and embedding surface. | Extend the existing engine. Do not write another model/tool loop or require an HTTP round trip for every internal call. |
| Managed runs | [API server](https://hermes-agent.nousresearch.com/docs/user-guide/features/api-server) documents sessions, run state, streaming, steering, stopping and idempotency. | Reuse these capabilities where they fit; framework lifetime, recovery and audit retention still require explicit ownership. |
| Profile state | [Profiles](https://hermes-agent.nousresearch.com/docs/user-guide/profiles/) separate configuration, memory, skills and sessions, but are not a security sandbox. | Map a stable agent ID to a profile and separately enforce filesystem/tool access and protected soul state. |
| Structured work | [Kanban](https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban/) and [worker lanes](https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban-worker-lanes) provide shared tasks, dispatch and review workflows. Their peer task model does not supply our recursive ownership. | Superseded for planning by the owner’s Plane selection, 2026-09-06. Reuse suitable execution primitives only; see [Plane integration](plane-project-management.md). |
| Task consistency | [Kanban database source](https://raw.githubusercontent.com/NousResearch/hermes-agent/main/hermes_cli/kanban_db.py) contains transactional claims, run identity checks and task events. Some completion guards are optional. | Keep useful primitives; require the relevant current-run and authority checks for managed workers and route direct mutations through the domain layer. |
| Human interface | [Web dashboard](https://hermes-agent.nousresearch.com/docs/user-guide/features/web-dashboard) includes profile, configuration, session, skill and task management. Its chat embeds a TUI. The inspected fork also has reconnectable PTY retention, so browser closure does not always kill it immediately; see the [UI source review](user-interface.md#correct-the-earlier-terminal-lifetime-assumption). | Reuse the web application, but connect managed-agent conversation to service-owned execution. A browser connection cannot own agent lifetime. |
| Sandbox lifetime | [Docker backend source](https://raw.githubusercontent.com/NousResearch/hermes-agent/main/tools/environments/docker.py) includes persistent-container behavior which can outlive the engine process. | Explicitly track and stop associated container work. Engine exit alone is not evidence of cancellation. |
| Configuration protection | [Managed scope](https://hermes-agent.nousresearch.com/docs/user-guide/managed-scope) supports operator-controlled configuration. [Environment policy source](https://raw.githubusercontent.com/NousResearch/hermes-agent/main/tools/environments/local_env_policy.py) filters implicit forwarding, with an explicit-forwarding override. | Lock managed configuration and add an unconditional exclusion for internal authority credentials across sandbox forwarding paths. Configuration protection is not filesystem isolation. |
| Tool boundaries | [Security](https://hermes-agent.nousresearch.com/docs/user-guide/security/), [tools](https://hermes-agent.nousresearch.com/docs/user-guide/features/tools/), and [MCP](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp/) describe execution backends and integrations. | Reuse tools within explicit capabilities. Generic command approval does not enforce business-action permissions or protect credentials exposed to generated code. |
| Extension and recording | [Plugins](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins) and [hooks](https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks/) offer extension points; observer hooks are not guaranteed enforcement or durable audit. | Use extensions when suitable, and patch shared operations where the product requires reliable authorization or recording. |
| Storage | [SQLite WAL](https://sqlite.org/wal.html) explains local shared-memory coordination and concurrent-reader/single-writer behavior. | Use a local disk on one service host initially. Do not put the live database on a shared network filesystem or claim distributed scheduling. |
| Fork rights and baseline | [Release v2026.8.31](https://github.com/NousResearch/hermes-agent/releases/tag/v2026.8.31) and its [MIT license](https://github.com/NousResearch/hermes-agent/blob/v2026.8.31/LICENSE). | Preserve applicable notices and check licenses of bundled assets and dependencies when producing our distribution. |

The highest uncertainty is integration breadth: whether every relevant tool,
CLI, dashboard and background path can share actor context, admission and stop
semantics with manageable changes. Profile isolation, durable chat, persistent
container stopping and task acceptance must be demonstrated early. The plan does
not assume that an API stop request immediately ends external effects or that
an event stream is a permanent audit log.

## Proposed product defaults

These fill the open choices in
[the product decision list](../design/07-open-decisions.md). Rows marked Accepted
link to the canonical owner-approved rules. Other rows remain proposals and do
not gain approval from the accepted subset. Implementation evidence is still
required independently of a product decision.

| Decision | Status and initial behavior |
| --- | --- |
| Multiple projects and priority | An agent may work across projects within its authority. It proposes priorities; its responsible parent resolves delegated conflicts, and the human can override. Project membership does not change parentage or grant access. |
| Next work and proposals | **Accepted, AN-60.** Follow [questions and permissions](../design/05-human-interaction.md#questions-proposals-and-permission). |
| Approval | **Accepted, AN-61.** Follow [standing permission and explicit approval](../design/05-human-interaction.md#questions-proposals-and-permission). |
| Parent permissions | **Accepted, AN-62.** Follow [delegable authority](../design/05-human-interaction.md#applying-ownership-to-permissions). |
| Default creation experience | **Accepted, AN-61.** Follow [default capabilities](../design/04-workspaces-and-skills.md#default-capabilities). |
| Purpose changes | **Accepted, AN-63.** Follow [lifecycle control](../design/05-human-interaction.md#steering-active-work), including automatic eligible replanning and parent notification. |
| Child replacement | **Accepted, AN-63.** Follow [replacement and selected handoff](../design/05-human-interaction.md#steering-active-work). |
| Purpose fulfillment and assignment completion | **Accepted owner revision, AN-64.** Follow [purpose evaluation](../design/01-agents.md#lifetime-and-work-assignment): every agent evaluates accepted work against its whole purpose and continuing obligations. No fixed ongoing/bounded type; a clearly fulfilled or no-longer-needed purpose with applicable accountable acceptance/disposition and no unresolved obligations permits controlled agent-initiated retirement. Escalate uncertainty without requiring human approval for every retirement. |
| Assignment cancellation | **Accepted, AN-64.** Stop the selected assignment and durably pause its performing agent and subtree; preserve independent assignments in paused state. Cancellation does not establish whole-purpose fulfillment. |
| Retirement and retention | Retirement preserves the subtree history and results without automatic reassignment. Replacement handoff is **accepted in AN-63**; general retention periods, export/deletion and other transfers remain separate operational choices in AN-68. |
| Resume | Remove the selected pause cause, preserve independent descendant pauses, and review changed instructions and outcomes before execution. An answer or timer does not remove a pause. |
| Project pause | Stop that project's assignments and work that depends on them. Do not pause an entire agent with independent work in other projects unless the owner explicitly pauses that agent. |
| Wakeups and downtime | Creation, owner messages, relevant answers/results and cadence can request reconsideration. Coalesce redundant ticks; retain every message. After downtime, perform one current-state review rather than replaying every missed tick. |
| Unanswered requests | Keep a visible pending item under its stable ID. Do not send repeated questions or reminders by default; an explicitly configured reminder updates the same item. |
| Capacity | Configure installation-wide execution slots and scoped child-creation permissions/limits. Admit work fairly across roots. Tree depth is not hard-coded; capacity waiting is visible and does not erase agents or work. Exact default counts follow M0 resource measurements. |
| Progress concerns | Use configurable signals such as repeated failed attempts or replanning without new evidence. Record one linked concern and require responsible review. Waiting time alone is insufficient, and a concern never automatically retires an agent or rewrites its purpose. |

Manual-only agents, replay/branching and multiple human chat channels stay outside
the initial release. Structured skills, multiple model providers, recursive
children, evaluation-driven lifespans, the human inbox, and the First Builder stay
inside. Purpose fulfillment includes continuing delivery and monitoring obligations
and distinguishes useful growth from established operations. Self-preservation,
busywork, weakened criteria and soul rewriting cannot justify continuation or retirement.

## Keeping the fork maintainable

Maintain a small, explicit inventory of upstream changes: actor and operation
hooks, dispatcher admission, profile/config protection, task acceptance, managed
chat lifetime, container cancellation, and event persistence. Most product rules
should live in `agent_native/`; avoid broad renames and formatting churn in
upstream code. This keeps changes understandable even when the inventory itself
is substantial.

Pin the upstream commit, dependency lockfiles and our own release version. Disable
unmanaged self-update paths in the deployed product. Review upstream changes in
batches, prioritizing security and engine correctness, and examine their effects
on the custom boundaries before releasing. Run the appropriate upstream and
product checks during implementation; none were run for this proposal.

Preserve upstream attribution and license notices. Upstream generic improvements
when practical, while retaining product-specific ownership and lifecycle rules in
our fork. Record dependency migrations explicitly, back up state before applying
them, and keep a compatible rollback or restore path for each release.

M0 is a decision gate, not an excuse to build a second framework beside Hermes.
If a subsystem proves unsuitable, first replace that subsystem behind the shared
domain operations. Revisit the foundation only with concrete evidence that the
fork costs more to maintain than the services it saves.
