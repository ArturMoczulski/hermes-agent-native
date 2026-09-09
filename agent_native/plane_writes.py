"""Scoped host planning writes with explicit grants and one-shot mutation records.

The host retains the credential, authority, journal and opaque contexts. Explicit outcome recovery is
GET-only. This is not worker authentication, run admission or result evaluation.
"""

import html
from html.parser import HTMLParser
import json

import httpx

from agent_native.plane_reads import (
    MAX_BODY_BYTES,
    PlaneReads,
    PlaneReadError,
    _record,
    _retry_after,
    _uuid,
)
from agent_native.plane_write_contracts import fingerprint, schemas, validate_arguments


class PlaneWriteError(PlaneReadError):
    def __init__(
        self, message, *, status=None, retry_after=None, operation_id=None, outcome=None
    ):
        super().__init__(message, status=status, retry_after=retry_after)
        self.operation_id, self.outcome = operation_id, outcome


class PlaneWriteConflict(PlaneWriteError):
    """Observed source changed or cannot be safely updated through this surface."""


def _paragraph(text):
    return "<p>" + html.escape(text).replace("\n", "<br>") + "</p>"


class _LiteralText(HTMLParser):
    """Compare our escaped paragraphs after Plane adds its HTML wrapper."""

    def __init__(self, value):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.links = []
        self.feed(value)
        self.close()

    def handle_starttag(self, tag, attrs):
        if tag not in ("p", "br", "div", "a"):
            raise PlaneWriteError("Plane changed the literal text markup")
        if tag == "a":
            attributes = dict(attrs)
            if (len(attributes) != len(attrs) or not attributes.get('href')
                    or any(k not in ('href', 'target', 'rel') for k in attributes)):
                raise PlaneWriteError("Plane changed the link markup")
            self.links.append(attributes['href'])
        if tag == "br":
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag == "p":
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(data)

    @property
    def text(self):
        return "".join(self.parts).rstrip("\n")


def _verify_applied(raw, payload):
    for key, value in payload.items():
        if key in ("external_source", "external_id"):
            continue  # Correlation is not a native idempotency guarantee.
        if key not in raw:
            raise PlaneWriteError("Plane omitted a requested field")
        actual = raw[key]
        if key in ("description_html", "comment_html"):
            if not isinstance(actual, str):
                raise PlaneWriteError("Plane did not return the requested literal text")
            returned, expected = _LiteralText(actual), _LiteralText(value)
            if returned.text != expected.text or returned.links != expected.links:
                raise PlaneWriteError("Plane did not return the requested text and link destinations")
        elif type(actual) is not type(value) or actual != value:
            raise PlaneWriteError("Plane did not return the requested field value")


