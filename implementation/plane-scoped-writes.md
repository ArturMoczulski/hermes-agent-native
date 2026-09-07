# Scoped Plane writes — AN-20

This increment adds a trusted-host planning dispatcher, explicit write grants,
fixed tool schemas and durable mutation receipts on top of the
[scoped read boundary](plane-scoped-reads.md). It implements planning operations
for one bound project. The host still needs to connect these operations to an
authenticated admitted agent run; no managed worker, cadence or new dashboard
control is established by this increment.

## Host authority and content ownership

The [write authority](../agent_native/plane_write_access.py) requires an existing,
active project read binding plus an explicit owner-granted set of write operations.
A read binding alone grants no writes. The trusted host retains the authority,
opaque context, database and Plane credential. Requests derive agent/project identity
from that context, and revalidate read, write and soul revisions. Revocation or
scope changes invalidate old contexts; regranting does not revive them.

Operation permission and permission to edit existing content are separate:

- The owner selects allowed fields for each existing project, item or cycle with
  `allow_resource`. Granting an operation does not authorize rewriting every
  resource in the project. The adapter also verifies current remote membership.
- Confirmed item/cycle creation records fixed editable fields for that new resource
  under the binding. This does not grant additional operations; editing still
  requires the corresponding operation permission. Repeating a creation receipt
  cannot widen fields the owner subsequently narrowed.
- Comments and artifact references append agent-attributed content. They do not
  edit another author's comment or become trusted owner instructions.
- Moving an item between cycles requires its `cycle` field and membership-edit
  permission on the target and previous cycles. Dependencies require permission
  on the source item's `dependencies` field; the target remains in the same project.

These are host capability checks, not transport authentication. Neither an opaque
context nor a journal row proves that a runtime agent is currently admitted. The
future managed-run boundary must bind calls to the invoking run and enforce its
lifecycle. Generated code must never receive these Python authority objects,
`OWNER`, control storage, or service credentials.

## Discoverable operations

`PlaneWrites.tool_schemas(context)` returns fixed OpenAI-style function schemas
for the granted operations plus read-only `resource.inspect`. The
[contracts](../agent_native/plane_write_contracts.py) map public `plane_*` names to
internal operation names. `execute(context, operation_id, operation, arguments)`
validates arguments and dispatches only this whitelist. Context and the canonical
operation UUID are supplied separately by trusted host code, never by model args.

| Operation | Scope and behavior |
| --- | --- |
| `project.update` | Change the bound project's description with field permission and an observed fingerprint. |
| `item.create` | Create an item from a plain-text name/description, allowed priority and nonterminal state. |
| `item.update` | Change explicitly granted name, description, priority or nonterminal state using an observed fingerprint. |
| `comment.create` | Append plain text as an internal comment, attributed to the framework agent and verified Plane service user. |
| `cycle.create` | Create an outcome cycle with null start/end dates. |
| `cycle.update` | Change permitted name/description using an observed fingerprint; reject dated managed cycles and preserve the existing Plane owner. |
| `cycle.assign` | Assign or move an item after checking its fingerprint and explicitly expected previous cycle, including null for unassigned. |
| `cycle.remove` | Remove the expected current membership after checking the item fingerprint. |
| `dependency.add` | Add an in-project `blocked_by` relationship after checking current source and bounded dependency traversal; reject detected cycles. |
| `artifact.record` | Append a clearly labeled unverified artifact reference and optional description as plain text. |

`resource.inspect` reads a project, item or cycle with a source fingerprint.
Project inspection has no caller-supplied project ID. Item/cycle inspection
requires a canonical resource UUID. Item inspection also supplies the current
`cycle_id` and `dependencies` alongside the selected `resource` and `fingerprint`,
so callers can form operations from actual source observations. These separate
reads are point-in-time observations, not an atomic project snapshot. Membership
inspection rejects ambiguous memberships and inventories above 100 cycles;
dependency traversal rejects graphs above 100 items rather than silently truncating.

Unknown fields and arbitrary HTTP operations are rejected. Names, descriptions,
comments and references have explicit length bounds; arguments are bounded to
32 KiB of canonical UTF-8 JSON. Update operations need at least one editable
field. Arguments remain plain text and the HTTP adapter escapes comment/item
HTML. Agent labels do not authenticate quoted text as human direction.

Artifacts are references, not evaluated results or verified uploads. The adapter
does not fetch a reference or create a native Plane issue link that would invoke
Plane's server-side crawler. It grants no file download, publication or arbitrary
network capability.

This surface accepts only states in Plane's `backlog`, `unstarted` and `started`
groups. It cannot mark a task accepted, complete or cancelled by choosing a
terminal board state. Framework result evaluation and lifecycle operations remain
separate work. Cycles remain undated; no scheduling estimates or date controls
are introduced.

## Source checks and concurrent changes

Fingerprints hash bounded canonical JSON of selected source metadata, excluding
only top-level `updated_at`. Plane can touch that timestamp asynchronously after a
successful write without changing task content. The entire input is still validated
before exclusion; content and other projected fields remain conflict-checked.
Previously stored timestamp-inclusive fingerprints require a fresh inspection if
they mismatch; they are not silently accepted. Before an
edit, the adapter re-fetches the relevant resource and compares the supplied
fingerprint. Cycle membership and dependencies receive additional current-source
checks. Scoped reads and responses retain project/resource validation, and the
adapter rechecks authority before and after the network operation. Returned
business fields must match the requested values, including literal HTML text,
undated cycle fields and preserved cycle ownership. Creation/comment attribution
and update attribution must match the configured Plane service identity.

