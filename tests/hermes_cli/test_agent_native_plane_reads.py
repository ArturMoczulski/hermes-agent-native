"""Real HTTP/SQLite scope boundary; no live Plane accounts or model services."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest

from agent_native.identity import OWNER, create_root, revise_soul
from agent_native.plane_access import ReadAuthority, grant_project, revoke_project
from agent_native.plane_reads import PlaneReads, PlaneReadError
from hermes_cli.kanban_db_connect import connect_closing


@pytest.fixture
def upstream():
    class Server(ThreadingHTTPServer):
        daemon_threads = True
        routes = {}
        requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlsplit(self.path)
            entry = (parsed.path, parse_qs(parsed.query), dict(self.headers))
            self.server.requests.append(entry)
            route = self.server.routes.get(parsed.path, (404, {}, {'error': 'not found'}))
            status, headers, payload = route(entry) if callable(route) else route
            body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            if 'Content-Length' not in headers:
                self.send_header('Content-Length', str(len(body)))
            for key, value in headers.items():
                if value is not None:
                    self.send_header(key, value)
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, *args):
            pass

    server = Server(('127.0.0.1', 0), Handler)
    server.routes = {}
    server.requests = []
    thread = Thread(target=server.serve_forever, kwargs={'poll_interval': 0.01}, daemon=True)
    thread.start()
    server.url = f'http://127.0.0.1:{server.server_port}'
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


@pytest.fixture
def scoped(tmp_path, upstream):
    with connect_closing(tmp_path / 'control.db') as conn:
        agent = create_root(conn, actor=OWNER, request_id='artist', name='Artist', purpose='Make music')
        workspace_id, project_id = str(uuid4()), str(uuid4())
        grant = grant_project(conn, actor=OWNER, agent_id=agent['id'], workspace_slug='test-workspace',
                              workspace_id=workspace_id, project_id=project_id)
        authority = ReadAuthority(conn)
        context = authority.issue_context(actor=OWNER, binding_id=grant['id'])
        reads = PlaneReads(authority, base_url=upstream.url, api_key='fixture-plane-secret', page_size=1)
        path = f'/api/v1/workspaces/test-workspace/projects/{project_id}/'
        yield conn, agent, grant, authority, context, reads, path, workspace_id, project_id


def project_record(scoped, **changes):
    return {'id': scoped[8], 'workspace': scoped[7], 'name': 'Music', 'identifier': 'MU',
            'description': 'Develop music', 'secret_extra': 'must-not-leave-service', **changes}


def test_project_read_uses_scoped_path_and_only_selected_metadata(scoped, upstream):
    _, _, _, _, context, reads, path, _, project_id = scoped
    upstream.routes[path] = (200, {}, project_record(scoped))
    result = reads.get_project(context)
    assert result['id'] == project_id
    assert result['name'] == 'Music'
    assert 'secret_extra' not in result
    assert upstream.requests[0][0] == path
    assert upstream.requests[0][2]['X-API-Key'] == 'fixture-plane-secret'
    assert 'fixture-plane-secret' not in repr(reads)


@pytest.mark.parametrize('context', [None, 'owner', {'actor': 'owner'}, object()])
def test_forged_context_does_not_reach_plane(scoped, upstream, context):
    with pytest.raises(PermissionError):
        scoped[5].get_project(context)
    assert upstream.requests == []


def item_record(scoped, **changes):
    return {'id': str(uuid4()), 'project': scoped[8], 'workspace': scoped[7],
            'name': 'Compose a demo', 'description_html': '<p>Write one song</p>',
            'state': str(uuid4()), 'priority': 'high', 'sequence_id': 1, **changes}


def page(records, next_cursor=None):
    return {'results': records, 'next_page_results': next_cursor is not None,
            'next_cursor': next_cursor, 'total_results': len(records)}


def test_list_items_reads_every_page_with_bound_path(scoped, upstream):
    context, reads, path = scoped[4:7]
    first, second = item_record(scoped), item_record(scoped, name='Record the demo')
    def route(entry):
        cursor = entry[1].get('cursor')
        return 200, {}, page([second]) if cursor else page([first], '1:1:0')
    upstream.routes[path + 'work-items/'] = route
    assert reads.list_work_items(context) == [first, second]
    assert [entry[0] for entry in upstream.requests] == [path + 'work-items/'] * 2
    assert upstream.requests[0][1] == {'per_page': ['1']}
    assert upstream.requests[1][1] == {'per_page': ['1'], 'cursor': ['1:1:0']}


def test_get_item_and_comments_are_bound_to_the_requested_item(scoped, upstream):
    _, _, _, _, context, reads, path, _, _ = scoped
    item = item_record(scoped)
    comment = {'id': str(uuid4()), 'workspace': scoped[7], 'project': scoped[8],
               'issue': item['id'], 'comment_html': '<p>Review the melody</p>',
               'actor': str(uuid4()), 'access': 'INTERNAL', 'private_extra': 'omit'}
    upstream.routes[path + f"work-items/{item['id']}/"] = 200, {}, item
    upstream.routes[path + f"work-items/{item['id']}/comments/"] = 200, {}, page([comment])
    assert reads.get_work_item(context, item['id']) == item
    result = reads.list_comments(context, item['id'])
    assert result[0]['issue'] == item['id']
    assert result[0]['comment_html'] == comment['comment_html']
    assert 'private_extra' not in result[0]


def test_attachments_return_metadata_without_download_or_storage_fields(scoped, upstream):
    _, _, _, _, context, reads, path, _, _ = scoped
    item = item_record(scoped)
    attachment = {'id': str(uuid4()), 'workspace': scoped[7], 'project': scoped[8],
                  'issue': item['id'], 'is_uploaded': True,
                  'attributes': {'name': 'song.wav', 'size': 142, 'type': 'audio/wav',
                                 'url': 'https://private.example/signed'},
                  'asset': 'uploads/private-key', 'storage_metadata': {'token': 'fixture-plane-secret'},
                  'asset_url': 'https://private.example/signed'}
    upstream.routes[path + f"work-items/{item['id']}/"] = 200, {}, item
    upstream.routes[path + f"work-items/{item['id']}/attachments/"] = 200, {}, [attachment]
    result = reads.list_attachments(context, item['id'])
    assert result == [{key: value for key, value in attachment.items()
                       if key in ('id', 'workspace', 'project', 'issue', 'is_uploaded')} |
                      {'attributes': {'name': 'song.wav', 'size': 142, 'type': 'audio/wav'}}]
    assert [entry[0] for entry in upstream.requests] == [path + f"work-items/{item['id']}/",
                                                        path + f"work-items/{item['id']}/attachments/"]


@pytest.mark.parametrize('method,suffix,fields', [
    ('list_cycles', 'cycles/', {'description': 'First outcome', 'start_date': None, 'end_date': None}),
    ('list_states', 'states/', {'group': 'started', 'color': '#abc123', 'sequence': 1000}),
])
def test_cycles_and_states_keep_planning_fields(scoped, upstream, method, suffix, fields):
    _, _, _, _, context, reads, path, _, _ = scoped
    record = {'id': str(uuid4()), 'workspace': scoped[7], 'project': scoped[8], 'name': 'First', **fields}
    upstream.routes[path + suffix] = 200, {}, page([record])
    assert getattr(reads, method)(context) == [record]


@pytest.mark.parametrize('change', [
    {'id': str(uuid4())}, {'workspace': str(uuid4())}, {'workspace': None},
])
def test_project_response_must_match_the_scope(scoped, upstream, change):
    _, _, _, _, context, reads, path, _, _ = scoped
    upstream.routes[path] = 200, {}, project_record(scoped, **change)
    with pytest.raises(PlaneReadError):
        reads.get_project(context)


@pytest.mark.parametrize('change', [
    {'project': str(uuid4())}, {'workspace': str(uuid4())}, {'id': 'not-a-uuid'},
])
def test_items_reject_wrong_or_missing_identity(scoped, upstream, change):
    _, _, _, _, context, reads, path, _, _ = scoped
    upstream.routes[path + 'work-items/'] = 200, {}, page([item_record(scoped, **change)])
    with pytest.raises(PlaneReadError):
        reads.list_work_items(context)


@pytest.mark.parametrize('method', ['get_work_item', 'list_comments', 'list_attachments'])
@pytest.mark.parametrize('item_id', ['../other', 'https://elsewhere.example/data', '', 42])
def test_item_ids_cannot_change_the_upstream_path(scoped, upstream, method, item_id):
    with pytest.raises(ValueError):
        getattr(scoped[5], method)(scoped[4], item_id)
    assert not upstream.requests


@pytest.mark.parametrize('method,suffix', [('list_comments', 'comments'), ('list_attachments', 'attachments')])
def test_nested_resources_reject_other_items(scoped, upstream, method, suffix):
    context, reads, path = scoped[4:7]
    item_id = str(uuid4())
    record = {'id': str(uuid4()), 'project': scoped[8], 'workspace': scoped[7], 'issue': str(uuid4())}
    upstream.routes[path + f'work-items/{item_id}/'] = 200, {}, item_record(scoped, id=item_id)
    payload = [record] if suffix == 'attachments' else page([record])
    upstream.routes[path + f'work-items/{item_id}/{suffix}/'] = 200, {}, payload
    with pytest.raises(PlaneReadError):
        getattr(reads, method)(context, item_id)


@pytest.mark.parametrize('change', ['revoke', 'soul'])
@pytest.mark.parametrize('during_request', [False, True])
def test_scope_is_rechecked_when_permission_changes(scoped, upstream, change, during_request):
    conn, agent, grant, _, context, reads, path, _, _ = scoped
    db_path = Path(conn.execute('PRAGMA database_list').fetchone()[2])
    def change_authority():
        with connect_closing(db_path) as other:
            if change == 'revoke':
                revoke_project(other, actor=OWNER, binding_id=grant['id'])
            else:
                revise_soul(other, actor=OWNER, agent_id=agent['id'], expected_revision=1, purpose='New purpose')
    def route(entry):
        change_authority()
        return 200, {}, page([item_record(scoped)], '1:1:0')
    upstream.routes[path + 'work-items/'] = route
    if not during_request:
        change_authority()
    with pytest.raises(PermissionError):
        reads.list_work_items(context)
    assert len(upstream.requests) == int(during_request)


@pytest.mark.parametrize('cursor', ['http://attacker.invalid/steal', '../escape', None, {}, 'secret\nheader'])
def test_untrusted_pagination_cannot_supply_paths_or_missing_cursors(scoped, upstream, cursor):
    context, reads, path = scoped[4:7]
    def route(entry):
        if len(upstream.requests) > 1:
            return 404, {}, {}
        return 200, {}, {'results': [item_record(scoped)], 'next_page_results': True, 'next_cursor': cursor}
    upstream.routes[path + 'work-items/'] = route
    with pytest.raises(PlaneReadError):
        reads.list_work_items(context)
    assert len(upstream.requests) == 1


def test_repeated_cursor_fails_without_returning_partial_results(scoped, upstream):
    context, reads, path = scoped[4:7]
    def route(entry):
        if len(upstream.requests) > 2:
            return 404, {}, {}
        return 200, {}, page([item_record(scoped)], '1:1:0')
    upstream.routes[path + 'work-items/'] = route
    with pytest.raises(PlaneReadError):
        reads.list_work_items(context)
    assert len(upstream.requests) == 2


def test_page_budget_fails_explicitly_instead_of_truncating(scoped, upstream, monkeypatch):
    import agent_native.plane_reads as module
    monkeypatch.setattr(module, 'MAX_PAGES', 2, raising=False)
    context, reads, path = scoped[4:7]
    def route(entry):
        n = len(upstream.requests)
        return (200, {}, page([item_record(scoped)], f'{n}:1:0')) if n <= 2 else (404, {}, {})
    upstream.routes[path + 'work-items/'] = route
    with pytest.raises(PlaneReadError):
        reads.list_work_items(context)
    assert len(upstream.requests) == 2


def test_body_budget_rejects_oversized_response(scoped, upstream, monkeypatch):
    import agent_native.plane_reads as module
    monkeypatch.setattr(module, 'MAX_BODY_BYTES', 256, raising=False)
    upstream.routes[scoped[6]] = 200, {}, project_record(scoped, description='x' * 1024)
    with pytest.raises(PlaneReadError):
        scoped[5].get_project(scoped[4])


@pytest.mark.parametrize('payload', [b'<html>bad</html>', b'{', b'null', {'name': {'asset_url': 'private'}}])
def test_malformed_resources_never_escape_as_unvalidated_objects(scoped, upstream, payload):
    upstream.routes[scoped[6]] = 200, {}, payload
    with pytest.raises(PlaneReadError):
        scoped[5].get_project(scoped[4])


def test_selected_fields_cannot_smuggle_nested_secret_objects(scoped, upstream):
    upstream.routes[scoped[6]] = 200, {}, project_record(scoped, name={'credential': 'fixture-plane-secret'})
    with pytest.raises(PlaneReadError):
        scoped[5].get_project(scoped[4])


@pytest.mark.parametrize('status', [301, 302, 307, 308, 401, 403, 404, 429, 503])
def test_errors_preserve_safe_status_without_following_redirects(scoped, upstream, status):
    context, reads, path = scoped[4:7]
    upstream.routes[path] = status, {'Location': upstream.url + '/steal', 'Retry-After': '59'}, {'error': 'fixture-plane-secret'}
    upstream.routes['/steal'] = 200, {}, project_record(scoped)
    with pytest.raises(PlaneReadError) as caught:
        reads.get_project(context)
    assert caught.value.status_code == status
    assert caught.value.retry_after == 59
    assert 'fixture-plane-secret' not in str(caught.value)
    assert caught.value.__suppress_context__
    assert len(upstream.requests) == 1


@pytest.mark.parametrize('url', [
    'http://user:pass@127.0.0.1:1', 'http://example.invalid', 'http://127.0.0.1:1/path',
    'http://127.0.0.1:1?secret=x', 'http://127.0.0.1:1#fragment', 'file:///etc/passwd',
])
def test_service_origin_cannot_include_credentials_or_ambiguous_routes(scoped, url):
    with pytest.raises(ValueError):
        PlaneReads(scoped[3], base_url=url, api_key='fixture-plane-secret')


@pytest.mark.parametrize('size', [0, -1, 101, True, '50'])
def test_page_size_is_a_bounded_integer(scoped, upstream, size):
    with pytest.raises(ValueError):
        PlaneReads(scoped[3], base_url=upstream.url, api_key='fixture-plane-secret', page_size=size)


@pytest.mark.parametrize('method,suffix', [('list_comments', 'comments'), ('list_attachments', 'attachments')])
def test_empty_nested_list_cannot_hide_an_inaccessible_parent(scoped, upstream, method, suffix):
    context, reads, path = scoped[4:7]
    item_id = str(uuid4())
    upstream.routes[path + f'work-items/{item_id}/'] = 404, {}, {'error': 'outside project'}
    upstream.routes[path + f'work-items/{item_id}/{suffix}/'] = 200, {}, [] if suffix == 'attachments' else page([])
    with pytest.raises(PlaneReadError) as caught:
        getattr(reads, method)(context, item_id)
    assert caught.value.status_code == 404
    assert [entry[0] for entry in upstream.requests] == [path + f'work-items/{item_id}/']


def test_stream_size_budget_does_not_trust_content_length(scoped, upstream, monkeypatch):
    import agent_native.plane_reads as module
    monkeypatch.setattr(module, 'MAX_BODY_BYTES', 256)
    upstream.routes[scoped[6]] = 200, {'Content-Length': None}, project_record(scoped, description='x' * 1024)
    with pytest.raises(PlaneReadError, match='budget'):
        scoped[5].get_project(scoped[4])


def test_aggregate_budget_rejects_many_small_pages(scoped, upstream, monkeypatch):
    import agent_native.plane_reads as module
    context, reads, path = scoped[4:7]
    record = item_record(scoped)
    body = page([record], '1:1:0')
    monkeypatch.setattr(module, 'MAX_TOTAL_BYTES', len(json.dumps(body).encode()) + 1)
    def route(entry):
        cursor = entry[1].get('cursor')
        return 200, {}, page([item_record(scoped)]) if cursor else body
    upstream.routes[path + 'work-items/'] = route
    with pytest.raises(PlaneReadError, match='budget'):
        reads.list_work_items(context)
    assert len(upstream.requests) == 2


def test_repeated_resource_between_pages_requires_refresh(scoped, upstream):
    context, reads, path = scoped[4:7]
    record = item_record(scoped)
    def route(entry):
        return 200, {}, page([record], None if entry[1].get('cursor') else '1:1:0')
    upstream.routes[path + 'work-items/'] = route
    with pytest.raises(PlaneReadError, match='repeated a resource'):
        reads.list_work_items(context)


def test_later_invalid_record_never_returns_partial_page(scoped, upstream):
    context, reads, path = scoped[4:7]
    records = [item_record(scoped), item_record(scoped, project=str(uuid4()))]
    upstream.routes[path + 'work-items/'] = 200, {}, page(records)
    with pytest.raises(PlaneReadError):
        reads.list_work_items(context)


def test_service_credential_does_not_follow_process_proxy_settings(scoped, upstream, monkeypatch):
    for name in ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy'):
        monkeypatch.setenv(name, 'http://127.0.0.1:9')
    monkeypatch.setenv('NO_PROXY', '')
    monkeypatch.setenv('no_proxy', '')
    upstream.routes[scoped[6]] = 200, {}, project_record(scoped)
    assert scoped[5].get_project(scoped[4])['id'] == scoped[8]


@pytest.mark.parametrize('retry', ['invalid secret', '-1', '9' * 200])
def test_untrusted_retry_metadata_is_not_echoed(scoped, upstream, retry):
    upstream.routes[scoped[6]] = 429, {'Retry-After': retry}, {'error': 'private'}
    with pytest.raises(PlaneReadError) as caught:
        scoped[5].get_project(scoped[4])
    assert caught.value.retry_after is None
    assert retry not in str(caught.value)


def test_retry_after_http_date_is_exposed_as_delay(scoped, upstream):
    from datetime import datetime, timezone, timedelta
    from email.utils import format_datetime
    value = format_datetime(datetime.now(timezone.utc) + timedelta(seconds=120), usegmt=True)
    upstream.routes[scoped[6]] = 429, {'Retry-After': value}, {}
    with pytest.raises(PlaneReadError) as caught:
        scoped[5].get_project(scoped[4])
    assert 115 <= caught.value.retry_after <= 120


def test_deleted_item_is_not_an_empty_or_recreated_result(scoped, upstream):
    item_id = str(uuid4())
    upstream.routes[scoped[6] + f'work-items/{item_id}/'] = 404, {}, {'error': 'gone'}
    with pytest.raises(PlaneReadError) as caught:
        scoped[5].get_work_item(scoped[4], item_id)
    assert caught.value.status_code == 404
    assert len(upstream.requests) == 1
