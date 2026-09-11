"""Recovery observes saved remote effects; it never resends an uncertain mutation."""

import pytest

from agent_native.identity import OWNER
from agent_native.plane_write_access import WriteAuthority
from agent_native.plane_write_journal import MutationJournal, ReplayError
from agent_native.plane_writes import PlaneWrites, PlaneWriteError
from hermes_cli.kanban_db_connect import connect_closing
from tests.hermes_cli import test_agent_native_plane_writes as fixtures

setup = fixtures.setup
upstream = fixtures.upstream


def lose_item_response(s, upstream, operation_id):
    created = fixtures.uid()
    saved = {}

    def post(request):
        saved.update(
            fixtures.record(s, id=created, created_by=s.user, **request["body"])
        )
        return 201, {}, b"connection ended before valid response"

    def lookup(request):
        assert request["query"] == {
            "external_source": ["agent-native"],
            "external_id": [operation_id],
        }
        return 200, {}, saved

    upstream.routes["POST", s.path + "work-items/"] = post
    upstream.routes["GET", s.path + "work-items/"] = lookup
    upstream.routes["GET", s.path + f"work-items/{created}/"] = lambda _: (
        200,
        {},
        saved,
    )
    with pytest.raises(PlaneWriteError):
        s.service.execute(
            s.context,
            operation_id,
            "item.create",
            {"name": "Recover the original", "description": "A durable task"},
        )
    return saved


def test_lost_create_response_recovers_same_item_after_reopening_without_another_post(
    setup, upstream
):
    s = setup
    operation_id = fixtures.uid()
    saved = lose_item_response(s, upstream, operation_id)
    assert s.journal.get(operation_id, actor=OWNER)["status"] == "unknown"
    with connect_closing(s.db_path) as reopened:
        authority = WriteAuthority(reopened)
        context = authority.issue_context(actor=OWNER, binding_id=s.binding["id"])
        journal = MutationJournal(reopened)
        service = PlaneWrites(
            authority,
            journal,
            base_url=upstream.url,
            api_key="private-fixture-key",
            service_user_id=s.user,
        )
        recovered = service.recover(context, operation_id)
        assert recovered["status"] == "confirmed"
        assert recovered["resource"]["id"] == saved["id"]
        assert journal.get(operation_id, actor=OWNER)["resource_id"] == saved["id"]
        again = service.recover(context, operation_id)
        assert again["resource"]["id"] == saved["id"]
        with pytest.raises(ReplayError):
            service.execute(
                context,
                operation_id,
                "item.create",
                {"name": "Recover the original", "description": "A durable task"},
            )
    assert len([r for r in upstream.requests if r["method"] == "POST"]) == 1


def test_prepared_request_and_attempt_marker_are_durable_before_delivery(
    setup, upstream
):
    s = setup
    operation_id = fixtures.uid()

    def post(request):
        with connect_closing(s.db_path) as observer:
            stored = MutationJournal(observer).preparation(operation_id, actor=OWNER)
            assert stored["attempted"] is True
            assert stored["prepared"]["payload"] == request["body"]
            assert stored["arguments"]["name"] == "Prepare before effect"
        return 201, {}, fixtures.record(s, created_by=s.user, **request["body"])

    upstream.routes["POST", s.path + "work-items/"] = post
    s.service.execute(
        s.context, operation_id, "item.create", {"name": "Prepare before effect"}
    )


@pytest.fixture(autouse=True)
def archived_inventory(setup, upstream):
    upstream.routes["GET", setup.path + "archived-cycles/"] = (
        200,
        {},
        fixtures.page([]),
    )


def lose_effect(s, operation_id, operation, arguments):
    with pytest.raises(PlaneWriteError):
        s.service.execute(s.context, operation_id, operation, arguments)
    assert s.journal.get(operation_id, actor=OWNER)["status"] == "unknown"


