"""Bounded host-only setup of one ordinary root's Plane planning home.

The caller persists an attempt before calling and holds its operation lock until
return. After an uncertain attempt it passes allow_create=False: this client has
no durable journal and never decides that an unknown create may be redelivered.
A fully matched project may still receive the idempotent privacy PATCH during
reconciliation; no new resource is created by that bounded repair.
Session/password and API credentials are protected host capabilities, never
model tools. This module creates neither accounts nor an agent run.
"""
import re
from uuid import UUID

import httpx

from agent_native.plane_reads import (
    MAX_BODY_BYTES, MAX_PAGES, MAX_RECORDS, MAX_TOTAL_BYTES,
    _CURSOR, _origin, _retry_after, _uuid,
)
from agent_native.plane_writes import _paragraph, _verify_applied, PlaneWriteError


class SetupError(RuntimeError):
    """Safe setup failure; no response content or credentials in its public fields."""

    def __init__(self, message, *, uncertain=False, status=None, retry_after=None):
        super().__init__(message)
        self.uncertain = uncertain
        self.status = status
        self.retry_after = retry_after


def _text(value, limit):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError('Invalid setup configuration or text')
    return value


def _workspace_slug(agent_id):
    return 'an-' + UUID(_uuid(agent_id)).hex


def _project_payload(agent_id):
    key = UUID(_uuid(agent_id)).hex
    return {
        'name': 'Agent work ' + key[:8], 'identifier': 'AN' + key[:10].upper(),
        'description': 'Planning home for agent ' + agent_id + '.',
        'cycle_view': True, 'module_view': True,
        'external_source': 'agent-native', 'external_id': agent_id,
    }


