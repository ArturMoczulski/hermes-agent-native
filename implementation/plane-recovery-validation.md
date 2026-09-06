# Plane recovery validation — 2026-09-06

Plane Community v1.4.2, local Compose project `agent-native-plane`. AN-3 covers
storage recovery and reconnect behavior. Its final acceptance criterion also covers
partial failures and retry safety; **that criterion remains open** until the managed
adapter and reconciliation work in AN-4/AN-5 provide an implementation to test.

## Observed results

`ops/plane/verify_restore.py` created a consistent PostgreSQL dump and MinIO archive
while application writers and object storage were stopped. It restarted the original
installation before testing the restore. Private backup/configuration/report:
`~/.local/share/agent-native/plane/backups/an3-20260906-2/`.

- The dump restored successfully into a new PostgreSQL volume with no network.
- All 16 live project work-item IDs matched the restored records exactly.
- A unique verification object survived the archive/restore; its bytes matched
  their SHA256 after retrieval through an isolated MinIO S3 endpoint.
- The original Builder API reconnected and returned the same 16 IDs.
- Temporary restore containers, volumes, internal network and source verification
  object were removed. Original volumes remained intact.

No restored application or dispatcher ran. The original instance remains the live
planning home. The private report records backup checksums and cleanup evidence.
The separate Playwright Chromium check passed after recovery: the owner could
see the API-created backlog and first-cycle work. No browser was downloaded.

The first attempt failed because PostgreSQL's inherited host configuration required
a password. Its cleanup restarted the original services and removed the source
verification object. The corrected dump uses the database container's configured
credentials over loopback without printing them. The second attempt passed.

## Limits and next work

This validates a local storage snapshot, representative object retrieval, stable
work IDs and reconnect. It does not certify every relation or attachment, disaster
cutover, off-machine backups, framework mappings, queue replay, or scheduled backups.
The current verifier intentionally requires one page (at most 100 project items)
and fails rather than silently accepting an incomplete item inventory.

AN-2 demonstrated sequential duplicate external-ID requests return the original ID,
but no atomic concurrency guarantee. AN-3's broader partial-failure/retry criterion
remains unverified. AN-4 introduces scoped operations; AN-5 must persist mutation
intents and reconcile ambiguous results without blindly creating new projects or
items. Retain AN-3 as incomplete until that evidence exists; do not equate recovery
of storage with acceptance of the entire integration.

See [operator procedure](../ops/plane/README.md#recovery) and
[API boundary findings](plane-api-validation.md).
