"""Stateful external Plane HTTP fixture for setup followed by writer planning."""
from contextlib import contextmanager
from uuid import uuid4

from tests.hermes_cli.test_agent_native_plane_setup import plane_server


def _page(values):
    values = list(values)
    return {'results': values, 'next_page_results': False, 'next_cursor': None,
            'total_results': len(values)}


def _route(server, request):
    path, method, body = request['path'], request['method'], request['body']
    parts = path.strip('/').split('/')
    if parts[:3] != ['api', 'v1', 'workspaces'] or len(parts) < 6:
        return None
    assert request['headers'].get('X-API-Key') == 'fixture-api-key'
    assert not request['headers'].get('Cookie')
    workspace = server.workspaces.get(parts[3])
    project = server.projects.get(parts[5])
    if workspace is None or project is None or project['workspace'] != workspace['id']:
        return 404, {}, {}
    pid = project['id']
    common = {'workspace': workspace['id'], 'project': pid}
    if pid not in server.states:
        server.states[pid] = [{'id': str(uuid4()), **common, 'name': 'Backlog',
                               'group': 'backlog', 'default': True},
                              {'id': str(uuid4()), **common, 'name': 'Done',
                               'group': 'completed', 'default': False}]
    if len(parts) == 6:
        if method == 'PATCH':
            project.update(body, updated_at=str(uuid4()), updated_by=server.user)
            return 200, {}, project
        return None
    resource = parts[6]
    if resource == 'cycles' and method == 'GET' and getattr(server, 'temporary_read_outage', False):
        server.temporary_read_outage = False
        return 503, {'Retry-After':'2'}, {'error':'Temporary fixture outage'}
    if resource == 'states' and len(parts) == 7 and method == 'GET':
        return 200, {}, _page(server.states[pid])
    if resource in ('archived-issues', 'archived-cycles') and method == 'GET':
        return 200, {}, _page([])
    if resource not in ('work-items', 'cycles'):
        return None
    inventory = server.items if resource == 'work-items' else server.cycles
    if len(parts) == 7:
        if method == 'GET':
            records = [v for v in inventory.values() if v['project'] == pid]
            if 'external_id' in request['query']:
                records = [v for v in records if v.get('external_id') == request['query']['external_id'][0]
                           and v.get('external_source') == request['query']['external_source'][0]]
                return (200, {}, records[0]) if len(records) == 1 else (404, {}, {})
            return 200, {}, _page(records)
        if method == 'POST':
            value = {'id': str(uuid4()), **common, 'updated_at': str(uuid4()),
                     'created_by': server.user, **body}
            if resource == 'work-items':
                value.setdefault('state', server.states[pid][0]['id'])
                value.setdefault('priority', 'none')
                value.setdefault('sequence_id', len(server.items) + 1)
            else:
                value.setdefault('owned_by', server.user)
            inventory[value['id']] = value
            return 201, {}, value
    rid = parts[7]
    value = inventory.get(rid)
    if value is None or value['project'] != pid:
        return 404, {}, {}
    if len(parts) == 8:
        if method == 'PATCH':
            value.update(body, updated_at=str(uuid4()), updated_by=server.user)
        return 200, {}, value
    tail = parts[8]
    if resource == 'work-items' and tail == 'comments':
        if method == 'POST':
            comment = {'id': str(uuid4()), **common, 'issue': rid,
                       'actor': server.user, 'created_by': server.user, **body}
            server.comments[comment['id']] = comment
            return 201, {}, comment
        return 200, {}, _page(c for c in server.comments.values() if c['issue'] == rid)
    if resource == 'work-items' and tail == 'relations':
        related = server.dependencies.setdefault(rid, set())
        if method == 'POST':
            related.update(body['issues'])
            return 201, {}, [{'id': other, 'project_id': pid, 'relation_type': 'blocked_by'}
                             for other in body['issues']]
        return 200, {}, {'blocked_by': [{'issue_id': other, 'project_id': pid}
                                       for other in sorted(related)]}
    if resource == 'cycles' and tail == 'cycle-issues':
        if method == 'POST':
            result = []
            for iid in body['issues']:
                member = {'id': str(uuid4()), **common, 'issue': iid, 'cycle': rid}
                server.memberships[iid] = member
                result.append(member)
            return 200, {}, [m for m in server.memberships.values() if m['cycle']==rid]
        iid = parts[9]
        member = server.memberships.get(iid)
        if member is None or member['cycle'] != rid:
            return 404, {}, {}
        if method == 'DELETE':
            del server.memberships[iid]
            return 204, {}, b''
        return 200, {}, member
    return 404, {}, {}


@contextmanager
def writer_plane_server():
    with plane_server(extension=_route) as server:
        server.cycles, server.states, server.comments = {}, {}, {}
        server.memberships, server.dependencies = {}, {}
        yield server
