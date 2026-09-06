"""Real loopback HTTP provisioning contracts; no live Plane account or model."""
from contextlib import contextmanager
import json
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest

from agent_native.plane_setup import PlaneSetup, SetupError


@contextmanager
def plane_server():
    class Handler(BaseHTTPRequestHandler):
        def handle_request(self):
            parsed = urlsplit(self.path)
            raw = self.rfile.read(int(self.headers.get('Content-Length', 0)))
            body = (parse_qs(raw.decode()) if 'application/x-www-form-urlencoded' in
                    self.headers.get('Content-Type', '') else json.loads(raw or b'{}'))
            request = {'method': self.command, 'path': parsed.path,
                       'query': parse_qs(parsed.query), 'headers': dict(self.headers), 'body': body}
            server.requests.append(request)
            key = self.command, parsed.path
            if key in server.overrides:
                status, headers, payload = server.overrides[key](request)
            else:
                status, headers, payload = route(request)
            if key in server.lose:
                server.lose.remove(key)
                self.connection.shutdown(socket.SHUT_RDWR)
                self.connection.close()
                return
            data = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
            self.send_response(status)
            for name, value in {'Content-Length': str(len(data)), **headers}.items():
                self.send_header(name, value)
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

        do_GET = do_POST = do_PATCH = handle_request

        def log_message(self, *args):
            pass

    def route(r):
        path, method, body = r['path'], r['method'], r['body']
        if path == '/auth/get-csrf-token/':
            return 200, {'Set-Cookie': 'csrftoken=fixture; Path=/'}, {'csrf_token': 'fixture'}
        if path == '/auth/sign-in/':
            assert body == {'email': ['host@fixture.test'], 'password': ['fixture-password']}
            assert r['headers']['X-CSRFToken'] == 'fixture'
            assert r['headers']['Origin'] == server.url
            return 302, {'Set-Cookie': 'session=fixture; Path=/', 'Location': '/home'}, b''
        api = path.startswith('/api/v1/')
        if api:
            assert r['headers'].get('X-API-Key') == 'fixture-api-key'
            assert not r['headers'].get('Cookie')
        else:
            assert 'session=fixture' in r['headers'].get('Cookie', '')
            assert 'X-API-Key' not in r['headers']
        if path in ('/api/users/me/', '/api/v1/users/me/'):
            return 200, {}, {'id': server.user}
        if path == '/api/workspaces/' and method == 'POST':
            if body['slug'] in server.workspaces:
                return 409, {}, {'error': 'already exists'}
            value = {'id': str(uuid4()), 'owner': server.user, **body}
            server.workspaces[body['slug']] = value
            # Real Plane creates a sample project; it must not become our project.
            seed = {'id': str(uuid4()), 'workspace': value['id'], 'network': 2,
                    'name': body['name'], 'identifier': body['name'][:5].upper(),
                    'external_source': None, 'external_id': None}
            server.projects[seed['id']] = seed
            return 201, {}, value
        pieces = path.strip('/').split('/')
        if pieces[:2] == ['api', 'workspaces'] and len(pieces) == 3:
            value = server.workspaces.get(pieces[2])
            return (200, {}, value) if value else (404, {}, {})
        if pieces[:3] == ['api', 'v1', 'workspaces']:
            slug = pieces[3]
            workspace = server.workspaces[slug]
            if len(pieces) == 5:
                if method == 'GET':
                    projects = [p for p in server.projects.values() if p['workspace'] == workspace['id']]
                    return 200, {}, {'results': projects, 'next_page_results': False,
                                     'total_results': len(projects)}
                assert method == 'POST'
                assert 'network' not in body  # The installed API silently ignores it.
                value = {'id': str(uuid4()), 'workspace': workspace['id'], 'network': 2, **body}
                server.projects[value['id']] = value
                return 201, {}, value
            project = server.projects.get(pieces[5])
            if project is None:
                return 404, {}, {}
            if len(pieces) == 6:
                return 200, {}, project
            if len(pieces) == 7 and pieces[6] == 'work-items':
                if method == 'GET':
                    matches = [v for v in server.items.values() if v['project'] == project['id']
                               and v['external_source'] == r['query']['external_source'][0]
                               and v['external_id'] == r['query']['external_id'][0]]
                    if len(matches) != 1:
                        return (404 if not matches else 500), {}, {}
                    return 200, {}, matches[0]
                assert method == 'POST'
                value = {'id': str(uuid4()), 'workspace': workspace['id'],
                         'project': project['id'], **body}
                server.items[value['id']] = value
                return 201, {}, value
            return 200, {}, server.items[pieces[7]]
        if pieces[:2] == ['api', 'workspaces'] and len(pieces) == 5:
            project = server.projects[pieces[4]]
            if method == 'PATCH':
                assert body == {'network': 0}
                project.update(body)
            return 200, {}, project
        raise AssertionError(f'Unexpected fixture request: {method} {path}')

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.daemon_threads = True
    server.url = f'http://127.0.0.1:{server.server_port}'
    server.user, server.agent, server.activation = (str(uuid4()) for _ in range(3))
    server.user_id = server.user
    server.requests, server.workspaces, server.projects, server.items = [], {}, {}, {}
    server.overrides, server.lose = {}, set()
    server.config = dict(base_url=server.url, email='host@fixture.test',
                         password='fixture-password', api_key='fixture-api-key',
                         expected_user_id=server.user)
    thread = Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


