#!/usr/bin/env python3
"""Deterministic Plane status for the external First Builder.

Plane is the single source of truth for long-term planning, current work and
milestones. This read-only tool prints the compact state the Builder needs on
resume so it does not re-read a stale planning file or spend model tokens
rediscovering priorities.

Commands:
    last-worked [--count N]   N most recent items the Builder touched
    current    [--count N]    work in progress + next N ready priorities
    milestones                current, next and last capability milestone
    summary                   compact combination of the above

Reads the private Builder API credential from
~/.local/share/agent-native/plane/builder-api.json; never prints it.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

DEFAULT_CONFIG = os.path.expanduser(
    "~/.local/share/agent-native/plane/builder-api.json"
)
DEFAULT_PROJECT = "0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897"
DONE_STATES = {"Done", "Cancelled"}
READY_STATES = {"Todo", "Backlog"}
PRIORITY_RANK = {"urgent": 0, "high": 1, "medium": 2, "low": 3, None: 4}
NAME_WIDTH = 62


# --- pure selection logic -------------------------------------------------


def state_name(item, states):
    """Readable state name for a work item, given a state-id map."""
    state = states.get(item.get("state"))
    if isinstance(state, dict):
        return state.get("name", "?")
    return state or "?"


def select_last_worked(items, builder_activity, limit=None):
    """Items the Builder touched, newest Builder activity first.

    ``builder_activity`` maps item id to the Builder's latest activity time;
    items absent from it were not touched by the Builder and are dropped.
    """
    touched = [i for i in items if i.get("id") in builder_activity]
    touched.sort(key=lambda i: builder_activity[i["id"]], reverse=True)
    return touched if limit is None else touched[:limit]


def select_in_progress(items, states, limit=None):
    """Items currently being worked on, most recently updated first."""
    active = [i for i in items if state_name(i, states) == "In Progress"]
    active.sort(key=lambda i: i.get("updated_at") or "", reverse=True)
    return active if limit is None else active[:limit]


def rank_ready(items, states, blocked_ids=frozenset(), limit=None):
    """Ready (not started, unblocked) items by priority then sequence."""
    ready = [
        i
        for i in items
        if state_name(i, states) in READY_STATES and i["id"] not in blocked_ids
    ]
    ready.sort(
        key=lambda i: (
            PRIORITY_RANK.get(i.get("priority"), PRIORITY_RANK[None]),
            i.get("sequence_id") or 0,
        )
    )
    return ready if limit is None else ready[:limit]


def _cycle_number(name):
    head = (name or "").split("-", 1)[0].strip()
    try:
        return int(head)
    except ValueError:
        return -1


def pick_current_cycle(membership, states):
    """Highest-numbered cycle that still has unfinished work.

    ``membership`` is a list of (cycle name, [items]). Falls back to the
    highest-numbered cycle when every cycle is concluded.
    """
    candidates = []
    for name, items in membership:
        if any(state_name(i, states) not in DONE_STATES for i in items):
            candidates.append(name)
    pool = candidates or [name for name, _ in membership]
    return max(pool, key=_cycle_number) if pool else None


def resolve_milestones(modules, module_issues, states):
    """Classify milestones from module status and member completion.

    current: status ``in-progress`` modules, most recently active first.
    next:    first ``planned`` module, else the first backlog module.
    last:    the most recently updated fully-complete module, else None.
    stats:   per-module total/done/started counts for display.
    """
    stats = {}
    complete = []
    current = []
    planned = []
    backlog = []
    for m in modules:
        members = module_issues.get(m["id"], [])
        names = [state_name(i, states) for i in members]
        done = sum(1 for n in names if n in DONE_STATES)
        started = sum(1 for n in names if n == "In Progress")
        stats[m["id"]] = {"total": len(names), "done": done, "started": started}
        if names and all(n in DONE_STATES for n in names):
            complete.append(m)
        status = m.get("status")
        if status == "in-progress":
            current.append(m)
        elif status == "planned":
            planned.append(m)
        elif status == "backlog":
            backlog.append(m)

    def newest(seq):
        return max(seq, key=lambda m: m.get("updated_at") or "", default=None)

    current.sort(key=lambda m: m.get("updated_at") or "", reverse=True)
    return {
        "current": current,
        "next": newest(planned) or newest(backlog),
        "last": newest(complete),
        "stats": stats,
    }


# --- Plane API boundary ---------------------------------------------------


class PlaneError(RuntimeError):
    pass


class PlaneClient:
    def __init__(self, config):
        self.base = config["base_url"].rstrip("/") + "/api/v1"
        self.workspace = config["workspace_slug"]
        self.project = config["project_id"]
        self.key = config["api_key"]
        self.user_id = config.get("user_id")

    def get(self, path):
        url = (
            f"{self.base}/workspaces/{self.workspace}"
            f"/projects/{self.project}/{path}"
        )
        request = urllib.request.Request(url, headers={"X-API-Key": self.key})
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            raise PlaneError(f"Plane GET {path} returned HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise PlaneError(
                f"Plane unavailable at {self.base}: {exc.reason}"
            ) from exc

    def get_all(self, path):
        results = []
        cursor = None
        separator = "&" if "?" in path else "?"
        while True:
            query = f"{path}{separator}per_page=100"
            if cursor:
                query += "&cursor=" + urllib.parse.quote(cursor)
            page = self.get(query)
            results.extend(page.get("results", []))
            if not page.get("next_page_results") or not page.get("next_cursor"):
                return results
            cursor = page["next_cursor"]

    def states(self):
        return self.get_all("states/")

    def modules(self):
        return self.get_all("modules/")

    def cycles(self):
        return self.get_all("cycles/")

    def work_items(self):
        return self.get_all("work-items/")

    def module_issues(self, module_id):
        return self.get_all(f"modules/{module_id}/module-issues/")

    def cycle_issues(self, cycle_id):
        return self.get_all(f"cycles/{cycle_id}/cycle-issues/")

    def activities(self, item_id):
        return self.get_all(f"work-items/{item_id}/activities/")

    def blocked_ids(self, item_ids):
        blocked = set()
        for item_id in item_ids:
            try:
                relations = self.get_all(f"work-items/{item_id}/relations/")
            except PlaneError:
                continue
            if any(r.get("relation_type") == "blocked_by" for r in relations):
                blocked.add(item_id)
        return blocked


def index_states(states):
    return {s["id"]: s.get("name", "?") for s in states}


def latest_actor_time(activities, user_id):
    times = [
        a.get("created_at")
        for a in activities
        if a.get("actor") == user_id and a.get("created_at")
    ]
    return max(times) if times else None


# --- presentation ---------------------------------------------------------


def fmt_time(value):
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return value[:16]


def fmt_item(item, states, suffix=""):
    seq = item.get("sequence_id")
    key = f"AN-{seq}" if seq is not None else "AN-?"
    return (
        f"  {key:<7} {state_name(item, states):<12} "
        f"{(item.get('name') or '')[:NAME_WIDTH]:<{NAME_WIDTH}} {suffix}".rstrip()
    )


def header(text):
    print(f"\n== {text} ==")


def emit_last_worked(client, count):
    states = index_states(client.states())
    items = client.work_items()
    items.sort(key=lambda i: i.get("updated_at") or "", reverse=True)
    activity = {}
    for candidate in items[: max(3 * count, 12)]:
        stamp = latest_actor_time(client.activities(candidate["id"]), client.user_id)
        if stamp:
            activity[candidate["id"]] = stamp
    chosen = select_last_worked(items, activity, count)
    header(f"LAST WORKED ({len(chosen)})")
    for item in chosen:
        print(fmt_item(item, states, f"({fmt_time(activity[item['id']])})"))


def emit_current(client, count):
    states = index_states(client.states())
    items = client.work_items()
    membership = [(c["name"], client.cycle_issues(c["id"])) for c in client.cycles()]
    cycle = pick_current_cycle(membership, states)
    cycle_items = dict(membership).get(cycle, [])

    header(f"CURRENT CYCLE: {cycle or 'none'}")
    active = select_in_progress(items, states)
    print(f"In progress ({len(active)}):")
    for item in active:
        print(fmt_item(item, states))

    candidates = rank_ready(cycle_items, states)
    ready = rank_ready(
        cycle_items, states, client.blocked_ids([i["id"] for i in candidates[:15]])
    )[:count]
    print(f"\nNext ready priorities ({len(ready)}):")
    for item in ready:
        print(fmt_item(item, states, f"[{item.get('priority') or 'none'}]"))


def emit_milestones(client):
    states = index_states(client.states())
    modules = client.modules()
    module_issues = {m["id"]: client.module_issues(m["id"]) for m in modules}
    result = resolve_milestones(modules, module_issues, states)

    header("MILESTONES")

    def line(m, marker):
        s = result["stats"][m["id"]]
        return (
            f"  {marker} {m['name'][:52]:<52} "
            f"{s['done']}/{s['total']} done"
            + (f", {s['started']} in progress" if s["started"] else "")
        )

    print("Current (in progress):")
    if result["current"]:
        for m in result["current"]:
            print(line(m, "*"))
    else:
        print("  (none marked in-progress)")

    print("\nNext:")
    print(line(result["next"], ">") if result["next"] else "  (none planned)")

    print("\nLast (fully complete):")
    print(line(result["last"], "-") if result["last"] else "  (none fully complete)")


def emit_summary(client):
    states = index_states(client.states())
    items = client.work_items()
    modules = client.modules()
    module_issues = {m["id"]: client.module_issues(m["id"]) for m in modules}
    result = resolve_milestones(modules, module_issues, states)
    membership = [(c["name"], client.cycle_issues(c["id"])) for c in client.cycles()]
    cycle = pick_current_cycle(membership, states)
    cycle_items = dict(membership).get(cycle, [])

    print(f"CURRENT CYCLE: {cycle or 'none'}")
    if result["current"]:
        names = ", ".join(m["name"] for m in result["current"])
        print(f"CURRENT MILESTONE(S): {names}")
    if result["next"]:
        print(f"NEXT MILESTONE: {result['next']['name']}")
    if result["last"]:
        print(f"LAST MILESTONE: {result['last']['name']}")

    active = select_in_progress(items, states, 5)
    print(f"\nIN PROGRESS ({len(select_in_progress(items, states))}):")
    for item in active:
        print(fmt_item(item, states))

    candidates = rank_ready(cycle_items, states)
    ready = rank_ready(
        cycle_items, states, client.blocked_ids([i["id"] for i in candidates[:15]])
    )[:3]
    print("\nNEXT PRIORITIES:")
    for item in ready:
        print(fmt_item(item, states, f"[{item.get('priority') or 'none'}]"))


def load_config(path):
    with open(path) as handle:
        config = json.load(handle)
    if "project_id" not in config:
        sibling = os.path.join(os.path.dirname(path), "planning-context.json")
        if os.path.exists(sibling):
            with open(sibling) as handle:
                config["project_id"] = json.load(handle).get("project_id")
    config.setdefault("project_id", DEFAULT_PROJECT)
    return config


def build_parser():
    parser = argparse.ArgumentParser(
        prog="plane_status", description=__doc__.splitlines()[0]
    )
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    sub = parser.add_subparsers(dest="command", required=True)
    last = sub.add_parser("last-worked", help="recent items the Builder touched")
    last.add_argument("--count", "-n", type=int, default=5)
    current = sub.add_parser("current", help="work in progress and next priorities")
    current.add_argument("--count", "-n", type=int, default=3)
    sub.add_parser("milestones", help="current, next and last milestone")
    sub.add_parser("summary", help="compact combination")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        client = PlaneClient(load_config(args.config))
    except (OSError, KeyError) as exc:
        print(f"Cannot read Plane config {args.config}: {exc}", file=sys.stderr)
        return 2
    try:
        if args.command == "last-worked":
            emit_last_worked(client, args.count)
        elif args.command == "current":
            emit_current(client, args.count)
        elif args.command == "milestones":
            emit_milestones(client)
        else:
            emit_summary(client)
    except PlaneError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
