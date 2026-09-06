# Plane write outcome recovery — AN-22

This increment lets trusted host code investigate an uncertain planning write
without sending it again. It extends [scoped writes](plane-scoped-writes.md) with
protected delivery preparations, a durable attempt marker, local operation
exclusion and read-only recovery for the existing ten planning operations.
It reuses existing project identities and grants. Project provisioning belongs
to AN-21; managed-agent authentication, cadence and a recovery UI remain separate.

## Delivery evidence and protected state

The [journal](../agent_native/plane_write_journal.py) retains the original
validated arguments and the exact prepared request in a separate protected
`agent_native_plane_preparations` table. Preparation includes the HTTP method,
project-relative suffix, body, expected status, resource kind and known resource
identity. Stored hashes must match the original intent and protected preparation;
preparation cannot be replaced with different arguments after creation.

This changes the earlier hash-only storage boundary: the protected table contains
planning text needed to compare an uncertain effect after restart. It must stay
in host-controlled storage and receive the same protection as the control
database and its backups. It is not part of model-facing tools, public mutation
receipts or event output. Receipts and events continue to contain identifiers,
revision numbers, hashes, timestamps and bounded status/reason fields. They do
not expose prepared text, service credentials or native response bodies.

The host commits preparation before delivery, then durably marks the operation
as attempted immediately before HTTP dispatch. The marker is never reset.
A process can die after recording that marker but before sending bytes, so an
attempted marker means delivery is possible, not proven. Conversely, a valid
prepared HTTP mutation whose marker remains unattempted can be rejected locally
without a remote request, once exclusion proves no active delivery owns it.
Legacy uncertain intents with only an argument hash lack sufficient preparation
and remain unresolved.

## One operation at a time on the local host

Both `execute` and `recover` acquire the same
[operation lock](../agent_native/plane_operation_lock.py) for the control database
and canonical operation UUID. It uses nonblocking POSIX `flock`; another active
caller gets `OperationBusy`. No SQLite transaction spans HTTP, and no elapsed
lease permits another caller to take over a still-running operation.

The operating system releases the lock when the last descriptor closes,
including process death. Lock descriptors are close-on-exec. Lock directories
and files remain private and persistent; they must not be removed or replaced
on release. The database must be a protected local file and must not be replaced
while open. Do not fork while holding a lock.

This excludes cooperating delivery/recovery calls for the same operation on one
POSIX host. It is not a distributed lock, managed-run admission or a lock on the
remote Plane resource. Different operation UUIDs and other Plane users can still
change the same resource. Process death also does not cancel a request already
accepted by Plane.

## Explicit recovery and authority

Trusted host code calls `PlaneWrites.recover(context, operation_id)`. The context
must still match the receipt's original agent, binding, workspace, project, read
revision, write revision and soul revision. The original operation must remain
granted. Recovering an uncertain outcome also rechecks current resource-field
permissions before and after examining Plane, including inside the transaction
that records confirmation. No SQLite transaction spans HTTP. A new context after revocation,
regrant or a purpose change cannot silently adopt an older operation's authority.

Recovery never calls POST, PATCH or DELETE. It uses protected expected content
and scoped GETs to observe the current effect:

| Operation | Recovery observation |
| --- | --- |
| `item.create` | Exact native `external_source=agent-native` and `external_id=operation UUID` lookup, followed by item detail, scope, attribution and prepared-field checks. |
| `cycle.create` | Complete bounded active and archived cycle inventories, one exact correlation candidate, then detail and prepared-field checks. |
| `comment.create`, `artifact.record` | Verify the parent item and scan its complete bounded comment inventory for one exact correlation candidate; recheck detail, internal access, attribution and literal content. |
| `project.update`, `item.update`, `cycle.update` | Read the original resource and compare the intended prepared fields and attribution. |
| `cycle.assign` | Read the item and target cycle, inspect memberships across the bounded active/archive cycle inventory, and require exactly the expected destination. |
| `cycle.remove` | Verify the item and target cycle remain readable and inspect the bounded cycle inventory for absence of memberships. |
| `dependency.add` | Verify both items and observe the intended in-project `blocked_by` edge. |

