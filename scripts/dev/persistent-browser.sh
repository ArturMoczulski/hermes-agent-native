#!/usr/bin/env bash
# Dedicated, long-lived Chromium instances for agent browsing and browser tests.
#
# Two roles keep profiles separate so test state never mixes with the agent's:
#   agent -> CDP 9222, profile ~/.local/share/agent-native/browser/profile
#   test  -> CDP 9223, profile ~/.local/share/agent-native/browser/profile-e2e
#
# Both are long-lived. The agent's Playwright MCP attaches to "agent"; every
# dashboard e2e spec attaches to "test" over CDP. Sessions (cookies,
# localStorage, open tabs) survive across turns, sessions and Kilo restarts.
#
# Usage:
#   scripts/dev/persistent-browser.sh <command> [agent|test]
#     start       run in the foreground; supervise as a persistent background process
#     stop        stop the role's browser (matches only its own profile)
#     status      exit 0 + /json/version when up
#     endpoint    print the CDP HTTP endpoint
#     ws-endpoint print the browser WebSocket URL
#
# Environment:
#   AN_BROWSER_ROLE      default role when omitted (agent)
#   AN_BROWSER_PORT      override the role's CDP port
#   AN_BROWSER_PROFILE   override the role's profile dir
#   AN_BROWSER_BIN       explicit Chrome/Chromium executable
#
# Profiles live outside the repository; never commit them or point tests at a
# personal profile.
set -euo pipefail

CMD="${1:-start}"
ROLE="${2:-${AN_BROWSER_ROLE:-agent}}"

case "$ROLE" in
  agent) DEF_PORT=9222; DEF_PROFILE="$HOME/.local/share/agent-native/browser/profile" ;;
  test)  DEF_PORT=9223; DEF_PROFILE="$HOME/.local/share/agent-native/browser/profile-e2e" ;;
  *) echo "unknown role: $ROLE (use agent|test)" >&2; exit 2 ;;
esac
PORT="${AN_BROWSER_PORT:-$DEF_PORT}"
PROFILE="${AN_BROWSER_PROFILE:-$DEF_PROFILE}"
CACHE="${HOME}/Library/Caches/ms-playwright"   # macOS; Linux uses ~/.cache/ms-playwright
[[ -d "$CACHE" ]] || CACHE="${HOME}/.cache/ms-playwright"

endpoint() { printf 'http://127.0.0.1:%s\n' "$PORT"; }

find_bin() {
  if [[ -n "${AN_BROWSER_BIN:-}" ]]; then printf '%s\n' "$AN_BROWSER_BIN"; return 0; fi
  local best='' best_revision='' revision='' dir rest
  # Highest-numbered cached Chrome for Testing across the common platform layouts.
  for dir in "$CACHE"/chromium-[0-9]*; do
    [[ -d "$dir" ]] || continue
    revision="${dir##*-}"
    [[ "$revision" =~ ^[0-9]+$ ]] || continue
    (( revision > ${best_revision:-0} )) || continue
    for rest in \
      "chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing" \
      "chrome-mac-x64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing" \
      "chrome-linux64/chrome" \
      "chrome-linux/chrome"; do
      if [[ -x "$dir/$rest" ]]; then
        best="$dir/$rest"; best_revision="$revision"
        break
      fi
    done
  done
  if [[ -n "$best" ]]; then printf '%s\n' "$best"; return 0; fi
  for name in \
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    "/usr/bin/google-chrome" \
    "/usr/bin/chromium" \
    "/usr/bin/chromium-browser"; do
    [[ -x "$name" ]] && { printf '%s\n' "$name"; return 0; }
  done
  echo "No Chrome/Chromium executable found; set AN_BROWSER_BIN" >&2
  return 1
}

case "$CMD" in
  start)
    BIN="$(find_bin)"
    mkdir -p "$PROFILE"
    printf 'persistent browser (%s)\n  bin:     %s\n  profile: %s\n  cdp:     %s\n' \
      "$ROLE" "$BIN" "$PROFILE" "$(endpoint)"
    exec "$BIN" \
      --remote-debugging-port="$PORT" \
      --remote-debugging-address=127.0.0.1 \
      --user-data-dir="$PROFILE" \
      --no-first-run \
      --no-default-browser-check \
      --restore-last-session \
      --window-size=1600,1100 \
      about:blank
    ;;
  stop)
    # Match only this role's profile so the other role and other Chrome windows survive.
    pkill -f "user-data-dir=$PROFILE" || true
    printf 'stopped %s browser (profile %s)\n' "$ROLE" "$PROFILE"
    ;;
  status)
    curl -fsS "$(endpoint)/json/version" || { echo "not running: $(endpoint)" >&2; exit 1; }
    ;;
  endpoint)
    endpoint
    ;;
  ws-endpoint)
    curl -fsS "$(endpoint)/json/version" \
      | sed -n 's/.*"webSocketDebuggerUrl":[[:space:]]*"\([^"]*\)".*/\1/p'
    ;;
  *)
    echo "usage: $0 {start|stop|status|endpoint|ws-endpoint} [agent|test]" >&2
    exit 2
    ;;
esac
