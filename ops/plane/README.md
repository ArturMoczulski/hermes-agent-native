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

A routine restart retains named volumes. Back up the Plane PostgreSQL database and
uploads volume together with framework mappings before upgrades or destructive
operations. A database backup alone does not preserve attachment files. Keep
backups private and restore to isolated storage for verification. Full automated
backup/restore and integration reconciliation are tracked in the Builder backlog;
do not infer recovery certification merely from successful startup.

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