In the pinned Plane Community v1.4.2 API, the item correlation lookup returns a
single resource rather than a page. Multiple matching native rows cause an error
because that endpoint uses an exact single-row lookup. An error leaves recovery
unresolved; it does not authorize choosing the first item or sending another POST.
Cycle and comment list endpoints do not filter by external IDs, so the host
matches those fields after traversing their inventories.

Each inventory enforces the scoped read response bound, aggregate byte, page and
record limits; rejects repeated IDs/cursors and malformed pagination; checks
provided totals for consistency; and requires a complete final page. Active and
archived cycle inventories may not contain the same identity. Membership recovery
also caps the cycle inventory at 100 and requires known target/prior cycles to
appear; an omitted cycle cannot establish that membership was removed. Assignment
returns the native membership ID; removal identifies the work item. An archived
or deleted resource that cannot
be verified through its required detail endpoint remains unresolved.

## What confirmation means

A successful original delivery response and a later matching observation retain
different provenance:

- A directly confirmed response is historical delivery-response evidence.
- Recovery returns `source="matching_plane_effect"` and
  `confirmation="matching_effect"`. It confirms that the intended effect is
  currently observable under the original scope and comparison rules.
- Repeating recovery reads the durable outcome with `source="journal"` and
  preserves its confirmation provenance. A journal read does not promote a
  matching observation into original delivery-response evidence.

Plane correlation fields, content and creator metadata are mutable. A matching
record therefore does not prove exclusive historical causation or global
uniqueness. A matching update or relationship may also have been produced by
another authorized actor. Recovery never treats native text as a new instruction
or grant of authority.

In particular, **recovered item or cycle creation installs no editable-field
grant**. Original directly successful creation retains its existing field-grant
behavior after response verification. A recovered candidate can be edited only
under an explicit owner grant allowed by the existing ownership policy. Finding
mutable correlation tags is insufficient to acquire ownership.

## Unresolved outcomes and further attempts

Missing, deleted, duplicated, changed, inaccessible or mismatched evidence raises
`PlaneRecoveryUnresolved`. An attempted operation stays uncertain. HTTP errors,
429 responses, incomplete pagination and unavailable preparation do not establish
that the write failed, and recovery does not roll back native effects.

No automatic retry or mutation resend is implemented. The consumed operation UUID
cannot be delivered again after recovery, uncertainty, rejection or restart.
A new UUID represents a different attempt and is not semantically deduplicated;
using one to repeat uncertain work can create another native resource. Owner
review and a separately authorized next action remain necessary where evidence
cannot resolve an outcome.

Native pagination is offset-based and offers no atomic snapshot. External IDs
are not immutable receipts or transactionally enforced idempotency keys. Even a
complete, internally consistent inventory cannot prove historical uniqueness
through concurrent edits or deletions. Soft-deleted records are hidden by native
public reads. These limits are preserved in the result semantics rather than
converted into success or a presumed safe retry.

## Verification

The focused internal command is:

```sh
scripts/run_tests.sh tests/hermes_cli/test_agent_native_plane_recovery.py tests/hermes_cli/test_agent_native_plane_recovery_failures.py tests/hermes_cli/test_agent_native_plane_recovery_journal.py tests/hermes_cli/test_agent_native_plane_operation_lock.py
```

The internal checks use real local HTTP, separate SQLite connections and child
processes. They cover all ten operations, response loss, abrupt client-process
death after a native save, concurrent delivery/recovery exclusion, ambiguous
inventories, changed scope, revoked field grants and failed receipt transactions.
The final combined command passed **452 tests with zero failures or skips**:
112 recovery/preparation/operation-lock cases plus the existing 340 planning,
identity and schema checks. Ruff passed for all changed Python files. No browser
surface changed, so this increment uses HTTP/process acceptance rather than a
new Playwright flow.