@pytest.mark.parametrize(
    "operation", ["cycle.create", "comment.create", "artifact.record"]
)
def test_created_cycle_or_append_is_recovered_from_complete_correlated_inventory(
    setup, upstream, operation
):
    s = setup
    op, created = fixtures.uid(), fixtures.uid()
    saved = {}
    item = fixtures.put_item(s, upstream)
    if operation == "cycle.create":
        path = s.path + "cycles/"
        args = {"name": "Undated outcome", "description": "Accept evidence"}
        metadata = {"owned_by": s.user}
    else:
        path = s.path + f"work-items/{item['id']}/comments/"
        args = {
            "item_id": item["id"],
            **(
                {"text": "Record progress"}
                if operation == "comment.create"
                else {"reference": "urn:result:1"}
            ),
        }
        metadata = {"actor": s.user, "issue": item["id"]}

    def post(request):
        saved.update({
            "id": created,
            "workspace": s.workspace,
            "project": s.project,
            "created_by": s.user,
            **metadata,
            **request["body"],
        })
        return 201, {}, b"lost response"

    upstream.routes["POST", path] = post
    upstream.routes["GET", path] = lambda _: (200, {}, fixtures.page([saved]))
    upstream.routes["GET", path + created + "/"] = lambda _: (200, {}, saved)
    lose_effect(s, op, operation, args)
    recovered = s.service.recover(s.context, op)
    assert recovered["resource"]["id"] == created
    assert len([r for r in upstream.requests if r["method"] != "GET"]) == 1


def test_cycle_recovery_reads_detail_correlation_when_inventory_is_projected(
    setup, upstream
):
    """Plane list responses may omit the correlation fields used by recovery."""
    s = setup
    op, created = fixtures.uid(), fixtures.uid()
    saved = {}
    path = s.path + "cycles/"
    args = {"name": "Projected recovery cycle", "description": "Confirm once"}

    def post(request):
        saved.update({
            "id": created,
            "workspace": s.workspace,
            "project": s.project,
            "created_by": s.user,
            "owned_by": s.user,
            **request["body"],
        })
        return 201, {}, b"lost response"

    upstream.routes["POST", path] = post
    upstream.routes["GET", path] = lambda _: (200, {}, fixtures.page([saved]))
    upstream.routes["GET", path + created + "/"] = lambda _: (200, {}, saved)
    lose_effect(s, op, "cycle.create", args)

    # The inventory endpoint is a projection, while the detail endpoint retains
    # the exact correlation markers needed to prove the original effect.
    upstream.routes["GET", path] = lambda _: (
        200,
        {},
        fixtures.page([{key: value for key, value in saved.items()
                        if key not in {"external_source", "external_id"}}]),
    )
    recovered = s.service.recover(s.context, op)

    assert recovered["resource"]["id"] == created
    assert s.journal.get(op, actor=OWNER)["status"] == "confirmed"
    assert len([r for r in upstream.requests if r["method"] == "POST"]) == 1


@pytest.mark.parametrize("kind", ["project", "item", "cycle"])
def test_lost_update_response_observes_intended_fields_without_reapplying_old_fingerprint(
    setup, upstream, kind
):
    from agent_native.plane_write_contracts import fingerprint

    s = setup
    raw = (
        s.project_record
        if kind == "project"
        else (
            fixtures.put_item(s, upstream)
            if kind == "item"
            else fixtures.put_cycle(s, upstream)
        )
    )
    fixtures.allow(s, kind, raw["id"], {"description"})
    resource_id = None if kind == "project" else raw["id"]
    seen = s.service._fetch(s.context, kind, resource_id)
    path = s.path + (
        ""
        if kind == "project"
        else f"{'work-items' if kind == 'item' else 'cycles'}/{raw['id']}/"
    )
    args = {
        "description": "Desired changed content",
        "expected_fingerprint": fingerprint(seen),
    }
    if kind != "project":
        args[kind + "_id"] = raw["id"]

    def patch(request):
        raw.update(request["body"], updated_at="v2", updated_by=s.user)
        return 200, {}, b"lost response"

    upstream.routes["PATCH", path] = patch
    op = fixtures.uid()
    lose_effect(s, op, kind + ".update", args)
    recovered = s.service.recover(s.context, op)
    assert recovered["resource"]["id"] == raw["id"]
    assert len([r for r in upstream.requests if r["method"] == "PATCH"]) == 1


