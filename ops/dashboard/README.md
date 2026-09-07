# Local Hermes dashboard

The framework preview uses Hermes's existing web application and native `/chat`.
The chat renderer is the embedded TUI; it uses Hermes sessions and the Hermes
agent engine. See [UI integration](../../implementation/user-interface.md) for
the managed-agent binding and remaining acceptance. A working native chat does not establish
that a record on `/agents` is executing.

## Start with the supported Node runtime

Use a Node/npm combination allowed by the root [package.json](../../package.json).
Both the web application and `ui-tui` need their dependencies installed. Building
only `web` does not prepare native chat.

From the repository root, put your compatible Node installation first on `PATH`:

```sh
export PATH='/absolute/path/to/compatible/node/bin:'"$PATH"
node --version
npm --version
npm install --workspace ui-tui --include=dev --no-fund --no-audit
npm run build --workspace ui-tui
npm run build --workspace web

export HERMES_NODE="$(command -v node)"
export HERMES_HOME="$HOME/.hermes-agent-native-preview"
export HERMES_KANBAN_DB="$HERMES_HOME/kanban.db"
.venv/bin/hermes dashboard --skip-build --no-open --port 19221
```

Keep the same home and database when restarting. Identify the process holding
port 19221 before stopping it; do not kill unrelated Hermes services. Settings,
agent records and protected provisioning data belong to this preview home.
A future managed deployment has its own service-owned lifetime.

On the development computer the already-installed Node 24.19.0 satisfied the
checkout. The earlier dashboard inherited Node 24.3.0: npm rejected it with
`EBADENGINE`, before the TUI could start. Reconnect retried the same failure.
The repair used the existing compatible runtime, installed the TUI dependencies
and built `ui-tui`; it did not lower package requirements or download Chromium.

## Model connection and verification

Sign in through [Keys](http://127.0.0.1:19221/env): use **Login** beside
**ChatGPT or Codex Subscription**, then choose the desired model in Models. The preview profile and the earlier capability-proof profile are separate;
starting the web server does not transfer a model login. Use the normal provider
sign-in flow for the selected profile. Keep credentials outside Git and agent
workspaces. Do not expose another private profile through a dashboard directory
alias as a shortcut to model authentication.

Open [Chat](http://127.0.0.1:19221/chat). Verify that the terminal connects and the
Reconnect banner clears, then send one bounded message and verify the reply and
saved session. Reload/resume should retain that conversation. Record separately
whether this used a deterministic local test provider or the real subscription.
Do not treat a connected terminal as proof of a successful model reply.

Browser regression setup lives in [web/e2e](../../web/e2e/README.md). Tests use
isolated storage and a local model fixture, never personal conversation history.
Use the existing Chromium executable override; no browser download is necessary.

## Framework agent model settings

On **Agents**, **Default agent model** chooses the provider/model copied to new
agents. The creation form can choose a different pair. Existing agents have
**Agent model → Change agent model** on their details page. These settings use
Hermes’s configured provider connections and model picker; credentials stay in
Keys/provider configuration. Updating the new-agent default leaves existing
agents unchanged.

The same picker includes **Reasoning effort**, with levels supported by the chosen
route and **Hermes default** to preserve native behavior. An unsupported retained
choice must be resolved before Save; Cancel leaves the saved preference unchanged.

A change applies to the next admitted work run or chat message. Current work and
the latest chat selection remain visible separately. Reload the preview after an
upgrade to load the new controls. No model request is made simply by saving a
choice. See [model behavior](../../design/15-model-selection.md).

## Reconnect input regression

The first native chat browser proof also found that PTY reattachment's Ctrl+L
redraw byte reached the macOS composer as a literal `l`. The TUI now passes that
chord to the existing redraw handler; ordinary `l` typing and Cmd+L are retained.
Focused Ink input tests cover empty and populated drafts. The browser test checks
exact saved messages and a history-dependent reply after reloading the same
session. Rebuild `ui-tui` after source changes and replace old renderer processes;
an already-running renderer does not hot-reload a rebuilt bundle.

## Talk to a framework agent

Open [Agents](http://127.0.0.1:19221/agents), choose an agent and select **Chat with
agent**. This uses the same native TUI as generic Chat, with the selected agent's
protected purpose and retained conversation. Switching agents and returning
restores the corresponding history. Chat is available before Plane setup completes.

The chat header identifies conversation-only scope. Talking does not start or
resume project work. Agent details show its independent work status. To enable
one initial writing run, configure explicit time and model-step limits there or
during creation; see [managed writing](../../implementation/writer-managed-run.md).
After changing purpose, reopen the agent conversation; an old connection is
rejected rather than silently adopting a different purpose behind its header.
See [scope and remaining acceptance](../../implementation/native-agent-chat.md).

## Links from Plane to saved work

Set `dashboard.public_url` in the preview home's `config.yaml` to the dashboard
address its owner can open (locally, `http://127.0.0.1:19221`). Restart the dashboard
after changing configuration. The host uses this explicit address for new saved
output/result comments; it never trusts a request Host header or embeds tokens.
Without a valid URL it reports identifiers with a configuration explanation.
Existing comments are not rewritten. Remote owners need a reachable deployment
URL and ordinary dashboard authentication.
