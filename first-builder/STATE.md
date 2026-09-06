# First Builder — current work and handoff

Updated: 2026-09-06. Working branch: `codex/astra-capability-proof`.
Active repository: `/Users/arturmoczulski/Projects/hermes-agent-native`.

## Current focus

Owner reprioritization: the current undated cycle 03 is now **Fantasy writer —
create, chat and observe**, before the First Builder handoff. The
[writer specification](../design/14-first-writer-milestone.md) and
[delivery plan](../implementation/fantasy-writer-milestone.md) define its complete
acceptance: ordinary root creation and immediate work, real saved stories,
durable chat/questions/steering, activity/session inspection, cadence, evaluation,
actual pause and basic restart recovery. One story is only an autonomous-work checkpoint.

Read [Plane](PLANE.md) for live state: AN-71 aggregates the writer milestone.
AN-77 is In Progress and urgent. Native Hermes chat now binds selected framework
identity, protected purpose and retained conversations, with conversation-only
scope. Native draft persistence and durable submission receipts now support
renderer restart and explicit retries. Remaining acceptance covers hard host
deadlines and full service-restart recovery; a live managed subscription exchange
is verified below.
The owner rejected a duplicate React conversation; the native TUI, gateway,
AIAgent and SessionDB remain authoritative.

AN-72 is Todo after AN-77. Creation/detail/initial review and protected filesystem/
Plane setup are accepted at `82241f4` and verified below. Writing, story artifacts
and Pause remain unfinished. AN-73 retains later proactive questions and steering
during work; AN-74–76 retain inspection, continuity and full acceptance. Early
managed conversation must work independently of Plane readiness and cannot admit
autonomous project work or expose project tools. Existing identity, owner auth,
provisioning, environment and Plane boundary evidence remains; AN-24's broad
remainder stays backlog. No managed writer or Builder run is established by this
planning update. Earlier next-step entries are historical; this focus wins.

## AN-77 draft and delivery recovery — current increment

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
