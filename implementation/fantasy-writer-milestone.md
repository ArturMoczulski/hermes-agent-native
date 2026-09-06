# Deliver one visible autonomous writer

Owner priority: 2026-09-06. Re-scope the existing undated cycle 03 to
**Fantasy writer — create, chat and observe**. This precedes the First Builder
handoff. [Product acceptance](../design/14-first-writer-milestone.md) defines what
counts as done; live Plane owns item status, priority and dependency membership.
This plan does not launch a writer or claim that the milestone is implemented.

## Starting point and reuse

The `/agents` page persists inactive records; creation is not wired to execution.
Protected profile/workspace provisioning and a restricted Docker environment are
implemented internal pieces. Plane host reads/writes and uncertain-write recovery
have evidence. The first AN-24 bridge exposes Plane inspection through Hermes,
not the complete managed planning tool set. No managed framework agent is running.

Extend `web/src/pages/AgentsPage.tsx`, `hermes_cli/web_routers/agent_native.py`
and `agent_native/`. Reuse Hermes's model loop and callbacks, existing owner
authentication, web components, persistence and suitable session/tool rendering.
Keep the service responsible for runs; inherited terminal chat/PTY retention is
not the managed conversation contract. Follow the structured-chat fork exception
in [UI implementation](user-interface.md), updating the web area instructions when
implementing it. Do not add another frontend, model loop or task board.

The writer uses ordinary private files and scoped Plane operations. Reuse the
existing protected profile/environment and planning adapters; connect the few
operations used by this path. A host-only artifact operation may store text from
the model in the writer's workspace without granting a general shell. Inspect
actual reuse seams before selecting the smallest implementation. No Builder
repository mount or computer-use dependency belongs on this path.

## Delivery order

Each row is a reviewable outcome delivered through several small red/green loops.
Do not build a backend phase followed by all the UI. Include visible behavior in
the first execution slice and retain it as every later slice is added.

| Order | Deliverable | Required evidence |
| --- | --- | --- |
| 1 | Create → first managed story → visible result and Pause | Configure model/cadence/finite run limits; provision one ordinary root's private and Plane home retry-safely; save immediate activation; bind protected purpose, current scoped plan, skills, authority and allowed tools to one service-owned Hermes run. Persist actions and a story artifact. Existing Agents UI opens a real activity/result view. Actual Pause terminates active execution. |
| 2 | Continuing Chat and owner steering | Persistent conversation keyed by agent, retained owner messages/replies, explicit handling states, proactive question/answer, root pending list, purpose revision stopping/replanning and pause-preserving conversation. Reconnect does not duplicate messages or runs. |
| 3 | Inspect Activity, Sessions and Stories | Agent detail views backed by the same event/run/artifact records: current work, cadence and freshness, activation cause, session history, expandable tools/results/errors, story versions and evaluations, Plane links. No synthetic telemetry or hidden-reasoning promise. |
| 4 | Continue purpose across bounded turns | Configured cadence and one active work attempt; load fresh Plane context, evaluate results and whole purpose, choose a new clear step or wait/ask/retire. Survive browser closure, model/Plane failure and service restart; reconcile before retry, retain questions, never wake paused work. |
| 5 | Demonstrate the complete owner journey | Run the product acceptance with a real configured model and isolated writer data: create, first story, chat/feedback, question/answer, another autonomous step, activity/artifacts, actual pause/resume, purpose edit and restart. Record evidence and limits; distinguish model quality from integration checks. |

The first behavior to drive with Playwright is: **creating a configured writer
opens that identity's detail page and records exactly one initial activation**.
Keep the complete first-story acceptance as the integration target while smaller
storage, provisioning, authority, worker and cancellation tests drive its internals.
Do not call a UI state transition proof that a real model wrote a story.

## Plane delivery records

The acceptance aggregate is [AN-71](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/6a70b94c-2c1f-483f-9c7c-93cd1a55cd05/); its children are the implementation
outcomes, not additional parallel copies of the broad capability backlog.

| Record | Outcome |
| --- | --- |
| [AN-72](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/887162ef-fc5e-49e5-a53a-4db81b5b1d13/) | Create a writer and show its first managed story with Pause |
| [AN-73](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/af1fd8d1-d834-47cb-8058-43311469688c/) | Chat with the writer and steer its ongoing work |
| [AN-74](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/2c4884af-2513-4c0b-908d-e2df1cb39686/) | Inspect writer activity, sessions and saved story versions |
| [AN-75](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/05338859-4138-411a-a36e-222ebdc8c420/) | Continue the writer purpose on cadence and recover interrupted work |
| [AN-76](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/cce1926f-51cb-4476-a658-a8d3553d1126/) | Demonstrate a real autonomous writer through the owner interface |

