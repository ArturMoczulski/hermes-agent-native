"""Opt-in AN-20 proof using only disposable local Plane planning data.

Uses two fresh accounts, one workspace and two private projects. Setup/readback
and adapter requests use separate service-user keys. No owner/Builder credentials,
managed worker, model, attachment upload or artifact URL retrieval is involved.
Keep the required new output directory private for recovery and cleanup evidence.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets
import sys
import time
from uuid import uuid4

from probe_scoped_reads import (
    Probe as ReadProbe,
    ProbeFailure,
    call,
    csrf,
    local_base,
    require,
    results,
    session,
)


class WriteProbe(ReadProbe):
    def __init__(self, base, output):
        super().__init__(base, output, api_container=None)
        self.manifest["slug"] = "scoped-write-probe-" + secrets.token_hex(5)
        self.manifest["operations"] = []
        self.report["limitations"].extend([
            "No managed-run authentication or autonomous execution is proved.",
            "Fingerprints are stale-read checks, not atomic upstream compare-and-swap.",
            "No timeout recovery or automatic retry is attempted; AN-22 owns recovery.",
            "Artifact references are unverified plain text recorded as comments.",
        ])
        self.last_adapter_operation = None
        self.save()

    def pace(self):
        # Each adapter operation can perform several reads before its single write.
        # A fresh key and small fixture bound request pressure; any 429 fails the
        # probe honestly instead of automatically replaying a mutation.
        if self.last_adapter_operation is not None:
            remaining = 12 - (time.monotonic() - self.last_adapter_operation)
            if remaining > 0:
                time.sleep(remaining)
        self.last_adapter_operation = time.monotonic()

    def setup(self):
        initial = session(self.base)
        try:
            config = call(initial, self.base, "GET", "/api/instances/").json()["config"]
            require(
                config.get("is_smtp_configured") is False,
                "Disposable setup requires explicitly unconfigured SMTP",
            )
        finally:
            initial.close()
        for role in ("workspace-owner", "service"):
            account = {
                "email": self.manifest["slug"] + "-" + role + "@agent-native.test",
                "password": secrets.token_urlsafe(32),
                "tokens": [],
            }
            self.manifest["accounts"].append(account)
            sess = session(self.base)
            self.sessions.append(sess)
            self.save()
            csrf(sess, self.base)
            account["signup_attempted"] = True
            self.save()
            signed = call(
                sess,
                self.base,
                "POST",
                "/auth/sign-up/",
                data={"email": account["email"], "password": account["password"]},
                expected=(302,),
            )
            require(
                "error" not in signed.headers.get("Location", ""),
                "Disposable account signup failed",
            )
            csrf(sess, self.base)
            account["id"] = call(sess, self.base, "GET", "/api/users/me/").json()["id"]
            self.save()
        admin, service = self.sessions
        account = self.manifest["accounts"][1]
        for name in ("fixture-setup-and-readback", "scoped-writes"):
            token = call(
                service,
                self.base,
                "POST",
                "/api/users/api-tokens/",
                body={"label": self.manifest["slug"] + "-" + name},
            ).json()
            account["tokens"].append({
                "id": token["id"],
                "api_key": token.get("api_key") or token["token"],
            })
            self.save()
        self.api = session(self.base)
        self.api.headers["X-API-Key"] = account["tokens"][0]["api_key"]
        self.manifest["workspace_creation_attempted"] = True
        self.save()
        workspace = call(
            admin,
            self.base,
            "POST",
            "/api/workspaces/",
            body={"name": self.manifest["slug"], "slug": self.manifest["slug"]},
        ).json()
        self.manifest["workspace_id"] = workspace["id"]
        self.save()
        wp = "/api/workspaces/" + self.manifest["slug"] + "/"
        call(
            admin,
            self.base,
            "POST",
            wp + "invitations/",
            body={"emails": [{"email": account["email"], "role": 15}]},
        )
        csrf(service, self.base)
        invitations = results(
            call(service, self.base, "GET", "/api/users/me/workspaces/invitations/")
        )
        call(
            service,
            self.base,
            "POST",
            "/api/users/me/workspaces/invitations/",
            body={"invitations": [item["id"] for item in invitations]},
        )
        self.v1 = "/api/v1/workspaces/" + self.manifest["slug"] + "/projects/"
        for letter in ("A", "B"):
            project = call(
                self.api,
                self.base,
                "POST",
                self.v1,
                body={
                    "name": "Disposable scoped writes " + letter,
                    "identifier": "WRITE" + letter,
                    "description": "Fixture brief " + letter,
                    "cycle_view": True,
                },
            ).json()
            fixture = {"id": project["id"], "items": [], "cycles": []}
            self.manifest["projects"].append(fixture)
            self.save()
            private = call(
                service,
                self.base,
                "PATCH",
                wp + "projects/" + project["id"] + "/",
                body={"network": 0},
            ).json()
            require(private["network"] == 0, "Fixture project was not made private")
            path = self.v1 + project["id"] + "/"
            for number in range(2 if letter == "A" else 1):
                item = call(
                    self.api,
                    self.base,
                    "POST",
                    path + "work-items/",
                    body={
                        "name": f"Owner fixture {letter} item {number}",
                        "external_source": self.manifest["slug"],
                        "external_id": f"{letter}-{number}",
                    },
                ).json()
                fixture["items"].append(item["id"])
                self.save()
            cycle = call(
                self.api,
                self.base,
                "POST",
                path + "cycles/",
                body={
                    "name": "Fixture outcome " + letter,
                    "owned_by": account["id"],
                    "start_date": None,
                    "end_date": None,
                },
            ).json()
            fixture["cycles"].append(cycle["id"])
            fixture["states"] = results(
                call(self.api, self.base, "GET", path + "states/")
            )
            self.save()
        self.check(
            "isolated_fixture", {"private_projects": 2, "accounts": 2, "attachments": 0}
        )

    def verify(self):
        from agent_native.identity import OWNER, create_root, revise_soul
        from agent_native.plane_access import ReadAuthority, grant_project
        from agent_native.plane_reads import PlaneReadError
        from agent_native.plane_write_access import (
            OPERATIONS,
            WriteAuthority,
            allow_resource,
            grant_writes,
            revoke_writes,
        )
        from agent_native.plane_write_journal import MutationJournal, ReplayError
        from agent_native.plane_writes import PlaneWriteConflict, PlaneWrites
        from hermes_cli.kanban_db_connect import connect_closing

        self.report["stage"] = "adapter_writes"
        self.save()
        first, other = self.manifest["projects"]
        account = self.manifest["accounts"][1]
        key = account["tokens"][1]["api_key"]
        first_path, other_path = (
            self.v1 + project["id"] + "/" for project in (first, other)
        )
        raw = session(self.base)
        raw.headers["X-API-Key"] = key
        try:
            for fixture in (first, other):
                record = call(
                    raw, self.base, "GET", self.v1 + fixture["id"] + "/"
                ).json()
                require(
                    record["id"] == fixture["id"],
                    "Adapter service cannot access both fixture projects",
                )
        finally:
            raw.close()
        self.check("underlying_adapter_key_accesses_both_projects")
        foreign_before = call(
            self.api,
            self.base,
            "GET",
            other_path + "work-items/" + other["items"][0] + "/",
        ).json()
        owner_before = call(
            self.api,
            self.base,
            "GET",
            first_path + "work-items/" + first["items"][0] + "/",
        ).json()

        with connect_closing(self.out / "control.db") as conn:
            authority = WriteAuthority(conn)
            journal = MutationJournal(conn)
            writer = PlaneWrites(
                authority,
                journal,
                base_url=self.base,
                api_key=key,
                service_user_id=account["id"],
            )
            roots, bindings = [], []
            for index, fixture in enumerate((first, other)):
                root = create_root(
                    conn,
                    actor=OWNER,
                    request_id=f"write-probe-root-{index}",
                    name=f"Isolated write root {index}",
                    purpose=f"Plan only fixture project {index}",
                )
                binding = grant_project(
                    conn,
                    actor=OWNER,
                    agent_id=root["id"],
                    workspace_slug=self.manifest["slug"],
                    workspace_id=self.manifest["workspace_id"],
                    project_id=fixture["id"],
                )
                roots.append(root)
                bindings.append(binding)
            grant_writes(
                conn, actor=OWNER, binding_id=bindings[0]["id"], operations=OPERATIONS
            )
            context = authority.issue_context(actor=OWNER, binding_id=bindings[0]["id"])
            readonly = ReadAuthority(conn).issue_context(
                actor=OWNER, binding_id=bindings[1]["id"]
            )
            self.manifest["roots"] = [root["id"] for root in roots]
            self.manifest["bindings"] = [binding["id"] for binding in bindings]
            self.save()

            def allow(kind, resource_id, fields):
                allow_resource(
                    conn,
                    actor=OWNER,
                    binding_id=bindings[0]["id"],
                    kind=kind,
                    resource_id=resource_id,
                    fields=fields,
                )

            def inspect(kind, resource_id=None):
                self.report["stage"] = "inspect_" + kind
                self.save()
                self.pace()
                observed = writer.inspect(context, kind, resource_id)
                require(
                    isinstance(observed.get("fingerprint"), str)
                    and len(observed["fingerprint"]) == 64,
                    "Source inspection did not supply a fingerprint",
                )
                return observed

            def execute(operation, arguments, *, use_context=None, operation_id=None):
                opid = operation_id or str(uuid4())
                pending = {"id": opid, "operation": operation, "status": "attempted"}
                self.manifest["operations"].append(pending)
                self.report["stage"] = "adapter_" + operation
                self.save()
                self.pace()
                result = writer.execute(
                    context if use_context is None else use_context,
                    opid,
                    operation,
                    arguments,
                )
                require(
                    result.get("status") == "confirmed"
                    and result.get("operation_id") == opid
                    and result.get("agent_id") == roots[0]["id"],
                    "Write receipt is missing verified attribution",
                )
                stored = journal.get(opid, actor=OWNER)
                require(
                    stored["status"] == "confirmed"
                    and stored["agent_id"] == roots[0]["id"]
                    and stored["project_id"] == first["id"],
                    "Confirmed mutation journal scope mismatch",
                )
                pending.update(status="confirmed", resource_id=result["resource"]["id"])
                self.save()
                return result

            def denied(
                label, action, *, permitted=(PermissionError,), remote_statuses=()
            ):
                try:
                    action()
                except permitted:
                    self.check(label)
                except PlaneReadError as exc:
                    require(
                        exc.status in remote_statuses,
                        "Denial operation failed for an unexpected remote reason",
                    )
                    self.check(label, {"status": exc.status})
                else:
                    raise ProbeFailure(
                        "Unauthorized operation returned instead of denying access"
                    )

            allow("project", first["id"], {"description"})
            allow("item", first["items"][0], {"priority"})
            allow("cycle", first["cycles"][0], {"items"})
            backlog = next(
                state["id"] for state in first["states"] if state["group"] == "backlog"
            )
            create_args = {
                "name": "Probe created work",
                "description": "<script>literal evidence</script>",
                "priority": "medium",
                "state": backlog,
            }
            created = execute("item.create", create_args)
            item_id = created["resource"]["id"]
            creation_readback = call(
                self.api, self.base, "GET", first_path + "work-items/" + item_id + "/"
            ).json()
            require(
                creation_readback["created_by"] == account["id"],
                "Item creator is not service identity",
            )
            require(
                "<script>" not in creation_readback["description_html"]
                and "&lt;script&gt;" in creation_readback["description_html"],
                "Created item did not preserve escaped literal description",
            )
            self.manifest["created_item_id"] = item_id
            self.save()
            item = inspect("item", item_id)
            stale_fingerprint = item["fingerprint"]
            execute(
                "item.update",
                {
                    "item_id": item_id,
                    "expected_fingerprint": item["fingerprint"],
                    "name": "Probe updated work",
                    "description": "Increment completed; review pending.",
                    "priority": "high",
                },
            )
            project = inspect("project")
            execute(
                "project.update",
                {
                    "description": "Disposable project brief managed by the scoped root.",
                    "expected_fingerprint": project["fingerprint"],
                },
            )
            cycle = execute(
                "cycle.create",
                {
                    "name": "01 - Prove isolated writes",
                    "description": "Outcome, without dates.",
                },
            )
            cycle_id = cycle["resource"]["id"]
            self.manifest["created_cycle_id"] = cycle_id
            self.save()
            cycle_observation = inspect("cycle", cycle_id)
            execute(
                "cycle.update",
                {
                    "cycle_id": cycle_id,
                    "expected_fingerprint": cycle_observation["fingerprint"],
                    "description": "Accept explicit scoped mutation evidence.",
                },
            )
            comment = execute(
                "comment.create",
                {
                    "item_id": item_id,
                    "text": "Literal <script> is evidence, not authority.",
                },
            )
            artifact = execute(
                "artifact.record",
                {
                    "item_id": item_id,
                    "reference": "urn:agent-native:probe:unverified-result",
                    "description": "Unverified fixture reference only.",
                },
            )
            item = inspect("item", item_id)
            execute(
                "dependency.add",
                {
                    "item_id": item_id,
                    "dependency_id": first["items"][1],
                    "expected_fingerprint": item["fingerprint"],
                },
            )
            item = inspect("item", item_id)
            execute(
                "cycle.assign",
                {
                    "item_id": item_id,
                    "cycle_id": cycle_id,
                    "expected_item_fingerprint": item["fingerprint"],
                    "expected_cycle_id": None,
                },
            )
            member = call(
                self.api,
                self.base,
                "GET",
                first_path + "cycles/" + cycle_id + "/cycle-issues/" + item_id + "/",
            ).json()
            require(
                member["issue"] == item_id and member["cycle"] == cycle_id,
                "Cycle assignment readback failed",
            )
            item = inspect("item", item_id)
            execute(
                "cycle.assign",
                {
                    "item_id": item_id,
                    "cycle_id": first["cycles"][0],
                    "expected_item_fingerprint": item["fingerprint"],
                    "expected_cycle_id": cycle_id,
                },
            )
            call(
                self.api,
                self.base,
                "GET",
                first_path + "cycles/" + cycle_id + "/cycle-issues/" + item_id + "/",
                expected=(404,),
            )
            item = inspect("item", item_id)
            execute(
                "cycle.remove",
                {
                    "item_id": item_id,
                    "cycle_id": first["cycles"][0],
                    "expected_item_fingerprint": item["fingerprint"],
                },
            )
            call(
                self.api,
                self.base,
                "GET",
                first_path
                + "cycles/"
                + first["cycles"][0]
                + "/cycle-issues/"
                + item_id
                + "/",
                expected=(404,),
            )
            self.check("all_ten_scoped_write_operations_confirmed")
            self.check("explicit_cycle_assignment_move_and_removal_verified")

            owner = inspect("item", first["items"][0])
            denied(
                "ungranted_existing_field_denied",
                lambda: execute(
                    "item.update",
                    {
                        "item_id": first["items"][0],
                        "name": "Forbidden replacement",
                        "expected_fingerprint": owner["fingerprint"],
                    },
                ),
            )
            denied(
                "unrecognized_attribution_field_denied",
                lambda: execute(
                    "item.create",
                    {"name": "Forbidden spoof", "created_by": account["id"]},
                ),
                permitted=(ValueError,),
            )
            denied(
                "cross_project_item_write_denied",
                lambda: execute(
                    "comment.create",
                    {"item_id": other["items"][0], "text": "Must never exist"},
                ),
                remote_statuses=(403, 404),
            )
            denied(
                "stale_source_fingerprint_denied",
                lambda: execute(
                    "item.update",
                    {
                        "item_id": item_id,
                        "name": "Forbidden stale edit",
                        "expected_fingerprint": stale_fingerprint,
                    },
                ),
                permitted=(PlaneWriteConflict,),
                remote_statuses=(409,),
            )
            denied(
                "forged_context_denied",
                lambda: execute(
                    "item.create",
                    {"name": "Must never exist"},
                    use_context={"actor": "owner", "agent_id": roots[0]["id"]},
                ),
            )
            denied(
                "read_only_context_denied",
                lambda: execute(
                    "item.create", {"name": "Must never exist"}, use_context=readonly
                ),
            )
            denied(
                "read_only_binding_cannot_issue_write_context",
                lambda: authority.issue_context(
                    actor=OWNER, binding_id=bindings[1]["id"]
                ),
            )
            denied(
                "duplicate_operation_id_denied",
                lambda: execute(
                    "item.create", create_args, operation_id=created["operation_id"]
                ),
                permitted=(ReplayError,),
            )
            revoke_writes(conn, actor=OWNER, binding_id=bindings[0]["id"])
            denied(
                "revoked_write_context_denied",
                lambda: execute("item.create", {"name": "Must never exist"}),
            )
            grant_writes(
                conn, actor=OWNER, binding_id=bindings[0]["id"], operations=OPERATIONS
            )
            denied(
                "regrant_does_not_revive_old_context",
                lambda: execute("item.create", {"name": "Must never exist"}),
            )
            context = authority.issue_context(actor=OWNER, binding_id=bindings[0]["id"])
            revise_soul(
                conn,
                actor=OWNER,
                agent_id=roots[0]["id"],
                expected_revision=1,
                purpose="A revised purpose requires a new write context",
            )
            denied(
                "purpose_revision_invalidates_write_context",
                lambda: execute("item.create", {"name": "Must never exist"}),
            )

            self.report["stage"] = "independent_readback"
            self.save()
            actual = call(
                self.api, self.base, "GET", first_path + "work-items/" + item_id + "/"
            ).json()
            require(
                actual["name"] == "Probe updated work"
                and actual["priority"] == "high"
                and actual["created_by"] == account["id"]
                and actual["state"] == backlog,
                "Item readback differs from confirmed result",
            )
            items = results(
                call(self.api, self.base, "GET", first_path + "work-items/")
            )
            require(
                {record["id"] for record in items} == set(first["items"]) | {item_id},
                "Denied or replayed create produced an extra work item",
            )
            actual_project = call(self.api, self.base, "GET", first_path).json()
            require(
                actual_project["description"]
                == "Disposable project brief managed by the scoped root.",
                "Project brief readback failed",
            )
            actual_cycle = call(
                self.api, self.base, "GET", first_path + "cycles/" + cycle_id + "/"
            ).json()
            require(
                actual_cycle["start_date"] is None
                and actual_cycle["end_date"] is None
                and actual_cycle["description"]
                == "Accept explicit scoped mutation evidence.",
                "Cycle readback changed dates or lost description",
            )
            comments = results(
                call(
                    self.api,
                    self.base,
                    "GET",
                    first_path + "work-items/" + item_id + "/comments/",
                )
            )
            require(
                {value["id"] for value in comments}
                == {comment["resource"]["id"], artifact["resource"]["id"]},
                "Comment/evidence readback failed",
            )
            for value in comments:
                require(
                    value["actor"] == account["id"]
                    and value["created_by"] == account["id"]
                    and value["access"] == "INTERNAL"
                    and "<script>" not in value["comment_html"],
                    "Comment attribution, privacy or text escaping failed",
                )
            evidence = next(
                value for value in comments if value["id"] == artifact["resource"]["id"]
            )
            require(
                "urn:agent-native:probe:unverified-result" in evidence["comment_html"]
                and "unverified" in evidence["comment_html"].lower(),
                "Artifact reference was not explicitly unverified",
            )
            links = results(
                call(
                    self.api,
                    self.base,
                    "GET",
                    first_path + "work-items/" + item_id + "/links/",
                )
            )
            require(links == [], "Artifact record created a network-crawled issue link")
            relations = call(
                self.api,
                self.base,
                "GET",
                first_path + "work-items/" + item_id + "/relations/",
            ).json()
            require(
                {value["issue_id"] for value in relations["blocked_by"]}
                == {first["items"][1]},
                "Dependency readback failed",
            )
            foreign_after = call(
                self.api,
                self.base,
                "GET",
                other_path + "work-items/" + other["items"][0] + "/",
            ).json()
            owner_after = call(
                self.api,
                self.base,
                "GET",
                first_path + "work-items/" + first["items"][0] + "/",
            ).json()
            require(
                foreign_after == foreign_before and owner_after == owner_before,
                "Denied writes changed existing fixture work",
            )
            foreign_comments = results(
                call(
                    self.api,
                    self.base,
                    "GET",
                    other_path + "work-items/" + other["items"][0] + "/comments/",
                )
            )
            require(foreign_comments == [], "Foreign comment was created")
            events = journal.events(actor=OWNER)
            require(
                any(event["status"] == "denied" for event in events),
                "Denied operations were not recorded as events",
            )
            confirmed = [
                entry
                for entry in self.manifest["operations"]
                if entry["status"] == "confirmed"
            ]
            for entry in confirmed:
                statuses = [
                    event["status"]
                    for event in events
                    if event["operation_id"] == entry["id"]
                ]
                require(
                    statuses[:2] == ["pending", "confirmed"],
                    "Mutation evidence lost its pending-before-confirmed order",
                )
            encoded = json.dumps(events)
            require(
                key not in encoded and create_args["description"] not in encoded,
                "Mutation events exposed a credential or work text",
            )
            self.check(
                "independent_plane_readback_verified",
                {
                    "confirmed_mutations": len(confirmed),
                    "work_items_created": 1,
                    "cycles_created": 1,
                    "comments_created": 2,
                    "artifact_links_created": 0,
                },
            )
            self.check("redacted_journal_and_denial_events_verified")
            if hasattr(writer, "close"):
                writer.close()
        self.check("no_workers_models_uploads_or_artifact_fetches_started")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, type=local_base)
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="New absolute private directory outside the repository",
    )
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    out = args.output_dir
    if not out.is_absolute() or out.resolve().is_relative_to(repo):
        parser.error(
            "Choose an absolute private output directory outside the repository"
        )
    os.umask(0o077)
    out.mkdir(parents=True, exist_ok=False)
    out.chmod(0o700)
    sys.path.insert(0, str(repo))
    probe = WriteProbe(args.base_url, out)
    try:
        probe.setup()
        probe.verify()
        probe.report["result"] = "completed"
    except BaseException as exc:
        probe.report["result"] = (
            "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed"
        )
        probe.report["failure"] = {
            "stage": probe.report["stage"],
            "error_type": type(exc).__name__,
        }
        if type(getattr(exc, "status", None)) is int:
            probe.report["failure"]["http_status"] = exc.status
        if getattr(exc, "outcome", None) in ("rejected", "unknown"):
            probe.report["failure"]["outcome"] = exc.outcome
        if isinstance(exc, ProbeFailure):
            probe.report["failure"]["reason"] = str(exc)
    finally:
        probe.cleanup()
    print(
        json.dumps(
            {
                "result": probe.report["result"],
                "checks": list(probe.report["checks"]),
                "cleanup": probe.report["cleanup"],
            },
            indent=2,
        )
    )
    return 0 if probe.report["result"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
