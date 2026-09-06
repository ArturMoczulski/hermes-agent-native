"""Uncertain effects remain unresolved under conflicts, changed authority and races."""

import sqlite3
from threading import Event, Thread

import pytest

from agent_native.identity import OWNER, revise_soul
from agent_native.plane_access import grant_project, revoke_project
from agent_native.plane_operation_lock import OperationBusy
from agent_native.plane_recovery import PlaneRecoveryUnresolved
from agent_native.plane_write_access import (
    OPERATIONS,
    WriteAuthority,
    allow_resource,
    grant_writes,
    revoke_writes,
)
from agent_native.plane_write_journal import MutationJournal
from agent_native.plane_writes import PlaneWrites, PlaneWriteError
from hermes_cli.kanban_db_connect import connect_closing
from tests.hermes_cli import test_agent_native_plane_writes as fixtures
from tests.hermes_cli.test_agent_native_plane_recovery import lose_item_response

setup = fixtures.setup
upstream = fixtures.upstream


def _mutations(upstream):
    return [request for request in upstream.requests if request["method"] != "GET"]


def _assert_no_item_grant(s, item_id):
    with pytest.raises(PermissionError):
        s.authority.authorize(
            s.context,
            "item.update",
            kind="item",
            resource_id=item_id,
            fields={"description"},
        )


@pytest.mark.parametrize("status", [404, 500])
def test_missing_or_ambiguous_correlated_lookup_remains_unknown_without_resend(
    setup, upstream, status
):
    s, operation = setup, fixtures.uid()
    saved = lose_item_response(s, upstream, operation)
    upstream.routes["GET", s.path + "work-items/"] = (
        status,
        {},
        {"error": "Private upstream detail"},
    )
    with pytest.raises(PlaneRecoveryUnresolved) as failure:
        s.service.recover(s.context, operation)
    assert failure.value.status == status
    assert "Private upstream detail" not in str(failure.value)
    assert s.journal.get(operation, actor=OWNER)["status"] == "unknown"
    assert len(_mutations(upstream)) == 1
    _assert_no_item_grant(s, saved["id"])


@pytest.mark.parametrize(
    "field,replacement",
    [
        ("external_source", "other-controller"),
        ("external_id", fixtures.uid()),
        ("name", "Someone changed this task"),
        ("description_html", "<p>Changed criteria</p>"),
        ("created_by", fixtures.uid()),
        ("project", fixtures.uid()),
    ],
)
def test_mismatched_marker_content_author_or_scope_cannot_confirm_or_grant_access(
    setup, upstream, field, replacement
):
    s, operation = setup, fixtures.uid()
    saved = lose_item_response(s, upstream, operation)
    saved[field] = replacement
    with pytest.raises(PlaneRecoveryUnresolved):
        s.service.recover(s.context, operation)
    assert s.journal.get(operation, actor=OWNER)["status"] == "unknown"
    assert len(_mutations(upstream)) == 1
    _assert_no_item_grant(s, saved["id"])


def test_candidate_lookup_match_does_not_hide_changed_detail_marker(setup, upstream):
    s, operation = setup, fixtures.uid()
    saved = lose_item_response(s, upstream, operation)
    changed = {**saved, "external_id": fixtures.uid()}
    upstream.routes["GET", s.path + f"work-items/{saved['id']}/"] = (200, {}, changed)
    with pytest.raises(PlaneRecoveryUnresolved):
        s.service.recover(s.context, operation)
    assert s.journal.get(operation, actor=OWNER)["status"] == "unknown"
    _assert_no_item_grant(s, saved["id"])
    assert len(_mutations(upstream)) == 1


