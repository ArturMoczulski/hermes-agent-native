"""Real persistence checks for explicit Plane write and field grants."""
from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from agent_native.identity import OWNER, create_root, revise_soul
from agent_native.plane_access import ReadAuthority, grant_project, revoke_project
from agent_native.plane_write_access import WriteAuthority, allow_resource, grant_writes, revoke_writes
from hermes_cli.kanban_db_connect import connect_closing


@pytest.fixture
def setup(tmp_path):
    with connect_closing(tmp_path / 'control.db') as conn:
        root = create_root(conn, actor=OWNER, request_id='builder', name='Builder', purpose='Build')
        grant = grant_project(conn, actor=OWNER, agent_id=root['id'], workspace_slug='build',
                              workspace_id=str(uuid4()), project_id=str(uuid4()))
        yield conn, root, grant


def test_read_binding_alone_cannot_issue_write_context(setup):
    conn, _, grant = setup
    read = ReadAuthority(conn)
    assert read.resolve(read.issue_context(actor=OWNER, binding_id=grant['id'])).project_id == grant['project_id']
    with pytest.raises(PermissionError):
        WriteAuthority(conn).issue_context(actor=OWNER, binding_id=grant['id'])


def test_explicit_operation_grant_is_immutable_and_idempotent(setup):
    conn, root, grant = setup
    first = grant_writes(conn, actor=OWNER, binding_id=grant['id'], operations=['item.create'])
    authority = WriteAuthority(conn)
    context = authority.issue_context(actor=OWNER, binding_id=grant['id'])
    assert grant_writes(conn, actor=OWNER, binding_id=grant['id'], operations=['item.create']) == first
    scope = authority.authorize(context, 'item.create')
    assert scope.agent_id == root['id'] and scope.operations == frozenset({'item.create'})
    with pytest.raises(FrozenInstanceError):
        scope.write_revision = 99
    with pytest.raises(PermissionError):
        authority.authorize(context, 'cycle.create')


@pytest.mark.parametrize('actor', [None, 'owner', {'role': 'owner'}, object()])
def test_only_owner_may_change_grants_and_issue_handles(setup, actor):
    conn, _, grant = setup
    grant_writes(conn, actor=OWNER, binding_id=grant['id'], operations=['item.create'])
    with pytest.raises(PermissionError):
        grant_writes(conn, actor=actor, binding_id=grant['id'], operations=['item.update'])
    with pytest.raises(PermissionError):
        revoke_writes(conn, actor=actor, binding_id=grant['id'])
    with pytest.raises(PermissionError):
        allow_resource(conn, actor=actor, binding_id=grant['id'], kind='item', resource_id=str(uuid4()), fields=['name'])
    with pytest.raises(PermissionError):
        WriteAuthority(conn).issue_context(actor=actor, binding_id=grant['id'])


def test_operation_change_and_revoke_regrant_never_revive_handles(setup):
    conn, _, grant = setup
    grant_writes(conn, actor=OWNER, binding_id=grant['id'], operations=['item.create'])
    authority = WriteAuthority(conn)
    stale = authority.issue_context(actor=OWNER, binding_id=grant['id'])
    grant_writes(conn, actor=OWNER, binding_id=grant['id'], operations=['cycle.create'])
    with pytest.raises(PermissionError):
        authority.resolve(stale)
    current = authority.issue_context(actor=OWNER, binding_id=grant['id'])
    revoke_writes(conn, actor=OWNER, binding_id=grant['id'])
    with pytest.raises(PermissionError):
        authority.resolve(current)
    with pytest.raises(PermissionError):
        authority.issue_context(actor=OWNER, binding_id=grant['id'])
    grant_writes(conn, actor=OWNER, binding_id=grant['id'], operations=['cycle.create'])
    with pytest.raises(PermissionError):
        authority.resolve(current)
    assert authority.authorize(authority.issue_context(actor=OWNER, binding_id=grant['id']), 'cycle.create')


def test_write_context_is_also_invalidated_by_purpose_or_read_revoke(setup):
    conn, root, grant = setup
    grant_writes(conn, actor=OWNER, binding_id=grant['id'], operations=['item.create'])
    authority = WriteAuthority(conn)
    first = authority.issue_context(actor=OWNER, binding_id=grant['id'])
    revise_soul(conn, actor=OWNER, agent_id=root['id'], expected_revision=1, purpose='Different')
    with pytest.raises(PermissionError):
        authority.resolve(first)
    second = authority.issue_context(actor=OWNER, binding_id=grant['id'])
    revoke_project(conn, actor=OWNER, binding_id=grant['id'])
    with pytest.raises(PermissionError):
        authority.resolve(second)


