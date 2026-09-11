#!/bin/sh
# Start the local Hermes dashboard for the agent-native preview.
#
# The live profile home lives inside this checkout (gitignored) so runtime
# state, databases, credentials, agent workspaces and logs stay with the
# project instead of under $HOME. See ops/dashboard/README.md.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)

export HERMES_HOME="${HERMES_HOME:-$ROOT/.hermes-agent-native-preview}"
export HERMES_KANBAN_DB="${HERMES_KANBAN_DB:-$HERMES_HOME/kanban.db}"

# Node is only needed when the dashboard builds the renderer; --skip-build keeps
# startup fast and uses the already-built web/ui-tui assets.
exec "$ROOT/.venv/bin/hermes" dashboard --skip-build --no-open \
  --host "${HERMES_DASHBOARD_HOST:-127.0.0.1}" \
  --port "${HERMES_DASHBOARD_PORT:-19222}" "$@"