class PlaneWrites:
    def __init__(self, authority, journal, *, base_url, api_key, service_user_id):
        self.authority, self.journal = authority, journal
        self._reads = PlaneReads(authority, base_url=base_url, api_key=api_key)
        self._service_user_id = _uuid(service_user_id)

    def tool_schemas(self, context):
        scope = self.authority.resolve(context)
        return schemas(scope.operations | {"resource.inspect"})

    def inspect(self, context, kind, resource_id=None):
        args = {"kind": kind}
        if resource_id is not None:
            args["resource_id"] = resource_id
        args = validate_arguments("resource.inspect", args)
        record = self._fetch(context, args["kind"], args.get("resource_id"))
        result = {
            "source": "plane",
            "resource": record,
            "fingerprint": fingerprint(record),
        }
        if args["kind"] == "item":
            memberships = self._memberships(context, record["id"])
            result["cycle_id"] = memberships[0]["cycle"] if memberships else None
            result["dependencies"] = sorted(self._dependencies(context, record["id"]))
        self.authority.resolve(context)
        return result

    def _fetch(self, context, kind, resource_id=None):
        suffix = (
            ""
            if kind == "project"
            else f"{'work-items' if kind == 'item' else 'cycles'}/{_uuid(resource_id)}/"
        )
        scope, payload, _ = self._reads._request(context, suffix)
        record = _record(
            payload, scope, kind, item_id=resource_id if kind == "item" else None
        )
        if kind == "cycle" and record["id"] != resource_id:
            raise PlaneWriteError("Plane cycle does not match the requested resource")
        return record

    def _permissions(self, scope, operation, args):
        if operation == "project.update":
            return [("project", scope.project_id, {"description"})]
        editable = {
            "item.update": (
                "item",
                "item_id",
                {"name", "description", "priority", "state"},
            ),
            "cycle.update": ("cycle", "cycle_id", {"name", "description"}),
        }
        if operation in editable:
            kind, key, fields = editable[operation]
            return [(kind, args[key], fields & args.keys())]
        if operation in ("cycle.assign", "cycle.remove"):
            rights = [
                ("item", args["item_id"], {"cycle"}),
                ("cycle", args["cycle_id"], {"items"}),
            ]
            old = args.get("expected_cycle_id")
            if old and old != args["cycle_id"]:
                rights.append(("cycle", old, {"items"}))
            return rights
        if operation == "dependency.add":
            return [("item", args["item_id"], {"dependencies"})]
        return []

    def _check(self, context, operation, requirements):
        scope = self.authority.authorize(context, operation)
        for kind, resource_id, fields in requirements:
            self.authority.authorize(
                context, operation, kind=kind, resource_id=resource_id, fields=fields
            )
        return scope

    def _current(self, context, kind, resource_id, expected):
        record = self._fetch(context, kind, resource_id)
        if fingerprint(record) != expected:
            raise PlaneWriteConflict("Plane source changed; inspect it before editing")
        return record

    def _state(self, context, requested=None):
        states = self._reads.list_states(context)
        if requested is not None:
            choices = [s for s in states if s["id"] == requested]
        else:
            choices = [s for s in states if s.get("default") is True]
            if not choices:
                choices = [
                    s for s in states if s.get("group") in ("backlog", "unstarted")
                ][:1]
        if len(choices) != 1 or choices[0].get("group") not in (
            "backlog",
            "unstarted",
            "started",
        ):
            raise PlaneWriteConflict(
                "A nonterminal state in the bound project is required"
            )
        return choices[0]["id"]

    def _prepare(self, context, operation, args, operation_id):
        handlers = {
            "item.create": self._create_item,
            "item.update": self._update_item,
            "project.update": self._update_project,
            "comment.create": self._comment,
            "artifact.record": self._artifact,
            "cycle.create": self._create_cycle,
            "cycle.update": self._update_cycle,
            "cycle.assign": self._assign_cycle,
            "cycle.remove": self._remove_cycle,
            "dependency.add": self._add_dependency,
        }
        return handlers[operation](context, args, operation_id)

    def _create_item(self, context, args, operation_id):
        payload = {
            "name": args["name"],
            "description_html": _paragraph(args["description"]),
            "priority": args["priority"],
            "state": self._state(context, args.get("state")),
            "external_source": "agent-native",
            "external_id": operation_id,
        }
        return "POST", "work-items/", payload, 201, "item", None

    def _update_project(self, context, args, operation_id):
        self._current(context, "project", None, args["expected_fingerprint"])
        return "PATCH", "", {"description": args["description"]}, 200, "project", None

    def _update_item(self, context, args, operation_id):
        self._current(context, "item", args["item_id"], args["expected_fingerprint"])
        payload = {
            key: args[key] for key in ("name", "priority", "state") if key in args
        }
        if "description" in args:
            payload["description_html"] = _paragraph(args["description"])
        if "state" in args:
            payload["state"] = self._state(context, args["state"])
        return (
            "PATCH",
            f"work-items/{args['item_id']}/",
            payload,
            200,
            "item",
            args["item_id"],
        )

    def _comment_payload(self, context, args, operation_id, text):
        self._fetch(context, "item", args["item_id"])
        scope = self.authority.resolve(context)
        payload = {
            "comment_html": _paragraph(f"Agent {scope.agent_id} (framework planning)")
            + _paragraph(text),
            "access": "INTERNAL",
            "external_source": "agent-native",
            "external_id": operation_id,
        }
        if 'link_url' in args:
            payload['comment_html'] += '<p><a href="' + html.escape(args['link_url'], quote=True) + '">' + html.escape(args['link_label']) + '</a></p>'
        return (
            "POST",
            f"work-items/{args['item_id']}/comments/",
            payload,
            201,
            "comment",
            args["item_id"],
        )

    def _comment(self, context, args, operation_id):
        return self._comment_payload(context, args, operation_id, args["text"])

    def _artifact(self, context, args, operation_id):
        text = (
            "Unverified artifact reference: "
            + args["reference"]
            + "\n"
            + args["description"]
        )
        # Plain text only. Native issue-link creation starts a server-side crawler.
        return self._comment_payload(context, args, operation_id, text)

    def _create_cycle(self, context, args, operation_id):
        payload = {
            "name": args["name"],
            "description": args["description"],
            "start_date": None,
            "end_date": None,
            "external_source": "agent-native",
            "external_id": operation_id,
        }
        return "POST", "cycles/", payload, 201, "cycle", None

    def _update_cycle(self, context, args, operation_id):
        cycle = self._current(
            context, "cycle", args["cycle_id"], args["expected_fingerprint"]
        )
        if cycle.get("start_date") is not None or cycle.get("end_date") is not None:
            raise PlaneWriteConflict(
                "Managed cycles must be undated; reconcile this cycle first"
            )
        owner = _uuid(cycle.get("owned_by"))
        # Plane changes owned_by on PATCH when omitted, even for a text-only edit.
        payload = {
            "owned_by": owner,
            **{k: args[k] for k in ("name", "description") if k in args},
        }
        return (
            "PATCH",
            f"cycles/{args['cycle_id']}/",
            payload,
            200,
            "cycle",
            args["cycle_id"],
        )

    def _membership(self, raw, scope, cycle_id, item_id):
        expected = {
            "workspace": scope.workspace_id,
            "project": scope.project_id,
            "cycle": cycle_id,
            "issue": item_id,
        }
        if not isinstance(raw, dict) or any(
            raw.get(k) != v for k, v in expected.items()
        ):
            raise PlaneWriteError("Cycle membership is outside the authorized resource")
        return {"id": _uuid(raw.get("id")), **expected}

    def _memberships(self, context, item_id):
        cycles = self._reads.list_cycles(context)
        if len(cycles) > 100:
            raise PlaneWriteConflict(
                "Cycle inventory exceeds the membership-check budget"
            )
        found = []
        for cycle in cycles:
            cid = cycle["id"]
            try:
                scope, raw, _ = self._reads._request(
                    context, f"cycles/{cid}/cycle-issues/{item_id}/"
                )
            except PlaneReadError as error:
                if error.status == 404:
                    continue
                raise
            found.append(self._membership(raw, scope, cid, item_id))
        if len(found) > 1:
            raise PlaneWriteConflict(
                "Ambiguous prior cycle membership; reconcile it first"
            )
        return found

    def _assign_cycle(self, context, args, operation_id):
        self._fetch(context, "cycle", args["cycle_id"])
        prior = self._memberships(context, args["item_id"])
        actual = prior[0]["cycle"] if prior else None
        # A repeated request for an already-established relationship has no
        # mutation left to protect. Confirm it before rejecting an observation
        # made stale by an unrelated item edit.
        if actual == args["cycle_id"]:
            return None, "", prior, None, "membership", args["item_id"]
        self._current(
            context, "item", args["item_id"], args["expected_item_fingerprint"]
        )
        if actual != args["expected_cycle_id"]:
            raise PlaneWriteConflict(
                "Prior cycle changed; inspect the item before moving it"
            )
        return (
            "POST",
            f"cycles/{args['cycle_id']}/cycle-issues/",
            {"issues": [args["item_id"]]},
            200,
            "membership",
            args["item_id"],
        )

    def _remove_cycle(self, context, args, operation_id):
        self._current(
            context, "item", args["item_id"], args["expected_item_fingerprint"]
        )
        self._fetch(context, "cycle", args["cycle_id"])
        prior = self._memberships(context, args["item_id"])
        if not prior or prior[0]["cycle"] != args["cycle_id"]:
            raise PlaneWriteConflict("The expected cycle membership is not current")
        return (
            "DELETE",
            f"cycles/{args['cycle_id']}/cycle-issues/{args['item_id']}/",
            None,
            204,
            "removed_membership",
            args["item_id"],
        )

    def _dependencies(self, context, item_id):
        scope, raw, _ = self._reads._request(
            context, f"work-items/{item_id}/relations/"
        )
        if not isinstance(raw, dict) or not isinstance(raw.get("blocked_by"), list):
            raise PlaneWriteError("Invalid Plane dependencies")
        if len(raw["blocked_by"]) > 100:
            raise PlaneWriteConflict("Dependency list exceeds the check budget")
        result = set()
        for entry in raw["blocked_by"]:
            if (
                not isinstance(entry, dict)
                or entry.get("project_id") != scope.project_id
            ):
                raise PlaneWriteError(
                    "Dependency points outside the authorized project"
                )
            result.add(_uuid(entry.get("issue_id")))
        return result

    def _check_dependency_path(self, context, source, target):
        stack, seen = [target], set()
        while stack:
            current = stack.pop()
            if current == source:
                raise PlaneWriteConflict("This dependency would create a cycle")
            if current in seen:
                continue
            seen.add(current)
            if len(seen) > 100:
                raise PlaneWriteConflict("Dependency graph exceeds the check budget")
            self._fetch(context, "item", current)
            stack.extend(self._dependencies(context, current) - seen)

    def _add_dependency(self, context, args, operation_id):
        source, target = args["item_id"], args["dependency_id"]
        dependencies = self._dependencies(context, source)
        if target in dependencies:
            return None, "", [], None, "dependency", source
        self._current(context, "item", source, args["expected_fingerprint"])
        self._fetch(context, "item", target)
        self._check_dependency_path(context, source, target)
        return (
            "POST",
            f"work-items/{source}/relations/",
            {"relation_type": "blocked_by", "issues": [target]},
            201,
            "dependency",
            source,
        )

    def _result(
        self,
        context,
        scope,
        operation,
        args,
        kind,
        resource_id,
        raw,
        method,
        payload,
        *,
        grant_created=True,
    ):
        if kind == "membership":
            # Plane returns the entire cycle after assignment, not only the
            # requested item. Confirm exactly one matching membership and never
            # expose unrelated members through this scoped receipt.
            if not isinstance(raw, list):
                raise PlaneWriteError("Unexpected cycle assignment response")
            matches = [member for member in raw if isinstance(member, dict)
                       and member.get("issue") == resource_id]
            if len(matches) != 1:
                raise PlaneWriteError("Unexpected cycle assignment response")
            record = self._membership(matches[0], scope, args["cycle_id"], resource_id)
            observed = self._memberships(context, resource_id)
            if len(observed) != 1 or observed[0] != record:
                raise PlaneWriteError("Cycle assignment could not be confirmed")
            return record
        if kind == "removed_membership":
            if self._memberships(context, resource_id):
                raise PlaneWriteError("Cycle removal could not be confirmed")
            return {
                "id": resource_id,
                "workspace": scope.workspace_id,
                "project": scope.project_id,
                "cycle": args["cycle_id"],
                "removed": True,
            }
        if kind == "dependency":
            target = args["dependency_id"]
            if method is not None:
                if (
                    not isinstance(raw, list)
                    or len(raw) != 1
                    or not isinstance(raw[0], dict)
                    or raw[0].get("id") != target
                    or raw[0].get("project_id") != scope.project_id
                    or raw[0].get("relation_type") != "blocked_by"
                ):
                    raise PlaneWriteError("Unexpected dependency response")
            if target not in self._dependencies(context, resource_id):
                raise PlaneWriteError("Dependency could not be confirmed")
            self._check_dependency_path(context, resource_id, target)
            return {
                "id": resource_id,
                "workspace": scope.workspace_id,
                "project": scope.project_id,
                "dependency_id": target,
                "relation_type": "blocked_by",
            }
        record = _record(
            raw,
            scope,
            kind,
            item_id=resource_id if kind in ("item", "comment") else None,
        )
        if kind == "cycle" and resource_id and record["id"] != resource_id:
            raise PlaneWriteError("Plane returned a different cycle")
        created_resource = operation in ("item.create", "cycle.create")
        if (created_resource or kind == "comment") and raw.get(
            "created_by"
        ) != self._service_user_id:
            raise PlaneWriteError(
                "Plane creation attribution does not match the service identity"
            )
        if kind == "comment" and raw.get("actor") != self._service_user_id:
            raise PlaneWriteError(
                "Plane comment attribution does not match the service identity"
            )
        if method == "PATCH" and raw.get("updated_by") != self._service_user_id:
            raise PlaneWriteError(
                "Plane update attribution does not match the service identity"
            )
        _verify_applied(raw, payload)
        if created_resource and grant_created:
            self.authority.record_created_resource(context, operation, record["id"])
        return record

    def _send(
        self,
        context,
        operation,
        requirements,
        method,
        suffix,
        payload,
        expected,
        mark_attempted,
    ):
        scope = self._check(context, operation, requirements)
        if method is None:
            return scope, payload
        url = (
            f"{self._reads._base_url}/api/v1/workspaces/{scope.workspace_slug}/"
            f"projects/{scope.project_id}/{suffix}"
        )
        try:
            with httpx.Client(
                follow_redirects=False, trust_env=False, timeout=15
            ) as client:
                # Intent is already committed. No redirects or automatic mutation retries.
                self._check(context, operation, requirements)
                mark_attempted()
                with client.stream(
                    method,
                    url,
                    json=payload,
                    headers={
                        "X-API-Key": self._reads._api_key,
                        "Accept-Encoding": "identity",
                    },
                ) as response:
                    if response.status_code != expected:
                        raise PlaneWriteError(
                            "Plane mutation was not confirmed",
                            status=response.status_code,
                            retry_after=_retry_after(
                                response.headers.get("Retry-After")
                            ),
                        )
                    if (
                        response.headers.get("Content-Encoding", "identity").lower()
                        != "identity"
                    ):
                        raise PlaneWriteError("Unexpected Plane response encoding")
                    length = response.headers.get("Content-Length")
                    if length is not None and (
                        not length.isdigit() or int(length) > MAX_BODY_BYTES
                    ):
                        raise PlaneWriteError("Plane response exceeds the write budget")
                    body = bytearray()
                    for chunk in response.iter_raw():
                        if len(body) + len(chunk) > MAX_BODY_BYTES:
                            raise PlaneWriteError(
                                "Plane response exceeds the write budget"
                            )
                        body.extend(chunk)
                    result = None if expected == 204 else json.loads(body)
        except (httpx.HTTPError, ValueError, RecursionError):
            raise PlaneWriteError(
                "Plane mutation response unavailable or invalid"
            ) from None
        self._check(context, operation, requirements)
        return scope, result

    def recover(self, context, operation_id):
        from agent_native.plane_recovery import recover
        from agent_native.plane_operation_lock import operation_lock

        operation_id = _uuid(operation_id)
        with operation_lock(self.journal._conn, operation_id):
            return recover(self, context, operation_id)

    def execute(self, context, operation_id, operation, arguments):
        from agent_native.plane_operation_lock import operation_lock

        operation_id = _uuid(operation_id)
        with operation_lock(self.journal._conn, operation_id):
            return self._execute(context, operation_id, operation, arguments)

    def _execute(self, context, operation_id, operation, arguments):
        # Context and correlation are injected by the trusted caller, never model arguments.
        operation_id = _uuid(operation_id)
        scope = None
        try:
            args = validate_arguments(operation, arguments)
            if operation == "resource.inspect":
                return self.inspect(context, args["kind"], args.get("resource_id"))
            scope = self.authority.authorize(context, operation)
            requirements = self._permissions(scope, operation, args)
            self._check(context, operation, requirements)
        except (PermissionError, ValueError):
            self.journal.denied(
                operation_id, operation, scope=scope, reason="permission_denied"
            )
            raise
        resources = [r for _, r, _ in requirements]
        try:
            self.journal.begin(
                scope, operation_id, operation, args, resource_ids=resources
            )
        except PermissionError:
            self.journal.denied(
                operation_id, operation, scope=scope, reason="scope_changed"
            )
            raise
        attempted = False

        def mark_attempted():
            nonlocal attempted
            self.journal.mark_attempted(
                scope,
                operation_id,
                authorize=lambda: self._check(context, operation, requirements),
            )
            attempted = True

        try:
            method, suffix, payload, status, kind, resource_id = self._prepare(
                context, operation, args, operation_id
            )
            self.journal.prepare(
                scope,
                operation_id,
                args,
                {
                    "method": method,
                    "suffix": suffix,
                    "payload": payload,
                    "expected": status,
                    "kind": kind,
                    "resource_id": resource_id,
                },
            )
            current_scope, raw = self._send(
                context,
                operation,
                requirements,
                method,
                suffix,
                payload,
                status,
                mark_attempted,
            )
            record = self._result(
                context,
                current_scope,
                operation,
                args,
                kind,
                resource_id,
                raw,
                method,
                payload,
            )
            self._check(context, operation, requirements)
            result = {
                "operation_id": operation_id,
                "status": "confirmed",
                "source": "plane",
                "agent_id": scope.agent_id,
                "resource": record,
                "fingerprint": fingerprint(record),
            }
            self.journal.finish(
                operation_id,
                "confirmed",
                resource_id=record["id"],
                authorize=lambda: self._check(context, operation, requirements),
            )
            return result
        except Exception as error:
            outcome = "unknown" if attempted else "rejected"
            self.journal.finish(operation_id, outcome)
            if isinstance(error, PermissionError):
                self.journal.denied(
                    operation_id, operation, scope=scope, reason="scope_changed"
                )
            if isinstance(error, PlaneWriteError):
                error.operation_id, error.outcome = operation_id, outcome
            raise
