# Dashboard browser acceptance

Run from the repository root with a Node version supported by package.json:

```sh
npm run build --workspace ui-tui
npm run test:e2e --workspace web
```

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

Run just those native chat checks with:

```sh
npm run test:e2e --workspace web -- native-chat.spec.ts
```

The first review and setup are durable. Native Hermes owner chat works separately
from managed-agent creation; managed purpose/workspace binding and cadence are not
connected by these tests. These checks do not prove an autonomous writing agent.

## Reuse an installed Chromium

No download is performed by the test command. If the installed Chromium differs
from Playwright's default revision, point the suite at its executable:

```sh
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH='/absolute/path/to/Chromium' npm run test:e2e --workspace web
```

On the development Mac this passed with the existing cached chromium-1208
(Chrome for Testing 145) and Playwright 1.62.1. The optional override remains local;
CI can use Playwright's matching cached browser. There is no auto-install step.

Failure traces are under `web/test-results/` and are ignored by Git. Existing
upstream development warnings may appear; they are not test failures.
