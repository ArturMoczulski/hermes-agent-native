"""Owner-only inspection of prepared planning, independent of agent execution.

The owner may inspect a stopped agent or one that has never run. This ephemeral
read authority does not install, restore, or borrow the agent's grants. Plane
credentials and contexts remain on the host; every external resource still goes
through the scoped, bounded PlaneReads adapter.
"""
from dataclasses import dataclass
from pathlib import Path

from agent_native.identity import _now, _require_owner
from agent_native.plane_reads import PlaneReads
from agent_native.startup import ConfigurationRequired, load_plane_configuration
from agent_native.writer_planning import _ready, _verify_principal


class PlanningNotReady(RuntimeError):
    pass


class PlanningConfigurationRequired(RuntimeError):
    pass


@dataclass(frozen=True)
class _OwnerScope:
    agent_id: str
    workspace_slug: str
    workspace_id: str
    project_id: str
    soul_revision: int


class _OwnerReadAuthority:
    def __init__(self, conn, *, actor, home, agent_id, state, config):
        _require_owner(actor)
        self._conn, self._home, self._agent_id = conn, home, agent_id
        self._state, self._config = state, config
        self._context, self._closed = object(), False
        self._scope = _OwnerScope(agent_id, state['workspace_slug'], state['workspace_id'],
                                  state['project_id'], state['soul_revision'])

    def check(self):
        if self._closed or self._conn.in_transaction:
            raise PermissionError('Planning inspection is no longer valid')
        try:
            _, state = _ready(self._conn, self._agent_id)
            config = load_plane_configuration(self._home)
        except (PermissionError, KeyError, ConfigurationRequired):
            raise PermissionError('Planning inspection is no longer valid') from None
        if state != self._state or config != self._config:
            raise PermissionError('Planning inspection is no longer valid')

    def resolve(self, context):
        if context is not self._context:
            raise PermissionError('Owner planning context required')
        self.check()
        return self._scope


def read_planning(conn, *, actor, agent_id, home):
    """Return one observed snapshot; no cache, scheduler, or guessed assignment."""
    _require_owner(actor)
    try:
        root, state = _ready(conn, agent_id)
    except PermissionError:
        raise PlanningNotReady('Planning setup is not ready') from None
    home = Path(home)
    try:
        config = load_plane_configuration(home)
    except ConfigurationRequired:
        raise PlanningConfigurationRequired('Planning connection is not configured') from None
    if (config['base_url'], config['expected_user_id']) != (
            state['plane_origin'], state['plane_user_id']):
        raise PermissionError('Plane connection does not match the prepared account')
    authority = _OwnerReadAuthority(conn, actor=actor, home=home, agent_id=agent_id,
                                    state=state, config=config)
    try:
        try:
            reads = PlaneReads(authority, base_url=config['base_url'], api_key=config['api_key'])
        except ValueError:
            raise PlanningConfigurationRequired('Planning connection is not configured') from None
        _verify_principal(authority, config)
        context = authority._context
        snapshot = {'project': reads.get_project(context), 'items': reads.list_work_items(context),
                    'cycles': reads.list_cycles(context), 'states': reads.list_states(context)}
        authority.resolve(context)
        return {'agent_id': agent_id, 'soul_revision': root['soul_revision'],
                'setup_activation_id': state['activation_id'], 'observed_at': _now(),
                'plane_origin': state['plane_origin'], 'workspace_slug': state['workspace_slug'],
                **snapshot}
    finally:
        authority._closed = True
