# User interface implementation and reuse

Status: engineering proposal supporting the [UX specification](../design/10-user-experience.md),
2026-09-05. The Hermes fork is selected; the following UI integration still needs
implementation and validation. This review did not launch the application or run tests.

For screen contents, controls and interaction states, implement against the
[control center screen specification](../design/12-control-center-screens.md).
It is the textual build brief; Figma drafts are not an implementation dependency.

## Recommendation

Build one browser-based agent console within the existing Hermes web application.
Reuse its server, authentication, navigation, visual primitives, settings and task
integration. Add agent-native views and explicit domain operations for Chat,
Monitor, Inbox and Work. Keep one authoritative backend state for all views.

Reuse desktop Bot Mode's interaction patterns and selectively extract suitable
presentation components for structured chat. Do not import the whole desktop
application or add Electron as a prerequisite for using the framework. Inspect
dependency boundaries before claiming that a component is portable.

## Source baseline and reusable pieces

Source inspected in this fork at `006b1beb00d9d25230571d14277aca3d70e5e11f`.
Online documentation can differ; local source is the evidence for this checkout.

| Capability | Source | Reuse decision |
| --- | --- | --- |
| Web shell and page extension | [App](../web/src/App.tsx), [plugin pages](../web/src/plugins/PluginPage.tsx) | Extend existing routes/navigation; group technical settings away from daily agent work. No second frontend/server application. |
| Shared web visual components | [Web package](../web/package.json) | Reuse current React components, styling and accessibility primitives; avoid a new design system. |
| Profiles and creation | [Profiles page](../web/src/pages/ProfilesPage.tsx), [profile builder](../web/src/pages/ProfileBuilderPage.tsx) | Reuse form/settings pieces; bind creation and edits to stable framework agent identity and authorized operations. A profile picker is not the organization tree. |
| Task board and activity transport | [Kanban plugin](../plugins/kanban/dashboard/manifest.json), [API](../plugins/kanban/dashboard/plugin_api.py) | Planning board reuse is superseded by [Plane](plane-project-management.md). Keep linked framework run/evaluation details and event transport where useful; board state cannot bypass acceptance. |
| Agent roster and continuing chat | [Desktop Bot Mode](../apps/desktop/src/plugins/hermes-bots/plugin.tsx), [roster actions](../apps/desktop/src/plugins/hermes-bots/roster-actions.ts) | Reuse concepts and suitable presentation logic. Desktop host/plugin state needs adaptation. Bind to framework IDs, not display names or recent activity alone. |
| Rich conversation rendering | [Desktop assistant messages](../apps/desktop/src/components/assistant-ui/thread/assistant-message.tsx) | Assess extraction of rendering pieces; replace desktop-specific state dependencies with the shared framework conversation contract. |
| Existing terminal chat | [Chat page](../web/src/pages/ChatPage.tsx), [WebSocket handler](../hermes_cli/web_routers/chat_ws.py), [PTY registry](../hermes_cli/pty_session.py) | Keep as inherited tooling if useful. Terminal bytes and a reconnect token are not the new agent conversation or lifecycle authority. |

Useful upstream background: [dashboard](https://hermes-agent.nousresearch.com/docs/user-guide/features/web-dashboard),
[dashboard extension](https://hermes-agent.nousresearch.com/docs/user-guide/features/extending-the-dashboard),
[Bot Mode](https://hermes-agent.nousresearch.com/docs/user-guide/bot-mode), and
[Kanban](https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban/).

## Correct the earlier terminal-lifetime assumption

The checkout has both legacy disconnect-and-kill behavior and a keep-alive PTY
registry. With attachment tokens, a socket can detach and reattach while the PTY
continues; detached sessions can later expire or be evicted. Changing dashboard
pages can also preserve the mounted chat. Therefore "closing the browser always
kills the agent immediately" is not an accurate general statement for this code.

Our requirement remains stronger: framework execution must survive client closure
and have durable identity, admission, cancellation and restart behavior. Its
lifetime cannot be owned by terminal retention or a browser subscription.

## Deliberate fork-specific chat design

The inherited [web contributor guide](../web/AGENTS.md) favors the embedded TUI
and prohibits a second React chat surface in upstream Hermes. The agent-native
proposal deliberately introduces a structured managed-agent conversation view,
reusing suitable desktop components, because identity, durable decision cards,
artifact review and connected monitoring are central to this product.

When implementing that view, update the area guide to describe this scoped fork
exception. Preserve useful upstream engineering rules. Do not create two separate
authoritative chat stores, task stores, agent loops or permission systems. This
document does not itself change the runtime or the area guide.

## Shared contracts before screens

Expose stable agent identity/parentage, own execution, descendant summary, work
and dependency state, cadence, last observations and lifecycle separately.
Conversation messages carry durable IDs, authenticated origin and observed delivery
states. Requests include their applicability/revision and response state. Work
includes criteria, artifacts and evaluations. All commands return an operation
identity and its observed state, not an optimistic promise of completion.

Use the same control operations from every UI path and native entry point.
Authoritative state and durable events live on the service; browser state owns
selection, filters, drafts and presentation. Reload from snapshots and resume
updates with cursors/deduplication. A second tab, delayed response, expired login
or stale cached purpose must not create duplicate agents, answers or work.

Do not infer ownership from Bot Mode folders or verified delivery from message
text/CLI-command parsing. Do not infer "running" from a recent message timestamp.
Human authority comes from the authenticated owner channel, not a frontend label.

## Delivery and verification

Current priority: the [fantasy-writer milestone](fantasy-writer-milestone.md).
Deliver one agent detail page with Chat, Activity and Stories, plus the roster.
The first execution slice already includes real status, result and Pause controls;
durable chat, detailed inspection and continuity complete this earlier milestone.
Reuse that foundation for the Builder. Full organization screens stay later.
The framework browser test harness now exists in [web/e2e](../web/e2e/README.md);
reuse it and the installed Chromium rather than creating another test stack.

| Increment | Existing milestone | UX evidence |
| --- | --- | --- |
| Creation, purpose retention and basic agent list | M1–M2 | UX-01, initial UX-02/04; immediate durable activation distinguished from observed execution. |
| Continuing conversation, basic requests and pause | M2 | UX-03/07/08/10/13; one root works independently of its browser. |
| Tree, children and escalation | M3 | UX-05/06/11/17; independent roots and descendants remain distinguishable. |
| Complete console navigation, global inbox and history | M4 | UX-02/09/12/14/18/19/20 and remaining monitoring/communication coverage. |
| Outcome review and progress concerns | M2 foundation, M5 completion | UX-15/16; submission is not acceptance and activity is not progress. |
| Restart, lost clients/workers and cancellation hardening | M6 | Repeat UX-09/10/12/13/20 against real failure boundaries. |

Use the [UX acceptance scenarios](../design/11-ux-scenarios.md) and
[continuous TDD practices](../first-builder/PRACTICES.md). Establish a real
browser/backend Playwright setup for the first slice; existing desktop tests do
not establish web product coverage. Add tests and implementation together in
small red-green-refactor loops. Do not postpone usable chat or stopping to M4.

Plane is now selected for project planning; link its workspace, board and cycle
views from Work. Retain framework Chat, Monitor, Inbox and authoritative result
evaluation. No graph-layout library, separate monitoring product, mobile client
or group-chat orchestration is required for this first console.
