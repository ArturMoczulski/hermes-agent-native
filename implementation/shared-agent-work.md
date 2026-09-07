# Shared agent work and outputs

Status: shared bounded execution and result/output storage implemented on
2026-09-07, with the shared Work planning and output/results views verified and
deployed to the local preview (AN-78 and AN-79 complete).
The owner also added continuous Plane reporting below. The First Builder handoff
remains later. The successful bounded writer
at `9c0bd0b` and live demo/refresh fix at `4164226` remain accepted evidence.

Product authority: [shared work/results](../design/03-projects-and-delegation.md#shared-work-and-results),
[common UX](../design/10-user-experience.md#work-and-results),
[screen contracts](../design/12-control-center-screens.md), and
[writer plus analyst checkpoint](../design/14-first-writer-milestone.md).
This extends those contracts rather than introducing another product specification.

## What changes and what is reused

The earlier writer checkpoint supplied fiction-specific instructions and a fixed
story tool. The shared worker now takes its domain from protected purpose and
supplied context. Its fixed catalog contains scoped Plane reads/writes,
`work_item_select`, `output_publish` and `result_record`; it grants no ambient shell
or browsing tools.
Generic output storage supports text and Markdown, independent output identities
and explicit immutable revisions. A finished attempt requires a recorded result,
which can have an empty output list. Waiting and blocked reports stay explicit;
they do not accept an assignment or fulfill the agent's purpose.

Reuse Hermes AIAgent/SessionDB, the service-owned worker, native TUI conversation,
protected purpose and operation checks, actual stopping and finite run limits.
Reuse the private publication/content verification machinery and Plane's scoped
operations, freshness checks and uncertain-write journal. Do not create another
agent engine, chat implementation, task board or speculative plugin platform.

Separate common execution instructions from selected domain skills. Common
instructions describe purpose, current plan, available operations, result reporting
and evaluation. A writer's fiction guidance belongs to its purpose/skill context;
a supplied-material analyst receives its own task/skill context. Approved skills
cannot grant new tools. Tool availability follows existing enforceable grants and
supported operations, with explicit missing-capability reporting. Do not silently
expose shell, browsing, spending or delegation to make the example seem general.

Use common result and output records: stable result/output identity, agent,
assignment and attempt, purpose/criteria revisions, format, content or reference,
version, integrity and evaluation references. One result can link multiple outputs;
several results may arise from an assignment. Saved content, unverified external
references and independently observed effects must remain distinguishable.
Plane's artifact-reference operation alone is not proof of a stored output.

Ending an attempt, submitting a result, accepting work and fulfilling a purpose
are separate operations. Valid discovery, an observed plan change, a wait or a
blocker need not produce a file. Provider failure, uncertain effects or exhausted
limits remain explicit; an agent's success claim does not erase them.

The initial shared implementation may still admit only one bounded attempt per
agent. Model that as an explicit current admission restriction, not the definition
of agent identity or lifetime. Multiple activations, cadence and Resume remain
in the existing continuity slice; do not enable them by a schema rename.

## Sequence and evidence

Keep implementation WIP one and the existing cycle undated. Each behavior uses
red/green/refactor, with Playwright for its human workflow and actual worker,
storage and permission checks underneath. Planning does not authorize a new live
model run or change any existing agent's capabilities.

| Order | Work | Completion evidence |
| --- | --- | --- |
| 1 | Generalize bounded work and result/output records. | Writer and analyst get appropriate purpose/skills through the same native boundary. Both can save a Markdown output, with verified version/origin. A plan-only outcome is representable without a story. Pause/limits/unknown effects and source authority remain enforced. |
| 2 | Expose shared Work and Saved outputs in the existing interface. | One create/detail flow uses neutral labels. Show the real plan/current assignment/criteria with Plane links and freshness, output opening and result evaluation. Both domains use the existing safe Markdown reader. Reload/switching agents retain correct output and controls. Unsupported decisions/children are honest unavailable states. |
| 3 | Continue shared conversations, decisions and inspection. | Extend existing work items for native chat/work steering and session/history; use shared result links. A question has one durable identity across Chat, Work and Inbox, with observed response handling and pause preserved. General image/audio viewing and full result acceptance reuse existing capability items. |
| 4 | Continue cadence and later child supervision. | Existing continuity/full-writer acceptance remains required. Later registered children reuse these same views, explicit parent scope, result handoff and escalation; own activity differs from descendant activity. Full recursive teams do not block the first shared root checkpoint. |

Near-term acceptance uses two private purposes: a fantasy writer and an analyst
summarizing supplied fictional operational data with recommendations and stated
limitations. The analyst requires no external research, publication or repository
privilege. Also exercise a plan-only result and legitimate waiting/clarification
without manufacturing files. These examples establish general shared mechanics,
not that every profession or integration is already supported.

Begin with text/Markdown production and preview. The existing media-viewer item
owns image/audio preview and a safe open/download fallback, added with real
producers or imports. No agent-authored executable renderer. Controls advertised
as supported must have a real backend operation; future features are not empty
mock dashboards.

## Work planning inspection and explicit selection

The shared Work view reads the prepared Plane project brief, cycles and their
goals, and selected item requirements through an authenticated owner endpoint.
This read-only inspection uses the current prepared account/project and the
existing bounded Plane adapter. It remains available for a chat-only or paused
agent without installing or restoring agent grants, starting work, or exposing
credentials. Configuration, purpose and scope are checked again after external
reads. It is a view into Plane, not another task board.

The managed worker reports its focus with `work_item_select(item_id)` before
substantive work and when it changes items. The host observes that authorized
item and records an immutable selection: item identity, name and description,
cycle membership at selection, assignment fingerprint, time, run and protected
purpose revision. Local receipt recovery returns the original selection without
making an older selection current again. Selection grants no new permissions and
does not accept work. Existing output/result checks remain in force independently.

Show **Current work item** during an active attempt and **Last selected work item**
after it stops. Keep the selected requirements separate from item details observed
by the latest successful Plane check. A difference does not prove the running
agent has adopted an edit. A cached inventory from before a new selection cannot
establish that the selected task is missing or that its requirements changed.
Cycle membership is the snapshot at selection, not a claim that no one has moved
the item since. Historical runs have no invented selection; no priority, status,
cycle order or saved output is a substitute for an explicit record.

Planning loads independently of local run status, on opening the view, changing
its agent/purpose/setup or selection, and **Refresh planning**. Display the last
successful observation time and retain visibly stale data on temporary outage.
Scope or authorization failures clear it; delayed responses cannot populate a
different agent or purpose. Rich item descriptions become readable inert text.
Saved outputs and recorded results retain their existing verified readers and
links. The owner can still pause while planning is unavailable.

This is a bounded initial-run monitoring increment. Selection is not a complete
assignment scheduler, acceptance decision or resumed activation. Cadence, broader
work steering, child supervision and automatic Plane reporting remain their own
tracked work.

AN-79 verification: missing endpoint, missing selection and missing view tests
failed before implementation. A browser regression also reproduced cached older
requirements being misrepresented after a new selection; binding the snapshot to
its selection and using neutral comparison text fixed it. **152 distinct focused
Python tests** passed across owner/scoped reads, planning, selection/replay,
work effects/results/API and native workers. **14 Playwright scenarios** passed
across shared planning, writer and analyst work: active selection, refresh/outage,
reselection and route isolation, safe text, saved output reading and actual Pause.
The production build and scoped lint passed. External Plane/model fixtures are
scripted; framework routes, stores and native worker processes are real.

The idle local preview was backed up and restarted. Authenticated reads and the
built browser verify real Plane planning and the previous saved story. All six
agents, three work states, model-call counts and saved outputs match the backup;
no new live work ran and historical selections remain absent. See
[Builder state](../first-builder/STATE.md) for logs and rollout details.

## Shared activity table

AN-74 owns the owner's paginated activity request. Use the [screen contract](../design/12-control-center-screens.md#9-event-history):
newest first, twenty rows by default, selectable 20/50/100, Previous/Next/Latest
and stable pages with a new-activity indicator. This component is shared by all
agents and links to the same work, session and output records.

Current `read_work()` returns all events ordered by ID, and agent detail/roster
polls repeatedly include that history. Introduce a bounded authenticated history
read; keep routine status/roster responses lightweight. Reuse existing router,
control storage and UI primitives. Enforce the page-size limit at the service;
reversing and slicing the full browser array is not pagination of the data source.

Use deterministic ordering and a stable history boundary while browsing older
pages. Bind continuation state to the agent/run and filters, discard stale UI
responses, and deduplicate by immutable identity. Independent setup, identity and
work event sequences need source-qualified identities if later merged; timestamp
or an unqualified local ID alone is insufficient. Do not invent actor/outcome
fields that current events do not record, or turn missing detail into success.

Before implementation, write a failing Playwright table flow with more than one
hundred real stored fixture events, then cover tied times, new events between
pages, changing page size, agent switching with a delayed response, and empty/error
states. Supporting API tests must prove bounded reads, maximum page size and
owner/scope enforcement. No live model is required for this presentation work.
Activity presentation remains unchanged until these small test-first increments are delivered.

## Plane work mapping

- [AN-78 — Generalize bounded agent work and result records](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/4b7a3d8b-a48d-4e0b-9e01-0645a126cffd/) contains the completed shared execution/records checkpoint and minimal common reader.
- [AN-79 — Show shared Work and Saved outputs for every agent](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/d4143b70-112e-421d-ad5a-288dfc92b48c/) is complete: explicit work selection, real planning context and freshness extend the common output/results workflow.
- AN-73 continues native conversations, decisions and steering; AN-74 owns deeper session/activity/output inspection. Their existing records are generalized, not copied.
- AN-75/76 retain continuity and full owner-journey acceptance; the analyst is an added bounded generality proof.
- AN-6/26/48 retain broader planning, skills and media/review scope. AN-37–45 retain actual child creation, delegation, escalation, recursive monitoring and global Inbox. Narrow subset evidence links back to them.

Current cycle: **03 — Shared agent work and the fantasy writer**, with no planned
dates. AN-78 and AN-79 are complete. The shared Work view now reads real planning
and explicit selections; Saved outputs/Results preserve the writer's ability to
open saved work and exact-version links. AN-80 is next for continuous Plane
reporting and output synchronization.
The original writer milestone/module remains the acceptance home. The new items
also link into the existing governed-work and control-center capability modules.

## Existing work and data

The schema initializer now copies verified legacy story rows into canonical output
records, retaining content, identity/version, original file path, dates, producer
attempt, Plane item and evaluation. It refuses conflicting data and closes the
legacy publisher after upgrade. Legacy read APIs remain available for current
accepted data. New versions use the generic publisher; no generation is rerun.
An isolated migration rehearsal verified the real demo's saved version and file
against a private database backup before switching the live reader.

Results retain protected purpose/revision, agent, assignment and attempt, the Plane
item fingerprint and criteria-description snapshot observed at submission, and
an immutable agent evaluation report. The description hash is a content revision,
not a native Plane revision or proof that the agent evaluated those criteria
correctly. Legacy evaluations remain on imported outputs; migration does not invent
result records or retrospective acceptance. `observed_effects` are confirmed Plane
receipts from the whole attempt, explicitly scoped as such, not proof that each
receipt belongs to this result's item or that an external URL was saved.

Verification includes real native workers against external provider fixtures,
real scoped Plane HTTP/SQLite and immutable files, and browser creation/Pause.
The latest executable evidence and rollout state are recorded in
[Builder state](../first-builder/STATE.md). Scripted model responses establish
integration, not independent planning judgment or quality.

The first story checkpoint stays Done. Broader native-chat ordering remains
owner-deferred. Existing conversation/inspection items adopt shared terminology;
child creation/delegation/escalation and global Inbox keep their original scope
and IDs. Narrow subset evidence links back to broad capability records without
claiming those records complete. See the [coverage index](plane-roadmap-coverage.md)
and live Plane for work IDs, priorities and dependencies.


## Continuous Plane reporting and output links

The owner added [continuous work-item reporting](../design/13-project-management.md#continuous-work-item-updates-and-outputs):
post progress comments while work is happening, apply an owner-controlled
concise/standard/detailed preference, link tangible outputs as soon as saved, and
maintain an Outputs block without replacing the item brief or human edits.
[AN-80 — Report continuous progress and link saved outputs in Plane](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/95bb6694-2030-4c3a-b28f-79a7ade35dbe/)
implements this after the shared output navigation in AN-79 and before broader
AN-73 conversation steering. The cycle remains undated with one implementation
item active. The bundled Plane skill applies the reporting convention now,
including to the externally hosted First Builder.

Existing `comment.create` supplies scoped plain-text comments with mutation IDs;
`artifact.record` posts an explicitly unverified reference. Neither is automatic
progress delivery, a verified saved-output link or an attachment upload. Existing
`item.update` converts a supplied plain-text description to HTML, so it cannot
safely maintain a section in arbitrary rich human text by flattening that text.
Reuse the scoped adapter, grants, freshness checks and mutation journal; add the
missing verified output-link/section operation and durable reporting delivery.
Retain sender/item/attempt IDs and pending, confirmed, failed or unknown status.
An unknown write must be reconciled before retry; it must not create duplicate
comments or output sections. Reporting failure cannot delay Pause.

First write a failing Playwright scenario that holds a real native worker after
a meaningful checkpoint and proves its comment already exists in Plane. Then
cover verbosity, saved-version opening from the item, update/restart idempotence,
a concurrent human description edit, outage and actual stop. Add the visible
verbosity control together with its owner-authorized persistent setting; do not
ship a selector that merely changes a local label. Saved drafts remain awaiting
evaluation, and file-free results do not manufacture an attachment. Runtime
reporting automation and rich-description synchronization remain AN-80 work.

### AN-80 first increment: work-selection progress

The host commits a progress intent in the same transaction as each new explicit
work selection. It then uses the existing scoped `comment.create` adapter and
mutation journal to post the selected item and next action, with actual agent,
item and run IDs. Selection replay returns the same result without another
comment, including after loss of the broker receipt. No historical selections
are backfilled and no existing agent is started.

The agent detail page shows the latest twenty delivery records, newest first.
Confirmed requires an acknowledged comment receipt. An uncertain network result
stays unknown and is not automatically retried; failure to report does not claim
that execution failed or that the work was accepted. Intent and external mutation
IDs remain available for later reconciliation. Pause retains its independent
process-stop path.

This is the first verified increment, not completion of AN-80. Owner verbosity,
additional checkpoints/outcome reporting, output links/description sections,
and an owner reconciliation flow remain open. The focused browser test holds a
real worker after selection and verifies that Plane already contains the comment;
reloading does not duplicate it, and Pause stops the run. Local scripted model
and external Plane fixtures incur no paid inference.

### AN-80 second increment: owner verbosity and checkpoints

Each agent has an owner-only reporting preference with a revision: concise,
standard (initial value), or detailed. The agent detail editor persists it with
stale-edit protection. Changes govern subsequent reports, not past receipts.
The managed worker uses `progress_report` for checkpoint, detail or blocker
updates on its currently selected item. Summaries, reported evidence and next
actions are bounded; comments carry host-supplied agent/item/attempt identity.
The model supplies reported evidence, not independent verification.

Standard delivers checkpoints; detailed also delivers smaller updates. Concise
suppresses both. Blockers and host selection updates remain unconditional.
Suppressed tool receipts stay suppressed on replay after a preference change.
Managed direct `comment.create` is refused so it cannot bypass this reporting
control; the scoped host adapter still uses that operation for actual delivery.
Saved-output references and end-of-attempt outcomes remain the next increment.

A focused browser case saves Detailed, reloads, then holds a real native worker
with both checkpoint and detail comments already in the Plane fixture. Supporting
checks cover concise/standard filtering, blockers, stable replay, wrong-item
rejection, stale/invalid settings and unauthenticated requests. No paid inference.

### AN-80 third increment: saved evidence and attempt outcomes

Saving an output or result now atomically records its reporting intent. Plane
comments link to the exact output version or recorded result, using the
operator-configured dashboard public URL. Missing configuration produces an
honest metadata-only report. Links contain no credentials and retain normal
dashboard authentication. Output/result/outcome reports are independent of verbosity.

Terminal state queues an attempt-status report; a bounded host delivery pass runs
after worker shutdown handling, so Plane cannot delay stopping the process.
Current purpose and planning authority are revalidated. Unknown acknowledgements
are retained without automatic resend. A saved output, an agent result, owner
acceptance and purpose completion remain separate facts. No historic backfill.

Verification: a scripted native-worker browser case observes the output comment
before completion, opens its exact saved version, then opens the recorded result
and checks the terminal comment. Eight focused domain tests cover atomicity,
version replay, file-free results, stopping, altered links, lost acknowledgements,
schema upgrade and changed-purpose authority. Three existing comment-format
regressions protect plain-text behavior. Rich Outputs sections and owner delivery
reconciliation remain open; this increment does not complete AN-80.

### AN-80 fourth increment: explicit pending description sections

The current Plane API ignores `If-Match` (see [the live API evidence](plane-api-validation.md)).
A read/merge/PATCH cannot guarantee preservation of a simultaneous human edit.
Consequently the host does not issue automatic description writes. The agent
page shows **Description update pending**, its reason, exact saved-version and
result links, and selectable reference text grouped by work item. This implements
the product's non-destructive conflict fallback, not automatic synchronization.

The proposal is derived from durable evidence-report intents for the attempt,
including prior versions and terminal reports, independently of the latest-20
comment table. A confirmed comment cannot confirm the description. File-free
results do not invent attachments. Repeated reads/reopens cannot duplicate a
section or send a mutation. References can be reviewed manually against the
current Plane item; no control claims a manual paste was verified.

Automatic merging remains blocked on a verified atomic conditional-write operation
in Plane. A second preflight GET or a framework-only lock is insufficient because
human editors do not participate in that lock. Do not introduce direct Plane DB
writes or claim current fingerprint checks solve this race. Owner reconciliation
of uncertain comments is the next independent delivery increment.
