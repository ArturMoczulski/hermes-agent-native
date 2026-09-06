"""Explicit host Plane write grants, never managed-run authentication.

Do not expose this authority, OWNER, its contexts, or its database to generated
code. The HTTP adapter receives an opaque context retained by the trusted host.
"""
from dataclasses import asdict, dataclass
import json
from uuid import UUID

from agent_native.identity import OWNER, _require_owner
from agent_native.plane_access import PlaneScope, ReadAuthority
from hermes_cli.kanban_db_connect import write_txn

OPERATIONS = frozenset({
    'project.update', 'item.create', 'item.update', 'comment.create',
    'cycle.create', 'cycle.update', 'cycle.assign', 'cycle.remove',
    'dependency.add', 'artifact.record',
})
RESOURCE_FIELDS = {
    'project': frozenset({'description'}),
    'item': frozenset({'name', 'description', 'state', 'priority', 'cycle', 'dependencies'}),
    'cycle': frozenset({'name', 'description', 'items'}),
}
_CREATIONS = {'item.create': 'item', 'cycle.create': 'cycle'}


@dataclass(frozen=True)
class WriteScope(PlaneScope):
    operations: frozenset
    write_revision: int


def canonical_uuid(value):
    if not isinstance(value, str):
        raise ValueError('A canonical UUID string is required')
    try:
        if str(UUID(value)) == value:
            return value
    except ValueError:
        pass
    raise ValueError('A canonical UUID string is required')


def _selection(values, allowed):
    if not isinstance(values, (list, tuple, set, frozenset)):
        raise ValueError('A collection of allowed names is required')
    if len(values) > len(allowed) or any(not isinstance(x, str) or x not in allowed for x in values):
        raise ValueError('Unsupported permission')
    return frozenset(values)


def _grant(conn, binding_id):
    row = conn.execute(
        'SELECT binding_id, operations, revision, active FROM agent_native_plane_write_access WHERE binding_id = ?',
        (binding_id,),
    ).fetchone()
    if row is None or not row[3]:
        raise PermissionError('Plane write access is not active')
    return {'binding_id': row[0], 'operations': frozenset(json.loads(row[1])), 'revision': row[2], 'active': row[3]}


def grant_writes(conn, *, actor, binding_id, operations):
    """Replace the explicit operation set; a read binding alone grants no writes."""
    _require_owner(actor)
    binding_id = canonical_uuid(binding_id)
    operations = _selection(operations, OPERATIONS)
    if not operations:
        raise ValueError('Grant at least one operation; use revoke_writes to remove access')
    encoded = json.dumps(sorted(operations))
    with write_txn(conn):
        ReadAuthority(conn)._scope(binding_id)
        conn.execute(
            'INSERT INTO agent_native_plane_write_access (binding_id, operations, revision, active) '
            'VALUES (?, ?, 1, 1) ON CONFLICT(binding_id) DO UPDATE SET '
            'operations = excluded.operations, revision = revision + 1, active = 1 '
            'WHERE active = 0 OR operations != excluded.operations',
            (binding_id, encoded),
        )
        return _grant(conn, binding_id)


def revoke_writes(conn, *, actor, binding_id):
    """Keep a revision tombstone so regrant cannot revive an issued handle."""
    _require_owner(actor)
    binding_id = canonical_uuid(binding_id)
    with write_txn(conn):
        conn.execute(
            'UPDATE agent_native_plane_write_access SET active = 0, revision = revision + 1 '
            'WHERE binding_id = ? AND active = 1', (binding_id,),
        )


def _resource(scope, kind, resource_id, fields):
    if not isinstance(kind, str) or kind not in RESOURCE_FIELDS:
        raise ValueError('Unsupported resource kind')
    resource_id = canonical_uuid(resource_id)
    fields = _selection(fields, RESOURCE_FIELDS[kind])
    if kind == 'project' and resource_id != scope.project_id:
        raise PermissionError('Project is outside the bound scope')
    return resource_id, fields


def _save_resource(conn, scope, kind, resource_id, fields):
    conn.execute(
        'INSERT INTO agent_native_plane_resource_access (binding_id, kind, resource_id, fields) VALUES (?, ?, ?, ?) '
        'ON CONFLICT(binding_id, kind, resource_id) DO UPDATE SET fields = excluded.fields',
        (scope.binding_id, kind, resource_id, json.dumps(sorted(fields))),
    )


def allow_resource(conn, *, actor, binding_id, kind, resource_id, fields):
    """Replace editable fields for existing content; an empty set revokes them.

    The adapter must separately prove current remote membership for items/cycles.
    These grants cannot authorize a request outside the bound project.
    """
    _require_owner(actor)
    binding_id = canonical_uuid(binding_id)
    with write_txn(conn):
        scope = WriteAuthority(conn)._scope(binding_id)
        resource_id, fields = _resource(scope, kind, resource_id, fields)
        _save_resource(conn, scope, kind, resource_id, fields)


class WriteAuthority(ReadAuthority):
    """Opaque host capability with live operation, purpose and field checks."""
    def _scope(self, binding_id):
        scope = super()._scope(canonical_uuid(binding_id))
        grant = _grant(self._conn, binding_id)
        return WriteScope(**asdict(scope), operations=grant['operations'], write_revision=grant['revision'])

    def authorize(self, context, operation, *, kind=None, resource_id=None, fields=()):
        scope = self.resolve(context)
        if not isinstance(operation, str) or operation not in scope.operations:
            raise PermissionError('Plane operation is not granted')
        if kind is None and resource_id is None and not fields:
            return scope
        try:
            resource_id, fields = _resource(scope, kind, resource_id, fields)
        except ValueError:
            raise PermissionError('Plane resource fields are not granted') from None
        row = self._conn.execute(
            'SELECT fields FROM agent_native_plane_resource_access WHERE binding_id = ? AND kind = ? AND resource_id = ?',
            (scope.binding_id, kind, resource_id),
        ).fetchone()
        if row is None or not fields or not fields.issubset(json.loads(row[0])):
            raise PermissionError('Plane resource fields are not granted')
        return scope

    def record_created_resource(self, context, operation, resource_id):
        """Trusted adapter only, after validating a confirmed create response.

        Derive fixed editable fields from the existing create grant. This never
        grants new operations and is not a worker-callable self-grant operation.
        """
        with write_txn(self._conn):
            scope = self.authorize(context, operation)
            kind = _CREATIONS.get(operation)
            if kind is None:
                raise PermissionError('Operation does not create an editable resource')
            resource_id, fields = _resource(scope, kind, resource_id, RESOURCE_FIELDS[kind])
            # Repeating a receipt must not expand fields the owner later narrowed.
            self._conn.execute(
                'INSERT OR IGNORE INTO agent_native_plane_resource_access '
                '(binding_id, kind, resource_id, fields) VALUES (?, ?, ?, ?)',
                (scope.binding_id, kind, resource_id, json.dumps(sorted(fields))),
            )