@pytest.mark.parametrize(
    "change", ["write_revoked", "read_revoked", "purpose_revised", "different_binding"]
)
def test_fresh_authority_cannot_recover_a_receipt_from_an_invalid_or_different_scope(
    setup, upstream, change
):
    s, operation = setup, fixtures.uid()
    lose_item_response(s, upstream, operation)
    context = s.context
    if change == "write_revoked":
        revoke_writes(s.conn, actor=OWNER, binding_id=s.binding["id"])
    elif change == "read_revoked":
        revoke_project(s.conn, actor=OWNER, binding_id=s.binding["id"])
    elif change == "purpose_revised":
        revise_soul(
            s.conn,
            actor=OWNER,
            agent_id=s.root["id"],
            expected_revision=s.root["soul_revision"],
            purpose="A different protected purpose",
        )
        context = s.authority.issue_context(actor=OWNER, binding_id=s.binding["id"])
    else:
        other = grant_project(
            s.conn,
            actor=OWNER,
            agent_id=s.root["id"],
            workspace_slug="other",
            workspace_id=fixtures.uid(),
            project_id=fixtures.uid(),
        )
        grant_writes(s.conn, actor=OWNER, binding_id=other["id"], operations=OPERATIONS)
        context = s.authority.issue_context(actor=OWNER, binding_id=other["id"])
    before = len(upstream.requests)
    with pytest.raises(PermissionError):
        s.service.recover(context, operation)
    assert len(upstream.requests) == before
    assert s.journal.get(operation, actor=OWNER)["status"] == "unknown"
    assert len(_mutations(upstream)) == 1


def test_revocation_during_recovery_read_blocks_confirmation_and_resource_grant(
    setup, upstream
):
    s, operation = setup, fixtures.uid()
    saved = lose_item_response(s, upstream, operation)

    def detail(_):
        with connect_closing(s.db_path) as owner_conn:
            revoke_writes(owner_conn, actor=OWNER, binding_id=s.binding["id"])
        return 200, {}, saved

    upstream.routes["GET", s.path + f"work-items/{saved['id']}/"] = detail
    with pytest.raises(PermissionError):
        s.service.recover(s.context, operation)
    assert s.journal.get(operation, actor=OWNER)["status"] == "unknown"
    assert (
        s.conn.execute(
            "SELECT COUNT(*) FROM agent_native_plane_resource_access WHERE binding_id = ? AND resource_id = ?",
            (s.binding["id"], saved["id"]),
        ).fetchone()[0]
        == 0
    )
    assert len(_mutations(upstream)) == 1


def test_failed_recovery_receipt_keeps_unknown_then_retry_uses_only_reads(
    setup, upstream
):
    s, operation = setup, fixtures.uid()
    saved = lose_item_response(s, upstream, operation)
    s.conn.execute("""CREATE TRIGGER reject_recovery_receipt BEFORE INSERT ON agent_native_plane_mutation_events
                     WHEN NEW.status = 'confirmed' BEGIN SELECT RAISE(ABORT, 'receipt persistence failed'); END""")
    try:
        with pytest.raises(sqlite3.IntegrityError):
            s.service.recover(s.context, operation)
    finally:
        s.conn.execute("DROP TRIGGER reject_recovery_receipt")
    assert s.journal.get(operation, actor=OWNER)["status"] == "unknown"
    assert all(
        event["status"] != "confirmed"
        for event in s.journal.events(actor=OWNER, operation_id=operation)
    )
    before = len(upstream.requests)
    recovered = s.service.recover(s.context, operation)
    assert recovered["resource"]["id"] == saved["id"]
    assert upstream.requests[before:] and all(
        request["method"] == "GET" for request in upstream.requests[before:]
    )
    assert s.journal.get(operation, actor=OWNER)["status"] == "confirmed"
    assert len(_mutations(upstream)) == 1


