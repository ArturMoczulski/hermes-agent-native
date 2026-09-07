"""Owner planning inspection through real HTTP, protected setup and SQLite."""
from datetime import datetime, timezone
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from agent_native.identity import OWNER, get_root, revise_soul
from agent_native.startup import prepare
from hermes_cli.kanban_db_connect import connect_closing
from tests.hermes_cli.test_agent_native_api import client, URL, BODY  # noqa: F401
from tests.hermes_cli.writer_plane_fixture import writer_plane_server


@pytest.fixture
def prepared(client, tmp_path):
    with writer_plane_server() as plane:
        agent = client.post(URL, json=BODY).json()
        home = tmp_path / 'home' / 'agent-native'
        home.mkdir(parents=True, mode=0o700, exist_ok=True)
        home.chmod(0o700)
        config = home / 'plane-setup.json'
        config.write_text(json.dumps(plane.config))
        config.chmod(0o600)
        with connect_closing(board='default') as conn:
            prepare(conn, actor=OWNER, agent_id=agent['id'], home=home)
            root = get_root(conn, actor=OWNER, agent_id=agent['id'])
        assert root['setup']['status'] == 'ready'
        yield SimpleNamespace(client=client, plane=plane, root=root, home=home, config=config,
                              path=URL+'/'+root['id']+'/planning')


def storage_snapshot():
    """A dashboard read may neither install permissions nor start or alter work."""
    with connect_closing(board='default') as conn:
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                  if r[0].startswith('agent_native_')]
        return {table: conn.execute('SELECT * FROM '+table+' ORDER BY rowid').fetchall() for table in tables}


@pytest.mark.parametrize('paused', [False, True])
def test_owner_reads_ready_planning_without_grant_or_execution_mutations(prepared, paused):
    s = prepared
    if paused:
        from agent_native.work_state import configure, request_pause
        from agent_native.writer_planning import install_grants
        from agent_native.plane_access import revoke_project
        with connect_closing(board='default') as conn:
            configure(conn, actor=OWNER, agent_id=s.root['id'], expected_revision=1,
                      limits={'timeout_seconds': 30, 'max_iterations': 2})
            request_pause(conn, actor=OWNER, agent_id=s.root['id'])
            binding = install_grants(conn, actor=OWNER, agent_id=s.root['id'])
            revoke_project(conn, actor=OWNER, binding_id=binding)
    before, count = storage_snapshot(), len(s.plane.requests)
    start = datetime.now(timezone.utc)
    response = s.client.get(s.path)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['agent_id'] == s.root['id']
    assert data['soul_revision'] == s.root['soul_revision']
    assert data['setup_activation_id'] == s.root['setup']['activation_id']
    assert data['project']['id'] == s.root['setup']['project_id']
    assert data['items'][0]['id'] == s.root['setup']['discovery_item_id']
    assert data['cycles'] == [] and data['states'][0]['group'] == 'backlog'
    assert data['plane_origin'] == s.plane.config['base_url']
    assert data['workspace_slug'] == s.root['setup']['workspace_slug']
    assert start <= datetime.fromisoformat(data['observed_at']) <= datetime.now(timezone.utc)
    assert storage_snapshot() == before
    requests = s.plane.requests[count:]
    assert all(r['method'] == 'GET' for r in requests)
    assert len(requests) == 5  # Principal + four inventories, no duplicate discovery read.
    assert 'fixture-api-key' not in response.text and 'fixture-password' not in response.text
    s.plane.items[data['items'][0]['id']]['description_html'] = '<p>Acceptance: revised by the owner.</p>'
    second = s.client.get(s.path).json()
    assert second['items'][0]['description_html'] == '<p>Acceptance: revised by the owner.</p>'
    assert second['observed_at'] >= data['observed_at']


def test_owner_authentication_precedes_any_plane_read(prepared):
    s = prepared
    before = len(s.plane.requests)
    s.client.headers.pop('X-Hermes-Session-Token')
    assert s.client.get(s.path).status_code == 401
    assert len(s.plane.requests) == before


def test_missing_agent_and_not_ready_setup_are_distinct(client):
    assert client.get(URL+'/missing/planning').status_code == 404
    root = client.post(URL, json=BODY).json()
    result = client.get(URL+'/'+root['id']+'/planning')
    assert result.status_code == 409
    assert result.json()['detail'] == 'Planning setup is not ready'


@pytest.mark.parametrize('change', ['configuration', 'invalid_api_key', 'principal', 'foreign_project', 'foreign_item'])
def test_untrusted_configuration_or_foreign_resources_never_leave_scope(prepared, change):
    s = prepared
    base = '/api/v1/workspaces/'+s.root['setup']['workspace_slug']+'/projects/'+s.root['setup']['project_id']+'/'
    expected = 403
    if change == 'configuration':
        s.config.chmod(0o644)
        expected = 409
    elif change == 'invalid_api_key':
        config = json.loads(s.config.read_text())
        config['api_key'] = 'invalid key'
        s.config.write_text(json.dumps(config))
        expected = 409
    elif change == 'principal':
        s.plane.overrides['GET', '/api/v1/users/me/'] = lambda _: (200, {}, {'id': str(uuid4())})
    elif change == 'foreign_project':
        s.plane.overrides['GET', base] = lambda _: (200, {}, {**s.plane.projects[s.root['setup']['project_id']], 'workspace': str(uuid4())})
    else:
        item = dict(s.plane.items[s.root['setup']['discovery_item_id']], project=str(uuid4()), description_html='PRIVATE FOREIGN CONTENT')
        s.plane.overrides['GET', base+'work-items/'] = lambda _: (200, {}, {'results': [item], 'next_page_results': False})
    before = len(s.plane.requests)
    response = s.client.get(s.path)
    assert response.status_code == expected, response.text
    assert 'fixture-api-key' not in response.text and 'PRIVATE FOREIGN CONTENT' not in response.text
    if change in ('configuration', 'invalid_api_key'):
        assert response.json()['detail'] == 'Planning connection is not configured'
        assert len(s.plane.requests) == before


def test_purpose_change_during_read_revokes_snapshot(prepared):
    s = prepared
    path = '/api/v1/workspaces/'+s.root['setup']['workspace_slug']+'/projects/'+s.root['setup']['project_id']+'/'
    def revise(_):
        with connect_closing(board='default') as conn:
            revise_soul(conn, actor=OWNER, agent_id=s.root['id'], expected_revision=1, purpose='A revised purpose')
        return 200, {}, s.plane.projects[s.root['setup']['project_id']]
    s.plane.overrides['GET', path] = revise
    response = s.client.get(s.path)
    assert response.status_code == 403, response.text
    assert 'project' not in response.json()


def test_plane_outage_is_not_reported_as_an_empty_fresh_project(prepared):
    s = prepared
    path = '/api/v1/workspaces/'+s.root['setup']['workspace_slug']+'/projects/'+s.root['setup']['project_id']+'/'
    s.plane.overrides['GET', path] = lambda _: (503, {}, {'error': 'UPSTREAM PRIVATE BODY'})
    response = s.client.get(s.path)
    assert response.status_code == 503, response.text
    assert response.json()['detail'] == 'Plane planning data is unavailable'
    assert 'UPSTREAM PRIVATE BODY' not in response.text
    assert 'observed_at' not in response.json()