@pytest.mark.parametrize("operation", ["cycle.assign", "cycle.remove"])
def test_lost_cycle_membership_response_recovers_current_effect_without_second_write(
    setup, upstream, operation
):
    from agent_native.plane_write_contracts import fingerprint

    s = setup
    item = fixtures.put_item(s, upstream)
    cycle = fixtures.put_cycle(s, upstream)
    active = (
        {}
        if operation == "cycle.assign"
        else {cycle["id"]: fixtures.membership(s, cycle["id"], item["id"])}
    )
    fixtures.setup_memberships(s, upstream, item, [cycle], active)
    args = {
        "cycle_id": cycle["id"],
        "item_id": item["id"],
        "expected_item_fingerprint": fingerprint(
            s.service._fetch(s.context, "item", item["id"])
        ),
    }
    if operation == "cycle.assign":
        args["expected_cycle_id"] = None

    def effect(_):
        if operation == "cycle.assign":
            active[cycle["id"]] = fixtures.membership(s, cycle["id"], item["id"])
        else:
            active.clear()
        return 503, {}, b"lost response"

    method = "POST" if operation == "cycle.assign" else "DELETE"
    suffix = "" if operation == "cycle.assign" else item["id"] + "/"
    upstream.routes[method, s.path + f"cycles/{cycle['id']}/cycle-issues/" + suffix] = (
        effect
    )
    op = fixtures.uid()
    lose_effect(s, op, operation, args)
    recovered = s.service.recover(s.context, op)
    assert recovered["status"] == "confirmed"
    expected_id = (
        active[cycle["id"]]["id"] if operation == "cycle.assign" else item["id"]
    )
    assert recovered["resource"]["id"] == expected_id
    assert s.journal.get(op, actor=OWNER)["resource_id"] == expected_id
    assert len([r for r in upstream.requests if r["method"] != "GET"]) == 1


def test_lost_dependency_addition_response_recovers_existing_edge(setup, upstream):
    from agent_native.plane_write_contracts import fingerprint

    s = setup
    source, target = fixtures.put_item(s, upstream), fixtures.put_item(s, upstream)
    fixtures.allow(s, "item", source["id"], {"dependencies"})
    edges = []
    path = s.path + f"work-items/{source['id']}/relations/"
    upstream.routes["GET", path] = lambda _: (200, {}, fixtures.relations(s, *edges))

    def effect(_):
        edges.append(target["id"])
        return 201, {}, b"lost response"

    upstream.routes["POST", path] = effect
    op = fixtures.uid()
    lose_effect(
        s,
        op,
        "dependency.add",
        {
            "item_id": source["id"],
            "dependency_id": target["id"],
            "expected_fingerprint": fingerprint(
                s.service._fetch(s.context, "item", source["id"])
            ),
        },
    )
    recovered = s.service.recover(s.context, op)
    assert recovered["resource"]["dependency_id"] == target["id"]
    assert len([r for r in upstream.requests if r["method"] == "POST"]) == 1


def test_matching_create_effect_does_not_grant_edit_authority_or_upgrade_its_evidence(
    setup, upstream
):
    s = setup
    op = fixtures.uid()
    saved = lose_item_response(s, upstream, op)
    result = s.service.recover(s.context, op)
    assert result["confirmation"] == "matching_effect"
    with pytest.raises(PermissionError):
        s.authority.authorize(
            s.context,
            "item.update",
            kind="item",
            resource_id=saved["id"],
            fields={"name"},
        )
    second = s.service.recover(s.context, op)
    assert second["confirmation"] == "matching_effect"
    assert second["source"] == "journal"