```sh
scripts/run_tests.sh tests/hermes_cli/test_agent_native_plane_write_contracts.py tests/hermes_cli/test_agent_native_plane_write_access.py tests/hermes_cli/test_agent_native_plane_write_journal.py tests/hermes_cli/test_agent_native_plane_writes.py tests/hermes_cli/test_agent_native_plane_write_failures.py tests/hermes_cli/test_agent_native_plane_access.py tests/hermes_cli/test_agent_native_plane_reads.py tests/hermes_cli/test_agent_native_identity.py tests/hermes_cli/test_kanban_db_init.py tests/hermes_cli/test_agent_native_plane_recovery.py tests/hermes_cli/test_agent_native_plane_recovery_failures.py tests/hermes_cli/test_agent_native_plane_recovery_journal.py tests/hermes_cli/test_agent_native_plane_operation_lock.py
```

Development followed red/green increments for protected preparation, durable
attempts, each recovery family, process exclusion and failure handling. Review
regressions first reproduced unsafe grant acquisition from mutable creation
evidence, lost confirmation provenance, omitted-cycle false confirmation and
field revocation before receipt commit; their fixes passed. A final strengthened
membership assertion initially omitted the journal's required owner argument;
that test setup mistake was corrected before the combined passing run.
The [live probe](../ops/plane/probe_write_recovery.py) runs explicitly against a
selected local Plane installation:

```sh
.venv/bin/python ops/plane/probe_write_recovery.py --base-url http://localhost:19230 --output-dir "$HOME/.local/share/agent-native/plane/probes/an22-write-recovery-unique"
```

The output directory must be new, absolute and outside the repository. It stores
private fixture credentials, original native identities, a control database and
redacted evidence. The probe creates two disposable accounts, one workspace and
two private projects, with separate setup/readback and adapter keys. It uses no
owner or Builder account, uploads, issue links, model calls or browser surface.
Existing setup and cleanup procedures come from the scoped-write/read probes.

A controlled loopback relay forwards one armed real mutation to the selected
local Plane origin, receives its successful result, then closes the client socket
before returning that result. It does not replace the writer's transport or fake
an API outcome. Recovery reopens SQLite and creates a fresh host authority and
writer. Per-method relay counters detect any attempted resend, including a
recovery write that the relay would refuse to forward.

The expected acceptance evidence is ten recovered operation types, three
unresolved create cases, thirteen discarded successful native responses and zero
automatic resends. Negative cases include actual duplicate native correlation
rows created through explicit fixture operations, changed content and a deleted
candidate. Repeated recovery preserves `matching_effect`, repeated execution of
the consumed UUID is denied, native inventories remain stable, and existing
project IDs and host bindings remain unchanged.

The probe verifies that recovered creates receive no field grants. To exercise
later update and membership cases, the fixture owner separately checks the
relay's original native creation ID and independent Plane readback, then grants
fields explicitly. This is test setup outside recovery, not automatic ownership
acquisition.

The completed live Plane v1.4.2 run passed all ten recovery types and all three
unresolved creation cases: thirteen discarded successful native responses, exactly
thirteen adapter mutations and zero recovery resends. Independent readback
preserved project identities, host bindings, updated content and relationship
state. Cleanup deleted the fixture workspace, revoked its tokens and deactivated
both accounts. Private evidence is retained outside Git at
`~/.local/share/agent-native/plane/probes/an22-write-recovery-2/`.

Early disposable runs were interrupted for ownership review or failed on probe
assumptions: one compared the native membership ID with its work-item ID; another
expected only the two fixture projects despite Plane's seeded demo project. The
production journal already held the correct membership. The probe now checks
its independently read identity/scope and compares complete project inventories
before and after recovery. All early runs completed cleanup and are not full
acceptance evidence. The fresh full run above passed after those corrections.

AN-3's existing-Builder recovery scope is accepted using this evidence plus its
prior storage restore. General workspace/project creation recovery is explicitly
retained in AN-21 after the handoff; this probe only preserves existing project
bindings and never proves recovery of a lost project-provisioning response.
