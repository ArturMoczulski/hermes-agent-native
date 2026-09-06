# First Builder — current work and handoff

Updated: 2026-09-06. Working branch: `codex/astra-capability-proof`.
Active repository: `/Users/arturmoczulski/Projects/hermes-agent-native`.

## Current focus

The owner selected Plane planning and a reusable sprint workflow skill. See the
local Plane deployment entry below and [live planning context](PLANE.md). Earlier
entries record completed increments and historical gaps, not the current inventory.
Use Plane through the Builder API account for current work and priorities. The
full specification is now organized in milestone modules and rolling cycles; see
[coverage index](../implementation/plane-roadmap-coverage.md). Next ready slice at
the latest review: AN-20 scoped writes (within AN-4), then AN-22 retry recovery.
AN-19 scoped reads are accepted; sequence 2 is current and remains undated.

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
