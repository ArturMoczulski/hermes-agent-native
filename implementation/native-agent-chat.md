# Native conversation with a framework agent

AN-77 now connects agent selection to the existing Hermes conversation stack.
From Agents, open an agent and select **Chat with agent**. The page identifies
its protected purpose and revision, then mounts the same embedded TUI used by
ordinary `/chat`. The TUI owns input, transcript, streaming and errors. The small
surrounding status is a connection indicator only.

## Identity and storage

The authenticated owner opens `/api/agent-native/agents/{id}/chat`. The host issues
an immutable binding from the control database and provisions the existing private
workspace if necessary. Plane readiness is not required. Caller-supplied profile,
resume or fresh-session options cannot select another identity.

`agent_native_chat_sessions` maps each agent/purpose revision to one durable
native SessionDB key. Repeated and concurrent opens reuse that key. Messages are
stored only by Hermes SessionDB; the framework table is not a second transcript.
The web launcher pins the displayed purpose revision through both authenticated
PTY and native WebSocket connections, and uses native resume to restore history.
PTY attachment includes the bound key so agents cannot share a renderer by mistake.

A purpose edit revokes the previous binding. Requests, turns and output validate
the binding; a stale conversation reports an error and must be reopened. A new
revision receives a new native session and a stable system prompt. Existing
history remains a record, not a source of authority for the new purpose. An
ordinary native connection cannot resume or branch a managed session by ID or
title to remove these restrictions.

## Conversation scope

The host constructs the existing AIAgent with the configured native model and
provider credentials. It uses the protected purpose and private workspace, with
ambient soul/context/memory disabled. It exposes no project tools, plugin tool
catalog or auxiliary agent routes. Existing request, execution and lifecycle
middleware remain in place; both native tool execution paths add an explicit
managed-chat denial. Text preprocessing, encoded multi-agent requests, automatic
continuations and inherited Kanban-worker nudges cannot initiate work.

Each owner message admits one native conversation turn. The current host settings
are two loop iterations, 2,048 output tokens and a 90-second advisory run budget.
These are early chat settings, not configured unattended-work limits. Hermes's
run budget is not a hard deadline; enforcing a host deadline remains AN-77 work.

Plain chat cannot start project work, change purpose or clear a pause. The current
identity model still reports project execution as **Not started**. Actual managed
writing and Pause belong to AN-72. Missing provider configuration and failures use
the native error path. Attachments, native management commands, model switching
inside this scoped conversation and automatic wake activation are unavailable.

## Evidence and remaining acceptance

The Playwright scenario drives two agents through the actual browser, authenticated
PTY, TUI, native gateway, AIAgent and SessionDB. Only the external model is replaced
by a local HTTP fixture. It verifies distinct protected purposes, no tools in model
requests, exact persisted exchanges, switching agents and retained follow-up
context. Supporting tests use real control storage and native session storage for
binding, concurrent opens, authentication, revision revocation, native request
guards, tool denial and stale output. Existing ordinary-chat and setup scenarios
remain part of the browser regression.

The owner's real subscription connection was verified separately through ordinary
native `/chat`; that proof alone does not establish every managed-chat behavior.
See [Builder state](../first-builder/STATE.md) for executed checks and preview status.

AN-77 stays In Progress. Remaining acceptance includes durable unsent drafts,
idempotent message receipts and retry, hard host deadlines, service-restart and
interrupted-delivery recovery, and a live managed subscription exchange. Revocation
checks at native persistence narrow stale writes; strict atomic ordering between
the control database and native transcript storage remains to be established.
Do not report this usable conversation checkpoint as the full writer milestone.

## Repeat the focused checks

Use the existing installed-Chromium override from [browser setup](../web/e2e/README.md).
The complete browser command includes existing agent setup and ordinary native chat.

```sh
npm run test:e2e --workspace web
scripts/run_tests.sh tests/hermes_cli/test_agent_native_chat.py tests/hermes_cli/test_agent_native_chat_api.py tests/agent/test_managed_chat_policy.py tests/tui_gateway/test_managed_chat.py --file-retries 0
npm run build --workspace web
```
