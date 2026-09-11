"""Focused behavior tests for the First Builder Plane status tool.

These exercise the pure selection/ordering logic only; the HTTP boundary is
verified live by running the tool. Contracts assert relationships between data,
never snapshots of a current item catalog.
"""

import plane_status as ps


STATES = {
    "backlog": "Backlog",
    "todo": "Todo",
    "inprog": "In Progress",
    "review": "In review",
    "done": "Done",
    "cancel": "Cancelled",
    "blocked": "Blocked",
}


def item(iid, name, state, priority=None, updated="2026-01-01T00:00:00Z", seq=1):
    return {
        "id": iid,
        "name": name,
        "state": state,
        "priority": priority,
        "updated_at": updated,
        "sequence_id": seq,
    }


def test_state_name_maps_id_to_readable_name():
    it = item("x", "Thing", "inprog")
    assert ps.state_name(it, STATES) == "In Progress"


def test_select_last_worked_orders_by_latest_builder_activity():
    items = [
        item("a", "Old", "done", updated="2026-01-01T00:00:00Z"),
        item("b", "Mid", "done", updated="2026-01-02T00:00:00Z"),
        item("c", "New", "done", updated="2026-01-03T00:00:00Z"),
        item("d", "Owner only", "done", updated="2026-01-04T00:00:00Z"),
    ]
    activity = {
        "a": "2026-01-01T10:00:00Z",
        "c": "2026-01-03T10:00:00Z",
        "b": "2026-01-02T10:00:00Z",
    }
    result = ps.select_last_worked(items, activity)
    assert [i["id"] for i in result] == ["c", "b", "a"]


def test_select_last_worked_respects_limit():
    items = [item(c, c, "done") for c in "abc"]
    activity = {c: f"2026-01-0{n}T00:00:00Z" for n, c in enumerate("abc", start=1)}
    result = ps.select_last_worked(items, activity, limit=2)
    assert len(result) == 2
    assert result[0]["id"] == "c"


def test_select_in_progress_filters_state_and_orders_recent_first():
    items = [
        item("a", "A", "todo", updated="2026-01-03T00:00:00Z"),
        item("b", "B", "inprog", updated="2026-01-01T00:00:00Z"),
        item("c", "C", "inprog", updated="2026-01-02T00:00:00Z"),
        item("d", "D", "done", updated="2026-01-04T00:00:00Z"),
    ]
    result = ps.select_in_progress(items, STATES)
    assert [i["id"] for i in result] == ["c", "b"]


def test_rank_ready_orders_by_priority_then_sequence_excluding_blocked():
    items = [
        item("low", "Low", "backlog", priority="low", seq=1),
        item("urgent", "Urgent", "todo", priority="urgent", seq=9),
        item("high2", "High two", "backlog", priority="high", seq=5),
        item("high1", "High one", "todo", priority="high", seq=2),
        item("blockedurgent", "Blocked urgent", "todo", priority="urgent", seq=3),
        item("done", "Done", "done", priority="urgent", seq=4),
    ]
    result = ps.rank_ready(items, STATES, blocked_ids={"blockedurgent"})
    assert [i["id"] for i in result] == ["urgent", "high1", "high2", "low"]


def test_rank_ready_respects_limit():
    items = [item(str(n), str(n), "todo", priority="high", seq=n) for n in range(5)]
    assert len(ps.rank_ready(items, STATES, limit=2)) == 2


def test_pick_current_cycle_prefers_latest_with_unfinished_work():
    membership = [
        ("03 - Shared agent work", [item("a", "A", "done"), item("b", "B", "cancel")]),
        ("06 - First Builder handoff proof", [item("c", "C", "todo")]),
    ]
    assert ps.pick_current_cycle(membership, STATES) == "06 - First Builder handoff proof"


def test_pick_current_cycle_skips_fully_concluded_later_cycle():
    membership = [
        ("04 - Setup", [item("a", "A", "inprog")]),
        ("06 - Handoff proof", [item("b", "B", "done")]),
    ]
    assert ps.pick_current_cycle(membership, STATES) == "04 - Setup"


def test_resolve_milestones_identifies_current_next_and_last():
    modules = [
        {"id": "m1", "name": "M1", "status": "in-progress", "updated_at": "2026-01-01T00:00:00Z"},
        {"id": "m2", "name": "M2", "status": "in-progress", "updated_at": "2026-01-05T00:00:00Z"},
        {"id": "m0", "name": "M0", "status": "completed", "updated_at": "2026-01-02T00:00:00Z"},
        {"id": "m3", "name": "M3", "status": "planned", "updated_at": "2026-01-06T00:00:00Z"},
    ]
    module_issues = {
        "m0": [item("a", "A", "done")],
        "m1": [item("b", "B", "inprog")],
        "m2": [item("c", "C", "todo")],
        "m3": [item("d", "D", "backlog")],
    }
    result = ps.resolve_milestones(modules, module_issues, STATES)
    assert result["last"]["id"] == "m0"
    assert {m["id"] for m in result["current"]} == {"m1", "m2"}
    assert result["next"]["id"] == "m3"


def test_resolve_milestones_treats_all_done_module_as_complete():
    modules = [
        {"id": "m1", "name": "M1", "status": "in-progress", "updated_at": "2026-01-01T00:00:00Z"},
        {"id": "m2", "name": "M2", "status": "in-progress", "updated_at": "2026-01-02T00:00:00Z"},
    ]
    module_issues = {
        "m1": [item("a", "A", "done")],
        "m2": [item("b", "B", "done"), item("c", "C", "cancel")],
    }
    result = ps.resolve_milestones(modules, module_issues, STATES)
    assert result["last"]["id"] == "m2"