During managed work, a `PlaneWriteConflict` confirmed rejected before delivery is
returned as a retained `status: conflict` tool result, with `write_attempted: false`.
The agent must inspect current content and relationships and decide whether a new
operation is appropriate. This covers editor-only HTML changes without hiding real
edits or automatically replaying writes. Repeating the original tool-call ID returns
the same conflict receipt. Unknown delivery and authority failures still stop work.
A new operation remains subject to normal authority and source checks.

These checks are advisory conflict detection, not atomic compare-and-swap.
Plane can change between the read and write; a fingerprint cannot lock the remote
resource. It also does not prove that a changed brief is owner-authorized or that
an artifact meets acceptance criteria. The
[API characterization](plane-api-validation.md) records the pinned release's
conditional-write limitations. AN-23 source reconciliation remains required before
safe managed admission relies on current planning information.

## One-shot intents and outcomes

The [journal](../agent_native/plane_write_journal.py) commits a `pending` intent
before a mutation request can be sent. It stores operation/scope/revision IDs,
argument hashes, timestamps and outcome events. It does not store task text,
request/response bodies, secrets or artifact bytes. Trusted owner inspection can
read the journal and event history.

A host operation UUID identifies one attempt. Once used, that UUID cannot be
sent again, including after rejection, uncertainty or restart. Authorization
failures record a bounded denial event without echoing model input. The dispatcher
returns confirmed resource metadata only after response/source checks and a
successful durable outcome record.

- `confirmed`: the operation's result was observed and its receipt persisted.
- `rejected`: failure occurred before the mutation request was attempted.
- `unknown`: a request may have affected Plane but its result could not be confirmed,
  including response errors or authority changes during the request.
- `pending`: no final receipt was durably recorded. A crash or failure writing the
  final journal record can leave this state even when Plane accepted the mutation.

Neither `pending` nor `unknown` permits automatic retry. HTTP errors and timeouts
do not prove that Plane had no effect. Successful upstream changes are not rolled
back by a later local failure, and a journal failure must not be presented as a
confirmed result.

A new UUID is a new attempt and is not semantically deduplicated against an earlier
request. Creating a new UUID to retry uncertain work can create duplicates.
`external_source`/`external_id` support correlation where the endpoint accepts
them; they are not a remote uniqueness or exactly-once guarantee. The original
AN-20 hash-only journal could not reconstruct a complete lost request by itself.

[AN-22 recovery](plane-write-recovery.md) now adds protected preparations, durable
attempt markers and explicit read-only investigation of uncertain outcomes.
Its evidence and limitations are separate from the AN-20 results below. Neither
increment supplies managed-run authentication or a general framework event stream.

## Verification

The focused internal command is:

```sh
scripts/run_tests.sh tests/hermes_cli/test_agent_native_plane_write_contracts.py tests/hermes_cli/test_agent_native_plane_write_access.py tests/hermes_cli/test_agent_native_plane_write_journal.py tests/hermes_cli/test_agent_native_plane_writes.py tests/hermes_cli/test_agent_native_plane_write_failures.py tests/hermes_cli/test_agent_native_plane_access.py tests/hermes_cli/test_agent_native_plane_reads.py tests/hermes_cli/test_agent_native_identity.py tests/hermes_cli/test_kanban_db_init.py
```

Contract checks use pure validation. Authority/journal checks use isolated SQLite;
adapter checks exercise the real HTTP boundary against an isolated local service.
They require no model call, personal Plane project mutation or browser surface.
The combined command passed **340 tests, zero failures or skips**: 109 contract,
29 write-authority, 31 journal, 52 HTTP write/failure, and 119 existing read,
identity and schema checks. Ruff passed for all changed Python files.

Development proceeded through failing contracts/authority/journal checks and four
HTTP increments. The last HTTP increment exposed ten missing checks before the
fix: item inspection lacked cycle/dependency observations, and successful status
codes could hide incorrect returned fields. All ten passed after implementation.
Independent failure checks exercise revocation during preflight and after delivery,
forged attribution, malformed/oversized/truncated responses, redirects, rate limits,
replay, and real SQLite failures before intent and outcome persistence.

This increment has no new UI; Playwright belongs with the later exposed workflow.
The live Plane result is recorded below.


## Live Plane verification

The opt-in probe passed against local Plane Community **v1.4.2** using two
disposable accounts, a fresh workspace and two private projects. The adapter key
could access both projects before framework scoping was applied. Independent
readback used a separate key.

| Check | Observed result |
| --- | --- |
| Planning operations | All ten operations confirmed, including an explicit move between two cycles and membership removal. |
| Created resources | One item, one undated cycle and two attributed internal comments; one comment records an unverified artifact reference. |
| Existing content and scope | Ungranted fields and cross-project writes denied; original owner/foreign records unchanged. |
| Authority | Forged/read-only/revoked/stale-purpose contexts denied; regrant did not revive an old context. |
| Source and replay | Stale fingerprint and reused operation UUID rejected; no duplicate item created. |
| Durable evidence | Pending intent precedes confirmed outcome; scope/agent attribution and denial events retained without credentials or task text. |
| References | No native issue links, uploads or artifact fetches created. |
| Cleanup | Fixture workspace deleted, both keys revoked and both accounts deactivated. |

Private recovery evidence is retained outside Git at
`~/.local/share/agent-native/plane/probes/an20-scoped-writes-1/`. Workspace deletion
and account deactivation are logical Plane operations, not proof of physical
record erasure. The proof did not use the owner/Builder workspace or credential.

```sh
.venv/bin/python ops/plane/probe_scoped_writes.py --base-url http://localhost:19230 --output-dir /absolute/private/new-scoped-write-probe
```

The script requires explicitly unconfigured SMTP and a new private directory.
It paces adapter operations and never retries mutations; inspect its cleanup
report after interruption. The live proof establishes this planning boundary,
not autonomous judgment, concurrent retry recovery or a managed First Builder.
