# First Builder — current work and handoff

Updated: 2026-09-06. Working branch: `codex/astra-capability-proof`.
Active repository: `/Users/arturmoczulski/Projects/hermes-agent-native`.

## Current focus

The owner selected Plane planning and a reusable sprint workflow skill. See the
2026-09-06 planning increment below and PLAN.md. Earlier entries record completed
implementation slices, not the current capability inventory. Plane is not deployed.

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
No Plane service, token, project, runtime adapter or automatic skill loading exists
yet. Next: validate a pinned Plane Community release and its scoped integration
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