def test_active_post_excludes_recovery_and_reexecution_without_blocking_owner_db_write(
    setup, upstream
):
    s, operation = setup, fixtures.uid()
    arrived, release, finished, owner_finished = Event(), Event(), Event(), Event()
    execution_outcomes, owner_outcomes, saved = [], [], {}
    item_id = fixtures.uid()

    def post(request):
        saved.update(
            fixtures.record(s, id=item_id, created_by=s.user, **request["body"])
        )
        arrived.set()
        if not release.wait(10):
            return 503, {}, {"error": "test release timed out"}
        return 201, {}, b"lost response after the held request"

    def execute_elsewhere():
        try:
            with connect_closing(s.db_path) as conn:
                authority = WriteAuthority(conn)
                context = authority.issue_context(
                    actor=OWNER, binding_id=s.binding["id"]
                )
                writer = PlaneWrites(
                    authority,
                    MutationJournal(conn),
                    base_url=upstream.url,
                    api_key="private-fixture-key",
                    service_user_id=s.user,
                )
                writer.execute(context, operation, "item.create", {"name": "Held once"})
        except Exception as error:
            execution_outcomes.append(error)
        finally:
            finished.set()

    def owner_write():
        try:
            with connect_closing(s.db_path) as conn:
                allow_resource(
                    conn,
                    actor=OWNER,
                    binding_id=s.binding["id"],
                    kind="project",
                    resource_id=s.project,
                    fields={"description"},
                )
        except Exception as error:
            owner_outcomes.append(error)
        finally:
            owner_finished.set()

    upstream.routes["POST", s.path + "work-items/"] = post
    upstream.routes["GET", s.path + "work-items/"] = lambda _: (200, {}, saved)
    upstream.routes["GET", s.path + f"work-items/{item_id}/"] = lambda _: (
        200,
        {},
        saved,
    )
    worker = Thread(target=execute_elsewhere, daemon=True)
    owner = Thread(target=owner_write, daemon=True)
    worker.start()
    try:
        assert arrived.wait(5), "Writer did not reach the held POST"
        assert s.journal.get(operation, actor=OWNER)["status"] == "pending"
        before = len(upstream.requests)
        with pytest.raises(OperationBusy):
            s.service.recover(s.context, operation)
        with pytest.raises(OperationBusy):
            s.service.execute(
                s.context, operation, "item.create", {"name": "Held once"}
            )
        assert len(upstream.requests) == before
        owner.start()
        assert owner_finished.wait(5), "Operation lock blocked a separate SQLite write"
        assert owner_outcomes == []
        s.authority.authorize(
            s.context,
            "project.update",
            kind="project",
            resource_id=s.project,
            fields={"description"},
        )
    finally:
        release.set()
        worker.join(timeout=5)
        if owner.ident is not None:
            owner.join(timeout=5)
    assert finished.is_set() and not worker.is_alive()
    assert len(execution_outcomes) == 1 and isinstance(
        execution_outcomes[0], PlaneWriteError
    )
    assert s.journal.get(operation, actor=OWNER)["status"] == "unknown"
    recovered = s.service.recover(s.context, operation)
    assert recovered["resource"]["id"] == item_id
    assert len(_mutations(upstream)) == 1


