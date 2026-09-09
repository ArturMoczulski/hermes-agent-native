"""Private host planning session for one admitted writer run.

This module never launches work, installs grants on open, or exposes credentials
and authority objects to a worker. The trusted dispatcher supplies ``validate``
and retains the session on its opening thread. Mutation admission invokes that
callback through the existing write authority, including inside the journal's
attempt/confirmation transactions. An already admitted HTTP effect remains
subject to the adapter's honest unknown-outcome reconciliation.
"""
from contextlib import contextmanager
import json
from pathlib import Path

import httpx

from agent_native.identity import OWNER, _require_owner, get_root
from agent_native.plane_access import grant_project
from agent_native.plane_reads import PlaneReadError
from agent_native.plane_write_access import (
    RESOURCE_FIELDS, WriteAuthority, allow_resource, grant_writes,
)
from agent_native.plane_write_contracts import validate_arguments
from agent_native.plane_write_journal import MutationJournal
from agent_native.plane_writes import PlaneWrites
from agent_native.provisioning import _projection, _verify
from agent_native.startup import _revision, _row, load_plane_configuration
from hermes_cli.kanban_db_connect import connect_closing

# Fixed host policy, never copied from a tool request or future adapter additions.
WRITER_OPERATIONS = frozenset({
    'project.update', 'item.create', 'item.update', 'comment.create',
    'cycle.create', 'cycle.update', 'cycle.assign', 'cycle.remove',
    'dependency.add', 'artifact.record',
})
_SETUP_KEYS = ('activation_id', 'plane_origin', 'plane_user_id', 'workspace_slug',
               'workspace_id', 'project_id', 'discovery_item_id')


def _ready(conn, agent_id):
    root = get_root(conn, actor=OWNER, agent_id=agent_id)
    state = _row(conn, agent_id)
    startup = root['startup']
    if (not state or state['status'] != 'ready' or state['phase'] != 'ready'
            or not state['files_ready'] or not startup
            or startup['id'] != state['activation_id']
            or _revision(conn, agent_id) != root['soul_revision']
            or any(not state[k] for k in _SETUP_KEYS)):
        raise PermissionError('Current writer setup is not ready')
    return root, {**{k: state[k] for k in _SETUP_KEYS}, 'soul_revision': root['soul_revision']}


def install_grants(conn, *, actor, agent_id):
    """Explicit owner configuration, not a dispatcher retry or a model operation.

    Existing bindings are returned unchanged, even if revoked or partly installed.
    Only an owner may repair such configuration through the existing grant APIs;
    opening or retrying work must never restore narrowed/revoked permissions.
    """
    _require_owner(actor)
    _, state = _ready(conn, agent_id)
    existing = conn.execute(
        'SELECT id FROM agent_native_plane_access '
        'WHERE agent_id = ? AND workspace_slug = ? AND project_id = ?',
        (agent_id, state['workspace_slug'], state['project_id']),
    ).fetchone()
    if existing:
        allow_resource(conn, actor=actor, binding_id=existing[0], kind='item',
                       resource_id=state['discovery_item_id'], fields=RESOURCE_FIELDS['item'])
        return existing[0]
    binding = grant_project(conn, actor=actor, agent_id=agent_id,
                            workspace_slug=state['workspace_slug'],
                            workspace_id=state['workspace_id'], project_id=state['project_id'])
    grant_writes(conn, actor=actor, binding_id=binding['id'], operations=WRITER_OPERATIONS)
    allow_resource(conn, actor=actor, binding_id=binding['id'], kind='project',
                   resource_id=state['project_id'], fields={'description'})
    allow_resource(conn, actor=actor, binding_id=binding['id'], kind='item',
                   resource_id=state['discovery_item_id'], fields=RESOURCE_FIELDS['item'])
    return binding['id']