@pytest.fixture
def plane():
    with plane_server() as server:
        yield server


def setup_all(plane, *, allow_create=True):
    with PlaneSetup(**plane.config) as client:
        workspace = client.ensure_workspace(plane.agent, 'Fantasy writer', allow_create=allow_create)
        project = client.ensure_project(plane.agent, workspace['slug'], allow_create=allow_create)
        item = client.ensure_discovery(plane.agent, plane.activation, 'Write <fantasy> & stories',
                                      workspace['slug'], project['id'], allow_create=allow_create)
    return workspace, project, item


def mutations(plane):
    return [r for r in plane.requests if r['method'] != 'GET' and r['path'].startswith('/api/')]


def test_setup_creates_private_scoped_planning_home_and_reuses_it(plane):
    first = setup_all(plane)
    writes = len(mutations(plane))
    assert setup_all(plane, allow_create=False) == first
    assert len(mutations(plane)) == writes
    workspace, project, item = first
    assert workspace['slug'] == 'an-' + plane.agent.replace('-', '')
    assert len(plane.projects) == 2  # One framework project and Plane's untouched sample.
    saved_project = plane.projects[project['id']]
    assert saved_project['network'] == 0
    assert saved_project['workspace'] == workspace['id']
    assert plane.items[item['id']]['project'] == project['id']
    assert '&lt;fantasy&gt; &amp; stories' in plane.items[item['id']]['description_html']
    assert all('password' not in str(value) and 'fixture-api-key' not in str(value) for value in first)


@pytest.mark.parametrize('stage', ['workspace', 'project', 'privacy', 'discovery'])
def test_lost_success_is_reconciled_by_fresh_client_without_mutation_replay(plane, stage):
    slug = 'an-' + plane.agent.replace('-', '')
    with PlaneSetup(**plane.config) as client:
        workspace = None if stage == 'workspace' else client.ensure_workspace(plane.agent, 'Fantasy writer')
        project = None if stage in ('workspace', 'project', 'privacy') else client.ensure_project(plane.agent, slug)
        path = {'workspace': '/api/workspaces/',
                'project': f'/api/v1/workspaces/{slug}/projects/',
                'discovery': f'/api/v1/workspaces/{slug}/projects/{project["id"]}/work-items/' if project else ''}
        if stage == 'privacy':
            # Observe the privacy PATCH through the fixture before dropping its response.
            original = plane.projects.copy()
            def lose_patch(r):
                value = {'id': str(uuid4()), 'workspace': workspace['id'], 'network': 2, **r['body']}
                plane.projects[value['id']] = value
                plane.lose.add(('PATCH', f'/api/workspaces/{slug}/projects/{value["id"]}/'))
                return 201, {}, value
            plane.overrides['POST', f'/api/v1/workspaces/{slug}/projects/'] = lose_patch
            assert original
        else:
            plane.lose.add(('POST', path[stage]))
        with pytest.raises(SetupError) as failed:
            if stage == 'workspace':
                client.ensure_workspace(plane.agent, 'Fantasy writer')
            elif stage in ('project', 'privacy'):
                client.ensure_project(plane.agent, slug)
            else:
                client.ensure_discovery(plane.agent, plane.activation, 'Write <fantasy> & stories', slug, project['id'])
        assert failed.value.uncertain
    writes = len(mutations(plane))
    with PlaneSetup(**plane.config) as resumed:
        if stage == 'workspace':
            resumed.ensure_workspace(plane.agent, 'Fantasy writer', allow_create=False)
        elif stage in ('project', 'privacy'):
            resumed.ensure_project(plane.agent, slug, allow_create=False)
        else:
            resumed.ensure_discovery(plane.agent, plane.activation, 'Write <fantasy> & stories', slug,
                                     project['id'], allow_create=False)
    remaining = mutations(plane)[writes:]
    assert not any(r['method'] == 'POST' for r in remaining)
    if stage == 'project':
        assert len(remaining) == 1 and remaining[0]['body'] == {'network': 0}
    else:
        assert remaining == []


