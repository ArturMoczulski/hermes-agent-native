"""Observe uncertain planning effects without redelivering a mutation.

Protected preparations and current host authority supply identity and expected
content. Plane correlation is mutable: a match proves current effect, not unique
historical causation. Only the original confirmed journal receipt is historical.
"""

from agent_native.identity import OWNER
from agent_native.plane_reads import (
    PlaneReadError,
    _record,
    _CURSOR,
    MAX_PAGES,
    MAX_RECORDS,
    MAX_TOTAL_BYTES,
)
from agent_native.plane_write_contracts import fingerprint, validate_arguments
from agent_native.plane_writes import PlaneWriteError


class PlaneRecoveryUnresolved(PlaneWriteError):
    def __init__(self, operation_id, reason, *, status=None, retry_after=None):
        super().__init__(
            "Plane outcome remains unresolved; do not resend",
            operation_id=operation_id,
            outcome="unknown",
            status=status,
            retry_after=retry_after,
        )
        self.reason = reason


def _historical(record, journal):
    confirmation = None
    if record["status"] == "confirmed":
        reconciled = any(
            event["status"] == "confirmed" and event["reason"] == "reconciled"
            for event in journal.events(
                actor=OWNER, operation_id=record["operation_id"]
            )
        )
        confirmation = "matching_effect" if reconciled else "delivery_response"
    return {
        "operation_id": record["operation_id"],
        "status": record["status"],
        "agent_id": record["agent_id"],
        "source": "journal",
        "recovered": True,
        "confirmation": confirmation,
        "resource": {"id": record["resource_id"]} if record["resource_id"] else None,
    }


def _marker(raw, operation_id):
    if (
        raw.get("external_source") != "agent-native"
        or raw.get("external_id") != operation_id
    ):
        raise PlaneRecoveryUnresolved(operation_id, "correlation_changed")


def _item_create(writer, context, scope, record, args, prepared):
    operation_id = record["operation_id"]
    _, candidate, _ = writer._reads._request(
        context,
        "work-items/",
        {"external_source": "agent-native", "external_id": operation_id},
    )
    projected = _record(candidate, scope, "item")
    _marker(candidate, operation_id)
    _, raw, _ = writer._reads._request(context, f"work-items/{projected['id']}/")
    _record(raw, scope, "item", item_id=projected["id"])
    _marker(raw, operation_id)
    return writer._result(
        context,
        scope,
        record["operation"],
        args,
        "item",
        projected["id"],
        raw,
        "POST",
        prepared["payload"],
        grant_created=False,
    )


def _inventory(writer, context, suffix, kind, item_id=None):
    """Bounded complete raw inventory; metadata is evidence, never authority."""
    result, ids, cursors = [], set(), set()
    cursor, total, size = None, None, 0
    for _ in range(MAX_PAGES):
        params = {"per_page": writer._reads.page_size}
        if cursor is not None:
            params["cursor"] = cursor
        scope, page, count = writer._reads._request(context, suffix, params)
        size += count
        if size > MAX_TOTAL_BYTES or not isinstance(page, dict):
            raise PlaneReadError(
                "Recovery inventory exceeds bounds or has invalid metadata"
            )
        records, more = page.get("results"), page.get("next_page_results")
        if not isinstance(records, list) or type(more) is not bool:
            raise PlaneReadError("Invalid recovery inventory page")
        totals = [page[k] for k in ("total_results", "total_count") if k in page]
        if totals:
            if any(
                type(value) is not int or value < 0 or value != totals[0]
                for value in totals
            ):
                raise PlaneReadError("Invalid recovery inventory totals")
            if total is not None and total != totals[0]:
                raise PlaneReadError("Recovery inventory changed during traversal")
            total = totals[0]
        if "count" in page and (
            type(page["count"]) is not int or page["count"] != len(records)
        ):
            raise PlaneReadError("Invalid recovery inventory count")
        if len(result) + len(records) > MAX_RECORDS:
            raise PlaneReadError("Recovery inventory exceeds the record budget")
        for raw in records:
            projected = _record(raw, scope, kind, item_id=item_id)
            if projected["id"] in ids:
                raise PlaneReadError("Recovery inventory repeated a resource")
            ids.add(projected["id"])
            result.append(raw)
        if not more:
            if total is not None and len(result) != total:
                raise PlaneReadError("Recovery inventory is incomplete")
            return result
        cursor = page.get("next_cursor")
        if (
            not records
            or not isinstance(cursor, str)
            or not _CURSOR.fullmatch(cursor)
            or cursor in cursors
        ):
            raise PlaneReadError("Invalid recovery inventory cursor")
        cursors.add(cursor)
    raise PlaneReadError("Recovery inventory exceeds the page budget")


def _cycles(writer, context):
    active = _inventory(writer, context, "cycles/", "cycle")
    archived = _inventory(writer, context, "archived-cycles/", "cycle")
    records = active + archived
    if len({value["id"] for value in records}) != len(records):
        raise PlaneReadError("Cycle visibility changed during recovery")
    return records


