"""Scoped, trusted-host Plane reads. No managed worker or download endpoint.

The service credential and authority object stay outside generated-code sandboxes.
Contexts are supplied by trusted host control; this module does not authenticate
HTTP callers or establish that a managed agent has been launched.
"""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import ipaddress
import json
import math
import re
import time
from urllib.parse import urlsplit
from uuid import UUID

import httpx

MAX_BODY_BYTES = 1024 * 1024
MAX_TOTAL_BYTES = 8 * 1024 * 1024
MAX_PAGES = 100
MAX_RECORDS = 5000
_CURSOR = re.compile(r'[-A-Za-z0-9_:=]{1,256}\Z')

_COMMON = ('id', 'workspace', 'project', 'created_at', 'updated_at')
_FIELDS = {
    'project': ('id', 'workspace', 'name', 'identifier', 'description', 'created_at', 'updated_at'),
    'item': _COMMON + ('name', 'description_html', 'sequence_id', 'state', 'priority',
                       'parent', 'start_date', 'target_date'),
    'comment': _COMMON + ('issue', 'comment_html', 'actor', 'access', 'edited_at', 'external_id', 'external_source'),
    'attachment': _COMMON + ('issue', 'is_uploaded', 'created_by'),
    'cycle': _COMMON + ('name', 'description', 'start_date', 'end_date', 'owned_by'),
    'state': _COMMON + ('name', 'description', 'group', 'color', 'sequence', 'default'),
}


class PlaneReadError(RuntimeError):
    """A safe upstream failure without response bodies or service credentials."""
    def __init__(self, message, *, status=None, retry_after=None):
        super().__init__(message)
        self.status = self.status_code = status
        self.retry_after = retry_after


class PlaneScopeError(PlaneReadError):
    """A returned resource does not belong to the authorized project or item."""


def _uuid(value):
    try:
        if not isinstance(value, str) or str(UUID(value)) != value:
            raise ValueError
    except (ValueError, AttributeError):
        raise ValueError('A canonical resource UUID is required') from None
    return value


def _record(payload, scope, kind, *, item_id=None):
    if not isinstance(payload, dict):
        raise PlaneReadError('Invalid Plane resource')
    try:
        _uuid(payload.get('id'))
    except ValueError:
        raise PlaneReadError('Invalid Plane resource identity') from None
    expected = {'workspace': scope.workspace_id}
    expected['id' if kind == 'project' else 'project'] = scope.project_id
    if item_id:
        expected['id' if kind == 'item' else 'issue'] = item_id
    if any(payload.get(key) != value for key, value in expected.items()):
        raise PlaneScopeError('Plane resource is outside the authorized scope')
    result = _select(payload, _FIELDS[kind])
    if kind == 'attachment':
        attributes = payload.get('attributes') or {}
        if not isinstance(attributes, dict):
            raise PlaneReadError('Invalid attachment metadata')
        result['attributes'] = _select(attributes, ('name', 'size', 'type'))
    return result


def _select(payload, fields):
    result = {key: payload[key] for key in fields if key in payload}
    for value in result.values():
        if value is not None and not isinstance(value, (str, int, float, bool)):
            raise PlaneReadError('Invalid Plane metadata field')
        if isinstance(value, float) and not math.isfinite(value):
            raise PlaneReadError('Invalid Plane number')
    return result


def _origin(value):
    try:
        if not isinstance(value, str) or any(ord(c) < 33 for c in value):
            raise ValueError
        parsed = urlsplit(value)
        if (parsed.scheme not in ('http', 'https') or not parsed.hostname or
                parsed.username is not None or parsed.password is not None or
                parsed.path not in ('', '/') or parsed.query or parsed.fragment):
            raise ValueError
        # Plain HTTP is only for the explicitly configured local installation.
        if parsed.scheme == 'http' and parsed.hostname != 'localhost':
            if not ipaddress.ip_address(parsed.hostname).is_loopback:
                raise ValueError
        if parsed.port is not None and not 0 < parsed.port <= 65535:
            raise ValueError
    except ValueError:
        raise ValueError('Plane requires a service origin: HTTPS or loopback HTTP') from None
    return value.rstrip('/')


def _retry_after(value):
    if not value or len(value) > 80:
        return None
    try:
        if re.fullmatch(r'[0-9]{1,10}', value):
            return int(value)
        when = parsedate_to_datetime(value)
        if when.tzinfo is None:
            return None
        return max(0, math.ceil((when - datetime.now(timezone.utc)).total_seconds()))
    except (TypeError, ValueError, OverflowError):
        return None


