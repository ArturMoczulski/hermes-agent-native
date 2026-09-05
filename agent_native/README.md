# Agent-native control domain

First increment: inactive root identity in the existing Hermes Kanban database.
`identity.py` supplies owner-only creation, reads, purpose revisions and event
history. Every creation and revision commits with its event in one transaction.
Request IDs deduplicate creation; expected revisions protect against stale edits.
Names are display labels, not identifiers. Schema initialization runs through
Hermes' existing connection/migration path. No new task store or agent loop exists.

This is an internal host interface, not an authentication mechanism. `OWNER` is
an in-process capability for trusted host code; it must never be selected from
request content or exposed in an agent tool. Any process with database write
access can bypass these operations. Managed workers are not launched yet.

Roots deliberately remain `not_started`. The existing dashboard now exposes creation and listing at `/agents`, through
owner-session authenticated `/api/agent-native/agents` endpoints. Request data
cannot choose the actor. Parent/grant rules, protected soul projections, workspace
isolation, activation intents and cadence remain to be implemented.
At that point creation must record an immediate activation atomically, as required
by the product specification. Do not present this interim record as a working agent.

Verification:

```sh
scripts/run_tests.sh tests/hermes_cli/test_agent_native_identity.py tests/hermes_cli/test_kanban_db_init.py
```

Tests use real isolated SQLite databases, including concurrent duplicate requests
and failed-event rollback. No model subscription, personal profile or browser is
used. The first dashboard flow must add Playwright coverage against the real API.

The Agents page is an interim inactive-record workflow and explicitly says work
has not started. Open it in the existing Hermes dashboard navigation. Browser
acceptance setup: [web/e2e/README.md](../web/e2e/README.md).
