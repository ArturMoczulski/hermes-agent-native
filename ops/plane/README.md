# Local Plane Community deployment

Pinned application release: **v1.4.2**. Compose is derived from the
[official release](https://github.com/makeplane/plane/releases/tag/v1.4.2), and retains the upstream [AGPL license](LICENSE.plane).
HTTP is published only on `127.0.0.1:19230`. Application data uses named Docker volumes
under Compose project `agent-native-plane`. This installation belongs to the owner;
it is not an isolated managed-agent runtime.

From this repository, start or stop the local service with:

```sh
docker compose -p agent-native-plane --env-file "$HOME/.local/share/agent-native/plane/plane.env" -f ops/plane/compose.yaml up -d
docker compose -p agent-native-plane --env-file "$HOME/.local/share/agent-native/plane/plane.env" -f ops/plane/compose.yaml stop
```

Use the same prefix with `ps --all`, `logs --tail 50 api`, or `restart` for operation.
Never add `down -v` to routine stop/restart: it deletes persistent planning data.
Docker must be running. Closing the browser does not stop Plane; shutting down
this computer does. The deployment is local, not an always-on remote installation.

Private configuration is outside Git at `~/.local/share/agent-native/plane/`:
`plane.env` holds generated service secrets; `accounts.json` holds local login
credentials; `builder-api.json` holds the Builder's API credential. Do not print,
commit, attach to work items, or forward these files to managed workers. The owner
account is for installation control; routine planning uses the separate Builder.

The service uses no configured SMTP delivery. Local account identifiers use the
reserved `agent-native.test` domain. No external email account is needed.

See [Builder planning context](../../first-builder/PLANE.md) for the project,
active-cycle discovery and API workflow. Follow the [integration plan](../../implementation/plane-project-management.md)
for managed agents; this local setup does not implement the framework adapter.

## Recovery

A routine restart retains named volumes. Before upgrades or destructive operations,
create and verify a private database and uploads snapshot:

```sh
.venv/bin/python ops/plane/verify_restore.py --output-dir "$HOME/.local/share/agent-native/plane/backups/unique-snapshot-name"
```

This operator command targets the local `agent-native-plane` installation. It
requires Docker, existing pinned images (plus an already installed Alpine image),
and the private Builder API configuration. It refuses an existing output directory.
It briefly stops the proxy, application writers and MinIO to capture a consistent
database/object snapshot, then restarts the original service. Run it during a
maintenance window without other operators writing directly to the database.

The directory contains `database.dump`, `uploads.tgz`, private `plane.env`, Compose
configuration, image lock, restore-only MinIO environment and `report.json`.
Treat the entire directory as secret: database rows and configuration include
credentials. It is mode 0700; backup files are mode 0600. Preserve the matching
configuration, including encryption/signing and object-store keys. Store a separate
protected copy outside this computer for protection against disk loss; this command
does not create off-machine backups or a scheduled backup policy.

Verification restores PostgreSQL and uploads into **new disposable volumes**, with
no restored application, worker or dispatcher running. It checks this project's
work-item IDs, retrieves a verification object through the restored S3 API, and
reconnects to the original API. Original volumes are never restore targets. The
script removes its temporary resources and source verification object; the backup
remains. Read `result`, `checks` and `cleanup` in the private report. A process failure
or any cleanup error requires investigation. If interrupted before normal cleanup,
use the report's exact temporary resource names; restart the original service with
the normal Compose command above. Never remove original volumes to clean a probe.

For operator recovery, restore the database dump with `pg_restore` into an empty
PostgreSQL database and unpack uploads into a new MinIO volume, using the matching
private configuration and pinned images. The verifier demonstrates these commands
without cutting over the live installation. Keep application writers stopped while
restoring both stores. Validate the restored data before deciding to replace the
original deployment. A production cutover, credential rotation, whole-framework
mapping recovery and replay of pending integration writes are separate work.

See [recovery evidence and limitations](../../implementation/plane-recovery-validation.md).
A successful storage restore is not proof that agent retries are duplicate-safe.

## Browser verification

`node ops/plane/smoke.cjs` checks that the API-created backlog and first cycle
render for the owner. It reads the private local planning context and existing
owner session cookies; it does not log credentials or create work. Set
`PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` to an existing compatible Chromium binary.
A fresh installation must complete API onboarding before this check applies; an
expired session requires a normal local login/session refresh. No browser download
is part of these instructions. The check is specific to the initial local setup.

The owner must explicitly be a project member: workspace administration alone
did not open the Builder-created project in the UI. Provisioning must include
owner project membership. The current owner is a project administrator.

`images.lock.json` records the image IDs, repository digests and architectures
actually pulled. The Compose file pins application tags and the MinIO digest.

## API characterization

See [AN-2 validation](../../implementation/plane-api-validation.md) for the isolated
`probe_api.py` command, observations and remaining gaps. It creates disposable
accounts/workspace and checks cleanup; it does not use the Builder's API quota.


## Scoped planning verification

The trusted-host [read proof](../../implementation/plane-scoped-reads.md) and
[write proof](../../implementation/plane-scoped-writes.md) use disposable accounts
and projects with separate API keys. The write probe exercises all ten planning
operations and authorization failures without uploads or reference fetches:

```sh
.venv/bin/python ops/plane/probe_scoped_writes.py --base-url http://localhost:19230 --output-dir /absolute/private/new-scoped-write-probe
```

Use a new private directory outside the repository. It retains the recovery
manifest, SQLite journal and a redacted report. Read both `result` and `cleanup`;
success requires deletion of its fixture workspace, token revocation and account
deactivation. These are logical Plane operations, not physical database erasure.
No owner/Builder project, credentials, model or managed worker is used by the probe.


## Uncertain write verification

The [AN-22 recovery proof](../../implementation/plane-write-recovery.md) discards
successful native responses through a loopback relay, then reopens the host
journal and recovers through GETs. It covers all ten planning operations and
ambiguous creation evidence without automatically resending mutations:

```sh
.venv/bin/python ops/plane/probe_write_recovery.py --base-url http://localhost:19230 --output-dir /absolute/private/new-write-recovery-probe
```

The same disposable-account and private-output rules above apply. Require a
completed report, zero recovery mutation attempts and successful cleanup.
Protected preparations contain planning text; protect the control database and
its backups along with the private fixture credentials. Keep operation lock files
in place while that database can be used; do not replace an open database.


## Ordinary agent planning homes

The dashboard now provisions a separate private planning home and initial discovery
task for new ordinary roots. It uses a protected, explicitly configured host
connection; routine Builder project-management credentials are not reused by agents.
See [writer setup](../../implementation/writer-startup-setup.md) for the exact
configuration, current human-account requirement, recovery behavior and limits.