@pytest.mark.parametrize('stage', ['workspace', 'project', 'discovery'])
def test_missing_resource_cannot_be_created_during_reconciliation(plane, stage):
    with PlaneSetup(**plane.config) as client:
        slug = 'an-' + plane.agent.replace('-', '')
        if stage != 'workspace':
            client.ensure_workspace(plane.agent, 'Fantasy writer')
        project = client.ensure_project(plane.agent, slug) if stage == 'discovery' else None
        writes = len(mutations(plane))
        with pytest.raises(SetupError):
            if stage == 'workspace':
                client.ensure_workspace(plane.agent, 'Fantasy writer', allow_create=False)
            elif stage == 'project':
                client.ensure_project(plane.agent, slug, allow_create=False)
            else:
                client.ensure_discovery(plane.agent, plane.activation, 'Write', slug,
                                        project['id'], allow_create=False)
        assert len(mutations(plane)) == writes


@pytest.mark.parametrize('path', ['/api/users/me/', '/api/v1/users/me/'])
def test_both_credential_principals_must_match_configured_host(plane, path):
    plane.overrides['GET', path] = lambda r: (200, {}, {'id': str(uuid4())})
    with pytest.raises(SetupError) as failed:
        with PlaneSetup(**plane.config):
            pytest.fail('Mismatched authority was accepted')
    assert not failed.value.uncertain
    assert mutations(plane) == []


@pytest.mark.parametrize('status,uncertain', [(400, False), (401, False), (403, False),
                                             (429, False), (500, True), (503, True)])
def test_creation_failure_is_safe_and_reports_effect_uncertainty(plane, status, uncertain):
    plane.overrides['POST', '/api/workspaces/'] = lambda r: (
        status, {'Retry-After': '7'}, {'password': 'fixture-password', 'error': 'fixture-api-key'})
    with PlaneSetup(**plane.config) as client:
        with pytest.raises(SetupError) as failed:
            client.ensure_workspace(plane.agent, 'Fantasy writer')
    assert failed.value.uncertain is uncertain
    assert failed.value.status == status
    assert failed.value.retry_after == 7
    assert len(mutations(plane)) == 1
    assert 'fixture-password' not in str(failed.value)
    assert 'fixture-api-key' not in str(failed.value)


@pytest.mark.parametrize('response', ['redirect', 'oversized', 'malformed', 'encoded'])
def test_untrusted_read_response_is_rejected_without_followups_or_mutation(plane, response):
    slug = 'an-' + plane.agent.replace('-', '')
    routes = {
        'redirect': (302, {'Location': plane.url + '/credential-trap'}, b''),
        'oversized': (200, {'Content-Length': str(2 * 1024 * 1024)}, b'{}'),
        'malformed': (200, {}, b'private upstream error fixture-password'),
        'encoded': (200, {'Content-Encoding': 'gzip'}, b'{}'),
    }
    plane.overrides['GET', f'/api/workspaces/{slug}/'] = lambda r: routes[response]
    with PlaneSetup(**plane.config) as client:
        with pytest.raises(SetupError) as failed:
            client.ensure_workspace(plane.agent, 'Fantasy writer')
    assert not failed.value.uncertain
    assert mutations(plane) == []
    assert not any(r['path'] == '/credential-trap' for r in plane.requests)
    assert 'fixture-password' not in str(failed.value)


def test_workspace_owner_mismatch_blocks_setup(plane):
    first, _, _ = setup_all(plane)
    plane.workspaces[first['slug']]['owner'] = str(uuid4())
    writes = len(mutations(plane))
    with PlaneSetup(**plane.config) as client:
        with pytest.raises(SetupError):
            client.ensure_workspace(plane.agent, 'Fantasy writer')
    assert len(mutations(plane)) == writes


def test_changed_workspace_identity_after_success_is_unresolved(plane):
    slug = 'an-' + plane.agent.replace('-', '')
    def created(r):
        value = {'id': str(uuid4()), 'owner': plane.user, **r['body']}
        plane.workspaces[slug] = {**value, 'id': str(uuid4())}
        return 201, {}, value
    plane.overrides['POST', '/api/workspaces/'] = created
    with PlaneSetup(**plane.config) as client:
        with pytest.raises(SetupError) as failed:
            client.ensure_workspace(plane.agent, 'Fantasy writer')
    assert failed.value.uncertain


