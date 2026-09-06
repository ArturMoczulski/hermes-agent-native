# Ordinary writer setup

AN-72 now connects owner creation to a dashboard-owned setup worker. The agent
page shows preparation, private-file readiness, the Plane project and discovery
task, recent setup events and retryable failures. This is the working-area part
of [the first writer slice](fantasy-writer-milestone.md), not model execution.

## Current behavior

Creation commits identity, the original-purpose review intent and one setup job
in the same transaction. Retried creation returns the same identities. Existing
records without setup jobs remain inactive; reads never provision them.

The dashboard service processes queued jobs without depending on an open browser:

1. Publish or validate the agent's private purpose projection, workspace and memory.
2. Authenticate the explicitly configured Plane host account using both its
   session and API key. Both must identify the configured principal.
3. Create/reconcile one UUID-derived workspace and one marked project. Make the
   project private through Plane's session API and verify privacy by reading it.
4. Create/reconcile the initial purpose-discovery task, with acceptance criteria.
5. Record setup readiness. Execution remains **Not started**.

The host supplies resource identities and correlations. Agent names/purposes do
not choose paths, credentials, another project's scope or arbitrary HTTP targets.
No model tool receives the setup service, account password, API key or database.
The setup receipt grants no worker authority. Run admission must still verify
current purpose, model/finite limits, planning freshness and the enabled tool set.

## Protected connection

For this initial local path, configure the **human owner's Plane account** as the
host provisioning principal. Creation then gives the owner workspace and project
membership automatically. A distinct service-account deployment needs explicit
human membership provisioning before adoption; merely using Builder's token is
insufficient, and worker credentials are never accepted as setup authority.

The host reads `agent-native/plane-setup.json` under the active Hermes home.
Its directory must be owned by the host user and mode 0700; the file must be a
regular file with a single hard link owned by that user with mode 0600. Symlinked files,
excessive size and unexpected fields are rejected. Store it outside the repository
and outside all agent mounts. The required JSON fields are:

```json
{
  "base_url": "http://localhost:19230",
  "email": "<human owner account>",
  "password": "<host-held account password>",
  "api_key": "<API key belonging to the same account>",
  "expected_user_id": "<that account's UUID>"
}
```

These are placeholders, not launch defaults. No account or key is created by the
runtime. An absent/invalid connection is a visible setup blocker with Retry setup.
A failed first login can be corrected. After authentication, the original Plane
origin/principal are retained to prevent recovery silently switching accounts or
instances. Configuration is not an agent-editable memory or practice file.

Plane v1.4.2 creates workspaces through its session API, not API-key v1 routes.
The v1 project-create endpoint ignores `network`; a separate session PATCH and
read-back are necessary for privacy. Workspace creation also seeds a sample
project. The managed project has a distinct name, identifier and correlation;
the sample is never adopted or granted to the writer. Removing those upstream
samples is not part of setup.

## Interruption and recovery

The existing local POSIX operation lock serializes each setup across processes.
The host commits an attempt before each external phase and checkpoints confirmed
IDs. Process death releases the OS lock but retains attempts and receipts. A new
service resumes unfinished setup; blocked/failed/uncertain outcomes wait for an
explicit owner retry, avoiding an automatic error loop.

An uncertain create may only be reconciled, never blindly sent again. Missing or
conflicting resources remain unresolved. A fully matched project can receive the
idempotent privacy PATCH during recovery. A confirmed resource is never replaced
by a different ID. Recovery validates previous checkpoints before readiness.

Purpose changes supersede setup in the same owner-edit transaction. Host checks
also run between phases and immediately before remote resource writes. Shutdown
stops further effects; already-sent requests may settle remotely and are reconciled
on restart. There is no worker/run to cancel in this increment. Model Pause remains
part of the next AN-72 delivery work.

The page polls serially, retains the last confirmed state with a disconnection
notice, and shows setup event summaries. These events describe observed host work,
not hidden model reasoning. Setup history and actual timestamps are retained;
no cycle dates or duration estimates are introduced.

## Verification

The browser suite uses the actual UI, authenticated API, database and setup
service. Its only replacement is an external Plane HTTP fixture with disposable
credentials; fixture controls are registered solely by `web/e2e/backend.py`.
Production routers contain no test-control routes.

Focused commands:

```sh
scripts/run_tests.sh tests/hermes_cli/test_agent_native_startup.py tests/hermes_cli/test_agent_native_plane_setup.py tests/hermes_cli/test_agent_native_identity.py tests/hermes_cli/test_agent_native_api.py tests/hermes_cli/test_agent_native_provisioning.py tests/hermes_cli/test_kanban_db_init.py --file-retries 0
npm run test:e2e --workspace web
npm run build --workspace web
```

Use the cached browser and local Node paths in [the E2E guide](../web/e2e/README.md).
Current red/green evidence, installed-Plane verification and remaining work live
in [Builder state](../first-builder/STATE.md) and Plane AN-72. A successful setup
is not first-story acceptance or proof of an autonomous running agent.
