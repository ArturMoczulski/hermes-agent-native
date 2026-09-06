"""Host-owned project read grants, not managed-run authentication.

Only trusted control code holding OWNER may install grants or issue contexts.
Contexts remain in the host process; never derive one from tool/request actor
fields or pass the authority, database or OWNER capability into a worker.
"""
from dataclasses import dataclass
import re
from uuid import UUID, uuid4

from agent_native.identity import OWNER, _require_owner, get_root
from hermes_cli.kanban_db_connect import write_txn


@dataclass(frozen=True)
class PlaneScope:
    binding_id: str
    agent_id: str
    workspace_slug: str
    workspace_id: str
    project_id: str
    revision: int
    soul_revision: int


def _uuid(value):
    if not isinstance(value, str):
        raise ValueError('Scope identifiers must be UUID strings')
    try:
        return str(UUID(value))
    except (ValueError, AttributeError):
        raise ValueError('Scope identifiers must be UUID strings') from None


def _binding(conn, binding_id):
    keys = ('id', 'agent_id', 'workspace_slug', 'workspace_id', 'project_id', 'revision', 'active')
    row = conn.execute(
        'SELECT id, agent_id, workspace_slug, workspace_id, project_id, revision, active '
        'FROM agent_native_plane_access WHERE id = ?', (binding_id,),
    ).fetchone()
    if row is None:
        raise KeyError(binding_id)
    return dict(zip(keys, row))


def grant_project(conn, *, actor, agent_id, workspace_slug, workspace_id, project_id):
    """Install an explicit owner-approved project binding; store no Plane secret."""
    _require_owner(actor)
    if not isinstance(workspace_slug, str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,99}', workspace_slug):
        raise ValueError('Invalid Plane workspace slug')
    workspace_id, project_id = _uuid(workspace_id), _uuid(project_id)
    with write_txn(conn):
        get_root(conn, actor=OWNER, agent_id=agent_id)
        row = conn.execute(
            'SELECT id FROM agent_native_plane_access '
            'WHERE agent_id = ? AND workspace_slug = ? AND project_id = ?',
            (agent_id, workspace_slug, project_id),
        ).fetchone()
        if row:
            binding = _binding(conn, row[0])
            if not binding['active'] or binding['workspace_id'] != workspace_id:
                conn.execute(
                    'UPDATE agent_native_plane_access '
                    'SET workspace_id = ?, active = 1, revision = revision + 1 WHERE id = ?',
                    (workspace_id, binding['id']),
                )
            return _binding(conn, binding['id'])
        binding_id = str(uuid4())
        conn.execute(
            'INSERT INTO agent_native_plane_access '
            '(id, agent_id, workspace_slug, workspace_id, project_id, revision, active) '
            'VALUES (?, ?, ?, ?, ?, 1, 1)',
            (binding_id, agent_id, workspace_slug, workspace_id, project_id),
        )
        return _binding(conn, binding_id)


def revoke_project(conn, *, actor, binding_id):
    """Persist a tombstone so a later regrant cannot revive an old context."""
    _require_owner(actor)
    with write_txn(conn):
        binding = _binding(conn, binding_id)
        if binding['active']:
            conn.execute(
                'UPDATE agent_native_plane_access SET active = 0, revision = revision + 1 WHERE id = ?',
                (binding_id,),
            )
        return _binding(conn, binding_id)


class ReadAuthority:
    """Issue opaque host contexts; revalidate current authority on every use.

    A host service restart discards contexts, while grants persist. The future
    authenticated run/transport boundary must retain the context privately and
    associate it with the invoking run; this class does not supply that boundary.
    """
    def __init__(self, conn):
        self._conn = conn
        self._contexts = {}

    def _scope(self, binding_id):
        binding = _binding(self._conn, binding_id)
        if not binding['active']:
            raise PermissionError('Plane read access is not active')
        root = get_root(self._conn, actor=OWNER, agent_id=binding['agent_id'])
        return PlaneScope(
            binding_id=binding['id'], agent_id=binding['agent_id'],
            workspace_slug=binding['workspace_slug'], workspace_id=binding['workspace_id'],
            project_id=binding['project_id'], revision=binding['revision'],
            soul_revision=root['soul_revision'],
        )

    def issue_context(self, *, actor, binding_id):
        _require_owner(actor)
        scope = self._scope(binding_id)
        context = object()
        self._contexts[context] = scope
        return context

    def resolve(self, context):
        if type(context) is not object or context not in self._contexts:
            raise PermissionError('Trusted Plane read context required')
        previous = self._contexts[context]
        try:
            current = self._scope(previous.binding_id)
        except KeyError:
            raise PermissionError('Plane read context is no longer valid') from None
        if current != previous:
            raise PermissionError('Plane read context is no longer valid')
        return current
