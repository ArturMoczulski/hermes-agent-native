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

Each owner message admits one native conversation turn, with two loop iterations
and 2,048 output tokens. Managed chat also has a host deadline, described below.
These are early chat settings, not configured unattended-work limits.

Plain chat cannot start project work, change purpose or clear a pause. The current
identity model still reports project execution as **Not started**. Actual managed
writing and Pause belong to AN-72. Missing provider configuration and failures use
the native error path. Attachments, native management commands, model switching
inside this scoped conversation and automatic wake activation are unavailable.
The local `/acknowledge` recovery command only closes an uncertain delivery record;
it is not sent to the model and does not start work.

## Managed message deadline

The gateway starts one dedicated native ComputeHost worker for each admitted
message. That worker uses the existing AIAgent and reopens the same canonical
SessionDB conversation. It receives the same protected system instructions on
each turn; worker replacement does not reset conversation history. The parent
holds routing and delivery metadata and never runs a second copy of the model loop.
Ordinary Hermes conversations keep their existing execution path.

The normal host `config.yaml` setting
`agent_native.managed_chat_timeout_seconds` defaults to 90 and must be positive
and finite. It is read when a new message is admitted; changing it does not extend
an already-running attempt. The deadline includes worker startup. At expiry the
supervisor kills and reaps that attempt's worker rather than waiting for a blocked
provider call to cooperate. No automatic replay or worker respawn occurs.

Private host IPC binds the worker to the exact agent, purpose revision, native
session, message UUID, receipt owner and deadline. The worker database retains that
immutable attempt even after calling context unwinds. Turn-lease acquisition and
refresh and transcript appends check the active receipt and deadline within their
native SQLite transaction, before and after the write. Expired edits roll back;
optional JSON transcript snapshots are disabled for these attempts. This storage
fence complements process termination; a clock check cannot guarantee that an OS
scheduler or SQLite commit finishes at an exact instant.

Only the owning attempt may forward model events or settle its receipt. Terminal
completion is published after confirmed worker death, preserving honest busy
state during cleanup. If stopping or recording cleanup cannot be confirmed, the
native status explains this and keeps the conversation busy. The owner's interrupt
control retries cleanup without running the model again. A timed-out message keeps
its terminal failure receipt;
retrying its UUID cannot invoke the model again. The owner may edit and explicitly
send a new message in the same conversation. Timeout ends this message attempt,
not the agent's purpose or lifespan. Closing the local provider connection does
not establish that a remote provider stopped all processing or billing.

## Draft and delivery recovery

The existing native composer now saves text, multiline input and collapsed paste
payloads in private host storage. Each browser attachment and bound agent/purpose
revision has its own state file, outside the agent workspace. Native input recall
uses the same scope. Switching agents or restarting the renderer preserves the
draft; opening a conversation never submits it. Storage failures are visible and
prevent sending a message that could not be saved.

Before clearing the composer, the TUI saves the message and its stable UUID.
The native gateway records admission in the existing SessionDB metadata before
launching the existing model turn. Repeating that UUID and text returns the saved
receipt without another turn; reusing it for different text is rejected. Only one
message can be admitted to a conversation at a time. Busy rejections also retain
a terminal receipt, so a delayed retry cannot unexpectedly start rejected work.
There is no automatic resend or separate conversation database.

The TUI checks receipts after a lost acknowledgement or renderer restart. Accepted
work remains pending; completed work reloads the native transcript. A late receipt
cannot overwrite a newer draft or change another turn's status. If no receipt
exists, the saved message is restored when the composer is empty and an explicit
Enter retries the same UUID. Failed attempts can be edited and retried explicitly.
A gateway restart turns an unfinished prior-process receipt into an **uncertain**
outcome instead of launching it again. The owner can inspect saved history and
replace the composer text with `/acknowledge` to close that local pending attempt,
then write a new message. The old receipt remains in native storage.

This checkpoint proves renderer restart and durable receipt behavior. Full browser
recovery across a service restart and complete writer lifecycle recovery remain
separate acceptance work. Draft recovery also
requires retaining the browser's attachment token; clearing browser storage or
using another browser selects a different draft scope.

## Evidence and remaining acceptance

The Playwright scenario drives two agents through the actual browser, authenticated
PTY, TUI, native gateway, AIAgent and SessionDB. Only the external model is replaced
by a local HTTP fixture. It verifies distinct protected purposes, no tools in model
requests, exact persisted exchanges, switching agents and retained follow-up
context. Supporting tests use real control storage and native session storage for
binding, concurrent opens, authentication, revision revocation, native request
guards, tool denial and stale output. Existing ordinary-chat and setup scenarios
remain part of the browser regression.

Deadline acceptance holds actual provider HTTP requests before any response bytes.
It checks worker death and connection closure, exclusion of late output, a new
explicit message in the retained conversation, and another simultaneous agent
remaining alive. Native tests cover startup, parent IPC loss, locked admission,
unconfirmed stop/close and failed-cleanup retry. Reopening an unsubmitted draft
also verifies the full managed metadata required by the existing native panel.

The owner's real subscription connection was verified through the selected setup
preview agent as well as ordinary native `/chat`. An installed-Chromium check sent
one harmless prompt through the managed native composer, received the exact reply
from `gpt-6-astra`, and verified both messages in SessionDB. This was repeated
after the per-message worker change, including the completed receipt and worker
registry cleanup. Protected identity,
conversation-only mode, zero tools and unchanged project execution were confirmed.
This single live exchange complements the isolated recovery tests; it does not
establish autonomous writing or every service-restart behavior.
See [Builder state](../first-builder/STATE.md) for executed checks and preview status.

AN-77 stays In Progress. Remaining acceptance includes full service-restart
recovery through the browser. Revocation
checks at native persistence narrow stale writes; strict atomic ordering between
the control database and native transcript storage remains to be established.
Do not report this usable conversation checkpoint as the full writer milestone.

## Repeat the focused checks

Use the existing installed-Chromium override from [browser setup](../web/e2e/README.md).
The complete browser command includes existing agent setup and ordinary native chat.

```sh
npm run test:e2e --workspace web
scripts/run_tests.sh tests/hermes_cli/test_agent_native_chat.py tests/hermes_cli/test_agent_native_chat_api.py tests/agent/test_managed_chat_policy.py tests/tui_gateway/test_managed_chat.py --file-retries 0
scripts/run_tests.sh tests/tui_gateway/test_managed_chat_deadline.py tests/state/test_managed_chat_attempt.py tests/agent/test_managed_chat_attempt_policy.py --file-retries 0
npm run build --workspace web
```