@pytest.mark.parametrize('field,value', [('workspace', 'uuid'), ('external_id', 'uuid'),
                                        ('external_source', 'another-system'), ('identifier', 'FOREIGN'),
                                        ('name', 'Unrelated project')])
def test_project_collision_never_adopts_foreign_resource_or_changes_privacy(plane, field, value):
    workspace, project, _ = setup_all(plane)
    plane.projects[project['id']][field] = str(uuid4()) if value == 'uuid' else value
    plane.projects[project['id']]['network'] = 2
    if field == 'workspace':
        plane.overrides['GET', f'/api/v1/workspaces/{workspace["slug"]}/projects/'] = lambda r: (
            200, {}, {'results': list(plane.projects.values()), 'next_page_results': False})
    writes = len(mutations(plane))
    with PlaneSetup(**plane.config) as client:
        with pytest.raises(SetupError):
            client.ensure_project(plane.agent, workspace['slug'])
    assert len(mutations(plane)) == writes


def test_duplicate_project_markers_are_unresolved(plane):
    workspace, project, _ = setup_all(plane)
    copy = {**plane.projects[project['id']], 'id': str(uuid4()), 'name': 'Extra', 'identifier': 'EXTRA'}
    plane.projects[copy['id']] = copy
    writes = len(mutations(plane))
    with PlaneSetup(**plane.config) as client:
        with pytest.raises(SetupError):
            client.ensure_project(plane.agent, workspace['slug'])
    assert len(mutations(plane)) == writes


@pytest.mark.parametrize('fault', ['repeated', 'missing', 'cursor'])
def test_project_reconciliation_rejects_incomplete_or_repeated_inventory(plane, fault):
    workspace, project, _ = setup_all(plane)
    values = list(plane.projects.values())
    def inventory(r):
        if fault == 'missing':
            return 200, {}, {'results': values[:1], 'next_page_results': False, 'total_results': 2}
        return 200, {}, {'results': values[:1], 'next_page_results': True,
                         'next_cursor': '/unsafe' if fault == 'cursor' else 'page-2'}
    plane.overrides['GET', f'/api/v1/workspaces/{workspace["slug"]}/projects/'] = inventory
    writes = len(mutations(plane))
    with PlaneSetup(**plane.config) as client:
        with pytest.raises(SetupError):
            client.ensure_project(plane.agent, workspace['slug'])
    assert len(mutations(plane)) == writes


@pytest.mark.parametrize('field,value', [('project', 'uuid'), ('workspace', 'uuid'),
                                        ('name', 'Different work'), ('description_html', '<p>Changed purpose</p>')])
def test_discovery_reconciliation_does_not_accept_changed_work(plane, field, value):
    workspace, project, item = setup_all(plane)
    plane.items[item['id']][field] = str(uuid4()) if value == 'uuid' else value
    writes = len(mutations(plane))
    with PlaneSetup(**plane.config) as client:
        with pytest.raises(SetupError):
            client.ensure_discovery(plane.agent, plane.activation, 'Write <fantasy> & stories',
                                    workspace['slug'], project['id'], allow_create=False)
    assert len(mutations(plane)) == writes


def test_cross_root_project_is_rejected_before_item_access(plane):
    workspace, project, _ = setup_all(plane)
    before = len(plane.requests)
    with PlaneSetup(**plane.config) as client:
        with pytest.raises(ValueError):
            client.ensure_project(str(uuid4()), workspace['slug'])
    assert all(r['path'] in ('/auth/get-csrf-token/', '/auth/sign-in/', '/api/users/me/',
                             '/api/v1/users/me/') for r in plane.requests[before:])


def test_missing_confirmed_project_is_not_recreated_in_reconciliation(plane):
    workspace, project, _ = setup_all(plane)
    del plane.projects[project['id']]
    writes = len(mutations(plane))
    with PlaneSetup(**plane.config) as client:
        with pytest.raises(SetupError):
            client.ensure_project(plane.agent, workspace['slug'], allow_create=False)
    assert len(mutations(plane)) == writes


def test_host_guard_can_veto_mutation_after_preflight_lookup(plane):
    class Stopped(RuntimeError):
        pass
    slug = 'an-' + plane.agent.replace('-', '')
    enabled = True
    def stop_during_lookup(r):
        nonlocal enabled
        enabled = False
        return 404, {}, {}
    plane.overrides['GET', f'/api/workspaces/{slug}/'] = stop_during_lookup
    with PlaneSetup(**plane.config) as client:
        def guard():
            if not enabled:
                raise Stopped('Host shutdown')
        client.before_write = guard
        with pytest.raises(Stopped):
            client.ensure_workspace(plane.agent, 'Fantasy writer')
    assert mutations(plane) == []
