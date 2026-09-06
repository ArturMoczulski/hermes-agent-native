# Scoped Plane read validation — AN-19

The trusted-host read boundary is implemented and verified against the pinned
local Plane Community v1.4.2 installation. It does not establish managed-agent
launch authentication or expose a new worker tool or dashboard endpoint.

## Implemented boundary

- Owner-managed project read grants live in the existing control database, with
  revisioned revocation tombstones. No Plane key is stored with a grant.
- Opaque contexts come from trusted host control. Actor labels or caller-selected
  workspace/project strings cannot mint or expand a context. Each read rechecks
  the grant and purpose revision; revocation and regrant do not revive old handles.
- Fixed project-scoped reads cover project details, work items, comments,
  attachment metadata, undated cycles and states. Nested reads verify their parent
  item first, including when an upstream list could otherwise return empty.
- Returned identities must match the expected workspace/project/item. Responses
  project selected scalar fields; attachment storage keys, signed URLs and storage
  metadata are excluded. Plane comments remain information, not owner authority.
- No redirects or process proxy/environment credentials are used. Bodies are
  bounded while streaming; page, record and aggregate limits fail explicitly.
  Pagination rejects invalid/repeated cursors and duplicated resources instead of
  silently truncating or returning partial results. Lists are observations, not
  a claimed atomic snapshot of a changing Plane project.
- Safe errors distinguish upstream HTTP status and retry delay without exposing
  bodies or credentials. The reader does not blindly retry or invent missing work.

The current per-call limits are 1 MiB per response, 8 MiB across a list, 100 pages
and 5,000 records. They are request safeguards, not product scale guarantees;
larger reads report the limitation. The service accepts HTTPS or loopback HTTP.
Credentials and contexts stay in the host process. The offline worker sandbox
and its explicit mounts are unchanged.

## Test-first evidence

The access increment began with 19 failing behavioral cases against explicit
unimplemented operations, then passed with persistence and context validation.
Added real database reopening, cross-connection revocation and concurrent grant
checks; 21 access tests pass. The HTTP increment progressed through failing
project, resource and boundary cases, including two nested-parent authorization
regressions, to 79 passing tests using real loopback HTTP and isolated SQLite.

Tests cover forged actors/contexts, stale purpose/workspace grants, revocation,
resource mismatches, post-request revocation, pagination, redirects, malformed
metadata, rate-limit retry information, streaming limits without Content-Length,
aggregate limits and safe failure behavior. Existing identity, owner API and
schema tests are included in the final focused regression run: **122 passed,
zero failed**. The repository lint checks also passed.

```sh
scripts/run_tests.sh tests/hermes_cli/test_agent_native_plane_access.py tests/hermes_cli/test_agent_native_plane_reads.py tests/hermes_cli/test_agent_native_identity.py tests/hermes_cli/test_agent_native_api.py tests/hermes_cli/test_kanban_db_init.py
```

This is an internal host boundary, so HTTP/storage integration tests are primary.
No new user interface was created; Playwright coverage accompanies later exposed
user workflows. No model response or autonomous-agent behavior is claimed here.

## Live Plane observations

The opt-in probe created two disposable local accounts, a workspace with two
private projects, real text attachments, comments and native undated cycles. Its
service credential could read both projects before the framework restricted it.

| Check | Observed result |
| --- | --- |
| Authorized work | Three items recovered over one-item pages; item detail, one comment, one attachment, two cycles and five states matched fixture records. |
| Independent scopes | The second root could read its own separate project. |
| Cross-project item/comment/attachment reads | All denied with HTTP 404 through the bound project path. The underlying service control reads established that the foreign resources existed. |
| Forged contexts | Rejected by framework authority. |
| Revocation and regrant | Revoked contexts remained invalid; an explicitly issued fresh context worked. |
| Purpose change | Previously issued context became invalid. |
| Attachment output | File metadata was available without storage/download capabilities. |
| Cleanup | Exact uploaded objects were hash-checked, deleted and verified absent; workspace deleted, API tokens revoked and both accounts deactivated. |

Plane's workspace deletion and account deactivation are logical operations, not
proof of physical removal of every database record. No owner or Builder workspace,
credential or account was used. The private manifest/report are retained outside
Git at `~/.local/share/agent-native/plane/probes/an19-scoped-reads-1/`.

Reproduce only against an explicitly selected local installation with SMTP
unconfigured, using a new private directory:

```sh
.venv/bin/python ops/plane/probe_scoped_reads.py --base-url http://localhost:19230 --output-dir /absolute/private/new-scoped-read-probe
```

The probe uploads only its small fixture files and uses the existing API container
to erase only recorded, verified object keys. Inspect its cleanup report after an
interruption; do not delete unrelated objects or workspaces.

## Remaining integration

AN-20 adds scoped planning writes; AN-22 addresses uncertain mutations and retries.
Managed launch identity and admission remain AN-24/AN-7 work. They must retain the
context privately, associate it with the invoking run, and enforce lifecycle.
Parent delegation policy, unified authorization events and attachment downloading
remain separate capabilities. A passing read boundary does not complete M1 or
establish an autonomous root.