Chat and detailed inspection both build on the first run; continuity uses both.
The real-model journey accepts the milestone. Configuration records AN-70 and
AN-66 remain open gates for actual launch/cadence, not a ban on test-first work
with explicitly isolated fixture settings.

## Minimum execution contract

- One service-owned dispatcher and explicit run record, keyed to stable agent,
  purpose revision, Plane item and activation. During provisioning, the host
  creates one idempotent initial discovery item in the new Plane project, with
  criteria to establish the brief and first useful work. The first coordination
  run binds that real item; the agent then authors its own plan and writing items.
  Setup failure remains pending/failed before admission, with no invented work IDs.
  Idempotent creation and admission
  prevent duplicate work on clicks, cadence or reconnect. Setup failure stays
  recoverable; record which resources exist rather than blindly provisioning again.
- A host-provisioned Plane workspace/project for the writer, kept separate from
  framework development. The model only receives scoped operations and source
  freshness, never the Builder account or installation credentials. Load the
  project-management skill; link attempts/artifacts/evaluations to real work IDs.
- Current grants checked at model/tool/effect boundaries. Allow only the model,
  private story tools, needed Plane operations and framework conversation/control
  operations. Nonselected native scheduling, delegation, auxiliary dispatch and
  other activation routes are unavailable for this managed profile. Full generic
  integration is later; no exposed bypass is acceptable now.
- Owner-configured finite per-run limits, concurrency and cadence stored as trusted
  configuration. AN-70/AN-66 stay open for defaults; do not silently turn existing
  prototype literals into policy. Setup must display effective values before
  activation. Credentials come from the configured provider connection, not chat.
- Durable conversation independent of engine context windows; bounded turns recover
  purpose, working memory, planning state and relevant messages. Store message
  origins and delivery/handling evidence, not authority inferred from text.
- Correlate service events, model/tool actions, work, run/session and artifact
  versions. Render safe text/Markdown and protect artifact paths; content is not
  a control command. Preserve failures and distinguish reported from observed state.
- Pause revokes dispatch immediately and interrupts the actual run/tools. Show
  stopping until confirmed. Cadence and message delivery cannot clear a pause.
  Root resume reconciles current purpose and retained work. Purpose edits invalidate
  old execution; unknown prior effects block conflicting new work.
- Atomic artifact version publication and durable result references allow restart
  reconciliation. No blind retry of unknown effects; no fresh admission from stale
  Plane content. Keep stop independent of Plane availability.

## Shared backlog and scope disposition

Cycle 03 replaces its unachieved “One controlled Builder run” goal with the writer
journey. Preserve all completed evidence and existing work IDs. Broad shared items
AN-4/7/18/21/23/24/25/26/28/29/30/32/33/34/35/37/43/44/46/69 are capability coverage;
writer slices implement the relevant parts and link evidence back. Do not mark a
broad item Done merely because the writer subset works, and do not make its full
multi-agent acceptance an artificial dependency of this milestone.

AN-24's accepted inspection/revocation increment remains valid; its broad remaining
work returns to backlog, with enabled writer-path enforcement delivered in slice 1.
AN-21's minimal ordinary-root provisioning moves forward in that slice; broad
repair/team provisioning stays later. Existing source-freshness requirements still
apply to admitted work. Any unsupported operation stays disabled.

AN-16/57/58 and M7 remain the subsequent Builder milestone. Later Builder cycles
reuse accepted writer chat, cadence and recovery evidence and contain only remaining
Builder-specific gaps; do not implement those foundations twice. Cycle/module
numbers are identifiers, not estimates. All cycle dates remain unset; WIP is one
implementation slice. This documentation update performs no runtime activation.

## Verification and acceptance

Follow [continuous TDD](../first-builder/PRACTICES.md) and the existing
[web E2E setup](../web/e2e/README.md). Use the installed Playwright Chromium; do not
download another browser. Real browser/API/service/storage/worker boundaries use
isolated data; deterministic model fixtures are allowed at the external model
boundary. Test relevant denial, cancellation, concurrency, outage and reconnect
cases alongside each feature, not as an end-of-milestone phase.

The final real-model demonstration supplements these tests. It must produce a
new saved story and later useful action, show owner interaction/control and retain
history after restart. Record exact observed behavior, failure cases, artifact
links and known limitations in Plane. Passing infrastructure tests or simulated
responses alone cannot accept the milestone. Literary quality is evaluated against
the brief, not guaranteed by the framework.
