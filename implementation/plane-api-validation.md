# Plane v1.4.2 API validation — AN-2

Evaluated 2026-09-06 against the local Community installation. Plane remains a
suitable planning backend. Its API does not replace framework authorization,
execution admission, conflict handling or durable reconciliation.

## Live observations

`ops/plane/probe_api.py` created two disposable local accounts and a separate
workspace. One account administered a secret project; the second belonged to the
workspace but not that project. The probe read no owner/Builder credentials.
It deleted its workspace, revoked both tokens and deactivated both accounts.

| Check | Observed result | Required integration behavior |
| --- | --- | --- |
| Pagination | Three one-item pages returned three unique IDs, matching created records. | Follow next_page_results/next_cursor; never assume the first page is complete. |
| Repeated external identity | Sequential repeated POST returned 409 and the original item ID. | Reconcile conflict IDs and payloads, rather than treating every 409 as success. |
| Conditional write | GET supplied no ETag. PATCH with an intentionally invalid If-Match returned 200 and overwrote the first update. | No demonstrated atomic conditional-write protection; detect drift, limit owned fields and surface conflicts. |
| Private-project access | Non-project workspace member received 404 for project detail, and 403 for item list/detail, update and creation. | Useful native boundary; still enforce agent scope in the adapter. Other operation families need their own authorization tests. |
| Deletion | DELETE succeeded; subsequent item GET returned 404. | Missing work must not be silently recreated or treated as accepted. |
| Rate limit | Disposable API key reached 429; Retry-After was 59 seconds; custom remaining header was absent. | Share a quota per key, honor Retry-After and tolerate absent quota headers. |

Earlier setup demonstrated project/item creation, custom states, cycle creation
and assignment, 22 native dependency links, comments and read-back. The owner
browser verified project and cycle views, including after a full service restart.
These checks do not prove every resource's permissions or atomicity.

Reproduce the isolated characterization with a new private output directory:

```sh
.venv/bin/python ops/plane/probe_api.py --base-url http://localhost:19230 --output-dir /absolute/private/new-probe-directory
```

The directory must not already exist. It contains a private recovery manifest and
report, including test credentials; never commit it. Signup must be available and
SMTP unconfigured. The probe consumes only its own API-key quota. Review cleanup
results if interrupted; do not delete any workspace except its recorded probe ID.
The successful run is locally retained at
`~/.local/share/agent-native/plane/probes/an2-contract-3/report.json`.

## Pinned-source findings, not live-delivery tests

[Webhook sender](https://github.com/makeplane/plane/blob/v1.4.2/apps/api/plane/bgtasks/webhook_task.py):
X-Plane-Signature uses HMAC-SHA256 over serialized payload bytes. Each task attempt
creates a new X-Plane-Delivery ID. Transport exceptions retry up to five times;
HTTP error responses do not trigger that retry path. Exhausted transport failures
deactivate the webhook. Private callback targets require an allowed destination.

Consequently, signature verification must use the received bytes and constant-time
comparison. A delivery ID alone cannot deduplicate task retries. Polling must
repair missed notifications, including receiver 429/503 responses. Live signature,
retry and recovery tests belong to AN-5; no callback delivery was claimed here.

[API throttle](https://github.com/makeplane/plane/blob/v1.4.2/apps/api/plane/api/rate_limit.py)
keys quotas by API credential. Its reset header is a conservative hint rather
than the exact rolling-window replenishment time. The live 429 test confirms
rejection and Retry-After behavior for this installation.

[Work-item endpoints](https://github.com/makeplane/plane/blob/v1.4.2/apps/api/plane/api/views/issue.py)
check external identity before saving. The
[model](https://github.com/makeplane/plane/blob/v1.4.2/apps/api/plane/db/models/issue.py)
has no uniqueness constraint on that external pair. Sequential duplicate detection
is therefore not a concurrency-safe idempotency guarantee. No concurrent duplicate
race was exercised here; serialize adapter creates and detect duplicate matches.

## Evaluation and next work

AN-2's characterization is accepted: required capability areas have either live
observations or identified source evidence and explicit validation gaps. Nothing
requires Commercial Edition for the planning operations exercised. Webhook delivery,
resource-specific scope enforcement and race/reconnect behavior remain acceptance
work for AN-4/AN-5, rather than claims of completed managed integration.

AN-4 must start with a small scoped read/write boundary and denial tests. AN-5 must
add durable operation intent, recovery lookup and polling; it must not claim
compare-and-swap or exactly-once delivery from these upstream APIs. AN-3 separately
verifies isolated backup/restore before further integration work.
