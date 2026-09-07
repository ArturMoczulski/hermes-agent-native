## AN-80 verbosity and checkpoints — 2026-09-07

Owner-only per-agent progress settings now persist concise/standard/detailed
with stale-edit protection and default Standard. A private managed progress_report
tool reports bounded summary, evidence and next action on the selected item.
Checkpoint/detail delivery follows the current preference; blockers are retained.
Direct managed comment.create is refused to keep reporting on this path. Prior
suppressed and delivered receipts are not reinterpreted when preferences change.

Red: missing settings editor and API functions. Green: real native-worker browser
case saves/reloads Detailed and sees both checkpoint/detail comments before the
worker finishes (5.0s). Domain verbosity case passed. Five focused delivery/settings/scope checks subsequently passed;
scoped Ruff and production TypeScript/Vite build passed. The idle preview was
refreshed and its built Standard preference editor visually verified. Evidence:
/tmp/an80-verbosity-{red,green}.log and /tmp/an80-verbosity-browser-{red,green}.log.
Next AN-80 work: saved-output linking, end-of-attempt outcomes, preserved rich
Outputs sections, and owner reconciliation with outage/stop acceptance. AN-80
remains In Progress; AN-73 follows. No live inference was used for these checks.

## AN-80 work-selection progress increment — 2026-09-07

AN-80 is In Progress. A new explicit work selection now atomically stores a
host-authored progress intent, then sends a scoped Plane comment with actual
agent, item and attempt identity. Broker replay does not duplicate delivery.
Lost HTTP acknowledgement remains Unknown, without automatic retry or false
work failure. Agent detail has a latest-20, newest-first delivery table.

Red: native worker ran with a selection but no Plane comment; both attribution
and lost-response storage tests failed on missing comments. Green: the browser
case passed in 7.4s; two storage cases passed in 1.3s. Evidence logs:
/tmp/an80-progress-{red,green}.log and /tmp/an80-storage-{red,green}.log.
Four affected focus regressions also passed (replay, rollback, stop and changed
purpose); focused Ruff and production TypeScript/Vite build passed. The idle
preview was restarted and its built progress panel verified. Historical runs
have no fabricated reports; no live work was started.
Models and Plane responses are local scripted fixtures; no paid inference.

Remaining AN-80: per-agent verbosity, meaningful additional checkpoints and
outcomes, immutable saved-output links and rich-description preservation,
owner reconciliation, outage/stop acceptance. Do not mark AN-80 Done based on
this first increment. AN-73 follows AN-80.

## Reasoning-default clarification — 2026-09-07

Owner requested actionable reasoning labels and the lightest Astra default.
Default/agent settings now open their own effort editor when the label is clicked.
Runtime automatic means built-in transport behavior, not global profile inheritance.
Fresh Astra creation defaults use Low; saved owner choices remain authoritative.
Targeted storage test failed on default versus low, then passed; the browser case
failed on the absent control, then passed (6.1s). Two storage cases passed.
Logs: /tmp/an83-default-{red,green}.log and /tmp/an83-link-{red,green}.log.
Production web build and focused Ruff passed. Live preview restarted idle; owner
API set the creation default and six automatic Astra agent preferences to explicit
Low. The live clickable editor confirmed Low; no inference was launched.
Next: AN-80 continuous progress comments and saved-output links in Plane.

# First Builder — current work and handoff

Updated: 2026-09-07. Working branch: `codex/astra-capability-proof`.
Active repository: `/Users/arturmoczulski/Projects/hermes-agent-native`.

## Current focus

Owner reprioritization: the current undated cycle 03 is now **Shared agent work and the fantasy writer**, before the First Builder handoff. The
[writer specification](../design/14-first-writer-milestone.md) and
[delivery plan](../implementation/fantasy-writer-milestone.md) define its complete
acceptance: ordinary root creation and immediate work, real saved stories,
durable chat/questions/steering, activity/session inspection, cadence, evaluation,
actual pause and basic restart recovery. One story is only an autonomous-work checkpoint.

Read [Plane](PLANE.md) for live state: AN-71 aggregates the writer milestone.
**AN-72, AN-78, AN-79, AN-27 and AN-83 are complete. AN-80 is next, then AN-73.** The captioned live demo video is
verified, and the completed item retains its evidence and scope. The owner
deferred AN-77's remaining purpose-revision/transcript ordering; AN-77 remains
Todo with accepted native chat, receipts, deadlines and full-service-restart
evidence at `b6c59aa`.

AN-72 now connects explicit owner run limits, existing private setup, native
Hermes execution, scoped Plane planning, immutable story versions and actual
Pause. The current Agents detail page displays work state, activity, sessions,
limits, shared outputs and reported evaluation. See [managed writing](../implementation/writer-managed-run.md).
Conversation remains native and separate; no duplicate composer or model loop.

The owner requested an actual recorded demonstration. A new, separately created
writer completed a real subscription-backed run; a separate demo agent proved
live UI Pause. The original three preview agents remain unchanged and unconfigured
for project work. The main demo used explicit limits of 300 seconds and 20 model
steps; these values apply to that demonstration, not unattended or global defaults.

Current: AN-78 has shared bounded execution, immutable text/Markdown outputs and
explicit result reports with or without files. The shared reader is verified and deployed, so newly saved writer and analyst
outputs remain accessible through the same interface. AN-79 now provides real
project/cycle planning, explicit current or last selected work and requirements,
freshness and direct Plane links. AN-80 adds the
owner's continuous Plane progress comments, persistent verbosity preference and
verified output links/description sections. The bundled Plane skill now instructs
incremental reporting; the external Builder posted and read back a progress comment
on the active AN-78 and AN-79 items while verification was still in progress.

AN-73 then continues conversation, questions and steering. AN-74 covers detailed
inspection and paginated activity; AN-75 cadence/resume/recovery. AN-76 and the full
writer milestone remain open. The First Builder still runs through the external
coding environment. Earlier next-step entries below are historical.

## Reasoning effort — AN-83 complete

Plane item `2fce2f02-2997-4538-b3ad-270dd1f562a3` extends model settings with
reasoning effort. The owner can choose a default for new agents, override during
creation or edit an existing agent. Exact route-supported levels appear in the
native model picker. Incompatible retained effort blocks Save until the owner
chooses a supported value. Hermes default preserves native transport behavior;
it does not mean reasoning is off. Unknown routes expose this default alone.

Four setting/event/attempt tables receive an additive column. Existing records
and omitted-field creation retries retain their meaning. Effort-only changes use
the existing setting revision, preserve identity/history and affect the next
admitted run/message. Native constructors use the captured preference. The final
request guard rejects dropped, clamped or rewritten explicit efforts. Astra’s
native Responses mapping now matches its documented low/medium/high/xhigh/max
API vocabulary; Codex app Ultra orchestration is not exposed as an API effort.

Red: two owner API cases failed on the missing field/endpoint; three capability
cases and three native request cases exposed missing metadata/unguarded effort;
the browser lacked its reasoning selector. Green: three new settings/upgrade
cases and two existing creation regressions, six runtime cases and three existing
native regressions. The upgrade test reopens the real pre-feature database through
native initialization and verifies idempotent migration and old creation retries.

One focused Playwright scenario passed in 24.4 seconds. It proves default copying,
creation override, an unsupported model/effort combination, lost-response retry,
a held active work selection, effort-only editing and held chat followed by a new
message using the new wire effort. Real native worker requests reach only the
local scripted provider. Logs: `/tmp/an83-settings-red.log`,
`/tmp/an83-settings-green.log`, `/tmp/an83-upgrade-green.log`,
`/tmp/an83-browser-red.log`, `/tmp/an83-browser-green.log`.
The initial browser red waited the full scenario timeout for a missing control;
short visibility/option assertions now make that stage fail promptly. Scoped
Ruff/ESLint and production TypeScript/Vite build pass (`/tmp/an83-web-build.log`).
No full suite, paid inference or live judgment evaluation ran.

Local preview restarted while idle with its existing home/database. Existing
agents retain their model and Hermes-default reasoning. A read-only owner UI
check confirms Astra’s available effort levels and Cancel without saving a live
change. Screenshot: ignored `apps/desktop/demo/reasoning-settings-2026-09-07/`.
AN-80 is next: continuous work-item comments with verbosity and verified output
links/description sections, followed by AN-73 conversations and steering.

## Model selection — AN-27 complete

Default provider/model settings are copied at creation, with optional per-agent
overrides and later owner edits. Reuse of the native model picker and configured
connections keeps credentials outside agent state. Default changes leave older
agents unchanged. Independent revisions and immutable original creation input
protect concurrent edits and lost-response retries, including a retry after the
original connection is removed. Existing agents retain their explicit native
profile choice, without changing their purpose, history or work.

Work captures a selection at admission; chat captures it with its accepted
message. The native worker resolves that exact connection and keeps it throughout
the attempt. A settings edit affects the next attempt. Managed runtime fallback
and auxiliary inference remain disabled; a final request guard rejects middleware
model substitutions before network I/O. Missing configuration cannot consume the
initial work attempt. The UI separates the saved choice from current/last work
and recent chat selections. See [product requirements](../design/15-model-selection.md)
and [implementation](../implementation/agent-model-selection.md).

Focused red/green evidence: three initial settings/API cases and the initial
browser workflow failed on missing behavior, then passed. A review regression
proved unconfigured work incorrectly allocated an attempt; its fix and explicit
retry-after-edit/removal case pass. Resolver/admission/native-chat tests cover
exact named connections, strict routing and retained history; two middleware
mutation cases verify no provider request escapes. Existing work creation,
paused/unpaused planning, uncertain Plane writes, work selection and no-file
results pass with explicitly isolated model fixtures.

