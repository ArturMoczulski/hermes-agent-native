# Agent creation and detail browser acceptance

Run from the repository root with a Node version supported by package.json:

```sh
npm run test:e2e --workspace web
```

Playwright starts the real Hermes FastAPI application and Vite on loopback ports
19219 and 19220. The backend uses disposable storage and removes inherited Hermes
settings/provider credentials. No model request or personal profile is needed.
The browser uses a test-only dashboard token; unauthenticated requests are also
checked. Servers are stopped by Playwright, and backend storage is temporary.

The suite checks creation-to-detail navigation, purpose/startup retention after
reload, a single record and initial request after a committed-but-lost POST response
plus browser reload, unknown detail/error states, storage failure before sending,
and rejected unauthenticated reads/writes. API/domain tests cover concurrent
retries, atomic rollback, older records without intents, stale-purpose retry,
conflict responses, validation and forged actor fields.

The first review request is durable; actual model execution, planning provisioning,
chat and cadence are not connected yet. These checks do not prove a writing agent.

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