def test_recovery_never_infers_resource_ownership_from_plane_matching_fields(
    setup, upstream
):
    s = setup
    op = fixtures.uid()
    saved = lose_item_response(s, upstream, op)
    s.service.recover(s.context, op)
    with pytest.raises(PermissionError):
        s.authority.authorize(
            s.context,
            "item.update",
            kind="item",
            resource_id=saved["id"],
            fields={"name"},
        )


def test_removal_cannot_be_confirmed_when_known_cycle_is_missing_from_inventory(
    setup, upstream
):
    from agent_native.plane_recovery import PlaneRecoveryUnresolved
    from agent_native.plane_write_contracts import fingerprint

    s = setup
    item, cycle = fixtures.put_item(s, upstream), fixtures.put_cycle(s, upstream)
    active = {cycle["id"]: fixtures.membership(s, cycle["id"], item["id"])}
    fixtures.setup_memberships(s, upstream, item, [cycle], active)
    path = s.path + f"cycles/{cycle['id']}/cycle-issues/{item['id']}/"
    upstream.routes["DELETE", path] = (503, {}, b"uncertain effect")
    op = fixtures.uid()
    lose_effect(
        s,
        op,
        "cycle.remove",
        {
            "cycle_id": cycle["id"],
            "item_id": item["id"],
            "expected_item_fingerprint": fingerprint(
                s.service._fetch(s.context, "item", item["id"])
            ),
        },
    )
    upstream.routes["GET", s.path + "cycles/"] = (200, {}, fixtures.page([]))
    with pytest.raises(PlaneRecoveryUnresolved):
        s.service.recover(s.context, op)
    assert active
    assert s.journal.get(op, actor=OWNER)["status"] == "unknown"


def test_field_revocation_at_reconciliation_boundary_prevents_confirmation(
    setup, upstream, monkeypatch
):
    from agent_native.plane_write_access import allow_resource
    from agent_native.plane_write_contracts import fingerprint

    s = setup
    fixtures.allow(s, "project", s.project, {"description"})
    args = {
        "description": "Requested update",
        "expected_fingerprint": fingerprint(s.project_record),
    }

    def patch(request):
        s.project_record.update(request["body"], updated_by=s.user)
        return 200, {}, b"lost response"

    upstream.routes["PATCH", s.path] = patch
    op = fixtures.uid()
    lose_effect(s, op, "project.update", args)
    reconcile = s.journal.reconcile

    def revoke_then_reconcile(*args, **kwargs):
        with connect_closing(s.db_path) as owner:
            allow_resource(
                owner,
                actor=OWNER,
                binding_id=s.binding["id"],
                kind="project",
                resource_id=s.project,
                fields=[],
            )
        return reconcile(*args, **kwargs)

    monkeypatch.setattr(s.journal, "reconcile", revoke_then_reconcile)
    with pytest.raises(PermissionError):
        s.service.recover(s.context, op)
    assert s.journal.get(op, actor=OWNER)["status"] == "unknown"


def test_field_revocation_at_delivery_receipt_boundary_prevents_confirmation(
    setup, upstream, monkeypatch
):
    from agent_native.plane_write_access import allow_resource
    from agent_native.plane_write_contracts import fingerprint

    s = setup
    fixtures.allow(s, "project", s.project, {"description"})
    args = {
        "description": "Changed",
        "expected_fingerprint": fingerprint(s.project_record),
    }
    upstream.routes["PATCH", s.path] = lambda e: (
        200,
        {},
        dict(s.project_record, **e["body"], updated_by=s.user),
    )
    finish = s.journal.finish

    def revoke_then_finish(*args, **kwargs):
        with connect_closing(s.db_path) as owner:
            allow_resource(
                owner,
                actor=OWNER,
                binding_id=s.binding["id"],
                kind="project",
                resource_id=s.project,
                fields=[],
            )
        return finish(*args, **kwargs)

    monkeypatch.setattr(s.journal, "finish", revoke_then_finish)
    op = fixtures.uid()
    with pytest.raises(PermissionError):
        s.service.execute(s.context, op, "project.update", args)
    assert s.journal.get(op, actor=OWNER)["status"] == "unknown"
