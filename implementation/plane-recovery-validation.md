# Plane recovery validation — 2026-09-06

Plane Community v1.4.2, local Compose project `agent-native-plane`. AN-3 covers
storage recovery and reconnect behavior. Its final acceptance criterion also covers
partial failures and retry safety. The later AN-22 acceptance below completes the
bounded existing-Builder scope. General new-project/workspace provisioning
recovery remains explicitly in AN-21; it has not been verified.

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
but no atomic concurrency guarantee. At the storage-only review, AN-3's partial-failure/retry criterion remained
unverified. AN-22 subsequently added protected mutation preparations and explicit
recovery; the acceptance below supersedes that blocker for the existing Builder
planning home. Storage recovery alone still does not accept the entire integration.

See [operator procedure](../ops/plane/README.md#recovery) and
[API boundary findings](plane-api-validation.md).


## Existing-Builder retry acceptance — 2026-09-06

[AN-22](plane-write-recovery.md) recovered all ten planning operation types after
successful native responses were discarded. Fresh host connections recovered
the same item IDs and retained existing project IDs/bindings. Repeated recovery
and repeated execution of the consumed operation UUID created nothing new.
Thirteen native responses were lost; ten effects were confirmed and three
ambiguous creations remained unresolved, with zero automatic resends. Separate
real-process tests cover abrupt client death and concurrent delivery/recovery.
Fixture cleanup passed; the previous storage/attachment evidence remains valid.

AN-3 is accepted for that bounded existing-Builder scope after explicit review.
The original broader requirement to recover new workspace/project creation from
partial failures is retained in AN-21, already deferred after the handoff under
the owner's priority. No project-provisioning implementation or lost-project-create
proof exists yet. Source notifications/freshness (AN-23), managed-run restart
reconciliation and service disaster cutover remain their own unfinished gates.
