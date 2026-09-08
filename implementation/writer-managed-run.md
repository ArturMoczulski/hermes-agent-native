# One managed writer run

AN-72 connects the existing private agent setup, scoped Plane adapter, native
Hermes engine and dashboard. This is the first autonomous-work checkpoint of the
[writer milestone](fantasy-writer-milestone.md), not completion of its cadence,
steering or recovery requirements.

## Next refinement

The owner requested a [shared work and output model](shared-agent-work.md) after
viewing the demo. Fiction-specific execution instructions, story-only completion
and the Stories data/UI are current implementation limitations. The next planned
work removes them while retaining this checkpoint's records and verification.
The remainder of this document describes the implemented bounded writer.

## Owner experience

Create an agent with a writing purpose. To enable its initial work, also provide
**Maximum run time (seconds)** and **Maximum model steps**. Both are optional
together, with no preselected values. Without them, creation retains the existing
conversation-only behavior. Existing records can be configured from their detail
page. Creation retries retain the original request and cannot duplicate a run.

A time limit bounds one attempt, beginning when the service starts preparing its
current planning context. A model step is one admitted provider request, including
retries; tools returned by that request do not each count as another model step.
The first reached limit ends the attempt. A per-run watchdog enforces the time
limit independently of the shared monitor and control-database write contention. These are execution limits, not cycle
estimates. The current input ceilings are 3600 seconds and 100 model steps, with
an internal 8192-token response ceiling; these ceilings are not default values.
The run captures its agent’s saved provider/model at admission. Credentials come
from that configured native connection. Later changes affect the next admitted
attempt; see [model selection](agent-model-selection.md).

Work waits for the agent's real private files and Plane workspace/project to be
ready. The dashboard service starts it without a chat prompt. The detail page
shows status, model-call count, native work-session identity and recorded actions.
Saved story versions open in its Markdown reader with the agent's evaluation.
**Pause** stops a queued attempt or terminates the active native worker; the UI
only reports Paused after confirmed process death. Leaving the page does not
stop work or schedule another attempt.

## Execution and persistence

The work run is bound to the initial activation, protected purpose revision and
explicit limits. It uses its own `an_work_` session in Hermes SessionDB. It reuses
ComputeHost, AIAgent, the native tool executor and persistence middleware. It does
not create another chat implementation or model loop.

The worker receives the protected purpose, a fresh Plane snapshot, fixed operation
contracts and the full project-management skill. Its fixed tools are:

- `plane_resource_inspect`: read a scoped project, task or cycle and its fingerprint.
- `plane_operation_execute`: perform the allowed planning operations through the existing host adapter.
- `story_publish`: save story text and its evaluation for a verified work item.

Credentials, grant objects and control-database access remain in the service.
Private process pipes carry requests with the run and native tool-call identities.
The host checks validity at actual model calls, persistence and external-effect
admission. Planning uses existing durable operation IDs and uncertain-write
journaling; an uncertain write ends this attempt without an automatic resend.
Ambient shell, Python, delegation and native scheduling tools are unavailable.

Story paths are chosen by the host beneath the prepared workspace. Each version
has immutable content, hash, Plane item, run/tool correlation and evaluation.
Canonical content is stored in SQLite and copied to the private version file;
the authenticated reader verifies it. Neither a model-supplied path nor a claimed
success message establishes an artifact. The service records actual planning and
publication outcomes. The evaluation is the agent's report, not human acceptance.

## Current boundaries

This increment admits one initial run per agent. It provides no automatic Resume,
recurring cadence, new activation after completion, proactive decision inbox or
chat-driven work steering. Those belong to AN-73/75. Chat remains a separate native
conversation: talking alone neither starts nor resumes work, and the chat context
is not yet a complete view of the agent's project work. Detailed session/tool
inspection and richer artifact navigation remain in AN-74.

A service restart marks interrupted work Outcome unknown and never automatically
replays it. Existing committed stories and planning receipts remain available.
Full reconciliation and continuation are subsequent work. An unfinished run may
retain a valid saved story; the UI must not mistake a later failure for loss of it.

Existing preview agents remain disabled for project work until explicitly
configured. Fixture runs use isolated homes, real native processes and local
external model/Plane servers. A passing scripted-provider flow proves integration;
the separate live evidence below demonstrates actual model-driven writing.
Neither establishes the complete writer milestone.

## Live checkpoint evidence

The owner-requested demonstration on 2026-09-07 created a separate Moonlit
Cartographer agent. Its configured GPT-6 Astra model used the existing ChatGPT
subscription for 13 actual provider calls. It wrote a Plane brief, an undated
cycle and a writing task, then saved **The Bridge That Remembered**, version 1.
The authenticated canonical readback was independently checked: 606 words, with
retained version, task reference and evaluation. The task remains In Progress
for owner review; completion of this bounded attempt does not accept the result.
The main demo's 300-second/20-step limits apply only to that run, with no change
to global defaults or the original three preview agents.

A separate live demonstration reached two model calls before the browser clicked
Pause. UI/API readback and an independent process check confirmed the real native
worker stopped. The exact identities and local recording paths are retained in
[Builder state](../first-builder/STATE.md#an-72-live-demonstration--completed-bounded-checkpoint).
The [captioned live demo](../apps/desktop/demo/writer-2026-09-07/writer-demo.mp4)
is 99.33 seconds, with the working section explicitly sped up 6×. Final visual
and full-video decode checks passed; AN-72 is Done in Plane with this evidence.

Recording also found duplicate work controls caused by colliding sibling React
keys. The regression held a real native writer through at least six actual agent
GET polls: RED grew to 13 Pause buttons. Distinct stable work/story keys restored
one of each panel and control. All six writer Playwright scenarios and the
production web build passed, including actual worker/socket cancellation.
AN-72's bounded checkpoint is complete. The shared-work plan places AN-78/79
before AN-73's continuing conversation work. Cadence, resume, richer
inspection and the full writer journey remain outside this checkpoint.

### Complete output and historical question reads

Managed workers can use `output_read` with an exact output ID and version to read
their own verified saved documents. Context excerpts are not full-document review.
Offsets/limits count Unicode characters (16,000 default, 32,000 maximum); follow
`next_offset` until null. Reading preserves selected work and verifies stored
content integrity. It accepts no filesystem path or another agent's output.

Reading an owned question rechecks its item's project scope and current context.
Changed context returns `applicable:false`, withholds any recorded answer, and
asks the worker to reassess current requirements; it does not fail the run.
Stored history is unchanged. Asking still requires the selected item. A null
answer is never approval, and stale reads do not authorize resuming paused work.

Owner recovery may proceed past an uncertain **terminal failure notification**
only when protected progress and mutation records identify that exact notification.
The unknown receipt remains unknown and is never resent. This exception does not
cover questions, output links, ordinary progress, or task/project changes. The same
classification permits cadence after the owner-recovered attempt completes;
failed work itself still requires owner recovery.

### Owner recovery control

Thinking cadence exposes Retry failed work for the latest failed attempt. The
owner reviews the attempt and confirms Start recovery. The request pins the
failed attempt and purpose revision; repeating an unconfirmed request cannot
create another recovery. A rejected request shows a review message. Paused and
unknown work are not eligible. This manual control does not implement automatic
dependency recovery; AN-75 tracks that remaining work.