class _RunAuthority(WriteAuthority):
    def __init__(self, conn, *, home, agent_id, state, config, validate):
        super().__init__(conn)
        self._home, self._agent_id, self._state = home, agent_id, state
        self._config, self._validate, self._closed = config, validate, False

    def check(self):
        if self._closed:
            raise PermissionError('Writer planning session has ended')
        self._validate(self._conn)
        root, state = _ready(self._conn, self._agent_id)
        if state != self._state or load_plane_configuration(self._home) != self._config:
            raise PermissionError('Writer planning configuration changed')
        try:
            storage = self._home / 'agents'
            if storage.is_symlink():
                raise ValueError('Unsafe storage')
            _verify(storage / self._agent_id, _projection(root))
        except (OSError, ValueError):
            raise PermissionError('Writer workspace is not the prepared workspace') from None

    def resolve(self, context):
        self.check()
        scope = super().resolve(context)
        if (scope.agent_id != self._agent_id or scope.project_id != self._state['project_id']
                or scope.workspace_slug != self._state['workspace_slug']
                or scope.workspace_id != self._state['workspace_id']):
            raise PermissionError('Writer grant does not match its prepared project')
        return scope


def _verify_principal(authority, config):
    """Check the API credential without opening an administrative web session."""
    authority.check()
    try:
        with httpx.Client(follow_redirects=False, trust_env=False, timeout=15) as client:
            with client.stream('GET', config['base_url'] + '/api/v1/users/me/',
                               headers={'X-API-Key': config['api_key'],
                                        'Accept-Encoding': 'identity'}) as response:
                if response.status_code != 200:
                    raise PlaneReadError('Plane identity could not be verified', status=response.status_code)
                if response.headers.get('Content-Encoding', 'identity').lower() != 'identity':
                    raise PlaneReadError('Invalid Plane identity response')
                body = bytearray()
                for chunk in response.iter_raw():
                    if len(body) + len(chunk) > 16384:
                        raise PlaneReadError('Plane identity response exceeds the read budget')
                    body.extend(chunk)
                identity = json.loads(body)
    except (httpx.HTTPError, ValueError, RecursionError):
        raise PlaneReadError('Plane identity response is unavailable or invalid') from None
    authority.check()
    if not isinstance(identity, dict) or identity.get('id') != config['expected_user_id']:
        raise PermissionError('Plane API identity does not match the prepared account')


class _PlanningSession:
    def __init__(self, writer, context, discovery_id):
        self._writer, self._context, self._discovery_id = writer, context, discovery_id

    def snapshot(self):
        reads, context = self._writer._reads, self._context
        result = {'project': reads.get_project(context),
                  'discovery': reads.get_work_item(context, self._discovery_id),
                  'items': reads.list_work_items(context), 'states': reads.list_states(context),
                  'cycles': reads.list_cycles(context)}
        self._writer.authority.resolve(context)
        return result

    def inspect(self, arguments):
        args = validate_arguments('resource.inspect', arguments)
        return self._writer.inspect(self._context, args['kind'], args.get('resource_id'))

    def comments(self, item_id):
        return self._writer._reads.list_comments(self._context, item_id)

    def execute(self, operation_id, operation, arguments):
        return self._writer.execute(self._context, operation_id, operation, arguments)

    def recover(self, operation_id):
        return self._writer.recover(self._context, operation_id)


@contextmanager
def open_planning(*, db_path, home, agent_id, binding_id, validate, on_read_retry=None):
    """Open on the broker thread; ``home`` is HERMES_HOME/agent-native.

    ``validate(conn)`` must raise unless this exact run is current, active, within
    its deadline and still authorized. It must use the supplied connection and
    must not start a nested transaction or perform external effects. No network
    operation is performed while a database transaction is held by this module.
    """
    if not callable(validate):
        raise TypeError('A host run validator is required')
    home = Path(home)
    with connect_closing(db_path) as conn:
        validate(conn)
        _, state = _ready(conn, agent_id)
        config = load_plane_configuration(home)
        if (config['base_url'], config['expected_user_id']) != (
                state['plane_origin'], state['plane_user_id']):
            raise PermissionError('Plane connection does not match the prepared account')
        authority = _RunAuthority(conn, home=home, agent_id=agent_id, state=state,
                                  config=config, validate=validate)
        try:
            context = authority.issue_context(actor=OWNER, binding_id=binding_id)
            authority.resolve(context)
            writer = PlaneWrites(authority, MutationJournal(conn), base_url=config['base_url'],
                                 api_key=config['api_key'], service_user_id=config['expected_user_id'])
            writer._reads.on_retry = on_read_retry
            _verify_principal(authority, config)
            yield _PlanningSession(writer, context, state['discovery_item_id'])
        finally:
            authority._closed = True
