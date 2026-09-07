# Owner removal of managed agents

The agent detail page provides **Remove agent**, followed by an explicit confirmation.
Removal ends the agent's role and removes it from the active roster. It is not a
filesystem, database or Plane deletion. The original detail URL, purpose, startup
record, attempt history, saved outputs and external project remain available.
There is no restore action; recreating an agent creates a distinct identity.

The owner-authenticated DELETE endpoint records a durable removal tombstone and
an `agent.removed` event, invalidates issued authority by advancing its revision,
disables cadence, supersedes setup, and requests existing work cancellation in
one transaction. A queued run is paused without starting; an active run remains
stopping until its existing supervisor confirms cleanup. Removal does not claim
that already-delivered external effects were undone. Repeating DELETE returns
the original removal record. Replaying the creation request returns the removed
identity rather than reviving it.

Removed identities reject new chat, setup, cadence and other owner mutation
requests. Existing native chat bindings become stale. The native chat supervisor
checks authority while awaiting even a silent provider and uses its existing
hard-stop/cleanup mechanism. Work uses its existing stop-request and authority
checks. Retained reads remain available; the removed detail explains when a work
process is still stopping.

This implementation covers the currently supported managed **root agents**.
Managed parent–child trees are not yet implemented. When they are added, removal
must apply recursively to the subtree as required by the retirement specification;
this root-only increment does not establish child lifecycle support.

Verification includes a real browser confirmation/reload/roster flow, owner API
checks for idempotency and disabled cadence/creation replay, and a native process
test proving a held model request is killed after removal without late assistant
output. Test model traffic uses the local fixture, not a paid provider.