@pytest.mark.parametrize("operation", ["cycle.create", "comment.create"])
@pytest.mark.parametrize("failure", ["duplicate_correlation", "incomplete_inventory"])
def test_paged_append_inventory_must_be_complete_and_uniquely_correlated(
    setup, upstream, operation, failure
):
    s, operation_id, created = setup, fixtures.uid(), fixtures.uid()
    saved = {}
    if operation == "cycle.create":
        path = s.path + "cycles/"
        arguments = {"name": "Verify the whole inventory"}
        metadata = {"owned_by": s.user}
    else:
        item = fixtures.put_item(s, upstream)
        path = s.path + f"work-items/{item['id']}/comments/"
        arguments = {"item_id": item["id"], "text": "Inspect every page"}
        metadata = {"issue": item["id"], "actor": s.user}

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

    def listing(request):
        total = 2 if failure == "duplicate_correlation" else 3
        if "cursor" not in request["query"]:
            return (
                200,
                {},
                {
                    "results": [saved],
                    "next_page_results": True,
                    "next_cursor": "next-page",
                    "total_results": total,
                },
            )
        assert request["query"]["cursor"] == ["next-page"]
        second = {**saved, "id": fixtures.uid()}
        if failure == "incomplete_inventory":
            second["external_id"] = fixtures.uid()
        return (
            200,
            {},
            {
                "results": [second],
                "next_page_results": False,
                "next_cursor": None,
                "total_results": total,
            },
        )

    upstream.routes["POST", path] = post
    upstream.routes["GET", path] = listing
    upstream.routes["GET", path + created + "/"] = lambda _: (200, {}, saved)
    upstream.routes["GET", s.path + "archived-cycles/"] = (200, {}, fixtures.page([]))
    with pytest.raises(PlaneWriteError):
        s.service.execute(s.context, operation_id, operation, arguments)
    with pytest.raises(PlaneRecoveryUnresolved):
        s.service.recover(s.context, operation_id)
    pages = [
        request
        for request in upstream.requests
        if request["method"] == "GET" and request["path"] == path
    ]
    assert len(pages) == 2 and pages[1]["query"]["cursor"] == ["next-page"]
    assert s.journal.get(operation_id, actor=OWNER)["status"] == "unknown"
    assert len(_mutations(upstream)) == 1
    assert (
        s.conn.execute(
            "SELECT COUNT(*) FROM agent_native_plane_resource_access WHERE binding_id = ? AND resource_id = ?",
            (s.binding["id"], created),
        ).fetchone()[0]
        == 0
    )


def test_process_death_during_post_recovers_persisted_attempt_with_only_reads(
    setup, upstream
):
    from pathlib import Path
    import subprocess
    import sys

    s, operation, created = setup, fixtures.uid(), fixtures.uid()
    arrived, release = Event(), Event()
    saved = {}

    def post(request):
        saved.update(
            fixtures.record(s, id=created, created_by=s.user, **request["body"])
        )
        arrived.set()
        release.wait(10)
        return 201, {}, saved

    upstream.routes["POST", s.path + "work-items/"] = post
    upstream.routes["GET", s.path + "work-items/"] = lambda _: (200, {}, saved)
    upstream.routes["GET", s.path + f"work-items/{created}/"] = lambda _: (
        200,
        {},
        saved,
    )
    program = """
import sys
from pathlib import Path
from agent_native.identity import OWNER
from agent_native.plane_write_access import WriteAuthority
from agent_native.plane_write_journal import MutationJournal
from agent_native.plane_writes import PlaneWrites
from hermes_cli.kanban_db_connect import connect_closing
with connect_closing(Path(sys.argv[1])) as conn:
    authority = WriteAuthority(conn)
    context = authority.issue_context(actor=OWNER, binding_id=sys.argv[2])
    service = PlaneWrites(authority, MutationJournal(conn), base_url=sys.argv[3],
                          api_key='private-fixture-key', service_user_id=sys.argv[4])
    service.execute(context, sys.argv[5], 'item.create', {'name': 'Survive writer death'})
"""
    child = subprocess.Popen(
        [
            sys.executable,
            "-c",
            program,
            str(s.db_path),
            s.binding["id"],
            upstream.url,
            s.user,
            operation,
        ],
        cwd=Path(__file__).resolve().parents[2],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        assert arrived.wait(5), "Child did not reach the held POST"
        assert child.poll() is None
        child.kill()
        assert child.wait(timeout=5) != 0
        assert s.journal.get(operation, actor=OWNER)["status"] == "pending"
        assert s.journal.preparation(operation, actor=OWNER)["attempted"] is True
        before = len(upstream.requests)
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
            result = service.recover(context, operation)
            assert result["resource"]["id"] == created
            assert journal.get(operation, actor=OWNER)["status"] == "confirmed"
        assert upstream.requests[before:] and all(
            request["method"] == "GET" for request in upstream.requests[before:]
        )
        assert len(_mutations(upstream)) == 1
    finally:
        release.set()
        if child.poll() is None:
            child.kill()
        child.communicate(timeout=5)
