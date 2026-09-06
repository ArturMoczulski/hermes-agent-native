"""Current field authority must hold when a Plane delivery attempt is committed."""

import pytest

from agent_native.identity import OWNER
from agent_native.plane_write_access import allow_resource
from agent_native.plane_write_contracts import fingerprint
from agent_native.plane_write_journal import ReplayError
from hermes_cli.kanban_db_connect import connect_closing
from tests.hermes_cli import test_agent_native_plane_writes as fixtures

setup = fixtures.setup
upstream = fixtures.upstream


def test_field_revoked_before_attempt_commit_never_reaches_plane(
    setup, upstream, monkeypatch
):
    s = setup
    fixtures.allow(s, "project", s.project, {"description"})
    operation_id = fixtures.uid()
    original_description = s.project_record["description"]
    arguments = {
        "description": "This update was revoked before delivery admission",
        "expected_fingerprint": fingerprint(s.project_record),
    }

    def patch(request):
        s.project_record.update(request["body"])
        return 200, {}, {**s.project_record, "updated_by": s.user}

    upstream.routes["PATCH", s.path] = patch
    mark_attempted = s.journal.mark_attempted

    def revoke_then_mark(*args, **kwargs):
        # Schedule the owner edit after adapter preflight but before the real
        # attempt transaction. Permission checks, SQLite and HTTP remain real.
        with connect_closing(s.db_path) as owner:
            allow_resource(
                owner,
                actor=OWNER,
                binding_id=s.binding["id"],
                kind="project",
                resource_id=s.project,
                fields=[],
            )
        return mark_attempted(*args, **kwargs)

    monkeypatch.setattr(s.journal, "mark_attempted", revoke_then_mark)
    with pytest.raises(PermissionError):
        s.service.execute(s.context, operation_id, "project.update", arguments)

    assert [request for request in upstream.requests if request["method"] != "GET"] == []
    assert s.project_record["description"] == original_description
    assert s.journal.preparation(operation_id, actor=OWNER)["attempted"] is False
    assert s.journal.get(operation_id, actor=OWNER)["status"] == "rejected"
    events = s.journal.events(actor=OWNER, operation_id=operation_id)
    assert [event["status"] for event in events] == ["pending", "rejected", "denied"]
    assert events[-1]["reason"] == "scope_changed"

    # Restoring permission does not turn the rejected UUID into a retry.
    fixtures.allow(s, "project", s.project, {"description"})
    before = list(upstream.requests)
    with pytest.raises(ReplayError):
        s.service.execute(s.context, operation_id, "project.update", arguments)
    assert upstream.requests == before