def _append_or_cycle(writer, context, scope, record, args, prepared):
    opid = record["operation_id"]
    if record["operation"] == "cycle.create":
        kind, parent, suffix = "cycle", None, "cycles/"
        candidates = _cycles(writer, context)
    else:
        kind, parent = "comment", args["item_id"]
        writer._fetch(context, "item", parent)
        suffix = f"work-items/{parent}/comments/"
        candidates = _inventory(writer, context, suffix, kind, parent)
    matched = [
        raw
        for raw in candidates
        if raw.get("external_source") == "agent-native"
        and raw.get("external_id") == opid
    ]
    if len(matched) != 1:
        raise PlaneRecoveryUnresolved(opid, "correlation_not_unique")
    candidate = matched[0]
    _, raw, _ = writer._reads._request(context, suffix + candidate["id"] + "/")
    _record(raw, scope, kind, item_id=parent)
    if raw.get("id") != candidate["id"]:
        raise PlaneRecoveryUnresolved(opid, "candidate_changed")
    _marker(raw, opid)
    return writer._result(
        context,
        scope,
        record["operation"],
        args,
        kind,
        parent if kind == "comment" else candidate["id"],
        raw,
        "POST",
        prepared["payload"],
        grant_created=False,
    )


def _update(writer, context, scope, record, args, prepared):
    kind = record["operation"].split(".")[0]
    rid = None if kind == "project" else args[kind + "_id"]
    suffix = (
        ""
        if kind == "project"
        else f"{'work-items' if kind == 'item' else 'cycles'}/{rid}/"
    )
    _, raw, _ = writer._reads._request(context, suffix)
    payload = dict(prepared["payload"])
    if record["operation"] == "project.update" and isinstance(payload.get("description"), str):
        # Historical preparations may predate request-side canonicalization.
        payload["description"] = payload["description"].rstrip("\r\n")
    return writer._result(
        context,
        scope,
        record["operation"],
        args,
        kind,
        rid,
        raw,
        "PATCH",
        payload,
    )


def _membership_effect(writer, context, scope, record, args, prepared):
    item, target = args["item_id"], args["cycle_id"]
    writer._fetch(context, "item", item)
    writer._fetch(context, "cycle", target)
    cycles = _cycles(writer, context)
    known = {target}
    if args.get("expected_cycle_id"):
        known.add(args["expected_cycle_id"])
    if not known.issubset({cycle["id"] for cycle in cycles}):
        raise PlaneRecoveryUnresolved(record["operation_id"], "cycle_inventory_changed")
    if len(cycles) > 100:
        raise PlaneRecoveryUnresolved(
            record["operation_id"], "membership_budget_exceeded"
        )
    observed = []
    for cycle in cycles:
        cid = cycle["id"]
        try:
            _, raw, _ = writer._reads._request(
                context, f"cycles/{cid}/cycle-issues/{item}/"
            )
        except PlaneReadError as error:
            if error.status == 404:
                continue
            raise
        observed.append(writer._membership(raw, scope, cid, item))
    if record["operation"] == "cycle.assign":
        if len(observed) != 1 or observed[0]["cycle"] != target:
            raise PlaneRecoveryUnresolved(
                record["operation_id"], "membership_not_confirmed"
            )
        return observed[0]
    if observed:
        raise PlaneRecoveryUnresolved(
            record["operation_id"], "membership_not_confirmed"
        )
    return {
        "id": item,
        "workspace": scope.workspace_id,
        "project": scope.project_id,
        "cycle": target,
        "removed": True,
    }


def _dependency(writer, context, scope, record, args, prepared):
    writer._fetch(context, "item", args["item_id"])
    writer._fetch(context, "item", args["dependency_id"])
    return writer._result(
        context,
        scope,
        record["operation"],
        args,
        "dependency",
        args["item_id"],
        [],
        None,
        prepared["payload"],
    )


def recover(writer, context, operation_id):
    scope = writer.authority.resolve(context)
    record = writer.journal._current_receipt(scope, operation_id)
    if record["status"] in ("confirmed", "rejected"):
        return _historical(record, writer.journal)
    try:
        stored = writer.journal.preparation(operation_id, actor=OWNER)
    except (KeyError, ValueError):
        raise PlaneRecoveryUnresolved(operation_id, "preparation_unavailable") from None
    args = validate_arguments(record["operation"], stored["arguments"])
    prepared = stored["prepared"]
    requirements = writer._permissions(scope, record["operation"], args)
    writer._check(context, record["operation"], requirements)
    if not stored["attempted"] and prepared["method"] is not None:
        result = writer.journal.reconcile(
            scope,
            operation_id,
            status="rejected",
            authorize=lambda: writer._check(context, record["operation"], requirements),
        )
        return _historical(result, writer.journal)
    try:
        handlers = {
            "item.create": _item_create,
            "cycle.create": _append_or_cycle,
            "comment.create": _append_or_cycle,
            "artifact.record": _append_or_cycle,
            "project.update": _update,
            "item.update": _update,
            "cycle.update": _update,
            "cycle.assign": _membership_effect,
            "cycle.remove": _membership_effect,
            "dependency.add": _dependency,
        }
        if record["operation"] not in handlers:
            raise PlaneRecoveryUnresolved(operation_id, "operation_not_supported")
        resource = handlers[record["operation"]](
            writer, context, scope, record, args, prepared
        )
        writer._check(context, record["operation"], requirements)
        writer.journal.reconcile(
            scope,
            operation_id,
            status="confirmed",
            resource_id=resource["id"],
            authorize=lambda: writer._check(context, record["operation"], requirements),
        )
        return {
            "operation_id": operation_id,
            "status": "confirmed",
            "agent_id": scope.agent_id,
            "source": "matching_plane_effect",
            "confirmation": "matching_effect",
            "recovered": True,
            "resource": resource,
            "fingerprint": fingerprint(resource),
        }
    except PlaneRecoveryUnresolved:
        raise
    except PlaneReadError as error:
        raise PlaneRecoveryUnresolved(
            operation_id,
            "effect_not_confirmed",
            status=error.status,
            retry_after=error.retry_after,
        ) from None
