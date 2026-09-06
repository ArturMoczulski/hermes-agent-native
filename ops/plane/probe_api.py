"""Explicit local Plane contract probe; creates and removes its own workspace/users.

Run with the repository Python environment. No owner/Builder credential is read.
A private recovery manifest is written before mutations. This characterizes an
installed upstream API; it is not the managed-agent authorization test suite.
"""
import argparse
import json
import secrets
from pathlib import Path
from urllib.parse import urlparse

import requests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    base = args.base_url.rstrip('/')
    parsed = urlparse(base)
    if parsed.hostname not in ('localhost', '127.0.0.1') or parsed.scheme != 'http':
        raise SystemExit('This probe only supports an explicitly selected local HTTP instance')
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=False)
    out.chmod(0o700)
    report = {'base_url': base, 'observations': {}, 'cleanup': []}
    manifest = {'slug': 'api-probe-' + secrets.token_hex(5), 'accounts': []}
    def save():
        for filename, value in [('manifest.json', manifest), ('report.json', report)]:
            f = out / filename
            f.write_text(json.dumps(value, indent=2) + '\n')
            f.chmod(0o600)
    save()
    def call(s, method, path, body=None, expected=(200, 201, 204), headers=None):
        r = s.request(method, base + path, json=body, headers=headers, timeout=30)
        if r.status_code not in expected:
            raise RuntimeError(f'{method} {path}: {r.status_code}; {r.text[:250]}')
        return r
    def csrf(s):
        s.headers['X-CSRFToken'] = call(s, 'GET', '/auth/get-csrf-token/').json()['csrf_token']
    sessions = []
    workspace_created = False
    try:
        instance = requests.get(base + '/api/instances/', timeout=15).json()
        if instance['config'].get('is_smtp_configured'):
            raise RuntimeError('Probe requires local SMTP to be unconfigured')
        for role in ['admin', 'member']:
            account = {'email': manifest['slug'] + '-' + role + '@agent-native.test', 'password': secrets.token_urlsafe(32)}
            manifest['accounts'].append(account)
            save()
            sess = requests.Session()
            sess.headers.update({'Origin': base, 'Referer': base + '/'})
            csrf(sess)
            response = sess.post(base + '/auth/sign-up/', data=account, allow_redirects=False, timeout=30)
            if response.status_code != 302 or 'error' in response.headers.get('Location', ''):
                raise RuntimeError('Probe account signup failed; inspect private manifest before retrying')
            sessions.append(sess)
            csrf(sess)
            account['id'] = call(sess, 'GET', '/api/users/me/').json()['id']
            token = call(sess, 'POST', '/api/users/api-tokens/', {'label': manifest['slug']}).json()
            account['token_id'] = token['id']
            account['api_key'] = token.get('api_key') or token['token']
            save()
        admin, member = sessions
        csrf(admin)
        ws = call(admin, 'POST', '/api/workspaces/', {'name': manifest['slug'], 'slug': manifest['slug']}).json()
        workspace_created = True
        manifest['workspace_id'] = ws['id']
        save()
        path = '/api/workspaces/' + manifest['slug'] + '/'
        call(admin, 'POST', path + 'invitations/', {'emails': [{'email': manifest['accounts'][1]['email'], 'role': 15}]})
        csrf(member)
        invitations = call(member, 'GET', '/api/users/me/workspaces/invitations/').json()
        if isinstance(invitations, dict): invitations = invitations['results']
        call(member, 'POST', '/api/users/me/workspaces/invitations/', {'invitations': [i['id'] for i in invitations]})
        a, m = requests.Session(), requests.Session()
        for sess, account in zip([a, m], manifest['accounts']): sess.headers['X-API-Key'] = account['api_key']
        v1 = '/api/v1/workspaces/' + manifest['slug'] + '/projects/'
        project = call(a, 'POST', v1, {'name': 'Disposable API probe', 'identifier': 'PROBE', 'cycle_view': True}).json()
        manifest['project_id'] = project['id']; save()
        pp = v1 + project['id'] + '/'
        csrf(admin)
        visibility = call(admin, 'PATCH', path + 'projects/' + project['id'] + '/', {'network': 0}).json()
        assert visibility['network'] == 0
        items = []
        for number in range(3):
            items.append(call(a, 'POST', pp + 'work-items/', {'name': f'Probe {number}', 'external_source': manifest['slug'], 'external_id': str(number)}).json())
        manifest['items'] = [x['id'] for x in items]; save()
        # Separate pages must represent the same durable set without duplicates.
        pages, ids, cursor = 0, [], None
        while True:
            suffix = '?per_page=1' + ('&cursor=' + cursor if cursor else '')
            data = call(a, 'GET', pp + 'work-items/' + suffix).json()
            pages += 1; ids.extend(x['id'] for x in data['results'])
            if not data['next_page_results']: break
            next_cursor = data['next_cursor']
            assert next_cursor != cursor and pages < 10
            cursor = next_cursor
        assert set(ids) == set(manifest['items']) and len(ids) == 3
        report['observations']['pagination'] = {'pages': pages, 'unique_items': len(set(ids))}
        duplicate = call(a, 'POST', pp + 'work-items/', {'name': 'Retry', 'external_source': manifest['slug'], 'external_id': '0'}, expected=(409,))
        assert duplicate.json()['id'] == items[0]['id']
        report['observations']['sequential_duplicate'] = {'status': duplicate.status_code, 'returns_original_id': True}
        # Test stale writes on our own data; do not assume a conditional-write API.
        detail = pp + 'work-items/' + items[0]['id'] + '/'
        original = call(a, 'GET', detail)
        call(a, 'PATCH', detail, {'name': 'First update'})
        stale = call(a, 'PATCH', detail, {'name': 'Stale second update'}, headers={'If-Match': '"intentionally-invalid-revision"'}, expected=(200, 409, 412))
        report['observations']['conditional_write'] = {'get_etag': original.headers.get('ETag'), 'stale_status': stale.status_code, 'final_name': call(a, 'GET', detail).json()['name']}
        # Same workspace member, but not a member of this secret project.
        denied = {}
        for method, endpoint, body in [('GET', pp, None), ('GET', pp+'work-items/', None), ('GET', detail, None), ('PATCH', detail, {'name':'Unauthorized overwrite'}), ('POST', pp+'work-items/', {'name':'Unauthorized create'})]:
            r = call(m, method, endpoint, body, expected=(200,201,400,403,404))
            denied[method+' '+endpoint.removeprefix(v1)] = r.status_code
        report['observations']['private_project_access'] = denied
        assert all(status in (403,404) for status in denied.values()), 'Private project access unexpectedly allowed; inspect report'
        deletion = pp + 'work-items/' + items[2]['id'] + '/'
        call(a, 'DELETE', deletion)
        deleted = call(a, 'GET', deletion, expected=(404,))
        report['observations']['deleted_item_read'] = deleted.status_code
        # Exhaust only this disposable account's API-key quota, not the Builder's.
        for number in range(70):
            limited = a.get(base + pp + 'states/', timeout=15)
            if limited.status_code == 429:
                report['observations']['rate_limit'] = {
                    'status': 429, 'additional_requests': number + 1,
                    'retry_after': limited.headers.get('Retry-After'),
                    'remaining_header': limited.headers.get('X-RateLimit-Remaining'),
                }
                break
            limited.raise_for_status()
        else:
            raise AssertionError('Expected disposable API key to reach its configured quota')
        report['result'] = 'completed'
    finally:
        save()
        if workspace_created:
            try:
                csrf(sessions[0]); call(sessions[0], 'DELETE', '/api/workspaces/' + manifest['slug'] + '/')
                report['cleanup'].append('probe workspace deleted')
            except Exception as exc: report['cleanup'].append('workspace cleanup failed: '+str(exc))
        for sess, account in zip(sessions, manifest['accounts']):
            try:
                csrf(sess)
                if account.get('token_id'): call(sess, 'DELETE', '/api/users/api-tokens/'+account['token_id']+'/')
                call(sess, 'DELETE', '/api/users/me/')
                report['cleanup'].append('probe token revoked and account deactivated')
            except Exception as exc: report['cleanup'].append('account cleanup failed: '+str(exc))
        save()
        print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