All three new browser scenarios pass. Actual held work stays on its admitted
provider/model after an owner edit. Held chat does likewise, and the next message
uses the new endpoint/model with the same conversation. Two intermediate failures
were test synchronization mistakes: streamed text preceded receipt completion,
and a fresh composer has no persisted file until first input. The helper now
waits for settled receipts after the first submission, with draft checks before
every Enter. No browser retry hid these failures. Logs: `/tmp/an27-browser-green.log`
(first workflow), `/tmp/an27-browser-final.log` (default-outage guard), and
`/tmp/an27-browser-runtime-green.log` (final native routing, 20 seconds).
API evidence: `/tmp/an27-settings-green.log`, `/tmp/an27-unconfigured-green.log`
and `/tmp/an27-fixture-regressions.log`. Scoped Python Ruff, frontend ESLint,
TypeScript and the production web build pass. No full suite or paid inference ran.

The local preview was restarted while idle with its existing home and database.
Existing agents retain `openai-codex / gpt-6-astra`; the owner can now change them
or the new-agent default through the UI. These live choices were not changed as
part of testing. Read-only preview inspection verifies the loaded controls and
configured picker; screenshots are in ignored
`apps/desktop/demo/model-settings-2026-09-07/`. The standard test model remains
local and scripted; no live model-quality evaluation was needed. AN-80 follows:
continuous Plane progress comments, verbosity and verified output traceability.

## Narrated main-feature tour — AN-82 complete

The owner requested a shorter product walkthrough with spoken explanation,
separate from the exhaustive AN-81 test video. The new tour covers purpose-based
creation, private Plane setup, bounded current work, project/cycle/task planning,
retained native chat, activity, exact-version outputs, result evaluation, a shared
analyst example, real Pause, and today's limits. The 4:37.8 video is 1600×1120
with 11 chapters and 6–24-second result holds. Voiceover is generated locally
with macOS Samantha; no paid speech service or live model was invoked.

Local artifacts (ignored by Git):
`apps/desktop/demo/features-2026-09-07/agent-native-narrated-feature-tour.mp4`,
`index.html`, `transcript.md`, `capture-manifest.json`, and `narrated-tour.json`.
The bundle retains raw browser clips, checkpoint images, narration sources and
the artifact assembly script. Capture uses the real built application, framework
API, isolated storage and native worker/tool execution, with controlled model and
Plane HTTP responses. This demonstrates the implemented interaction, not fresh
live-model judgment. Personal preview agents and live work were unchanged.

The narration explicitly separates conversation from active-work steering,
self-assessment from independent acceptance, and bounded runs from future cadence,
resume, children, decisions and richer inspection. Full audio/video decoding
passed; final frames, chapter boundaries, source hashes and narration duration
were checked. Final-film chat, planning, writer/analyst
outputs and Pause frames were visually inspected. The local chapter player opens,
plays and seeks in installed Chromium. No product behavior changed and no broad
test suite was run. AN-80 remains the next implementation slice.

Capture observations retained for follow-up: the setup panel keeps its static
“Execution has not started” sentence after execution begins, and a chat reload
can display an unsupported terminal-resize warning. A normal fresh attachment
restored a clean view with both exchanges retained; the warning screenshot
remains in the evidence. Neither issue was patched for the recording.

## Owner brainstorm captured — 2026-09-07

Saved [foundational skills and parallel internal roles](../design/ideas/2026-09-07-foundational-skills-and-internal-roles.md)
in the new non-normative ideas folder. It preserves shared versus specialized
skills, concurrent communication/work/review roles, and the speculative one-way
subconscious-signal analogy. Architecture, defaults and signal visibility remain
open. The owner requested notes only; no runtime or delivery priority changed.
AN-80 remains next. Verification: documentation consistency and local links.

## Readable end-to-end demonstration — AN-81 complete

The owner requested a video of all implemented framework browser scenarios, with
clear expected outcomes and enough time to inspect the verified results. Opt-in
`AN_E2E_DEMO=1` checkpoints now annotate assertions already passed, highlight the
screen, capture exact screenshots and hold for five seconds. Dedicated recording
configs preserve 1600×1000 browser videos. Default verification has no annotation
or viewing delay; one named normal-mode creation case passed in **2.5 seconds**.

All **30 distinct framework browser scenarios** have passing final recordings:
28 default and two full-service-restart scenarios. There are **47 proof
checkpoints**. The initial default run passed 27/28; a documentation edit caused
Tailwind/Vite to reload the browser during the remaining test's deliberately
blocked API request. The trace navigation occurred 123 ms after the Markdown
edit. The same named scenario passed when re-recorded with edits paused; product
code and assertions were unchanged. The original failure, trace and successful
rerun are retained. Do not edit watched files while recording Vite.

