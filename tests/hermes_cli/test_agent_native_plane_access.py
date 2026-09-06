"""Real persistence and revocation tests for trusted host Plane read contexts."""
from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from agent_native.identity import OWNER, create_root, revise_soul
from agent_native.plane_access import ReadAuthority, grant_project, revoke_project
from hermes_cli.kanban_db_connect import connect_closing


@pytest.fixture
def setup(tmp_path):
    with connect_closing(tmp_path / 'control.db') as conn:
        root = create_root(conn, actor=OWNER, request_id='artist', name='Artist', purpose='Compose music')
        params = dict(actor=OWNER, agent_id=root['id'], workspace_slug='music',
                      workspace_id=str(uuid4()), project_id=str(uuid4()))
        yield conn, root, params


def test_grant_is_persistent_and_repeated_identical_grant_does_not_invalidate_context(setup):
    conn, root, params = setup
    grant = grant_project(conn, **params)
    authority = ReadAuthority(conn)
    context = authority.issue_context(actor=OWNER, binding_id=grant['id'])
    assert grant_project(conn, **params) == grant
    scope = authority.resolve(context)
    assert scope.agent_id == root['id']
    assert scope.project_id == params['project_id']
    assert scope.workspace_slug == 'music'
    with pytest.raises(FrozenInstanceError):
        scope.project_id = str(uuid4())
    # A new host authority can recover a binding, but not another service's context.
    restarted = ReadAuthority(conn)
    assert restarted.resolve(restarted.issue_context(actor=OWNER, binding_id=grant['id'])) == scope
    with pytest.raises(PermissionError):
        restarted.resolve(context)


@pytest.mark.parametrize('actor', [None, 'owner', {'role': 'owner'}, object()])
def test_untrusted_actors_cannot_install_grants_issue_contexts_or_revoke(setup, actor):
    conn, root, params = setup
    grant = grant_project(conn, **params)
    with pytest.raises(PermissionError):
        grant_project(conn, **dict(params, actor=actor))
    authority = ReadAuthority(conn)
    with pytest.raises(PermissionError):
        authority.issue_context(actor=actor, binding_id=grant['id'])
    with pytest.raises(PermissionError):
        revoke_project(conn, actor=actor, binding_id=grant['id'])


@pytest.mark.parametrize('context', [None, 'owner', {}, {'agent_id': 'artist'}, object(), OWNER])
def test_forged_contexts_are_rejected(setup, context):
    conn, root, params = setup
    grant_project(conn, **params)
    with pytest.raises(PermissionError):
        ReadAuthority(conn).resolve(context)


def test_revocation_and_regrant_never_revive_old_context(setup):
    conn, root, params = setup
    grant = grant_project(conn, **params)
    authority = ReadAuthority(conn)
    stale = authority.issue_context(actor=OWNER, binding_id=grant['id'])
    revoke_project(conn, actor=OWNER, binding_id=grant['id'])
    with pytest.raises(PermissionError):
        authority.resolve(stale)
    with pytest.raises(PermissionError):
        authority.issue_context(actor=OWNER, binding_id=grant['id'])
    renewed = grant_project(conn, **params)
    assert renewed['id'] == grant['id']
    assert renewed['revision'] > grant['revision']
    with pytest.raises(PermissionError):
        authority.resolve(stale)
    assert authority.resolve(authority.issue_context(actor=OWNER, binding_id=grant['id'])).project_id == params['project_id']


def test_purpose_revision_and_workspace_rebinding_invalidate_contexts(setup):
    conn, root, params = setup
    grant = grant_project(conn, **params)
    authority = ReadAuthority(conn)
    first = authority.issue_context(actor=OWNER, binding_id=grant['id'])
    revise_soul(conn, actor=OWNER, agent_id=root['id'], expected_revision=1, purpose='Write a different album')
    with pytest.raises(PermissionError):
        authority.resolve(first)
    second = authority.issue_context(actor=OWNER, binding_id=grant['id'])
    rebound = grant_project(conn, **dict(params, workspace_id=str(uuid4())))
    assert rebound['revision'] > grant['revision']
    with pytest.raises(PermissionError):
        authority.resolve(second)


def test_different_roots_keep_distinct_grants_and_unknown_agent_cannot_be_bound(setup):
    conn, root, params = setup
    first = grant_project(conn, **params)
    other = create_root(conn, actor=OWNER, request_id='other', name='Artist', purpose='Other music')
    second = grant_project(conn, **dict(params, agent_id=other['id']))
    assert first['id'] != second['id']
    authority = ReadAuthority(conn)
    assert authority.resolve(authority.issue_context(actor=OWNER, binding_id=second['id'])).agent_id == other['id']
    with pytest.raises(KeyError):
        grant_project(conn, **dict(params, agent_id=str(uuid4())))


@pytest.mark.parametrize('field,value', [('workspace_slug', '../outside'), ('workspace_slug', 'a/b'),
    ('workspace_slug', 'a?x=1'), ('workspace_id', 'not-a-uuid'), ('project_id', '../projects')])
def test_invalid_scope_identifiers_are_rejected(setup, field, value):
    conn, root, params = setup
    with pytest.raises(ValueError):
        grant_project(conn, **dict(params, **{field: value}))


def test_grants_survive_reopen_and_revocation_from_another_connection_is_observed(tmp_path):
    path = tmp_path / 'control.db'
    with connect_closing(path) as conn:
        root = create_root(conn, actor=OWNER, request_id='artist', name='Artist', purpose='Music')
        grant = grant_project(conn, actor=OWNER, agent_id=root['id'], workspace_slug='music',
                              workspace_id=str(uuid4()), project_id=str(uuid4()))
    with connect_closing(path) as reader_conn:
        authority = ReadAuthority(reader_conn)
        context = authority.issue_context(actor=OWNER, binding_id=grant['id'])
        assert authority.resolve(context).project_id == grant['project_id']
        with connect_closing(path) as owner_conn:
            revoke_project(owner_conn, actor=OWNER, binding_id=grant['id'])
        with pytest.raises(PermissionError):
            authority.resolve(context)
    with connect_closing(path) as conn:
        with pytest.raises(PermissionError):
            ReadAuthority(conn).issue_context(actor=OWNER, binding_id=grant['id'])


def test_concurrent_owner_grants_deduplicate_without_losing_identity(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    path = tmp_path / 'control.db'
    with connect_closing(path) as conn:
        root = create_root(conn, actor=OWNER, request_id='artist', name='Artist', purpose='Music')
    params = dict(actor=OWNER, agent_id=root['id'], workspace_slug='music',
                  workspace_id=str(uuid4()), project_id=str(uuid4()))

    def grant(_):
        with connect_closing(path) as conn:
            return grant_project(conn, **params)

    with ThreadPoolExecutor(max_workers=4) as workers:
        results = list(workers.map(grant, range(4)))
    assert len({x['id'] for x in results}) == 1
    assert all(x['revision'] == 1 for x in results)