def test_existing_resources_require_explicit_fields_and_recheck_changes(setup):
    conn, _, grant = setup
    item_id = str(uuid4())
    grant_writes(conn, actor=OWNER, binding_id=grant['id'], operations=['item.update'])
    authority = WriteAuthority(conn)
    context = authority.issue_context(actor=OWNER, binding_id=grant['id'])
    with pytest.raises(PermissionError):
        authority.authorize(context, 'item.update', kind='item', resource_id=item_id, fields=['name'])
    allow_resource(conn, actor=OWNER, binding_id=grant['id'], kind='item', resource_id=item_id, fields=['name'])
    assert authority.authorize(context, 'item.update', kind='item', resource_id=item_id, fields=['name'])
    with pytest.raises(PermissionError):
        authority.authorize(context, 'item.update', kind='item', resource_id=item_id, fields=['description'])
    allow_resource(conn, actor=OWNER, binding_id=grant['id'], kind='item', resource_id=item_id, fields=[])
    with pytest.raises(PermissionError):
        authority.authorize(context, 'item.update', kind='item', resource_id=item_id, fields=['name'])


def test_confirmed_creation_gets_fixed_fields_without_self_granting_operations(setup):
    conn, _, grant = setup
    item_id = str(uuid4())
    grant_writes(conn, actor=OWNER, binding_id=grant['id'], operations=['item.create', 'item.update'])
    authority = WriteAuthority(conn)
    context = authority.issue_context(actor=OWNER, binding_id=grant['id'])
    authority.record_created_resource(context, 'item.create', item_id)
    assert authority.authorize(context, 'item.update', kind='item', resource_id=item_id, fields=['name', 'description'])
    with pytest.raises(PermissionError):
        authority.authorize(context, 'item.update', kind='item', resource_id=item_id, fields=['authority'])
    with pytest.raises(PermissionError):
        authority.record_created_resource(context, 'cycle.create', str(uuid4()))


@pytest.mark.parametrize('operations', [[], ['admin'], ['item.create', 'authority.grant'], 'item.create', [None]])
def test_unknown_or_ambiguous_operation_grants_are_rejected(setup, operations):
    conn, _, grant = setup
    with pytest.raises(ValueError):
        grant_writes(conn, actor=OWNER, binding_id=grant['id'], operations=operations)
    with pytest.raises(PermissionError):
        WriteAuthority(conn).issue_context(actor=OWNER, binding_id=grant['id'])


@pytest.mark.parametrize('context', [None, {}, {'agent_id': 'owner'}, 'owner', OWNER, object()])
def test_forged_write_context_is_rejected(setup, context):
    conn, _, grant = setup
    grant_writes(conn, actor=OWNER, binding_id=grant['id'], operations=['item.create'])
    with pytest.raises(PermissionError):
        WriteAuthority(conn).authorize(context, 'item.create')


def test_read_handle_is_not_upgraded_and_restarted_host_does_not_accept_old_handle(setup):
    conn, _, grant = setup
    reader = ReadAuthority(conn)
    read_context = reader.issue_context(actor=OWNER, binding_id=grant['id'])
    grant_writes(conn, actor=OWNER, binding_id=grant['id'], operations=['item.create'])
    authority = WriteAuthority(conn)
    with pytest.raises(PermissionError):
        authority.resolve(read_context)
    context = authority.issue_context(actor=OWNER, binding_id=grant['id'])
    with pytest.raises(PermissionError):
        WriteAuthority(conn).resolve(context)