The captioned MP4 is **13:33.2**, 1600×1120, with actual browser footage, labeled
playback acceleration and 8–12-second exact screenshot holds. The separate bottom
strip preserves the complete application viewport. `index.html` provides clickable
chapters; `evidence.json` records final reporter outcomes, attempt history, hashes,
source timings, frame counts and measured duration. The reusable
[assembler](../scripts/assemble_e2e_demo.py) rejects missing/failing final coverage.
See [recording instructions](../web/e2e/README.md#readable-test-demonstration).

Local artifacts (ignored by Git):
`apps/desktop/demo/e2e-2026-09-07/agent-native-e2e-demo.mp4`, `index.html`,
`chapters.md`, `evidence.json`, and `raw/`. Capture logs:
`/tmp/an81-demo-default.log`, `/tmp/an81-demo-restart.log`,
`/tmp/an81-demo-creation-rerun.log`; assembly log:
`/tmp/an81-assembly-encode.log`. Full MP4 decoding completed without errors.
Representative final-film frames, including chat drafts/replies, uncertain
restart, writer and analyst output, API rejection and the outage rerun, were
visually inspected. Frame counts and final duration match the edit plan. Scoped
ESLint, TypeScript and Python Ruff checks passed. No application build or broad
unit suite was required for these recording-only changes.

The real browser, framework API, databases, files and native worker processes are
exercised; **model and Plane responses are isolated HTTP fixtures**. This proves
current integration behavior, not live-model judgement or future requirements.
No personal preview or live agent was changed and no live model was invoked.
The earlier AN-72 live demonstration remains separate evidence. AN-80 remains
next: continuous Plane progress comments, verbosity and output traceability.

## Owner testing convention — 2026-09-07

Future work defaults to named test cases, including Playwright, under
[targeted verification](PRACTICES.md#targeted-verification-by-default). Broader
coverage requires an identified impact or gate; passing checks are reused until
relevant changes invalidate them. Earlier large verification runs below are
historical evidence, not the default testing recipe. This instructions-only
change used documentation checks, without application tests or runtime changes.
AN-80 remains the next implementation item.

## Shared Work planning — AN-79 complete

The common create/detail UI uses work labels for all purposes. Work planning
shows the prepared Plane project brief and cycle goals, an explicit selected item
and its requirements, the recorded cycle at selection, direct Plane links and the
last successful planning check. Current selection is distinct from last selection
on a stopped attempt. Historical runs never acquire a guessed assignment.

The host admits `work_item_select(item_id)` through the existing private worker
boundary. It records immutable selection history and an event atomically; lost
receipt replay cannot make an old selection current again. The worker now has five
fixed tools: scoped Plane inspection and operations, explicit selection, output
publication and result recording. Selection cannot widen authority or accept work.
The owner planning API can inspect prepared chat-only/paused agents independently
of revoked agent grants, without installing grants or starting a worker.

Planning loads separately from live local state and offers Refresh planning.
Temporary outage keeps visibly stale data; scope changes discard it. Requirements
observed in Plane stay separate from the selection snapshot. Independent review
found an older cached snapshot could be described as a change after reselection;
a real held-worker/browser test reproduced that failure. The fix binds comparison
to the selection that requested the snapshot and uses neutral last-check wording.
Decision handling and child controls are explicitly unavailable in this increment.

TDD evidence: endpoint and selection failures preceded implementation. **152 distinct
Python checks** passed: planning API/Plane reads/writer planning (104), focus/work
effects/results/work API (39) and native workers (9). Logs:
`/tmp/an79-planning-final-green.log`, `/tmp/an79-focus-regression.log` and
`/tmp/an79-focus-green.log`. **14 Playwright scenarios passed** in
`/tmp/an79-ui-final-regression.log`, including shared writer/analyst outputs, actual
Pause, limits, selection, changed requirements, outage, reselection and route
switching. RED logs are `/tmp/an79-ui-red.log` and
`/tmp/an79-ui-reselection-red.log`. Production build and scoped lint passed:
`/tmp/an79-ui-final-build.log` and `/tmp/an79-ui-final-lint.log`.

Preview at `http://127.0.0.1:19221` now runs the tested build (PID **60055**).
Before restarting the exact idle preview, its control database was backed up to
`~/.hermes-agent-native-preview/backups/work-planning-2026-09-07/kanban.db`.
Authenticated planning/output reads and the actual built browser succeeded; all
six agents, three work states and model-call counts, and saved-output records and
content are unchanged. The historical demo has no invented work selection.
`/tmp/an79-preview-planning.png` was visually inspected. No new live model run was
started. AN-80 is the next slice; automatic Plane reporting is not implemented yet.

## Shared bounded work — AN-78 verification

Native work now uses the same restricted tool catalog for writer and analyst
purposes: scoped Plane operations, output publication and result recording. Result
reports retain purpose/criteria provenance and explicit outcomes; a file alone no
longer makes a run successful. Waiting/discovery can legitimately have no file.
A report never implies accepted work. Late completion after a purpose change or
expired limit is paused, retaining prior evidence without claiming completion.

The output store supports several outputs per assignment and immutable explicit
revisions. Migration keeps original story content, file paths, identity/version,
attempt/item origin and evaluation. The old writer is closed after upgrade. A
rehearsal on a private copy of the preview database verified the one existing demo
story and physical file without changing the live database.

TDD evidence: native catalog/output/result RED then 9 native worker tests passed;
result broker RED then 19 result checks passed, including two reproduced late
completion races. Output migration's late legacy publisher regression failed
before the guard and passed afterward. The final focused Python run passed **93
tests across seven files** (`/tmp/an78-final-python.log`). Browser foundation
checks passed **9 scenarios** (`/tmp/an78-shared-browser-green.log`) with real
framework/native execution and scripted external Plane/model services. Those first
browser checks retrieved new content through the owner API; they do not establish
a human reader. The subsequent shared-reader RED proved the missing UI; **10 Playwright scenarios
passed** after implementation (`/tmp/shared-output-browser-green.log`). These cover
writer and analyst Markdown reading, literal plain text, exact-version deep-link
reload and error handling, file-free results, Pause and limits. Production web
build and scoped lint passed (`/tmp/shared-output-build.log`,
`/tmp/shared-output-lint.log`, `/tmp/an78-lint.log`). No new live model demonstration has been launched.

At the AN-78 checkpoint, the tested backend and built reader were running at
`http://127.0.0.1:19221` (then preview PID 36743; superseded by AN-79 above). The exact idle process was checked
before restart. Its control backup is
`~/.hermes-agent-native-preview/backups/shared-work-2026-09-07/kanban.db`.
All six agents, three completed/paused work states and model-call counts were
verified unchanged after migration. The original story content/hash/evaluation
matches the backup; the actual built browser opened its new exact-version link
with no alerts. No generation was rerun. The story is now in Saved outputs;
its older evaluation stays attached to that output, without an invented result.
The minimal reader uses `?output=<UUID>&version=<integer>` on the agent route,
requires ordinary owner authentication and preserves missing-version errors. AN-80 is specified and planned, not a claim that
runtime verbosity or continuous delivery is already implemented.

## Shared work planning — record before implementation

The owner identified profession-specific UI and asked for shared Work, results,
plans, decisions and children, using Saved outputs instead of Saved stories.
The existing product already specifies generic concepts; this update clarifies
their relationships and selects delivery rather than adding a parallel design.
The writer remains the complete first usable-agent example, with an analyst and
plan-only outcome added to prove that the common executor and result model are
generic. Unsupported decision/child operations must be labeled unavailable.

Plane adds AN-78 (shared bounded execution/results, urgent) and AN-79 (shared
Work/output UI), both Todo, to undated cycle 03 and existing capability modules.
Existing AN-73/74 records adopt generic names; AN-71/76 gain the generality proof.
Selected broad planning/skill/output/child/Inbox records receive scope links;
accepted AN-72 and deferred AN-77 are preserved. Full teams, global Inbox, media
viewing and continuity retain their existing accountable work rather than being
implemented as placeholder screens. No code, runtime state, skills or grants were
changed, and no tests or model calls were run for this documentation-only plan.

Verification: 165 local documentation links/anchors resolve; whitespace checks
pass. Plane API readback confirms the two unique Todo items, their dependencies
and cycle/module membership, preserved completed/deferred states, and null dates
on every cycle. Independent design review found no contradictions in the selected
work/result, evaluation, capability or child-boundary contracts.

## Shared Activity table — planning refinement

The owner requested newest-first activity in a paginated table, twenty rows by
default and adjustable to one hundred. The screen contract now specifies
20/50/100, Previous/Next/Latest, stable pages and a new-activity indicator. AN-74
retains this work; no extra item or priority change is needed. Its implementation
must stop returning the full event history on routine status/roster reads, enforce
bounded scoped pages, and test new arrivals/tied times/agent switches. Domain-neutral
views and truthful unavailable states remain the shared UX direction.

This is a documentation/Plane refinement only. Runtime code and agents are
unchanged; no browser or model run was started. Verification is recorded with
the planning update; implementation still follows the selected TDD sequence.

## AN-72 live demonstration — completed bounded checkpoint

On 2026-09-07, [Moonlit Cartographer — live demo](http://127.0.0.1:19221/agents/f6889031-7c56-482d-b395-49cd8584c12e)
completed 13 actual GPT-6 Astra calls through the configured ChatGPT subscription.
It authored a Plane project brief, an undated cycle, a writing item with acceptance
criteria, and a recorded result/evaluation. It published **The Bridge That
Remembered**, version 1, with 606 words in the independently checked canonical
story content. This is real-model evidence in addition to the external-provider
fixture checks below; it does not establish artistic quality or a continuing cadence.

The [demo Plane project](http://localhost:19230/an-f68890317c56482db39549cd8584c12e/projects/026e1ed4-f6fc-442e-8e38-ef50f2104533/issues/)
retains the writing task In Progress for owner review. A completed native attempt,
saved version and agent self-evaluation do not bypass terminal result acceptance.
The main native worker, PID 80327, was independently confirmed dead after completion.

A separate [Pause control — verified demo](http://127.0.0.1:19221/agents/6d27e238-bfaf-4f58-99b0-9f0ad5672964)
reached two model calls. The actual browser clicked its unique Pause button; both
UI and API reported Paused. A separate read of the control database and process
check confirmed native worker PID 92265 was dead. An earlier Pause recording
encountered the duplicate-control bug below; its worker PID 84338 was stopped
through the owner API. That earlier clip is not evidence of a successful UI click.

The live recording exposed duplicate sibling React keys on the work and story
panels. A new Playwright regression kept a real held-model writer on its detail
page across at least six actual successful polling responses. RED accumulated
13 Pause controls. Distinct stable sibling keys fixed the defect; all six writer
scenarios passed, including one work panel, one stories panel, one Pause control,
then actual worker/socket termination. Scoped lint and the production web build
passed. Logs: `/tmp/an72-duplicate-controls-{red,green,build}.log`; the RED trace
is retained at `/tmp/an72-duplicate-controls-red-trace.zip`.

Local evidence is intentionally ignored by Git under
`apps/desktop/demo/writer-2026-09-07/`: `capture.json`, `story.json`, the raw UI/Plane
recordings, and `pause-verified-capture.json` / `pause-verified-live-raw.webm`.
The [captioned demo video](../apps/desktop/demo/writer-2026-09-07/writer-demo.mp4)
is 99.33 seconds, H.264 at 1600 × 1120. Its working section is explicitly sped
up 6×; cuts and timing are recorded in `video-edit.json`. Final frames were
visually checked and the full video decoded without errors. AN-72's Done state
and evidence were independently read back through the Plane API.

## AN-72 bounded native writer — implementation evidence

- Creation or explicit existing-agent configuration saves one initial work run.
  Creation input remains immutable across retries and later work configuration.
- Service-owned ComputeHost uses real AIAgent/SessionDB and the protected purpose,
  fresh Plane context, full planning skill and a fixed three-tool catalog. The
  worker receives no Plane credentials or owner capability. Native model calls,
  persistence and broker effects require parent admission.
- Plane operations reuse existing grants, fingerprints and mutation journaling.
  A lost mutation response stops work as Outcome unknown and cannot trigger an
  automatic new operation. The original journal stays available for reconciliation.
- Story publication validates its Plane item, saves immutable host-chosen versions
  and records canonical content/hash/evaluation. Owner API and Markdown reading
  expose committed versions; a later failure retains already-saved stories.
- Pause terminates the actual native worker and closes its held provider socket.
  Both time and model-step limits are enforced. No recurring cadence or automatic
  Resume is part of this initial run. Terminal task acceptance remains separate;
  a saved draft and self-evaluation are handed off for owner review.

Verification: 15 installed-Chromium scenarios passed, covering actual creation,
setup, native chat, full planning/story reading, navigation/reload, Pause and both
execution limits (`/tmp/an72-final-browser.log`). 152 focused Python tests passed
across nine files: identity/API, setup, Plane writes, writer planning, broker,
versioned story storage and native worker (`/tmp/an72-final-python.log`). The web
production build passed. External Plane/model servers are fixtures; framework
storage, API, processes, native execution and renderer are real. Existing native
worker/chat-policy regression batches were also verified by the delegated work.

Browser red/green work found the macOS `/var` host-root alias at publication;
only the trusted installation base is canonicalized, preserving no-follow checks
inside the agent workspace. Planning retains its existing prohibition on terminal
Plane task states; the fixture now records a ready-for-review result rather than
bypassing acceptance. One additional real-process regression reproduced and fixed
a deadline fairness issue: a blocked SQLite writer cannot delay termination of
another expired native worker. Both PIDs and provider sockets now close while
the control write lock remains held, then state settles after release
(`/tmp/an72-work-deadline-contention-green.log`). This brings focused Python
evidence to 153 passing tests. All five writer browser scenarios passed again
after that fix (`/tmp/an72-writer-release-browser.log`), and the final web build
and scoped lint passed. All 68 changed-document local links resolve.

Before the live demonstration above, the preview at http://127.0.0.1:19221 was
restarted on the same private home and database (verified PID 76228). Its three
original IDs/purpose revisions and configured `gpt-6-astra` model were preserved.
All three had no configured work run, and that deployment smoke check did not
launch live provider work. The subsequent demo created separate agents.

## AN-77 full service-restart recovery — previous accepted increment

Managed chat now recovers automatically when a service restart rotates the local
owner session token. The existing native ChatPage performs an authenticated,
read-only agent lookup before connecting its PTY. This exposes HTTP 401 to the
existing guarded dashboard reload; browser WebSocket rejection alone appeared as
1006 and previously retried the stale token indefinitely. Connection timeout and
unmount cancel the lookup; stale attempts cannot open another socket. Ordinary
native chat retains its existing connection path.

Two installed-Chromium scenarios kill only a disposable real backend, observe the
exact renderer/worker processes disappear, and restart against the same private
home with a new normal dashboard token. The external model fixture stays alive.
Saved exchanges and unsent drafts return without navigation, manual reload or
resend. A held model request loses its actual socket; native storage and composer
both recover the same UUID/text as unknown. The native UI explains /acknowledge;
an explicit subsequent message completes in the retained conversation. Exact
transcript and provider counts reject automatic replay or late results. Project
execution remains not_started; no autonomous-work recovery is claimed.

TDD: the first setup attempt exposed an early transcript polling error and fixture
teardown issue, both corrected before product evidence. The actual RED then
showed an expired browser token after a successful real service replacement
(`/tmp/an77-service-restart-red2.log`). The reconnect fix passed both scenarios
(`/tmp/an77-service-restart-green1.log`). Existing auth/reconnect unit checks:
13 passed (`/tmp/an77-service-restart-unit.log`). Dashboard type-check/build and
Ruff passed. ESLint reported zero errors and three existing ChatPage hook warnings
outside the change. Independent review checked authority, cancellation, exact
process evidence and observational receipt reads.

All 16 distinct browser scenarios passed: the two full service-crash checks,
13 existing scenarios in `/tmp/an77-service-restart-regression.log`, and the
renderer-recovery scenario in `/tmp/an77-service-restart-renderer-final3.log`.
The latter needed test-only corrections for VT line wrapping and late frames from
an agent being left behind during navigation. It now requires frames from the
selected agent's own PTY, compares complete saved drafts, verifies the other
agent's composer is empty, and retains exact transcript/model-count assertions.
The final test version passed. All 27 local documentation link targets resolve.

The preview serves the rebuilt ChatPage asset; readback preserves all three agent
IDs/revisions and gpt-6-astra configuration. No service restart, owner conversation
submission or paid model call was needed for this frontend change. Existing open
tabs need one reload to acquire the new bundle.

Next: AN-77 purpose-revision/transcript ordering. Keep AN-72 waiting; managed
writing, saved story artifacts and actual Pause remain unimplemented.

## AN-77 host deadline — previous increment

Each admitted managed owner message now runs in its own native ComputeHost.
The parent keeps routing/receipt metadata; the worker reuses AIAgent, protected
instructions and the same SessionDB transcript. Ordinary conversations retain
their existing path. `agent_native.managed_chat_timeout_seconds` defaults to 90,
is validated on admission, and includes startup. The native iteration/token
limits remain in place; no unattended writer defaults were selected.

The deadline kills/reaps only that worker before waiting for admission, event or
SQLite locks. Its immutable attempt binds agent/revision, native session, UUID,
receipt owner and deadline. Native lease acquisition/refresh and transcript
appends check the same receipt transactionally, before and after their edits.
Late callbacks cannot use a subsequent attempt or publish into another receipt.
A timed-out UUID is terminal; an explicit new message uses a new worker and the
same conversation. Managed-only IPC loss also exits the actual child process.

Completion is visible only after confirmed death. Failed stop or cleanup keeps
the conversation busy with an explanatory native status; the owner's interrupt
retries cleanup without replaying model work. Close/reopen retains the controller
until stopping is confirmed. Browser regression also exposed incomplete metadata
when reopening an unsubmitted conversation: the native unpersisted-resume path
now supplies the full managed SessionInfo, preventing a SessionPanel crash.

TDD reproduced the missing host deadline, expiry during actual SQLite writes,
late native persistence, cleanup failure, kill blocked by admission locks,
unsubmitted-conversation metadata and discarded controllers after failed close.
The provider fixture stalls real HTTP responses and observes real socket closure.
Its hold marker matches the current prompt suffix because native request repair
can merge adjacent user messages after a failed turn; canonical transcript and
request-count assertions are retained.

Native verification: 41 gateway/receipt/deadline/lifecycle checks passed
(`/tmp/an77-host-final-managed.log`). Persistence verification: 84 checks passed
across `test_managed_chat_attempt`, `test_managed_chat_attempt_policy`,
`test_managed_chat_policy`, `test_session_turn_lease`,
`test_append_messages_batch` and `test_cross_process_turn_lease`; their tool
outputs are the evidence, with no separate stdout log saved. Existing ordinary
ComputeHost regressions passed 29 checks (`/tmp/an77-deadline-ordinary-host.log`).

All **14 distinct Playwright scenarios passed**: 13 in the final full run, and
the renderer-recovery scenario in a focused recheck after updating its final
assertion for the intentionally absent transcript of a never-submitted agent.
The actual metadata crash was fixed in the native resume response. Exact restored
user text, provider reply and no-replay counts remain asserted.
Logs: `/tmp/an77-deadline-browser-final.log` and
`/tmp/an77-deadline-recovery-final.log`. Earlier deadline/isolation checks also
passed, verifying the affected PID/request stopped, another active request stayed
alive, late output was excluded and the next worker kept the same system prompt.

Together with 17 ordinary gateway close/routing checks
(`/tmp/an77-deadline-gateway-final.log`), **171 focused Python checks passed**.
Scoped Ruff/ESLint, whitespace and 27 local documentation link targets passed.
No native TypeScript production changed, so the existing verified TUI bundle is
reused. First red evidence: `/tmp/an77-deadline-browser-red.log`,
`/tmp/an77-host-deadline-red.log`, `/tmp/an77-host-lock-red.log` and
`/tmp/an77-host-close-metadata-red.log`.

The preview is healthy on port 19221, PID **21206**, retaining all three agents,
purpose revisions, databases and the approved subscription. One harmless prompt
through the existing setup-preview agent returned the exact `gpt-6-astra` reply
through the new worker path. Native storage confirmed the exchange and completed
receipt, and the worker registry was removed. Conversation-only mode, zero tools
and unchanged project execution/startup were verified. Evidence:
`/tmp/an77-deadline-live-managed-chat-result.json` and
`/tmp/an77-deadline-live-managed-chat.png`.

AN-77 stays In Progress. Next is full service-restart recovery through the browser
and remaining purpose-revision/transcript ordering. AN-72 writing/story/Pause
follows. This increment does not establish autonomous writing or a hosted Builder.

## AN-77 draft and delivery recovery — accepted checkpoint

The existing native composer saves its text, buffered lines and paste payloads in
private host storage, scoped by browser attachment and bound agent/revision.
Submission atomically moves the draft into a saved UUID envelope before the model
request. Native SessionDB metadata records admission and terminal receipts; a
repeated ID cannot invoke a second model turn. Native transcript storage is unchanged.
Recovery only checks receipts; it never automatically resends.

Review reproduced and fixed late acknowledgements changing a newer turn, recovery
cleanup erasing a human edit, and a crash between saving and clearing resurrecting
already-sent text. Tests also cover corrupt/changed state files, uncertain outcomes,
explicit acknowledgement, atomic transfer and the gateway's Unicode message limit.
Busy rejection leaves a durable terminal receipt without affecting the active
reply; the owner can edit and retry explicitly.
The `/acknowledge` command closes only an uncertain local attempt without resending
or deleting its stored history. Renderer restart is covered in the real browser;
full service-restart UX and a hard execution deadline still need follow-up.

Verification: all **12 distinct Playwright scenarios passed** (10 in the full
regression and the remaining two in a focused recheck after fixture corrections).
Browser fault injection drops only one outgoing acknowledgement after actual
native dispatch; exact persisted messages and a single model request are asserted.
An actual Node renderer restart verifies unsent-draft and completed-history
recovery. Browser automation waits for the native process to consume typed text
before a separate Enter and normalizes terminal control sequences for replay
presentation checks; exact native transcript assertions remain unchanged.

**54 focused Python checks** and **56 native unit checks** passed, plus 44 existing
input-parser/burst checks. TypeScript, native TUI build, scoped Python/web/native
lint and 26 local document link targets passed (one existing lifecycle hook lint
warning remains). Red→green evidence covers receipt admission/restart, late
responses, recovery-owned draft cleanup, Unicode limits and atomic transfer.
Logs: `/tmp/an77-recovery-browser-full.log`,
`/tmp/an77-recovery-browser-affected.log`, `/tmp/an77-recovery-native-final.log`,
`/tmp/an77-receipts-final.log`, `/tmp/an77-recovery-host-final.log`.

The preview restarted on port 19221 (PID 97313), preserving its three agent
identities/purpose revisions, existing databases and approved `gpt-6-astra`
subscription configuration. A live installed-Chromium check sent one harmless
message through the existing setup-preview agent's native composer and received
the exact requested `gpt-6-astra` reply. Native SessionDB verified the exact exchange;
protected identity, conversation-only mode, zero tools and unchanged project
execution/startup were confirmed. Evidence: `/tmp/an77-live-managed-chat-result.json`
and `/tmp/an77-live-managed-chat.png`. The probe reads native session metadata
on resume rather than assuming a fresh `session.info` event for an already-open
conversation; it waits for the actual saved draft before pressing Enter.

AN-77 remains In Progress for hard host deadlines and full service-restart UX.
Strict atomic ordering between purpose validation and transcript append is still
open. AN-72's managed writing/story/Pause follows; no autonomous writer or hosted
First Builder is established by this increment.

## AN-77 managed conversation — accepted checkpoint

The agent detail page now opens **Chat with agent**, showing the protected name,
purpose/revision and conversation-only scope around the existing embedded TUI.
Host-issued binding and per-revision native SessionDB keys preserve identity and
history across agent switching/reopening. Opening chat works while Plane setup is
unavailable and leaves the agent's project execution/startup intent unchanged.

TDD first reproduced the missing link and missing host binding/API. The integrated
browser then caught native create failing to hydrate resumed history; selecting
native resume with the exact stored key fixed it. Review reproduced a purpose
revision reconnect mismatch, stale saved output and inherited synthetic worker
nudges. The fixes pin the displayed revision, fence output/persistence and refuse
that worker context. Connection status deliberately reports connectivity; native
TUI events own reply progress/errors. Full-suite execution also found test fixture
readiness/counts mixing managed and ordinary sessions; those now use their own
session/request scope without relaxing exact transcript assertions.

Verification: **10 Playwright scenarios passed** against the real native stack
and local external-model fixture; **43 managed host/gateway/core checks passed**
together. Existing focused native gateway, core, persistence and host regressions
also passed, as did 35 affected web unit tests. Production web build, scoped
Ruff/ESLint and whitespace passed; ESLint retains five existing hook warnings.
Checked 54 local documentation links/anchors. Logs: `/tmp/an77-browser-all-session-readiness.log`,
`/tmp/an77-managed-integration-final.log`, `/tmp/an77-managed-final-build.log`.

The local preview was rebuilt and only its identified dashboard restarted
(PID 78326), retaining its existing home, both agent identities/revisions, native
history and approved subscription configuration. An installed-Chromium readiness
check opened the existing setup-preview agent through **Chat with agent**, observed
its protected metadata, `gpt-6-astra`, 31 PTY frames and zero tools. Project execution
and startup remained unchanged. No live model message was sent in that check;
managed send/reply/history is verified with the isolated provider fixture. Evidence:
`/tmp/an77-managed-preview-result.json`, `/tmp/an77-managed-preview.png`.

See [implementation and remaining acceptance](../implementation/native-agent-chat.md).
AN-77 stays open; AN-72's saved story and actual Pause are still next after early
communication acceptance. This increment does not launch autonomous writing or
establish a hosted First Builder.

## AN-77 native chat repair — current verification

The owner approved reusing native Hermes `/chat`; the unfinished custom React
conversation and one-shot model wrapper were removed from the working tree, with
a local draft backup under `/tmp/agent-native-custom-chat-draft`. No custom chat
schema, dispatcher or endpoint was deployed. The inherited web/TUI guidance
applies without the withdrawn exception.

The preview's failed TUI dependency installation was caused by inherited Node
24.3.0, rejected by the root package engine constraint. Installed the TUI workspace
dependencies and built its existing bundle using already-installed Node 24.19.0.
Restarted only the identified dashboard on port 19221 with the original
`~/.hermes-agent-native-preview` home and `kanban.db`; the new process has compatible
Node first on PATH and an explicit HERMES_NODE. See
[dashboard operations](../ops/dashboard/README.md) for the launch procedure.

An installed-Chromium readiness check observed a mounted native terminal, 43 PTY
frames, an open socket, no unavailable banner and no Reconnect control. This is
connection evidence, not a model reply. Logs: `/tmp/hermes-native-chat-install.log`,
`/tmp/hermes-native-chat-build.log`, `/tmp/an77-preview-server.log`.

The real native browser test caught a macOS reconnect defect: PTY reattachment
sends Ctrl+L to redraw, but the composer inserted it as a literal `l`. Two actual
Ink input tests reproduced corruption of empty and existing drafts. The fix
reuses the macOS action fallback and existing global redraw handler; the composer
passes the redraw chord through and ordinary `l` remains ordinary typing.

Verification now passes: **9 Playwright scenarios**, including native send/reply,
exact transcript/history and the same session after reload, rejected unauthenticated
WebSocket, plus all 7 existing agent setup scenarios; **78 focused TUI unit tests**;
native TUI build and TypeScript check; scoped Ruff/ESLint and whitespace. ESLint
retains one pre-existing TextInput hook warning. Logs: `/tmp/an77-redraw-red.log`,
`/tmp/an77-redraw-green.log`, `/tmp/an77-native-all-browser-green.log`,
`/tmp/an77-tui-build.log`, `/tmp/an77-tui-typecheck.log`. Tests replace only the
external model with a disposable HTTP fixture; TUI/gateway/AIAgent/SessionDB stay
real. This establishes integration, not real-model quality or managed authority.

The rebuilt bundle is available to the preview. Replaced its two old renderer
processes without restarting the dashboard or its sign-in worker. A fresh browser
check received 49 PTY frames with no unavailable/reconnect state. Existing stored
sessions and managed setup data remain intact; use a new native terminal session
if a previously open tab still shows its old renderer as ended.

The owner completed the refreshed normal Hermes device sign-in. The preview
reports approved authentication and selects `openai-codex` / `gpt-6-astra`.
A fresh installed-Chromium native chat sent one harmless connection-test prompt;
the real subscription returned the exact requested response, and the native
messages API confirmed both the exact user message and assistant reply in saved
session `20260906_222222_e5b524`. Evidence: `/tmp/an77-live-chat-result.json`.
No project tools or autonomous managed work were requested. Real subscription
send/reply/persistence is now verified; reload/history remains covered by the
isolated browser regression, not by this single live exchange.

For live verification, runtime session IDs differ from persistent SessionDB keys.
Use the channel-scoped `session.info` payload's `stored_session_id` when reading
saved messages. The first probe used the runtime ID and received 404; exact-match
lookup of only its own test prompt resolved the saved session and verified the
successful exchange. No unrelated conversation contents were logged.

Automatic review rejected an earlier directory alias exposing the authenticated
private profile; no alias was created and no credentials were copied. The normal
Hermes sign-in is now complete. Do not retry that alias or start another device
flow unless a fresh sign-in is needed and requested.
Managed agent-to-session binding, protected execution and lifecycle controls
remain AN-77 work after native chat verification; no managed agent is running.

## AN-72 setup increment — private files and Plane planning home

New owner creation now atomically queues setup alongside identity and first-review
intent. The dashboard owns a background setup worker; closing a browser does not
cancel setup. It publishes protected private files, creates/reconciles a separate
Plane workspace, verifies its managed project is private, and seeds one correlated
discovery task. Readiness creates no worker grant and launches no model.

The agent page shows live setup progress, recent event history, a planning link,
missing-configuration/errors and authenticated Retry setup. Polls are serialized;
disconnection retains the last confirmed state with an explicit stale-data notice.
Setup uses a protected host connection, validating that session and API-key
credentials belong to the configured principal. No credential is returned to the
browser or written into an agent's workspace. Initial deployment uses the human
owner account so the owner receives workspace/project membership.

Recovery records attempts before effects, retains IDs after confirmation and
reuses the existing OS operation lock across processes. Unknown creates are only
reconciled; an identified project's privacy can be narrowed idempotently. Missing,
conflicting or replaced resources are not recreated. Purpose edits supersede setup
in the same transaction; even late receipts cannot restore readiness for the old
purpose. Shutdown/stale-purpose checks also run immediately before remote writes.

TDD began with a failing Playwright setup-state assertion and a failing durable
queue assertion. Review then reproduced and fixed incorrect initial-account
pinning, stale setup after purpose changes, false uncertain state when shutdown
vetoed the first write, and a late receipt reviving a superseded intent. Contract
checks exercised real HTTP response loss, privacy confirmation, duplicate/foreign
scope, redirects, malformed/oversized responses and host revocation. Browser test
synchronization and a test-only fixture route order were corrected; these were
verification-fixture defects, not passing product evidence.

Verification: 7 Playwright scenarios passed using cached Chromium. The final
six-file Python regression passed 89 tests with 1 existing opt-in Docker skip
(no container changes). Production build, targeted Ruff/ESLint, 43 local
documentation links/anchors and whitespace checks passed.
See [setup documentation](../implementation/writer-startup-setup.md) for commands.
Logs: `/tmp/an72-setup-browser.log`, `/tmp/an72-setup-python-final.log`,
`/tmp/an72-setup-terminal-green.log`, `/tmp/an72-setup-build.log`.

The installed Plane v1.4.2 smoke also passed with a disposable account/workspace:
ready, one private managed project, one discovery task, retained state after DB
reopen and no additional remote effects on repeat. Workspace deletion, token
revocation and disposable-account deactivation all passed. Safe report:
`/var/folders/2b/7m6z3dx90ll0dw34_3gs7jcc0000gn/T/an72-live-setup-avqjk1n7/report.json`.

The production preview was rebuilt/restarted with its existing database retained.
Its protected connection is configured for the existing human Plane owner, outside
Git at `~/.hermes-agent-native-preview/agent-native/plane-setup.json`. A real ordinary
root **Fantasy writer (setup preview)** now has ready private files, a private
Plane project and discovery task; all previous agents remain. It explicitly shows
**Not started**, has no model execution, and is a setup demonstration only.

- Agent: `b2632bb0-cdbd-4557-8650-4fd6936e8a50`.
- Preview: http://127.0.0.1:19221/agents/b2632bb0-cdbd-4557-8650-4fd6936e8a50.
- Plane project: `27a1ee07-e48c-4178-9abd-8a1572a0ffab`.
- Discovery item: `b1ddc120-a813-41c9-95cd-27161bc448db`.
- Preview process session for this harness: 90109.
- Production browser rendering verified; screenshot `/tmp/an72-writer-setup.png`.

Remaining AN-72 work after the newly prioritized AN-77 conversation: explicit
model/finite-limit configuration, narrow managed Hermes tool/schema dispatch, one
service-owned writing run, durable story artifact and actual Pause. Reuse the
setup/discovery receipt, but revalidate current purpose, planning freshness and
authority at admission. Hermes run budgets are advisory; the host must enforce
displayed limits. Broader work-time chat/inspection/cadence follow in AN-73–76.
No setup result completes AN-72 or the broader writer milestone.

## AN-72 first increment — startup intent and agent detail

Implemented one durable initial-review intent in the same transaction as identity
and creation history. Concurrent/repeated creation returns the same agent and
request. The request retains its original purpose revision; existing records
without intents are not silently activated by reading or retrying them.

Creation opens a real `/agents/:agentId` detail page, with roster links, purpose,
request identity/time/revision and explicit Not started activity. Pending creation
is retained in tab session storage before POST, survives a lost reply and reload,
and clears after confirmation. Failed storage prevents sending an unrecoverable
write. No model/cadence configuration or actual execution is implied by the intent.

TDD: initial Playwright failed because creation stayed on the roster; four new
API/domain cases failed because no startup request existed. After the first pass,
review reproduced a lost-response-plus-reload defect: a different agent ID was
created. The retained envelope fixed that regression. A later browser assertion
was scoped to the main page because the shell also displays its title; the test
now waits for the intended heading without a race or relaxed content check.

Final checks: 5 browser scenarios passed using cached chromium-1208; 60 Python
checks passed, 1 pre-existing opt-in Docker case skipped (no container change in
this increment). Production web build, targeted ESLint/Ruff and whitespace passed.
Commands:

```sh
npm run test:e2e --workspace web
scripts/run_tests.sh tests/hermes_cli/test_agent_native_identity.py tests/hermes_cli/test_agent_native_api.py tests/hermes_cli/test_kanban_db_init.py tests/hermes_cli/test_agent_native_provisioning.py tests/hermes_cli/test_agent_native_plane_access.py
npm run build --workspace web
```

Use the local Node/browser paths in earlier setup notes. Test data is disposable;
no model call or managed agent was started. Logs for this session:
`/tmp/an72-browser.log`, `/tmp/an72-python.log`, `/tmp/an72-build.log`.

The local preview at http://127.0.0.1:19221/agents was rebuilt and restarted
with its existing preview home/database. Read-only health/API/detail checks
confirmed its one existing agent was preserved; no agent was created or started.
Preview process session for this harness: 40548.

Next within AN-72: bind the initial intent to configured model/finite limits,
retry-safe protected/filesystem and Plane provisioning (including a host-seeded
discovery item), then one service-owned run and story artifact with actual Pause.
Reuse AIAgent.run_conversation and its callbacks for observation; callback errors
are swallowed, so enforce authority/persistence outside callbacks. Hermes's
run_budget_seconds is advisory, not a hard deadline; enforce displayed limits in
the host. A narrow explicit schema/dispatch binding must deny all unselected tools.
Do not enable unattended work before those boundaries are connected and tested.
AN-72 remains In Progress; this is not the first-story or complete-writer proof.

## Writer planning verification — 2026-09-06

Plane readback confirmed AN-71–76 with acceptance/dependencies and parent links,
AN-72 Todo/urgent, AN-24 returned to Backlog with verified evidence retained,
AN-57 moved to cycle 04, and AN-66 moved to cycle 03. Current cycle members are
AN-17/66/70/71/72/73/74/75/76; all six cycles have null planned dates. Other original
work-item states and cycle membership were preserved. A new writer milestone
module precedes the retained M7 Builder handoff. No work was marked Done.

Independent read-only review checked milestone scope and existing spec consistency.
It identified and resolved first-discovery admission and stale Builder-first
pointers. Documentation link/heading and whitespace checks passed; 24 product and
20 UX scenario mappings were retained. This planning increment changed no code
and launched no managed agent. Runtime tests were not run. Next: AN-72, beginning with
its small configured-creation/activation Playwright behavior.

## Initial identity increment

Owner authorized framework implementation after the Hermes capability proof.
Implemented the first internal identity slice in `agent_native/`: inactive root
creation/read, owner purpose revision, creation idempotency and durable history.
Uses namespaced tables installed by the existing Kanban initializer, with its
transaction helper. No UI, worker, profile projection or cadence is enabled.

The owner capability is a trusted in-process object, not transport authentication.
Protect the database from workers and authenticate the dashboard before exposing
these operations. The slice does not complete M0 or M1.

## Verification

- Initial identity tests failed on unimplemented operations; the event rollback
  case also lacked its required schema at that stage (setup gap, not behavioral red).
- After implementation: 11 identity tests and 6 existing database-init tests passed.
- Added focused concurrent-retry and failed-revision-event rollback coverage.
- No Playwright test ran: this increment has no browser/API surface yet.
- Implementation notes and verification command: `agent_native/README.md`.

## Next increment

Expose authenticated owner creation/read through the existing web server and web
shell, with Playwright acceptance written first. Add an agent-readable protected
projection, then workspace/launch authority before activation. Preserve the product
requirement of immediate durable activation when actual user-facing creation ships.
Do not enable a timer until authorization and worker isolation are enforced.

Bundled Node 24.19.0 is available at
`/Users/arturmoczulski/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node`.
System Node 24.3.0 failed the web engine check; use the bundled compatible runtime.
Web dependencies and framework browser acceptance setup remain to be established.

## Prior capability evidence

- ChatGPT Pro OAuth profile: `/Users/arturmoczulski/.hermes-agent-native`, outside Git.
- Live Astra inference and TextEdit screenshot reading passed.
- cua-driver 0.23.2 installed; owner granted both macOS permissions; doctor passed.
- Fixed one-shot approval stall in commit `6ac8c49`: 19 targeted tests passed;
  live default-policy denial returned promptly. No approval policy was broadened.
- Successful desktop editing remains unverified; owner explicitly chose to proceed
  with framework development. Details: `implementation/astra-capability-proof.md`.

Existing uncommitted design and First Builder documents are deliberate and must
be preserved. First Builder is still hosted by the external harness, not this framework.

## Latest increment — authenticated creation and listing

Added the Agents screen in the existing web shell at `/agents`: name/purpose form,
loading/error/empty states, retry deduplication, persistent roster, stable IDs and
explicit Not started status. New real API routes use existing dashboard owner
session authentication and the shared identity operations/default control board.
Unexpected actor fields are rejected; no worker launch or approval broadening.

TDD evidence: Playwright first failed because the form was absent; API acceptance
first failed because endpoints were absent. After implementation, 2 Playwright
checks and 16 API/identity tests passed; web typecheck passed. Removed the one new
React lint warning and reran the affected browser checks. Cached chromium-1208 was
used through PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH; no browser downloaded.

Test instructions: `web/e2e/README.md`. Web dependencies are now installed using
bundled Node 24.19.0. Do not repeat the earlier browser-install attempt; owner
explicitly directed reuse of the existing browser cache.

Next: protected workspace/profile provisioning and agent-readable soul projection,
then activation/admission with a controlled model boundary. Creation currently
persists inactive records; it does not yet fulfill the complete autonomous agent
creation scenario. Earlier notes saying no UI or browser setup exists are superseded.

## Preview and production-build verification

Owner requested progress preview. `npm run build --workspace web` found an
unsupported Button variant prop missed by the no-build typecheck; removed it and
the full production build passed. Include `npm run build --workspace web` for
future frontend increments. Local preview runs at http://127.0.0.1:19221/agents
with separate home `/Users/arturmoczulski/.hermes-agent-native-preview` and its
own Kanban database. No agent execution or subscription connection is configured
in this preview. Server process session in the current harness: 9670.

## Latest increment — private profile provisioning (2026-09-06)

Implemented `agent_native/provisioning.py`: host-owned atomic layout publication,
read-only purpose/revision projections, empty credentials file, separate writable
workspace/practices and memories. Retrying preserves mutable data, rejects stale
revisions, symlinks, content tampering and weakened protected permissions.
`sandbox_mounts` returns only explicit soul/identity/workspace/memory binds.

TDD: six initial operation tests failed, then passed; mount contract failed before
implementation. Review identified permission drift; three new cases failed before
validation was added. Final command:
`HERMES_TEST_IMAGE=alpine:latest scripts/run_tests.sh tests/hermes_cli/test_agent_native_provisioning.py tests/hermes_cli/test_agent_native_identity.py`
passed 25 tests with zero skips, including real Docker isolation. An earlier custom
opt-in variable was stripped by the runner and skipped Docker; that was corrected
by using the supported HERMES_TEST_IMAGE knob. No image download or network access.

Next: restricted Hermes Docker execution integration. Upstream currently adds
credential/skills/cache mounts automatically, and environment/reuse paths must be
reviewed and constrained. The tested direct Docker invocation is NOT that integration.
Provisioning is not exposed in the dashboard or coupled to creation yet. New PLAN.md
tracks these increments; no autonomous worker has been launched.

## Latest increment — restricted Hermes environment (2026-09-06)

Added `agent_native/environment.py`, reusing Hermes Docker command/session handling
with a closed launch policy. Added one overridable automatic-mount seam upstream;
ordinary Hermes environments retain their behavior. Managed workers omit inherited
mounts/env/egress and cross-process reuse, pin a local image ID, reject image Volumes,
and cannot silently recreate a removed container. Synchronous checked cleanup
retains container identity if removal fails.

TDD: entry-point tests failed before implementation. Review then identified lost
cleanup identity and implicit image volumes; both reproduced with failing tests
and were fixed. Final command:
`HERMES_TEST_IMAGE=agent-native/dev:latest scripts/run_tests.sh tests/hermes_cli/test_agent_native_environment.py tests/tools/test_docker_environment.py`
passed 69 tests, no skips. Real Docker test used existing image without pulls,
inspected mounts/network/capabilities/user, checked private writes and denied soul
changes, created distinct containers, removed one and verified no recreation,
and checked cleanup. No UI changes and no Playwright rerun for this internal layer.

Next: durable run admission/state/events and cancellation, then bind the managed
environment to the model loop under current soul revision. The environment is not
yet called by dashboard creation or a recurring dispatcher. All dashboard records
remain not_started; no autonomous agent is running. See PLAN.md.

## Planning specification increment — 2026-09-06

Owner redirected work to Plane planning specifications and a reusable agent skill.
Added design/13-project-management.md, implementation/plane-project-management.md
and skills/productivity/plane-project-management/SKILL.md; reconciled the previous
Hermes-only board recommendation and linked the skill from Builder startup/practices.
At that specification-only point no Plane service or token existed; the deployment
entry below supersedes that operational status. The managed runtime adapter is
still absent. Next at that point: validate a pinned Plane Community release and its scoped integration
capabilities before binding work records to the managed execution loop.
Verification: all relative Markdown file targets across design/, implementation/,
first-builder/, PLAN.md and the new skill resolve (28 files). The existing Hermes
authoring checks passed 6 tests with
`scripts/run_tests.sh tests/skills/test_authoring_standards.py -k plane-project-management -q`.
The Codex skill quick-validator rejects Hermes-required frontmatter fields
(author/platforms/version); use the native Hermes checks for this bundled skill.
An independent scenario walk-through covered bootstrap, sprint rollover with
active children, premature Done, and task-size handling. It found an ambiguous
bootstrap exception and a host-specific file-tool assumption; both were clarified.
No runtime integration or autonomous planning quality has been verified.

## Local Plane deployment — 2026-09-06

Plane Community v1.4.2 now runs in local Docker Compose on localhost:19230.
The owner authorized setup and API-first Builder planning. Applied the bundled
planning skill to establish the Agent Native Framework project, AN-1–AN-16 backlog,
22 native dependency links and initial September 6–12 cycle (AN-1–AN-3, WIP 1).
See [PLANE.md](PLANE.md) for durable IDs, private credential locations and API use.
The Builder is a distinct workspace member/project administrator, not an instance
admin. The human owner was explicitly added as project administrator.

Verification: Compose config validates; proxy binds only 127.0.0.1:19230; API
read-back found 16 unique imported records. Full stop/start retained all item IDs,
sampled dependency links and Builder authentication. `ops/plane/smoke.cjs` passed
owner-visible backlog and first-cycle checks using existing Chromium before/after
restart. The initial browser failure exposed missing owner project membership,
which was fixed through Plane’s project membership API. No browser downloaded.

AN-1 now includes explicit self-evaluation/evidence and is accepted in Plane.
AN-2 and AN-3 carry partial findings and remain open; read live states before
choosing further work. Full API isolation/reconciliation and backup/restore remain
unverified. The managed-agent adapter and autonomous Builder cadence are absent.
PLAN.md now points to the live backlog instead of mirroring its status.

Final checks: 6 focused Hermes skill-authoring tests passed; relative file links
resolve across 30 documentation files; Compose validates and the expected one-shot
migrator exited successfully while 12 services remain running.

## AN-2 — API boundary characterization, 2026-09-06

Accepted live characterization: pagination, sequential external-ID conflict,
private-project denial, deletion and API-key rate limiting. Stale If-Match PATCH
was accepted, so no atomic conditional-write guarantee. Pinned-source review found
webhook delivery IDs change on retries and HTTP error responses are not retried.
See implementation/plane-api-validation.md for precise evidence and limits.
Probe created and cleaned its own workspace and accounts, leaving the real backlog
unchanged. Next priority is AN-3 isolated database/attachment backup and restore.

## AN-3 — storage restore verified, 2026-09-06

Added ops/plane/verify_restore.py and the operator recovery procedure. The first
export failed safely; corrected container-authenticated pg_dump and reran. The
isolated restore recovered all 16 project item IDs and matching S3 object bytes.
Original API reconnected; temporary restore resources were removed. Private backup
includes database, uploads, deployment secrets/configuration and checksums.
See implementation/plane-recovery-validation.md for limits. AN-3 remains incomplete:
partial-failure/retry guarantees require AN-4 scoped operations and AN-5 reconciliation.
Next implementation slice: AN-4, with failing authorization tests before adapter code.

Post-recovery Playwright Chromium board/cycle checks passed. Python syntax, changed
relative documentation links and whitespace checks passed. No managed-run capability
was added by this operational verification.

## Full specification translated into Plane — 2026-09-06

Owner requested full design-to-backlog coverage and removal of the unused default
project. Reviewed all 14 design chapters/index, engineering plans/evidence and
Builder workflow. Preserved AN-1–AN-16 and added AN-17–AN-67 with source references,
acceptance, implementer/evaluator, native parent/dependency links and priorities.
Eight M0–M7 milestone modules plus a product-decision module cover the work; all
24 product scenarios and UX-01–20 have linked delivery records. The nine product
choices were undecided at that review; subsequent decisions are recorded below.

Current cycle retains setup/API evidence and blocked AN-3, adding AN-19 scoped
reads. The next two weekly cycles were tentative at that historical review
(superseded by the undated-cycle decision below): scoped writes/uncertain-write
recovery, then root planning setup/source reconciliation. Each selects two slices;
WIP 1, with explicit carry/split/return/cancel review rather than calendar promises.
Distant milestones remain undated. See implementation/plane-roadmap-coverage.md;
Plane owns live states and this document is only a handoff.

Confirmed the separate agent-native project was Plane's demo with seven onboarding
samples, deleted it under the owner's explicit instruction, and verified 404.
The Agent Native Framework project remains the planning home. Owner-visible
Chromium checks passed for modules, future cycles, current scoped-read work and
product-decision items. No runtime feature was implemented in this planning turn.

Final roadmap audit passed: 67 unique items, 51 additions, all module/cycle/parent
assignments and native dependencies verified; no dependency cycle, including
parent-completion edges. Original accepted setup/API work retained. Documentation
links and all 44 scenario references checked. Plane remains the live priority source.

## Owner decision — autonomy and permissions (historical next-action note)

Owner approved the three presented defaults, resolving AN-60, AN-61 and AN-62.
Canonical design/02, /04, /05 and the resolved section of /07 now specify clear
next-work autonomy, standing scoped permissions or explicit approval, no approval
by silence, and bounded parent-to-child permission delegation. Reconciled the
engineering/UX caveats; no runtime enforcement or remaining policy adoption is
claimed. Next decision discussion: completed bounded children and replacement
handoff. AN-3 still requires retry implementation evidence, not an owner decision.

## Historical owner lifecycle clarification — superseded below

Ongoing children remain autonomous after milestones and can initiate projects
within their purposes. Only bounded-assignment children idle after accepted
completion. Updated canonical role and scenario wording. AN-63 is approved:
immediate stopping, reconciliation and eligible automatic replanning after purpose
change; parent notification without veto; replacement retires old subtree and
uses a distinct identity plus selected explicit handoff. AN-64 is partially
resolved; cancellation disposition remains for the next question. No runtime
behavior was changed or claimed by this documentation update.

## Latest design update — purpose-based lifespan

The owner replaced creation-time ongoing/bounded lifetime types with purpose
review using acceptance evidence and continuing obligations. Updated canonical
lifecycle, cadence, evaluation, scenarios, UI requirements and the Plane skill.
Cancellation now pauses the performing agent/subtree while preserving independent
assignments; retirement is separate. Earlier completion-by-role notes above are
historical and superseded. General retention/export/deletion remains separate.
This is specification and planning work; runtime enforcement is not implemented.
AN-64 is accepted in Plane. AN-68 holds the separate open retention decision;
AN-69 implements purpose evaluation in M2 under AN-11 and gates AN-12. Updated
existing planning, evaluation, cancellation, children, instructions and UI items,
plus M2/M3/decision modules; API readback verified the changes and dependencies.
Checked 146 local documentation links/anchors and preserved 24 product plus 20 UX
scenarios. No runtime tests were needed for this documentation-only increment.
The next implementation selection still comes from live Plane.

## Latest planning correction — undated outcome sequence

The owner removed calendar estimates from cycle planning. All three existing
Plane cycles now have null start/end dates and ordered outcome briefs, verified
through API readback. Scope, dependencies and acceptance evidence determine
progression: scoped reads; scoped writes and retry/recovery evidence; then planning
setup and reconciliation. Existing item IDs, states and cycle membership are
preserved. Explicitly carry retry-dependent recovery acceptance into the second
sequence at review, without falsely marking it done or blocking scoped-read progress.
Updated the canonical planning design, skill, UI requirements and Builder startup
references so future cycles do not regain invented dates or duration estimates.
This is a planning/documentation change; no runtime behavior or tests are claimed.

Verified null dates and preserved member counts in all three cycles, plus the
updated cadence/cycle work-item requirements. Checked 61 local documentation
links/anchors and diff whitespace; the native Hermes skill authoring checks passed.

## Latest implementation — scoped Plane read boundary accepted

AN-19 is complete as a trusted-host read boundary. Added persistent owner-managed
project bindings and opaque contexts revalidated against grant and purpose revisions.
The reader covers project/items/comments/attachment metadata/cycles/states, validates
nested parents and returned scope, rejects unsafe pagination/redirects and limits
streamed data. It does not expose a managed worker tool, launch transport or new UI.
Service credentials remain outside worker state; sandbox rules are unchanged.

TDD progressed from failing authority/resource/security cases to green increments.
Final canonical runner: 122 tests passed across new access/HTTP tests and existing
identity, owner API and schema regressions. Independent review found no actionable
issues. The isolated live Plane probe passed with real attachments and two private
projects; exact objects were verified erased and the test workspace/accounts/tokens
cleaned up. See [the evidence report](../implementation/plane-scoped-reads.md).

Plane readback confirmed AN-19 Done. Sequence 1's three remaining items are accepted;
AN-3's still-blocked retry-dependent recovery acceptance was explicitly carried to
sequence 2 with its prior cycle history retained in comments/briefs. Scoped writes
(AN-20) are Todo and next, then AN-22; no dates or duration estimates were added.
The private planning-context cycle pointer now identifies sequence 2. This does not
complete M1 or establish a managed autonomous agent.

## First major milestone reprioritized — 2026-09-06

The owner directed the first major handoff to be the First Builder running inside
this framework with persistent chat and autonomous repository development. Updated
39 existing Plane items without changing their states, retained all accepted
evidence, and added the focused open runtime-limits decision AN-70. Broad capacity
and progress defaults remain AN-67; root timing remains AN-66. Root resume is AN-31;
unresolved descendant/project pause choices stay AN-65 before AN-40.

The existing M7 module is now **First milestone - Autonomous First Builder**, first
in module order. It aggregates 39 existing/new prerequisite records, preserving
all original capability memberships. AN-16 now depends on the root and real Builder
proof gates; complete teams, organization UI and Linux operations no longer block
it. AN-57 includes the actual Hermes/model/repository/test connection and protected
installed release; AN-58 proves TDD, owner steering, browser closure, service restart
and subsequent independent work. Planning edits do not establish runtime completion.

Six native cycles remain undated. Sequence 1 stays accepted; sequence 2 remains
current (AN-20 next, then AN-22 and carried AN-3). Sequence 3 now delivers one
controlled Builder run; 4 chat and owner control; 5 autonomous continuity; 6 the
handoff proof. General onboarding AN-21 is returned to the post-handoff backlog.

Verification: API readback confirmed all 70 unique items, the 14 revised native
dependency sets, six exact cycle memberships/null dates, module ordering and all
original states/memberships. The dependency graph including aggregate completion
is acyclic and the handoff has no deferred-feature blockers. Independent document
review checked 71 local links/anchors and all 24 product plus 20 UX scenario rows.
No runtime tests were needed for this planning/documentation change. Current live
scope remains in Plane; this entry is handoff evidence rather than a second board.


## Latest increment — scoped Plane writes (2026-09-06)

AN-20 adds ten trusted-host planning mutations, discoverable schemas, explicit
operation/field grants and redacted durable intent/outcome events. Source checks
reject observed drift, cycle moves verify prior membership, and dependencies stay
within the project with bounded cycle detection. Returned business fields and
service attribution must match. Artifact references are escaped unverified text;
no crawler, upload or terminal state bypass is exposed.

TDD progressed through failing contract, authority, journal and real HTTP checks.
The final run passed 340 tests with zero failures/skips, including existing read,
identity and schema regressions. Independent failure tests cover revocation,
replay, lost/invalid responses and storage failures. Ruff and documentation links
passed. The isolated live Plane v1.4.2 probe confirmed all ten operations plus
cycle movement, scope/ownership denials, journal attribution and independent
readback. Its workspace was deleted, tokens revoked and accounts deactivated.
Commands, evidence location and limits: [AN-20 validation](../implementation/plane-scoped-writes.md).

Next at the AN-20 review: AN-22. Start with a committed Plane creation whose response is lost, reopen
the local journal and recover the original item ID without a second creation.
AN-20 receipts were hash-only and one-shot; they did not recover uncertain writes
or deduplicate equivalent requests with new UUIDs. AN-3 remains Blocked on that
proof. Fingerprints are not atomic remote compare-and-swap. No managed-agent tool
transport, activation, autonomous work or new UI was enabled by AN-20.


## Latest increment — uncertain Plane write recovery (2026-09-06)

AN-22 persists protected delivery preparations and an irreversible attempt marker
before dispatch. Delivery and recovery share a private POSIX operation lock;
process death releases it without authorizing another write. Explicit recovery
uses scoped GETs to investigate all ten operations. Confirmed observations retain
matching-effect provenance; missing, changed or duplicated evidence stays
uncertain. Recovered creation never installs editable-field grants.

TDD progressed through small red/green storage, HTTP and process increments.
Final regression: 452 tests passed, zero failures/skips; Ruff and documentation
checks passed. An abrupt-process-death test preserved the original native effect
and journal across restart without another POST. The isolated live Plane v1.4.2
probe recovered ten operation types and left three ambiguous creates unresolved:
13 successful native responses discarded, zero recovery resends. All fixture
cleanup passed. Early probe assertions confused a membership ID with the item ID and assumed
only two projects existed despite native workspace seeding. Both assumptions
were corrected before the fresh full probe passed. See
[recovery behavior and evidence](../implementation/plane-write-recovery.md).

Plane review accepted AN-22 and the bounded existing-Builder AN-3 recovery scope,
preserving prior storage evidence. General new-project/workspace provisioning
recovery remains explicitly in AN-21. Sequence 2 now retains accepted AN-3/20/22;
AN-4 carries to sequence 3 for actual run-derived actors and skill/tool transport.
AN-5 now depends on host operations AN-20 rather than aggregate AN-4, eliminating
the runtime dependency deadlock while keeping AN-23 freshness before AN-7 admission.
AN-4 explicitly requires AN-7/26. API readback verified states, memberships and
all six cycles' null dates. The private cycle pointer now identifies sequence 3.

Next: AN-17 records the exact Hermes baseline and execution-entry inventory.
AN-70 remains an open runtime-limits decision. The preview is still inactive
agent records; this increment adds no worker, cadence, chat or UI activation.

## Latest increment — Hermes execution audit (AN-17)

Recorded the [execution map](../implementation/hermes-execution-audit.md) and
[complete committed delta](../implementation/hermes-fork-inventory.json) from
upstream `006b1be` to fork `f7c54d1`: 19 commits, 90 files (nine inherited changes),
six dependency/deployment records and 12 license/notice records. The snapshot
excludes this audit and the three pre-existing uncommitted paths listed in the
inventory. It does not change the engine version or execution behavior.

Source review confirms that the model-free owner CRUD is integrated; native
execution still lacks framework admission. Alternate TUI/API/session/compute-host,
scheduler, detached child/review and recovery routes require routing or rejection.
Auxiliary model calls and nested execute_code tool dispatch mean a chat/facade
guard alone cannot enforce authority. Raw shell RPC and environment fallbacks also
need boundaries. The first controlled run retains an embedded Hermes agent and
approved development/Plane tools; unused native entry points must be rejected for
managed use until integrated. Those rejections are not implemented by this audit.

Verification: exact Git range/blob inventory, local links and pinned source
references, two independent source reviews, whitespace checks and preservation of
all 24 product/20 UX coverage mappings. No runtime tests, model calls, containers
or browser workflows were run for this documentation increment. Existing proof
remains evidence of the earlier limited capabilities, not a managed Builder launch.

Next: AN-24, beginning with failing tests for missing/forged actor context at the
actual boundary. AN-61/62 policy decisions are accepted. AN-23 source freshness is
independently ready; AN-70 configured runtime limits remain open before admission.
AN-7/26/30/32/18/57 retain implementation and live controlled-run proof. Cycle 3
remains selected and undated; no autonomous Builder is running.

## Latest increment — connected Plane tool authority (AN-24, partial)

AN-24 is In Progress in sequence 3 under the owner's explicit direction to begin
the audit findings. The [connected Plane tool boundary](../agent_native/README.md#hermes-plane-tool-boundary-an-24-first-increment)
now reserves Plane names in both Hermes dispatch entry points and routes
`plane_resource_inspect` through a private, host-bound adapter. Forged fields,
task/session IDs and native handler registration cannot select scope or bypass
the guard. Purpose changes, grant revocation, bare threads and ended/copied
bindings deny access. Real `CellAuthority` socket RPC uses the same context.

The adapter and SQLite connection are opened, used and closed on one host thread.
Binding exit revokes queued/captured reads before I/O cleanup; late item responses
are discarded and cannot trigger further membership/dependency reads. Cleanup
still reclaims the executor if adapter closure raises. Existing owner identity
and provisioning checks remain unchanged. No arbitrary worker code receives host
objects, credentials or a new capability through this implementation.

Also fixed a demonstrated Plane write race: field authorization now participates
in the delivery-attempt transaction. A second owner connection revoking a field
before that transaction prevents all HTTP writes, records rejection and cannot
be bypassed by regranting and retrying the same operation ID. Already admitted
in-flight effects retain their existing unknown/no-resend handling.

TDD evidence: six native-handler impersonation cases first performed the forbidden
fixture effect, then passed. After adding the host binding, four authorized-read
cases still failed until actual dispatch was connected. A real socket-RPC case
then reproduced SQLite's cross-thread error; thread ownership fixed it. A cleanup
exception test reproduced the unreclaimed worker and passed after guaranteed
shutdown. The pre-attempt field-revocation test first delivered one unauthorized
fixture PATCH and then passed with zero writes. Independent lifetime verification
holds an HTTP response across binding exit and confirms no data/follow-up reads.

Regression validation: the final combined 20-file Hermes/identity/API/Plane set
passed 423 tests, zero failures, with automatic retries disabled. The command
is recorded below and the evidence is attached to AN-24 in Plane. One inherited kernel test initially failed on macOS because `pgrep -c`
is Linux-only; the test now checks the actual owned PID using portable options,
preserving the single-kernel/no-orphan assertion. A subsequent inherited remote
kernel test raced a changing dictionary; it now waits for the actual fixture
result-read event with bounded cleanup, preserving its busy-kernel assertion.
New and changed framework code
passes Ruff; changed documentation links and whitespace are checked before commit.
No live Plane accounts or model calls were used for behavior verification, and
no browser workflow changed. Only project-management records were updated in Plane.

AN-24 remains open. Next: extend host-bound operation identity and current grant
checks to the remaining selected tools and model boundaries. Model-facing Plane
writes still need durable host correlation; native and auxiliary admission gates,
run-derived skill/schema loading and real stopping are not established here.
AN-7/26/30/32/18/57 retain those integrations and live proof. AN-70 remains open
before configured runtime admission. The preview still shows inactive agent
records; no autonomous Builder or new UI workflow has been launched.

AN-24 combined verification command (isolated fixture services):

```sh
HERMES_TEST_FILE_RETRIES=0 scripts/run_tests.sh -j 8 tests/hermes_cli/test_agent_native_plane_tools.py tests/hermes_cli/test_agent_native_plane_tool_lifetime.py tests/hermes_cli/test_agent_native_plane_attempt_authority.py tests/tools/test_agent_native_dispatch.py tests/tools/test_registry.py tests/test_model_tools.py tests/test_model_tools_async_bridge.py tests/tools/test_code_execution.py tests/tools/test_code_kernel.py tests/tools/test_code_kernel_remote.py tests/hermes_cli/test_agent_native_identity.py tests/hermes_cli/test_agent_native_api.py tests/hermes_cli/test_agent_native_plane_write_access.py tests/hermes_cli/test_agent_native_plane_writes.py tests/hermes_cli/test_agent_native_plane_write_failures.py tests/hermes_cli/test_agent_native_plane_write_journal.py tests/hermes_cli/test_agent_native_plane_recovery.py tests/hermes_cli/test_agent_native_plane_recovery_failures.py tests/hermes_cli/test_agent_native_plane_recovery_journal.py tests/hermes_cli/test_agent_native_plane_operation_lock.py -q
```
