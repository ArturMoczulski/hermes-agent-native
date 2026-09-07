"""Fixed model-facing Plane operation contracts; authority comes from the host.

Schemas and validation share field constraints. The host supplies authentication
context and operation correlation separately; plain text is escaped by the HTTP
adapter. JSON Schema defaults are explicitly applied by ``validate_arguments``.
Cross-field rules require an editable field for updates and a resource ID only
for item/cycle inspection. UTF-8 byte, JSON depth and metadata node limits are
additional host validation constraints; JSON Schema has no UTF-8 byte limit.
"""

import copy
import hashlib
import json
import math
import re


TOOL_OPERATIONS = {
    'plane_project_update': 'project.update',
    'plane_item_create': 'item.create',
    'plane_item_update': 'item.update',
    'plane_comment_create': 'comment.create',
    'plane_cycle_create': 'cycle.create',
    'plane_cycle_update': 'cycle.update',
    'plane_cycle_assign': 'cycle.assign',
    'plane_cycle_remove': 'cycle.remove',
    'plane_dependency_add': 'dependency.add',
    'plane_artifact_record': 'artifact.record',
    'plane_resource_inspect': 'resource.inspect',
}


class ContractError(ValueError):
    """Invalid operation metadata, with no caller-controlled error details."""


_UUID = {
    'type': 'string',
    'pattern': r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    'maxLength': 36,
}
_DIGEST = {'type': 'string', 'pattern': r'^[0-9a-f]{64}$', 'maxLength': 64}
_NAME = {'type': 'string', 'minLength': 1, 'maxLength': 255, 'pattern': r'\S'}
_DESCRIPTION = {'type': 'string', 'maxLength': 16000}
_PRIORITY = {'type': 'string', 'enum': ['urgent', 'high', 'medium', 'low', 'none']}


def _object(properties, required):
    return {
        'type': 'object',
        'properties': properties,
        'required': required,
        'additionalProperties': False,
    }


_CONTRACTS = {
    'project.update': _object(
        {'description': _DESCRIPTION, 'expected_fingerprint': _DIGEST},
        ['description', 'expected_fingerprint'],
    ),
    'item.create': _object(
        {
            'name': _NAME,
            'description': {**_DESCRIPTION, 'default': ''},
            'priority': {**_PRIORITY, 'default': 'none'},
            'state': _UUID,
        },
        ['name'],
    ),
    'item.update': _object(
        {
            'item_id': _UUID,
            'expected_fingerprint': _DIGEST,
            'name': _NAME,
            'description': _DESCRIPTION,
            'priority': _PRIORITY,
            'state': _UUID,
        },
        ['item_id', 'expected_fingerprint'],
    ),
    'comment.create': _object(
        {
            'item_id': _UUID,
            'link_url': {'type': 'string', 'minLength': 1, 'maxLength': 2048},
            'link_label': _NAME,
            'text': {
                'type': 'string',
                'minLength': 1,
                'maxLength': 8000,
                'pattern': r'\S',
            },
        },
        ['item_id', 'text'],
    ),
    'cycle.create': _object(
        {'name': _NAME, 'description': {**_DESCRIPTION, 'default': ''}}, ['name']
    ),
    'cycle.update': _object(
        {
            'cycle_id': _UUID,
            'expected_fingerprint': _DIGEST,
            'name': _NAME,
            'description': _DESCRIPTION,
        },
        ['cycle_id', 'expected_fingerprint'],
    ),
    'cycle.assign': _object(
        {
            'cycle_id': _UUID,
            'item_id': _UUID,
            'expected_item_fingerprint': _DIGEST,
            'expected_cycle_id': {**_UUID, 'type': ['string', 'null']},
        },
        ['cycle_id', 'item_id', 'expected_item_fingerprint', 'expected_cycle_id'],
    ),
    'cycle.remove': _object(
        {'cycle_id': _UUID, 'item_id': _UUID, 'expected_item_fingerprint': _DIGEST},
        ['cycle_id', 'item_id', 'expected_item_fingerprint'],
    ),
    'dependency.add': _object(
        {'item_id': _UUID, 'dependency_id': _UUID, 'expected_fingerprint': _DIGEST},
        ['item_id', 'dependency_id', 'expected_fingerprint'],
    ),
    'artifact.record': _object(
        {
            'item_id': _UUID,
            'reference': {
                'type': 'string',
                'minLength': 1,
                'maxLength': 2048,
                'pattern': r'\S',
            },
            'description': {**_DESCRIPTION, 'default': ''},
        },
        ['item_id', 'reference'],
    ),
    'resource.inspect': _object(
        {
            'kind': {'type': 'string', 'enum': ['project', 'item', 'cycle']},
            'resource_id': _UUID,
        },
        ['kind'],
    ),
}
_EDIT_FIELDS = {
    'item.update': ('name', 'description', 'priority', 'state'),
    'cycle.update': ('name', 'description'),
}
for _operation, _fields in _EDIT_FIELDS.items():
    _CONTRACTS[_operation]['anyOf'] = [{'required': [field]} for field in _fields]
_CONTRACTS['resource.inspect']['oneOf'] = [
    {
        'properties': {'kind': {'const': 'project'}},
        'not': {'required': ['resource_id']},
    },
    {'properties': {'kind': {'enum': ['item', 'cycle']}}, 'required': ['resource_id']},
]

MAX_ARGUMENT_BYTES = 32768
MAX_FINGERPRINT_BYTES = 1024 * 1024
MAX_METADATA_DEPTH = 16
MAX_METADATA_NODES = 10000