class PlaneSetup:
    def __init__(self, *, base_url, email, password, api_key, expected_user_id):
        self._base = _origin(base_url)
        self._email = _text(email, 255)
        self._password = _text(password, 4096)
        self._key = _text(api_key, 1024)
        if any(ord(c) < 33 or ord(c) > 126 for c in self._key):
            raise ValueError('Invalid setup credential')
        self._user = _uuid(expected_user_id)
        self._session = self._api = None
        self._mutation_possible = False
        self.before_write = lambda: None

    def __enter__(self):
        if self._session is not None:
            raise ValueError('Plane setup context is already open')
        shared = dict(follow_redirects=False, trust_env=False, timeout=15)
        self._session = httpx.Client(**shared, headers={
            'Origin': self._base, 'Referer': self._base + '/',
            'Accept-Encoding': 'identity',
        })
        self._api = httpx.Client(**shared, headers={
            'X-API-Key': self._key, 'Accept-Encoding': 'identity',
        })
        try:
            _, csrf = self._request('GET', '/auth/get-csrf-token/', session=True)
            token = csrf.get('csrf_token') if isinstance(csrf, dict) else None
            if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9]{1,512}', token):
                self._fail('Plane session could not be established')
            self._session.headers['X-CSRFToken'] = token
            self._request('POST', '/auth/sign-in/', session=True, expected=(302,),
                          form={'email': self._email, 'password': self._password}, parse=False)
            for session, path in ((True, '/api/users/me/'), (False, '/api/v1/users/me/')):
                _, user = self._request('GET', path, session=session)
                if not isinstance(user, dict) or user.get('id') != self._user:
                    self._fail('Plane credential identity does not match configuration')
        except BaseException:
            self.__exit__()
            raise
        return self

    def __exit__(self, *args):
        for client in (self._session, self._api):
            if client is not None:
                client.close()
        self._session = self._api = None

    def _begin(self, allow_create):
        if self._session is None:
            raise ValueError('Plane setup requires an open context')
        if type(allow_create) is not bool:
            raise ValueError('allow_create must be explicit boolean authority')
        self._mutation_possible = False

    def _fail(self, message, *, status=None, retry_after=None):
        raise SetupError(message, uncertain=self._mutation_possible,
                         status=status, retry_after=retry_after) from None

    def _request(self, method, path, *, session=False, expected=(200,), payload=None,
                 params=None, form=None, effect=False, parse=True):
        import json

        client = self._session if session else self._api
        previous = self._mutation_possible
        if effect:
            # The host checks current revision/shutdown immediately before each
            # resource effect, after any preflight reads. Preserve its exception.
            self.before_write()
            self._mutation_possible = True
        try:
            with client.stream(method, self._base + path, json=payload, data=form, params=params) as response:
                status = response.status_code
                if status not in expected:
                    if effect and status in (400, 401, 403, 404, 405, 422, 429):
                        self._mutation_possible = previous
                    self._fail('Plane setup request failed', status=status,
                               retry_after=_retry_after(response.headers.get('Retry-After')))
                # A 409 is not success: the ensure operation must reconcile it.
                if effect and status == 409:
                    self._mutation_possible = previous
                if response.headers.get('Content-Encoding', 'identity').lower() != 'identity':
                    self._fail('Plane returned unexpected response encoding')
                length = response.headers.get('Content-Length')
                if length is not None and (not length.isdigit() or int(length) > MAX_BODY_BYTES):
                    self._fail('Plane setup response exceeds bounds')
                body = bytearray()
                for chunk in response.iter_raw():
                    if len(body) + len(chunk) > MAX_BODY_BYTES:
                        self._fail('Plane setup response exceeds bounds')
                    body.extend(chunk)
                self._last_size = len(body)
                return status, json.loads(body) if parse else None
        except (httpx.HTTPError, ValueError, RecursionError):
            self._fail('Plane setup response unavailable or invalid')

    def _record(self, raw, expected):
        if not isinstance(raw, dict):
            self._fail('Plane setup resource is invalid')
        try:
            _uuid(raw.get('id'))
        except ValueError:
            self._fail('Plane setup resource identity is invalid')
        for key, value in expected.items():
            if type(raw.get(key)) is not type(value) or raw[key] != value:
                self._fail('Plane setup resource conflicts with the prepared request')
        return raw

    def _workspace(self, agent_id, slug, *, name=None, missing=False):
        if slug != _workspace_slug(agent_id):
            raise ValueError('Workspace is outside the prepared root scope')
        status, raw = self._request('GET', f'/api/workspaces/{slug}/', session=True,
                                    expected=(200, 404) if missing else (200,))
        if status == 404:
            return None
        expected = {'slug': slug, 'owner': self._user}
        if name is not None:
            expected['name'] = name
        return self._record(raw, expected)

    def ensure_workspace(self, agent_id, name, allow_create=True):
        self._begin(allow_create)
        slug = _workspace_slug(agent_id)
        label = ' '.join(re.sub(r'[^A-Za-z0-9 ]', ' ', _text(name, 10000)).split())[:60] or 'Agent'
        label += ' ' + UUID(agent_id).hex[:8]
        raw = self._workspace(agent_id, slug, name=label, missing=True)
        if raw is None:
            if not allow_create:
                self._fail('Workspace setup remains unresolved; creation is not authorized')
            status, raw = self._request('POST', '/api/workspaces/', session=True,
                                       expected=(201, 409), payload={'name': label, 'slug': slug}, effect=True)
            created_id = None
            if status == 201:
                self._record(raw, {'slug': slug, 'name': label, 'owner': self._user})
                created_id = raw['id']
            raw = self._workspace(agent_id, slug, name=label)
            if created_id is not None and raw['id'] != created_id:
                self._fail('Plane workspace identity changed during confirmation')
        return {'id': raw['id'], 'slug': slug}

    def _projects(self, workspace):
        records, seen, cursors, total_size = [], set(), set(), 0
        cursor, total = None, None
        path = f'/api/v1/workspaces/{workspace["slug"]}/projects/'
        for _ in range(MAX_PAGES):
            params = {'per_page': 100}
            if cursor is not None:
                params['cursor'] = cursor
            _, page = self._request('GET', path, params=params)
            total_size += self._last_size
            if not isinstance(page, dict) or total_size > MAX_TOTAL_BYTES:
                self._fail('Plane project inventory exceeds bounds or is invalid')
            values, more = page.get('results'), page.get('next_page_results')
            if not isinstance(values, list) or type(more) is not bool:
                self._fail('Plane project inventory is invalid')
            counts = [page[k] for k in ('total_results', 'total_count') if k in page]
            if counts:
                if any(type(v) is not int or v < 0 or v != counts[0] for v in counts):
                    self._fail('Plane project inventory totals are invalid')
                if total is not None and total != counts[0]:
                    self._fail('Plane project inventory changed during traversal')
                total = counts[0]
            if 'count' in page and (type(page['count']) is not int or page['count'] != len(values)):
                self._fail('Plane project inventory count is invalid')
            if len(records) + len(values) > MAX_RECORDS:
                self._fail('Plane project inventory exceeds bounds')
            for raw in values:
                self._record(raw, {'workspace': workspace['id']})
                if raw['id'] in seen:
                    self._fail('Plane project inventory repeated a resource')
                seen.add(raw['id'])
                records.append(raw)
            if not more:
                if total is not None and len(records) != total:
                    self._fail('Plane project inventory is incomplete')
                return records
            cursor = page.get('next_cursor')
            if not values or not isinstance(cursor, str) or not _CURSOR.fullmatch(cursor) or cursor in cursors:
                self._fail('Plane project inventory cursor is invalid')
            cursors.add(cursor)
        self._fail('Plane project inventory exceeds the page budget')

    def _project(self, workspace, agent_id, project_id, *, private=False):
        _uuid(project_id)
        _, raw = self._request('GET', f'/api/v1/workspaces/{workspace["slug"]}/projects/{project_id}/')
        expected = {'id': project_id, 'workspace': workspace['id'], **_project_payload(agent_id)}
        if private:
            expected['network'] = 0
        return self._record(raw, expected)

    def ensure_project(self, agent_id, workspace_slug, allow_create=True):
        self._begin(allow_create)
        workspace = self._workspace(agent_id, workspace_slug)
        expected = _project_payload(agent_id)
        matches = [p for p in self._projects(workspace)
                   if p.get('external_id') == expected['external_id']
                   or p.get('identifier') == expected['identifier'] or p.get('name') == expected['name']]
        if len(matches) > 1:
            self._fail('Plane project correlation is not unique')
        path = f'/api/v1/workspaces/{workspace_slug}/projects/'
        if not matches:
            if not allow_create:
                self._fail('Project setup remains unresolved; creation is not authorized')
            status, raw = self._request('POST', path, payload=expected, expected=(201, 409), effect=True)
            if status == 409:
                matches = [p for p in self._projects(workspace)
                           if p.get('external_id') == agent_id or p.get('identifier') == expected['identifier']
                           or p.get('name') == expected['name']]
                if len(matches) != 1:
                    self._fail('Plane project conflict remains unresolved')
                raw = matches[0]
        else:
            raw = matches[0]
        self._record(raw, {'workspace': workspace['id'], **expected})
        project_id = raw['id']
        raw = self._project(workspace, agent_id, project_id)
        if type(raw.get('network')) is not int or raw['network'] not in (0, 2):
            self._fail('Plane project visibility is invalid')
        if raw['network'] != 0:
            # Narrowing the fully reconciled project's visibility is idempotent
            # and permitted even when uncertain creation cannot be retried.
            self._request('PATCH', f'/api/workspaces/{workspace_slug}/projects/{project_id}/',
                          session=True, payload={'network': 0}, effect=True)
        self._project(workspace, agent_id, project_id, private=True)
        return {'id': project_id}

    def ensure_discovery(self, agent_id, activation_id, purpose, workspace_slug,
                         project_id, allow_create=True):
        self._begin(allow_create)
        _uuid(activation_id)
        _text(purpose, 100000)
        workspace = self._workspace(agent_id, workspace_slug)
        self._project(workspace, agent_id, project_id, private=True)
        payload = {
            'name': 'Discover purpose and plan first work',
            'description_html': _paragraph('Purpose:\n' + purpose + '\n\nAcceptance criteria:\n'
                'Establish the brief, identify needed clarification, and plan the first useful work.\n'
                'Record the plan and acceptance criteria in this project before further execution.'),
            'priority': 'high', 'external_source': 'agent-native', 'external_id': activation_id,
        }
        path = f'/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/'
        marker = {key: payload[key] for key in ('external_source', 'external_id')}
        status, raw = self._request('GET', path, params=marker, expected=(200, 404))
        if status == 404:
            if not allow_create:
                self._fail('Discovery setup remains unresolved; creation is not authorized')
            status, raw = self._request('POST', path, payload=payload, expected=(201, 409), effect=True)
            if status == 409:
                _, raw = self._request('GET', path, params=marker)
        self._record(raw, {'workspace': workspace['id'], 'project': project_id, **marker})
        item_id = raw['id']
        _, raw = self._request('GET', path + item_id + '/')
        self._record(raw, {'id': item_id, 'workspace': workspace['id'], 'project': project_id, **marker})
        try:
            _verify_applied(raw, payload)
        except PlaneWriteError:
            self._fail('Plane discovery conflicts with the prepared request')
        return {'id': item_id}