class PlaneReads:
    def __init__(self, authority, *, base_url, api_key, page_size=50):
        self.authority = authority
        self._base_url = _origin(base_url)
        if (not isinstance(api_key, str) or not api_key or len(api_key) > 1024 or
                any(ord(c) < 33 or ord(c) > 126 for c in api_key)):
            raise ValueError('A valid service API key is required')
        if type(page_size) is not int or not 1 <= page_size <= 100:
            raise ValueError('Page size must be an integer between 1 and 100')
        self._api_key = api_key
        self.page_size = page_size

    def _request(self, context, suffix='', params=None):
        # Only retry read throttles. Never replay a mutation or retry before
        # the server's delay; host authority/deadline stays live while waiting.
        budget = 30
        for attempt in range(3):
            try:
                return self._request_once(context, suffix, params)
            except PlaneReadError as error:
                if error.status != 429 or attempt == 2:
                    raise
                delay = error.retry_after if error.retry_after is not None else 1
                if delay > budget:
                    raise
                budget -= delay
                until = time.monotonic() + delay
                while True:
                    self.authority.resolve(context)
                    remaining = until - time.monotonic()
                    if remaining <= 0:
                        break
                    time.sleep(min(0.1, remaining))

    def _request_once(self, context, suffix='', params=None):
        scope = self.authority.resolve(context)
        url = (f'{self._base_url}/api/v1/workspaces/{scope.workspace_slug}/'
               f'projects/{scope.project_id}/{suffix}')
        try:
            with httpx.Client(follow_redirects=False, trust_env=False, timeout=15) as client:
                with client.stream('GET', url, headers={'X-API-Key': self._api_key,
                                   'Accept-Encoding': 'identity'}, params=params) as response:
                    if response.status_code != 200:
                        raise PlaneReadError('Plane read failed', status=response.status_code,
                                             retry_after=_retry_after(response.headers.get('Retry-After'))) from None
                    if response.headers.get('Content-Encoding', 'identity').lower() != 'identity':
                        raise PlaneReadError('Unexpected Plane response encoding') from None
                    length = response.headers.get('Content-Length')
                    if length is not None and (not length.isdigit() or int(length) > MAX_BODY_BYTES):
                        raise PlaneReadError('Plane response exceeds the read budget') from None
                    body = bytearray()
                    for chunk in response.iter_raw():
                        if len(body) + len(chunk) > MAX_BODY_BYTES:
                            raise PlaneReadError('Plane response exceeds the read budget') from None
                        body.extend(chunk)
                    payload = json.loads(body)
        except (httpx.HTTPError, ValueError, RecursionError):
            raise PlaneReadError('Plane response unavailable or invalid') from None
        self.authority.resolve(context)
        return scope, payload, len(body)

    def _list(self, context, suffix, kind, *, item_id=None, unpaginated=False):
        result, cursor, cursors, ids, total_bytes = [], None, set(), set(), 0
        for _ in range(MAX_PAGES):
            params = {'per_page': self.page_size}
            if cursor is not None:
                params['cursor'] = cursor
            scope, payload, body_bytes = self._request(context, suffix, None if unpaginated else params)
            total_bytes += body_bytes
            if total_bytes > MAX_TOTAL_BYTES:
                raise PlaneReadError('Plane results exceed the read budget')
            if unpaginated:
                records, more = payload, False
            elif isinstance(payload, dict):
                records, more = payload.get('results'), payload.get('next_page_results')
            else:
                raise PlaneReadError('Invalid Plane page')
            if not isinstance(records, list) or not isinstance(more, bool):
                raise PlaneReadError('Invalid Plane page')
            if len(result) + len(records) > MAX_RECORDS:
                raise PlaneReadError('Plane results exceed the record budget')
            for record in records:
                projected = _record(record, scope, kind, item_id=item_id)
                if projected['id'] in ids:
                    raise PlaneReadError('Plane pagination repeated a resource; refresh required')
                ids.add(projected['id'])
                result.append(projected)
            if not more:
                self.authority.resolve(context)
                return result
            cursor = payload.get('next_cursor')
            if (not records or not isinstance(cursor, str) or not _CURSOR.fullmatch(cursor) or
                    cursor in cursors):
                raise PlaneReadError('Invalid or repeated Plane cursor')
            cursors.add(cursor)
        raise PlaneReadError('Plane pagination exceeds the page budget')

    def get_project(self, context):
        scope, payload, _ = self._request(context)
        result = _record(payload, scope, 'project')
        self.authority.resolve(context)
        return result

    def list_work_items(self, context):
        return self._list(context, 'work-items/', 'item')

    def get_work_item(self, context, item_id):
        item_id = _uuid(item_id)
        scope, payload, _ = self._request(context, f'work-items/{item_id}/')
        result = _record(payload, scope, 'item', item_id=item_id)
        self.authority.resolve(context)
        return result

    def list_comments(self, context, item_id):
        item_id = _uuid(item_id)
        self.get_work_item(context, item_id)
        return self._list(context, f'work-items/{item_id}/comments/', 'comment', item_id=item_id)

    def list_attachments(self, context, item_id):
        item_id = _uuid(item_id)
        self.get_work_item(context, item_id)
        return self._list(context, f'work-items/{item_id}/attachments/', 'attachment',
                          item_id=item_id, unpaginated=True)

    def list_cycles(self, context):
        return self._list(context, 'cycles/', 'cycle')

    def list_states(self, context):
        return self._list(context, 'states/', 'state')