_DESCRIPTIONS = {
    'project.update': 'Update the bound project description from plain text using an observed fingerprint.',
    'item.create': 'Create a work item in the bound project. Supply plain text; authority is supplied by the host.',
    'item.update': 'Update a work item from plain text using an observed fingerprint. Supply at least one editable field.',
    'comment.create': 'Record a plain-text comment on a work item.',
    'cycle.create': 'Create an undated outcome cycle in the bound project.',
    'cycle.update': 'Update an outcome cycle using an observed fingerprint. Supply at least one editable field.',
    'cycle.assign': 'Assign a work item to a cycle after checking its observed fingerprint and prior cycle (null if unassigned).',
    'cycle.remove': 'Remove a work item from this cycle after checking its observed fingerprint.',
    'dependency.add': 'Make a work item depend on another work item using an observed fingerprint.',
    'artifact.record': 'Record a plain-text artifact reference and description on a work item.',
    'resource.inspect': 'Read a project, work item or cycle and its fingerprint. Project omits resource_id; item and cycle require it.',
}


def _field(value, rule):
    if value is None and rule['type'] == ['string', 'null']:
        return value
    if type(value) is not str:
        raise ContractError('Invalid operation arguments')
    if len(value) < rule.get('minLength', 0) or len(value) > rule.get(
        'maxLength', 32768
    ):
        raise ContractError('Invalid operation arguments')
    if 'enum' in rule and value not in rule['enum']:
        raise ContractError('Invalid operation arguments')
    if 'pattern' in rule and re.search(rule['pattern'], value) is None:
        raise ContractError('Invalid operation arguments')
    return value


def validate_arguments(operation, arguments):
    """Validate a fixed operation and return a new argument dict with defaults."""
    if (
        type(operation) is not str
        or operation not in _CONTRACTS
        or type(arguments) is not dict
    ):
        raise ContractError('Invalid operation arguments')
    spec = _CONTRACTS[operation]
    if (
        arguments.keys() - spec['properties'].keys()
        or set(spec['required']) - arguments.keys()
    ):
        raise ContractError('Invalid operation arguments')
    result = {
        key: _field(value, spec['properties'][key]) for key, value in arguments.items()
    }
    for key, rule in spec['properties'].items():
        if key not in result and 'default' in rule:
            result[key] = rule['default']
    if operation in _EDIT_FIELDS and not any(
        field in result for field in _EDIT_FIELDS[operation]
    ):
        raise ContractError('Invalid operation arguments')
    if operation == 'resource.inspect':
        needs_id = result['kind'] in ('item', 'cycle')
        if needs_id != ('resource_id' in result):
            raise ContractError('Invalid operation arguments')
    if operation == 'comment.create':
        if ('link_url' in result) != ('link_label' in result):
            raise ContractError('A comment link requires its destination and label')
        if 'link_url' in result:
            from urllib.parse import urlsplit
            try:
                url = urlsplit(result['link_url'])
                if (url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password
                        or any(ord(c) < 33 or ord(c) == 127 for c in result['link_url'])):
                    raise ValueError
                _ = url.port
            except ValueError:
                raise ContractError('Comment links require an HTTP URL without credentials') from None
    _canonical_json(result, MAX_ARGUMENT_BYTES, 'Invalid operation arguments')
    return result


def schemas(operations):
    """Return isolated OpenAI function definitions for the requested whitelist."""
    if type(operations) not in (list, tuple, set, frozenset):
        raise ContractError('Invalid operation selection')
    if any(
        type(operation) is not str or operation not in _CONTRACTS
        for operation in operations
    ):
        raise ContractError('Invalid operation selection')
    selected = set(operations)
    return [
        {
            'type': 'function',
            'function': {
                'name': name,
                'description': _DESCRIPTIONS[operation],
                'parameters': copy.deepcopy(_CONTRACTS[operation]),
            },
        }
        for name, operation in TOOL_OPERATIONS.items()
        if operation in selected
    ]


def _canonical_json(record, byte_limit, message):
    if type(record) is not dict:
        raise ContractError(message)
    nodes = 0

    def check(value, depth=0):
        nonlocal nodes
        nodes += 1
        if nodes > MAX_METADATA_NODES or depth > MAX_METADATA_DEPTH:
            raise ContractError(message)
        kind = type(value)
        if kind is dict:
            for key, child in value.items():
                if type(key) is not str:
                    raise ContractError(message)
                check(key, depth + 1)
                check(child, depth + 1)
        elif kind is list:
            for child in value:
                check(child, depth + 1)
        elif kind is str:
            if len(value) > byte_limit:
                raise ContractError(message)
        elif kind is float:
            if not math.isfinite(value):
                raise ContractError(message)
        elif kind not in (type(None), bool, int):
            raise ContractError(message)

    check(record)
    encoder = json.JSONEncoder(
        sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False
    )
    payload = bytearray()
    try:
        for chunk in encoder.iterencode(record):
            encoded = chunk.encode('utf-8')
            if len(payload) + len(encoded) > byte_limit:
                raise ContractError(message)
            payload.extend(encoded)
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise ContractError(message) from None
    return bytes(payload)


def fingerprint(record):
    """Hash observed content, excluding volatile touch time; not an upstream CAS token.

    Plane can asynchronously change updated_at after returning a successful write,
    without changing the projected task fields. Keep validating the entire input
    before excluding that timestamp; actual field changes still conflict.
    """
    payload = _canonical_json(
        record, MAX_FINGERPRINT_BYTES, 'Invalid fingerprint metadata'
    )
    if isinstance(record, dict) and "updated_at" in record:
        payload = _canonical_json(
            {key: value for key, value in record.items() if key != "updated_at"},
            MAX_FINGERPRINT_BYTES, "Invalid fingerprint metadata",
        )
    return hashlib.sha256(payload).hexdigest()
