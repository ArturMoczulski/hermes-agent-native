"""Durable redacted host mutation intents; no retry or outcome recovery yet.

Host code passes resolved WriteScope values, never caller-supplied identity.
Records retain hashes and identifiers, not work text, Plane secrets or responses.
A successful begin commits before the caller can send the network request.
"""
from hashlib import sha256
import json
import math

from agent_native.identity import OWNER, _now, _require_owner
from agent_native.plane_write_access import OPERATIONS, WriteAuthority, WriteScope, canonical_uuid
from hermes_cli.kanban_db_connect import write_txn

_SCOPE_KEYS = ('binding_id', 'agent_id', 'workspace_slug', 'workspace_id', 'project_id',
               'revision', 'write_revision', 'soul_revision')
_RECORD_KEYS = ('operation_id', 'operation', *_SCOPE_KEYS, 'arguments_sha256', 'resource_ids',
                'status', 'resource_id', 'created_at', 'finished_at')
_EVENT_KEYS = ('sequence', 'operation_id', 'operation', *_SCOPE_KEYS, 'status', 'reason',
               'resource_id', 'created_at')
_TERMINAL = frozenset({'confirmed', 'rejected', 'unknown'})
_REASONS = frozenset({'permission_denied', 'invalid_arguments', 'scope_changed', 'replay'})
MAX_ARGUMENT_BYTES = 256 * 1024
MAX_ARGUMENT_NODES = 1024
MAX_ARGUMENT_DEPTH = 16


class ReplayError(ValueError):
    """An operation ID has already been consumed; no delivery may be retried."""


def _scope_values(scope):
    if type(scope) is not WriteScope:
        raise PermissionError('Resolved host write scope required')
    return tuple(getattr(scope, key) for key in _SCOPE_KEYS)


def _arguments_hash(arguments):
    if type(arguments) is not dict:
        raise ValueError('Mutation arguments must be a JSON object')
    nodes, byte_count = 0, 0

    def visit(value, depth):
        nonlocal nodes, byte_count
        nodes += 1
        if nodes > MAX_ARGUMENT_NODES or depth > MAX_ARGUMENT_DEPTH:
            raise ValueError('Mutation arguments exceed structural bounds')
        kind = type(value)
        if kind is str:
            byte_count += len(value.encode('utf-8'))
        elif kind is dict:
            for key, child in value.items():
                if type(key) is not str:
                    raise ValueError('Mutation argument keys must be strings')
                visit(key, depth + 1)
                visit(child, depth + 1)
        elif kind is list:
            for child in value:
                visit(child, depth + 1)
        elif kind is float:
            if not math.isfinite(value):
                raise ValueError('Mutation arguments must contain finite numbers')
        elif value is not None and kind not in (int, bool):
            raise ValueError('Mutation arguments must be JSON values')
        if byte_count > MAX_ARGUMENT_BYTES:
            raise ValueError('Mutation arguments exceed size bound')

    visit(arguments, 0)
    encoded = json.dumps(arguments, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')
    if len(encoded) > MAX_ARGUMENT_BYTES:
        raise ValueError('Mutation arguments exceed size bound')
    return sha256(encoded).hexdigest()


class MutationJournal:
    """Host-owned receipt store. Pending and unknown writes are never replayed."""
    def __init__(self, conn):
        self._conn = conn

    def begin(self, scope, operation_id, operation, arguments, resource_ids=()):
        operation_id = canonical_uuid(operation_id)
        with write_txn(self._conn):
            if self._conn.execute(
                'SELECT 1 FROM agent_native_plane_mutation_events WHERE operation_id = ? LIMIT 1',
                (operation_id,),
            ).fetchone():
                raise ReplayError('Mutation operation already exists; reconciliation is required')
            values = _scope_values(scope)
            if WriteAuthority(self._conn)._scope(scope.binding_id) != scope:
                raise PermissionError('Plane write scope is no longer valid')
            if not isinstance(operation, str) or operation not in OPERATIONS or operation not in scope.operations:
                raise PermissionError('Mutation operation is not granted')
            if not isinstance(resource_ids, (list, tuple)) or len(resource_ids) > 100:
                raise ValueError('Mutation resource identifiers exceed bounds')
            resource_ids = [canonical_uuid(value) for value in resource_ids]
            arguments_hash = _arguments_hash(arguments)
            self._conn.execute(
                'INSERT INTO agent_native_plane_mutations (' + ', '.join(_RECORD_KEYS) + ') VALUES (' +
                ', '.join('?' for _ in _RECORD_KEYS) + ')',
                (operation_id, operation, *values, arguments_hash, json.dumps(resource_ids), 'pending', None, _now(), None),
            )
            record = self.get(operation_id, actor=OWNER)
            self._event(record, 'pending')
        return record

    def finish(self, operation_id, status, resource_id=None):
        operation_id = canonical_uuid(operation_id)
        if not isinstance(status, str) or status not in _TERMINAL:
            raise ValueError('Mutation status must be a terminal outcome')
        if resource_id is not None:
            resource_id = canonical_uuid(resource_id)
        with write_txn(self._conn):
            before = self.get(operation_id, actor=OWNER)
            if before['status'] != 'pending':
                raise ReplayError('Mutation outcome was already recorded')
            self._conn.execute(
                'UPDATE agent_native_plane_mutations SET status = ?, resource_id = ?, finished_at = ? '
                'WHERE operation_id = ?', (status, resource_id, _now(), operation_id),
            )
            record = self.get(operation_id, actor=OWNER)
            self._event(record, status)
        return record

    def get(self, operation_id, *, actor):
        _require_owner(actor)
        operation_id = canonical_uuid(operation_id)
        row = self._conn.execute(
            'SELECT ' + ', '.join(_RECORD_KEYS) + ' FROM agent_native_plane_mutations WHERE operation_id = ?',
            (operation_id,),
        ).fetchone()
        if row is None:
            raise KeyError(operation_id)
        record = dict(zip(_RECORD_KEYS, row))
        record['resource_ids'] = json.loads(record['resource_ids'])
        return record

    def events(self, *, actor, operation_id=None):
        _require_owner(actor)
        query = 'SELECT ' + ', '.join(_EVENT_KEYS) + ' FROM agent_native_plane_mutation_events'
        params = ()
        if operation_id is not None:
            params = (canonical_uuid(operation_id),)
            query += ' WHERE operation_id = ?'
        rows = self._conn.execute(query + ' ORDER BY sequence', params).fetchall()
        return [dict(zip(_EVENT_KEYS, row)) for row in rows]

    def denied(self, operation_id, operation, scope=None, reason='permission_denied'):
        operation_id = canonical_uuid(operation_id)
        values = (None,) * len(_SCOPE_KEYS) if scope is None else _scope_values(scope)
        operation = operation if isinstance(operation, str) and operation in OPERATIONS else 'unsupported'
        reason = reason if isinstance(reason, str) and reason in _REASONS else 'permission_denied'
        record = dict(zip(_SCOPE_KEYS, values), operation_id=operation_id, operation=operation, resource_id=None)
        with write_txn(self._conn):
            self._event(record, 'denied', reason)

    def _event(self, record, status, reason=None):
        columns = _EVENT_KEYS[1:]
        self._conn.execute(
            'INSERT INTO agent_native_plane_mutation_events (' + ', '.join(columns) + ') VALUES (' +
            ', '.join('?' for _ in columns) + ')',
            (record['operation_id'], record['operation'], *(record[key] for key in _SCOPE_KEYS),
             status, reason, record['resource_id'], _now()),
        )
