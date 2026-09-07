# Dashboard browser acceptance

For feature work, run the affected spec and named case from the repository root
with a Node version supported by package.json. Replace the example selector:

```sh
npm run build --workspace ui-tui  # prerequisite only if missing or relevant TUI code changed
npm run test:e2e --workspace web -- feature.spec.ts --grep 'case name' --retries 0
```

Follow the [targeted verification policy](../../first-builder/PRACTICES.md#targeted-verification-by-default).
Broaden to a whole spec or suite only for identified affected behavior or a required
gate; do not rerun the default suite for each small change.

Playwright starts the real Hermes FastAPI application and Vite on loopback ports
19219 and 19220. The backend uses disposable storage and removes inherited Hermes
settings/provider credentials. No live model, personal profile, or paid API call
is needed. Native chat uses a disposable HTTP provider on loopback.
The browser uses a test-only dashboard token; unauthenticated requests are also
checked. Servers are stopped by Playwright, and backend storage is temporary.

The suite checks creation-to-detail navigation, purpose/startup retention after
reload, a single record and initial request after a committed-but-lost POST response
plus browser reload, unknown detail/error states, storage failure before sending,
and rejected unauthenticated reads/writes. API/domain tests cover concurrent
retries, atomic rollback, older records without intents, stale-purpose retry,
conflict responses, validation and forged actor fields.

The suite also covers automatic private-file setup, missing Plane configuration,
retry/reload, a configured private Plane project with exactly one discovery task,
and visible disconnection while retaining the last confirmed setup state. Plane
is replaced only at its external HTTP boundary with disposable credentials; the
application setup service, routes and database remain real. Test configuration
and evidence endpoints are installed solely by the test backend entry point.

Native `/chat` acceptance drives the existing xterm terminal by keyboard through
Hermes's real TUI, gateway, AIAgent, and SessionDB. It verifies a provider reply,
reloads the page, submits a follow-up whose fixture response requires the earlier
exchange, and checks the exact persisted transcript and unchanged session ID.
A separate check rejects an unauthenticated terminal WebSocket. The provider is
replaced only at its external HTTP boundary; the test records request counts to
catch unexpected model calls. Native test configuration disables title generation,
memory, and compression. It is test isolation, not a managed-agent security policy.

When the native chat flows are affected, select the relevant case with:

```sh
npm run test:e2e --workspace web -- native-chat.spec.ts --grep 'case name' --retries 0
```

Managed conversation scenarios select two framework agents, verify their distinct
protected purposes and private native transcripts, and check retained context after
switching/reloading. The existing native composer is exercised for draft recovery,
a lost admission acknowledgement and a real renderer restart. Receipt checks never
automatically resend; exact stored messages and provider request counts catch replay.

Deadline scenarios hold actual external HTTP requests before any response bytes.
They require timeout to close the affected request, reject its late output, preserve
the same protected prompt across replacement workers, and let a new explicit
message finish. An overlapping second conversation must stay connected and finish
successfully while the first times out. The test-only configuration endpoint writes
the normal managed-chat timeout setting and restores it after the scenario.
These checks do not establish autonomous writing or cadence;
see [managed chat scope](../../implementation/native-agent-chat.md).

## Agent model selection

`model-selection.spec.ts` has three focused scenarios: defaults and independent
creation/edit choices (including lost-response retry), actual routing during a
work/chat model change, and explicit creation when the default is unavailable.
The same disposable model server exposes two named provider routes with distinct
model IDs. Requests are held where needed to change settings during a real native
attempt; evidence checks the exact endpoint and model used. Work/chat records
must retain the old selection while the next chat message uses the new one.

These scenarios require no intelligence, real credentials or paid inference.
Any future live judgment evaluation must be separately invoked, explicitly choose
an economical account-supported model and finite run limits, and never inherit a
premium host default. See [the cost policy](../../design/15-model-selection.md#verification-without-routine-inference-costs).

`reasoning-effort.spec.ts` adds one focused default/override/retry and active-attempt
workflow. A native provider-profile plugin exists only in the disposable test home
and declares the fixture models’ exact effort levels. The local model server
records the actual request fields. The test verifies unsupported combinations,
reasoning-only edits, unchanged active work/chat effort and the next message’s new
effort. It exercises the native request path without paid intelligence.

## Full service restart

When restart behavior is affected, select the relevant case in the separate
restart configuration. Never run it concurrently with other browser checks;
running the default suite first is not a prerequisite:

```sh
npm run test:e2e --workspace web -- --config playwright.restart.config.ts --grep 'case name' --retries 0
```

It uses the same installed-Chromium override and adds fixture control port 19218.
A stable external model server and private home surround the real dashboard child.
Unlike the ordinary suite, dashboard authentication uses the normal freshly minted
token on every launch and normal HTML injection, with no browser token override.
Startup verifies the owned backend PID and a per-launch nonce. Crash stops only
that backend; the fixture records exact descendant identities and refuses restart
if any old process survives. Emergency teardown is separate from product evidence.

The browser remains open while the service is replaced. Tests require automatic
auth recovery, retained history and draft, actual renderer/worker death and model
socket closure, a durable uncertain receipt, the native acknowledgement guidance,
no replay, and a successful explicitly submitted follow-up. Read-only native
receipt evidence cannot perform recovery itself. No user profile, live preview or
paid model is touched. Graceful fixture shutdown removes its disposable storage;
a launcher-loss watchdog cleans up only when the fixture controller disappears.

## Reuse an installed Chromium

No download is performed by the test command. If the installed Chromium differs
from Playwright's default revision, point the suite at its executable:

```sh
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH='/absolute/path/to/Chromium' npm run test:e2e --workspace web -- feature.spec.ts --grep 'case name' --retries 0
```

On the development Mac this passed with the existing cached chromium-1208
(Chrome for Testing 145) and Playwright 1.62.1. The optional override remains local;
CI can use Playwright's matching cached browser. There is no auto-install step.

Failure traces are under `web/test-results/` and are ignored by Git. Existing
upstream development warnings may appear; they are not test failures.


## Readable test demonstration

The opt-in demo configurations record the existing framework browser scenarios,
including their error and recovery paths. They do not establish every future
product requirement, live model quality or production Plane availability. The
browser, framework, storage and native processes are real; only the external
model and Plane HTTP services are scripted fixtures.

`demoCheckpoint` is called **after** the corresponding assertions. In demo mode
it adds an Expected/Verified caption, highlights the relevant screen area,
captures a screenshot and holds it for five seconds. API-only checks display an
explicit API evidence card. A failed assertion cannot earn a verified checkpoint.
Normal test runs do not inject captions or add these viewing pauses, and product
timeouts remain unchanged. The final Playwright report determines the test result;
a checkpoint passing does not imply that later assertions or teardown passed.

For a requested complete recording, run these commands **sequentially** from the
repository root, using the installed Chromium override described above:

```sh
AN_E2E_DEMO=1 npm run test:e2e --workspace web -- --config playwright.demo.config.ts
AN_E2E_DEMO=1 npm run test:e2e --workspace web -- --config playwright.restart-demo.config.ts
```

The output directories are `web/test-results/e2e-demo/default` and
`web/test-results/e2e-demo/restart`. Each contains a JSON reporter result, videos,
annotated screenshots and per-test checkpoint manifests. Tests with two pages
retain separate recordings. A pilot or targeted re-recording must use a separate
`AN_E2E_DEMO_OUTPUT_DIR` so it cannot overwrite the complete recording:

```sh
AN_E2E_DEMO=1 AN_E2E_DEMO_OUTPUT_DIR=/tmp/e2e-demo-pilot \
  npm run test:e2e --workspace web -- --config playwright.demo.config.ts \
  planning-work.spec.ts --grep 'selected work shows brief, cycle and criteria'
```

Do not edit watched repository files while Vite is recording. Tailwind can issue a
full browser reload even for a Markdown change, which invalidates a deliberately
held network-outage scene. Keep preparation and recording sequential.

Assemble completed recordings with [the evidence assembler](../../scripts/assemble_e2e_demo.py).
It requires Python with Pillow and local `ffmpeg`/`ffprobe`; no model call or
browser download is involved:

```sh
.venv/bin/python scripts/assemble_e2e_demo.py \
  --run-dir web/test-results/e2e-demo/default \
  --run-dir web/test-results/e2e-demo/restart \
  --output-dir apps/desktop/demo/e2e-review --expected-tests 30 --plan-only
```

Review the validated plan, then omit `--plan-only` to encode. Add another
`--run-dir /absolute/path/to/targeted-rerun` if a case needed re-recording. The
latest timestamped attempt for every scenario must pass; prior attempts, including
failures, remain archived and explicitly identified. The expected scenario count
is an explicit completeness check; update it when the suite changes.

The destination contains `agent-native-e2e-demo.mp4`, an `index.html` chapter
player, `chapters.md`, and `evidence.json` with the full edit plan and asset hashes.
Raw recordings, screenshots, manifests and reporter results are retained under
`raw/`. Final reporter attachments resolve Playwright's renamed video paths,
including tests with multiple browser pages. Preserve this destination before
running commands that clean test output directories.

The assembled demonstration holds each exact checkpoint screenshot for 8–12
seconds and labels accelerated workflow footage. The encoder validates frame
counts and final duration so chapter timestamps match playback. Raw evidence
remains available alongside the chapter index. These recording configurations
are an owner review tool, not the default feature-verification command.
