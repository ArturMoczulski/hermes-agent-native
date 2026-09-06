"""Real HTTP and SQLite checks of write effects, scope and persisted outcomes."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from types import SimpleNamespace
from urllib.parse import urlsplit
from uuid import uuid4

import pytest

from agent_native.identity import OWNER, create_root
from agent_native.plane_access import grant_project
from agent_native.plane_write_access import (
    OPERATIONS,
    WriteAuthority,
    allow_resource,
    grant_writes,
)
from agent_native.plane_write_journal import MutationJournal
from agent_native.plane_writes import PlaneWrites
from hermes_cli.kanban_db_connect import connect_closing


def uid():
    return str(uuid4())


def page(records):
    return {"results": records, "next_page_results": False, "next_cursor": None}


@pytest.fixture
def upstream():
    class Handler(BaseHTTPRequestHandler):
        def serve(self):
            data = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            payload = json.loads(data) if data else None
            entry = {
                "method": self.command,
                "path": urlsplit(self.path).path,
                "body": payload,
                "headers": dict(self.headers),
            }
            self.server.requests.append(entry)
            route = self.server.routes.get((self.command, entry["path"]), (404, {}, {}))
            status, headers, result = route(entry) if callable(route) else route
            body = result if isinstance(result, bytes) else json.dumps(result).encode()
            self.send_response(status)
            if "Content-Length" not in headers:
                self.send_header("Content-Length", str(len(body)))
            for name, value in headers.items():
                self.send_header(name, value)
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        do_GET = do_POST = do_PATCH = do_DELETE = serve

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    server.requests = []
    server.routes = {}
    thread = Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
    )
    thread.start()
    server.url = f"http://127.0.0.1:{server.server_port}"
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


@pytest.fixture
def setup(tmp_path, upstream):
    with connect_closing(tmp_path / "control.db") as conn:
        root = create_root(
            conn,
            actor=OWNER,
            request_id="builder",
            name="Builder",
            purpose="Build the framework",
        )
        workspace, project, user, state = uid(), uid(), uid(), uid()
        binding = grant_project(
            conn,
            actor=OWNER,
            agent_id=root["id"],
            workspace_slug="test",
            workspace_id=workspace,
            project_id=project,
        )
        grant_writes(conn, actor=OWNER, binding_id=binding["id"], operations=OPERATIONS)
        authority = WriteAuthority(conn)
        context = authority.issue_context(actor=OWNER, binding_id=binding["id"])
        journal = MutationJournal(conn)
        service = PlaneWrites(
            authority,
            journal,
            base_url=upstream.url,
            api_key="private-fixture-key",
            service_user_id=user,
        )
        path = f"/api/v1/workspaces/test/projects/{project}/"
        project_record = {
            "id": project,
            "workspace": workspace,
            "name": "Framework",
            "identifier": "FW",
            "description": "Build it",
            "updated_at": "v1",
        }
        state_record = {
            "id": state,
            "workspace": workspace,
            "project": project,
            "name": "Backlog",
            "group": "backlog",
            "default": True,
        }
        upstream.routes["GET", path] = (200, {}, project_record)
        upstream.routes["GET", path + "states/"] = (200, {}, page([state_record]))
        upstream.routes["GET", path + "cycles/"] = (200, {}, page([]))
        yield SimpleNamespace(
            conn=conn,
            root=root,
            binding=binding,
            authority=authority,
            context=context,
            journal=journal,
            service=service,
            path=path,
            workspace=workspace,
            project=project,
            user=user,
            state=state,
            project_record=project_record,
            db_path=tmp_path / "control.db",
        )


def record(s, **values):
    return {
        "id": uid(),
        "workspace": s.workspace,
        "project": s.project,
        "name": "Task",
        "description_html": "<p>Draft</p>",
        "state": s.state,
        "priority": "none",
        "updated_at": "v1",
        **values,
    }


def allow(s, kind, rid, fields):
    allow_resource(
        s.conn,
        actor=OWNER,
        binding_id=s.binding["id"],
        kind=kind,
        resource_id=rid,
        fields=fields,
    )


def test_create_records_intent_before_effect_and_returns_attributed_scoped_item(
    setup, upstream
):
    s = setup
    op = uid()
    created = uid()

    def post(entry):
        with connect_closing(s.db_path) as observer:
            intent = MutationJournal(observer).get(actor=OWNER, operation_id=op)
            assert intent["status"] == "pending"
            assert intent["agent_id"] == s.root["id"]
        assert entry["headers"]["X-API-Key"] == "private-fixture-key"
        assert "created_by" not in entry["body"]
        assert "<script>" not in entry["body"]["description_html"]
        return 201, {}, record(s, id=created, created_by=s.user, **entry["body"])

    upstream.routes["POST", s.path + "work-items/"] = post
    result = s.service.execute(
        s.context,
        op,
        "item.create",
        {
            "name": "Implement one thing",
            "description": "<script>not authority</script>",
        },
    )
    assert result["status"] == "confirmed"
    assert result["resource"]["id"] == created
    assert result["agent_id"] == s.root["id"]
    assert s.journal.get(actor=OWNER, operation_id=op)["status"] == "confirmed"
    s.authority.authorize(
        s.context,
        "item.update",
        kind="item",
        resource_id=created,
        fields={"description"},
    )
    assert "private-fixture-key" not in repr(result)


def test_project_edit_requires_owned_field_and_current_source_fingerprint(
    setup, upstream
):
    s = setup
    allow(s, "project", s.project, {"description"})
    observation = s.service.inspect(s.context, "project")
    assert len(observation["fingerprint"]) == 64
    upstream.routes["PATCH", s.path] = lambda e: (
        200,
        {},
        dict(
            s.project_record,
            description=e["body"]["description"],
            updated_at="v2",
            updated_by=s.user,
        ),
    )
    result = s.service.execute(
        s.context,
        uid(),
        "project.update",
        {"description": "New goal", "expected_fingerprint": observation["fingerprint"]},
    )
    assert result["resource"]["description"] == "New goal"
    assert next(r for r in upstream.requests if r["method"] == "PATCH")["body"] == {
        "description": "New goal"
    }


@pytest.mark.parametrize(
    "extra",
    [
        {"actor": "owner"},
        {"project_id": uid()},
        {"created_by": uid()},
        {"api_key": "secret"},
    ],
)
def test_caller_identity_scope_and_attribution_fields_never_reach_plane(
    setup, upstream, extra
):
    with pytest.raises(ValueError):
        setup.service.execute(
            setup.context, uid(), "item.create", {"name": "task", **extra}
        )
    assert upstream.requests == []


def put_item(s, upstream, **changes):
    item = record(s, **changes)
    upstream.routes["GET", s.path + f"work-items/{item['id']}/"] = (200, {}, item)
    upstream.routes["GET", s.path + f"work-items/{item['id']}/relations/"] = (
        200,
        {},
        relations(s),
    )
    return item


def put_cycle(s, upstream, **changes):
    cycle = {
        "id": uid(),
        "workspace": s.workspace,
        "project": s.project,
        "name": "01 - Goal",
        "description": "Outcome",
        "start_date": None,
        "end_date": None,
        "owned_by": s.user,
        "updated_at": "v1",
        **changes,
    }
    upstream.routes["GET", s.path + f"cycles/{cycle['id']}/"] = (200, {}, cycle)
    return cycle


def test_item_update_changes_only_granted_planning_fields(setup, upstream):
    s = setup
    item = put_item(s, upstream)
    allow(s, "item", item["id"], {"priority"})
    observed = s.service.inspect(s.context, "item", item["id"])
    path = s.path + f"work-items/{item['id']}/"
    upstream.routes["PATCH", path] = lambda e: (
        200,
        {},
        dict(item, **e["body"], updated_by=s.user, updated_at="v2"),
    )
    result = s.service.execute(
        s.context,
        uid(),
        "item.update",
        {
            "item_id": item["id"],
            "priority": "high",
            "expected_fingerprint": observed["fingerprint"],
        },
    )
    assert result["resource"]["priority"] == "high"
    assert next(r for r in upstream.requests if r["method"] == "PATCH")["body"] == {
        "priority": "high"
    }


def test_item_description_cannot_be_changed_without_criteria_source_permission(
    setup, upstream
):
    s = setup
    item = put_item(s, upstream)
    allow(s, "item", item["id"], {"priority"})
    with pytest.raises(PermissionError):
        s.service.execute(
            s.context,
            uid(),
            "item.update",
            {
                "item_id": item["id"],
                "description": "Weaken criteria",
                "expected_fingerprint": "0" * 64,
            },
        )
    assert upstream.requests == []


def test_stale_project_source_is_rejected_without_a_patch(setup, upstream):
    from agent_native.plane_writes import PlaneWriteConflict

    s = setup
    allow(s, "project", s.project, {"description"})
    old = s.service.inspect(s.context, "project")
    upstream.routes["GET", s.path] = (
        200,
        {},
        dict(s.project_record, description="Owner changed it", updated_at="v2"),
    )
    op = uid()
    with pytest.raises(PlaneWriteConflict):
        s.service.execute(
            s.context,
            op,
            "project.update",
            {"description": "Overwrite", "expected_fingerprint": old["fingerprint"]},
        )
    assert all(r["method"] == "GET" for r in upstream.requests)
    assert s.journal.get(actor=OWNER, operation_id=op)["status"] == "rejected"


@pytest.mark.parametrize(
    "operation,fields",
    [
        ("comment.create", {"text": "<b>hello</b>"}),
        (
            "artifact.record",
            {
                "reference": "https://example.invalid/private",
                "description": "unverified result",
            },
        ),
    ],
)
def test_comments_and_evidence_are_attributed_escaped_text_without_fetches(
    setup, upstream, operation, fields
):
    s = setup
    item = put_item(s, upstream)
    comment_id = uid()

    def post(e):
        assert "<b>" not in e["body"]["comment_html"]
        assert s.root["id"] in e["body"]["comment_html"]
        assert "created_by" not in e["body"] and "actor" not in e["body"]
        return (
            201,
            {},
            dict(
                id=comment_id,
                workspace=s.workspace,
                project=s.project,
                issue=item["id"],
                actor=s.user,
                created_by=s.user,
                **e["body"],
            ),
        )

    upstream.routes["POST", s.path + f"work-items/{item['id']}/comments/"] = post
    result = s.service.execute(
        s.context, uid(), operation, {"item_id": item["id"], **fields}
    )
    assert result["resource"]["id"] == comment_id
    assert all("/links/" not in r["path"] for r in upstream.requests)
    if operation == "artifact.record":
        assert "unverified" in result["resource"]["comment_html"].lower()


def test_cycle_creation_is_undated_and_registers_editable_fields(setup, upstream):
    s = setup
    cycle_id = uid()

    def post(e):
        assert e["body"]["start_date"] is None and e["body"]["end_date"] is None
        return (
            201,
            {},
            dict(
                id=cycle_id,
                workspace=s.workspace,
                project=s.project,
                owned_by=s.user,
                created_by=s.user,
                **e["body"],
            ),
        )

    upstream.routes["POST", s.path + "cycles/"] = post
    result = s.service.execute(
        s.context,
        uid(),
        "cycle.create",
        {"name": "02 - Verified outcome", "description": "Ship a working improvement"},
    )
    assert result["resource"]["id"] == cycle_id
    s.authority.authorize(
        s.context,
        "cycle.update",
        kind="cycle",
        resource_id=cycle_id,
        fields={"description"},
    )


def test_cycle_update_preserves_observed_owner_and_unedited_fields(setup, upstream):
    s = setup
    cycle = put_cycle(s, upstream, owned_by=uid())
    allow(s, "cycle", cycle["id"], {"description"})
    seen = s.service.inspect(s.context, "cycle", cycle["id"])

    def patch(e):
        assert e["body"] == {
            "description": "New outcome",
            "owned_by": cycle["owned_by"],
        }
        return 200, {}, dict(cycle, **e["body"], updated_at="v2", updated_by=s.user)

    upstream.routes["PATCH", s.path + f"cycles/{cycle['id']}/"] = patch
    result = s.service.execute(
        s.context,
        uid(),
        "cycle.update",
        {
            "cycle_id": cycle["id"],
            "description": "New outcome",
            "expected_fingerprint": seen["fingerprint"],
        },
    )
    assert result["resource"]["owned_by"] == cycle["owned_by"]


def test_terminal_state_does_not_bypass_framework_evaluation_or_cancellation(
    setup, upstream
):
    from agent_native.plane_writes import PlaneWriteConflict

    s = setup
    item = put_item(s, upstream)
    allow(s, "item", item["id"], {"state"})
    done = uid()
    upstream.routes["GET", s.path + "states/"] = (
        200,
        {},
        page([
            {
                "id": done,
                "workspace": s.workspace,
                "project": s.project,
                "group": "completed",
                "name": "Done",
            }
        ]),
    )
    seen = s.service.inspect(s.context, "item", item["id"])
    with pytest.raises(PlaneWriteConflict):
        s.service.execute(
            s.context,
            uid(),
            "item.update",
            {
                "item_id": item["id"],
                "state": done,
                "expected_fingerprint": seen["fingerprint"],
            },
        )
    assert all(r["method"] == "GET" for r in upstream.requests)


def membership(s, cycle_id, item_id):
    return {
        "id": uid(),
        "workspace": s.workspace,
        "project": s.project,
        "cycle": cycle_id,
        "issue": item_id,
    }


def setup_memberships(s, upstream, item, cycles, active):
    upstream.routes["GET", s.path + "cycles/"] = (200, {}, page(cycles))
    for cycle in cycles:
        cid = cycle["id"]
        path = s.path + f"cycles/{cid}/cycle-issues/{item['id']}/"
        upstream.routes["GET", path] = lambda e, cid=cid: (
            (200, {}, active[cid]) if cid in active else (404, {}, {})
        )
        allow(s, "cycle", cid, {"items"})
    allow(s, "item", item["id"], {"cycle"})


def test_cycle_assignment_moves_only_the_scoped_item_from_the_expected_cycle(
    setup, upstream
):
    s = setup
    item = put_item(s, upstream)
    old, new = put_cycle(s, upstream), put_cycle(s, upstream)
    active = {old["id"]: membership(s, old["id"], item["id"])}
    setup_memberships(s, upstream, item, [old, new], active)
    observation = s.service.inspect(s.context, "item", item["id"])

    def move(e):
        assert e["body"] == {"issues": [item["id"]]}
        active.clear()
        active[new["id"]] = membership(s, new["id"], item["id"])
        return 200, {}, list(active.values())

    upstream.routes["POST", s.path + f"cycles/{new['id']}/cycle-issues/"] = move
    result = s.service.execute(
        s.context,
        uid(),
        "cycle.assign",
        {
            "item_id": item["id"],
            "cycle_id": new["id"],
            "expected_item_fingerprint": observation["fingerprint"],
            "expected_cycle_id": old["id"],
        },
    )
    assert (
        result["resource"]["issue"] == item["id"]
        and result["resource"]["cycle"] == new["id"]
    )
    assert set(active) == {new["id"]}


def test_cycle_remove_requires_matching_membership_and_verifies_its_removal(
    setup, upstream
):
    s = setup
    item = put_item(s, upstream)
    cycle = put_cycle(s, upstream)
    active = {cycle["id"]: membership(s, cycle["id"], item["id"])}
    setup_memberships(s, upstream, item, [cycle], active)
    observation = s.service.inspect(s.context, "item", item["id"])

    def remove(e):
        active.clear()
        return 204, {}, b""

    upstream.routes[
        "DELETE", s.path + f"cycles/{cycle['id']}/cycle-issues/{item['id']}/"
    ] = remove
    result = s.service.execute(
        s.context,
        uid(),
        "cycle.remove",
        {
            "cycle_id": cycle["id"],
            "item_id": item["id"],
            "expected_item_fingerprint": observation["fingerprint"],
        },
    )
    assert result["resource"]["removed"] is True and not active


@pytest.mark.parametrize("bad_prior", ["stale", "ambiguous"])
def test_stale_or_ambiguous_prior_membership_never_moves_work(
    setup, upstream, bad_prior
):
    from agent_native.plane_writes import PlaneWriteConflict

    s = setup
    item = put_item(s, upstream)
    one, two = put_cycle(s, upstream), put_cycle(s, upstream)
    active = {one["id"]: membership(s, one["id"], item["id"])}
    if bad_prior == "ambiguous":
        active[two["id"]] = membership(s, two["id"], item["id"])
    setup_memberships(s, upstream, item, [one, two], active)
    from agent_native.plane_write_contracts import fingerprint

    with pytest.raises(PlaneWriteConflict):
        s.service.execute(
            s.context,
            uid(),
            "cycle.assign",
            {
                "item_id": item["id"],
                "cycle_id": two["id"],
                "expected_item_fingerprint": fingerprint(
                    s.service._fetch(s.context, "item", item["id"])
                ),
                "expected_cycle_id": None,
            },
        )
    assert all(r["method"] == "GET" for r in upstream.requests)


def relations(s, *deps):
    return {
        "blocked_by": [{"project_id": s.project, "issue_id": d} for d in deps],
        "blocking": [],
        "relates_to": [],
    }


def test_dependency_addition_checks_both_items_and_confirms_the_relation(
    setup, upstream
):
    s = setup
    source, target = put_item(s, upstream), put_item(s, upstream)
    allow(s, "item", source["id"], {"dependencies"})
    edges = []
    source_path = s.path + f"work-items/{source['id']}/relations/"
    upstream.routes["GET", source_path] = lambda e: (200, {}, relations(s, *edges))
    upstream.routes["GET", s.path + f"work-items/{target['id']}/relations/"] = (
        200,
        {},
        relations(s),
    )
    seen = s.service.inspect(s.context, "item", source["id"])

    def add(e):
        assert e["body"] == {"relation_type": "blocked_by", "issues": [target["id"]]}
        edges.append(target["id"])
        return (
            201,
            {},
            [
                {
                    "id": target["id"],
                    "project_id": s.project,
                    "relation_type": "blocked_by",
                    "created_by": s.user,
                }
            ],
        )

    upstream.routes["POST", source_path] = add
    result = s.service.execute(
        s.context,
        uid(),
        "dependency.add",
        {
            "item_id": source["id"],
            "dependency_id": target["id"],
            "expected_fingerprint": seen["fingerprint"],
        },
    )
    assert result["resource"]["dependency_id"] == target["id"] and edges == [
        target["id"]
    ]


def test_dependency_that_would_create_a_cycle_is_rejected(setup, upstream):
    from agent_native.plane_writes import PlaneWriteConflict

    s = setup
    source, target = put_item(s, upstream), put_item(s, upstream)
    allow(s, "item", source["id"], {"dependencies"})
    upstream.routes["GET", s.path + f"work-items/{source['id']}/relations/"] = (
        200,
        {},
        relations(s),
    )
    upstream.routes["GET", s.path + f"work-items/{target['id']}/relations/"] = (
        200,
        {},
        relations(s, source["id"]),
    )
    seen = s.service.inspect(s.context, "item", source["id"])
    with pytest.raises(PlaneWriteConflict):
        s.service.execute(
            s.context,
            uid(),
            "dependency.add",
            {
                "item_id": source["id"],
                "dependency_id": target["id"],
                "expected_fingerprint": seen["fingerprint"],
            },
        )
    assert all(r["method"] == "GET" for r in upstream.requests)


def test_item_inspection_supplies_observed_cycle_and_dependencies(setup, upstream):
    s = setup
    item, dependency = put_item(s, upstream), put_item(s, upstream)
    cycle = put_cycle(s, upstream)
    active = {cycle["id"]: membership(s, cycle["id"], item["id"])}
    setup_memberships(s, upstream, item, [cycle], active)
    upstream.routes["GET", s.path + f"work-items/{item['id']}/relations/"] = (
        200,
        {},
        relations(s, dependency["id"]),
    )
    observed = s.service.inspect(s.context, "item", item["id"])
    assert observed["cycle_id"] == cycle["id"]
    assert observed["dependencies"] == [dependency["id"]]


@pytest.mark.parametrize(
    "wrong",
    [
        {"name": "Wrong task"},
        {"description_html": "<p>Different text</p>"},
        {"priority": "urgent"},
        {"state": uid()},
    ],
)
def test_success_status_with_wrong_item_content_is_unknown_and_grants_no_rights(
    setup, upstream, wrong
):
    from agent_native.plane_writes import PlaneWriteError

    s = setup
    created, op = uid(), uid()
    upstream.routes["POST", s.path + "work-items/"] = lambda e: (
        201,
        {},
        {**record(s, id=created, created_by=s.user), **e["body"], **wrong},
    )
    with pytest.raises(PlaneWriteError):
        s.service.execute(
            s.context,
            op,
            "item.create",
            {"name": "Expected", "description": "Exact text"},
        )
    assert s.journal.get(op, actor=OWNER)["status"] == "unknown"
    with pytest.raises(PermissionError):
        s.authority.authorize(
            s.context, "item.update", kind="item", resource_id=created, fields={"name"}
        )


def test_unapplied_project_patch_is_never_reported_confirmed(setup, upstream):
    from agent_native.plane_writes import PlaneWriteError

    s = setup
    allow(s, "project", s.project, {"description"})
    seen = s.service.inspect(s.context, "project")
    upstream.routes["PATCH", s.path] = (
        200,
        {},
        dict(s.project_record, updated_by=s.user),
    )
    op = uid()
    with pytest.raises(PlaneWriteError):
        s.service.execute(
            s.context,
            op,
            "project.update",
            {"description": "Changed", "expected_fingerprint": seen["fingerprint"]},
        )
    assert s.journal.get(op, actor=OWNER)["status"] == "unknown"


@pytest.mark.parametrize(
    "wrong",
    [{"start_date": "2026-09-06"}, {"name": "Unexpected"}, {"description": "Other"}],
)
def test_cycle_response_must_preserve_the_requested_undated_outcome(
    setup, upstream, wrong
):
    from agent_native.plane_writes import PlaneWriteError

    s = setup
    upstream.routes["POST", s.path + "cycles/"] = lambda e: (
        201,
        {},
        {
            "id": uid(),
            "workspace": s.workspace,
            "project": s.project,
            "created_by": s.user,
            **e["body"],
            **wrong,
        },
    )
    with pytest.raises(PlaneWriteError):
        s.service.execute(
            s.context,
            uid(),
            "cycle.create",
            {"name": "Ordered outcome", "description": "Accept it"},
        )


def test_comment_response_must_preserve_the_attributed_literal_content(setup, upstream):
    from agent_native.plane_writes import PlaneWriteError

    s = setup
    item = put_item(s, upstream)
    upstream.routes["POST", s.path + f"work-items/{item['id']}/comments/"] = lambda e: (
        201,
        {},
        {
            "id": uid(),
            "workspace": s.workspace,
            "project": s.project,
            "issue": item["id"],
            "created_by": s.user,
            "actor": s.user,
            **e["body"],
            "comment_html": "<p>Different author/content</p>",
        },
    )
    with pytest.raises(PlaneWriteError):
        s.service.execute(
            s.context,
            uid(),
            "comment.create",
            {"item_id": item["id"], "text": "Expected text"},
        )


def test_plane_html_wrapper_preserves_literal_text_and_line_breaks(setup, upstream):
    s = setup
    upstream.routes["POST", s.path + "work-items/"] = lambda e: (
        201,
        {},
        {
            **record(s, created_by=s.user),
            **e["body"],
            "description_html": "<div>"
            + e["body"]["description_html"].replace("<br>", "<br />")
            + "</div>",
        },
    )
    result = s.service.execute(
        s.context,
        uid(),
        "item.create",
        {"name": "Task", "description": "<literal> & text\nnext line"},
    )
    assert result["status"] == "confirmed"
