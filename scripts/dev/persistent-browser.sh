#!/usr/bin/env bash
# Dedicated, long-lived Chromium for agent browsing and browser tests.
#
# Keeps ONE browser alive with a private profile and a loopback CDP endpoint so
# the agent's Playwright MCP and opt-in test runs attach to the same instance
# instead of cold-starting and closing a browser per action. The session (cookies,
# localStorage, open tabs) survives across turns, sessions and Kilo restarts.
#
# Usage:
#   scripts/dev/persistent-browser.sh start     # run in the foreground; supervise it as a
#                                               # persistent background process, do not nohup
#   scripts/dev/persistent-browser.sh stop
#   scripts/dev/persistent-browser.sh status    # exit 0 + /json/version JSON when up
#   scripts/dev/persistent-browser.sh endpoint  # print the CDP HTTP endpoint
#   scripts/dev/persistent-browser.sh ws-endpoint  # print the browser WebSocket URL for test attach
#
# Environment:
#   AN_BROWSER_PORT       CDP port on loopback (default 9222)
#   AN_BROWSER_PROFILE    private profile dir (default ~/.local/share/agent-native/browser/profile)
#   AN_BROWSER_BIN        explicit Chrome/Chromium executable (overrides discovery)
#
# The profile lives outside the repository; never commit it or point tests at it.
set -euo pipefail

PORT="${AN_BROWSER_PORT:-9222}"
PROFILE="${AN_BROWSER_PROFILE:-$HOME/.local/share/agent-native/browser/profile}"
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

case "${1:-start}" in
  start)
    BIN="$(find_bin)"
    mkdir -p "$PROFILE"
    printf 'persistent browser\n  bin:     %s\n  profile: %s\n  cdp:     %s\n' "$BIN" "$PROFILE" "$(endpoint)"
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
    # Match only the dedicated profile so unrelated Chrome windows are untouched.
    pkill -f "user-data-dir=$PROFILE" || true
    printf 'stopped persistent browser (profile %s)\n' "$PROFILE"
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
    echo "usage: $0 {start|stop|status|endpoint|ws-endpoint}" >&2
    exit 2
    ;;
esac