def test_resource_rights_are_bound_to_project_binding_and_kind(setup):
    conn, root, grant = setup
    other_grant = grant_project(conn, actor=OWNER, agent_id=root['id'], workspace_slug='other',
                                workspace_id=str(uuid4()), project_id=str(uuid4()))
    for binding in (grant, other_grant):
        grant_writes(conn, actor=OWNER, binding_id=binding['id'], operations=['item.update', 'project.update', 'cycle.update'])
    item_id = str(uuid4())
    allow_resource(conn, actor=OWNER, binding_id=grant['id'], kind='item', resource_id=item_id, fields=['name'])
    authority = WriteAuthority(conn)
    context = authority.issue_context(actor=OWNER, binding_id=grant['id'])
    other = authority.issue_context(actor=OWNER, binding_id=other_grant['id'])
    with pytest.raises(PermissionError):
        authority.authorize(other, 'item.update', kind='item', resource_id=item_id, fields=['name'])
    with pytest.raises(PermissionError):
        authority.authorize(context, 'cycle.update', kind='cycle', resource_id=item_id, fields=['name'])
    with pytest.raises(PermissionError):
        allow_resource(conn, actor=OWNER, binding_id=grant['id'], kind='project', resource_id=other_grant['project_id'], fields=['description'])
    with pytest.raises(ValueError):
        allow_resource(conn, actor=OWNER, binding_id=grant['id'], kind='project', resource_id=grant['project_id'], fields=['purpose'])


def test_created_resource_receipt_cannot_undo_owner_field_narrowing(setup):
    conn, _, grant = setup
    grant_writes(conn, actor=OWNER, binding_id=grant['id'], operations=['cycle.create', 'cycle.update'])
    authority = WriteAuthority(conn)
    context = authority.issue_context(actor=OWNER, binding_id=grant['id'])
    cycle_id = str(uuid4())
    authority.record_created_resource(context, 'cycle.create', cycle_id)
    assert authority.authorize(context, 'cycle.update', kind='cycle', resource_id=cycle_id, fields=['name'])
    allow_resource(conn, actor=OWNER, binding_id=grant['id'], kind='cycle', resource_id=cycle_id, fields=['description'])
    authority.record_created_resource(context, 'cycle.create', cycle_id)
    with pytest.raises(PermissionError):
        authority.authorize(context, 'cycle.update', kind='cycle', resource_id=cycle_id, fields=['name'])


def test_resource_and_operation_revocations_persist_and_are_observed_across_connections(tmp_path):
    path = tmp_path / 'control.db'
    item_id = str(uuid4())
    with connect_closing(path) as conn:
        root = create_root(conn, actor=OWNER, request_id='builder', name='Builder', purpose='Build')
        grant = grant_project(conn, actor=OWNER, agent_id=root['id'], workspace_slug='build',
                              workspace_id=str(uuid4()), project_id=str(uuid4()))
        grant_writes(conn, actor=OWNER, binding_id=grant['id'], operations=['item.update'])
        allow_resource(conn, actor=OWNER, binding_id=grant['id'], kind='item', resource_id=item_id, fields=['name'])
    with connect_closing(path) as conn:
        authority = WriteAuthority(conn)
        context = authority.issue_context(actor=OWNER, binding_id=grant['id'])
        assert authority.authorize(context, 'item.update', kind='item', resource_id=item_id, fields=['name'])
        with connect_closing(path) as owner_conn:
            allow_resource(owner_conn, actor=OWNER, binding_id=grant['id'], kind='item', resource_id=item_id, fields=[])
        with pytest.raises(PermissionError):
            authority.authorize(context, 'item.update', kind='item', resource_id=item_id, fields=['name'])
        with connect_closing(path) as owner_conn:
            revoke_writes(owner_conn, actor=OWNER, binding_id=grant['id'])
        with pytest.raises(PermissionError):
            authority.resolve(context)
    with connect_closing(path) as conn:
        with pytest.raises(PermissionError):
            WriteAuthority(conn).issue_context(actor=OWNER, binding_id=grant['id'])


@pytest.mark.parametrize('resource_id', ['../items', 'not-a-uuid', str(uuid4()).upper(), str(uuid4()).replace('-', '')])
def test_permission_resource_identifiers_must_be_canonical_uuids(setup, resource_id):
    conn, _, grant = setup
    grant_writes(conn, actor=OWNER, binding_id=grant['id'], operations=['item.create', 'item.update'])
    authority = WriteAuthority(conn)
    context = authority.issue_context(actor=OWNER, binding_id=grant['id'])
    with pytest.raises(ValueError):
        allow_resource(conn, actor=OWNER, binding_id=grant['id'], kind='item', resource_id=resource_id, fields=['name'])
    with pytest.raises(ValueError):
        authority.record_created_resource(context, 'item.create', resource_id)
