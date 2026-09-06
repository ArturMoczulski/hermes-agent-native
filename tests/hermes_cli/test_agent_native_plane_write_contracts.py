"""Model argument contracts are independent from Plane HTTP and authority."""

import copy
import hashlib
import json

import pytest

from agent_native.plane_write_contracts import (
    ContractError,
    TOOL_OPERATIONS,
    fingerprint,
    schemas,
    validate_arguments,
)

UUID = '12345678-1234-1234-1234-123456789abc'
OTHER = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
DIGEST = 'a' * 64
VALID = {
    'project.update': {
        'description': 'A planning home',
        'expected_fingerprint': DIGEST,
    },
    'item.create': {'name': 'Write tests'},
    'item.update': {'item_id': UUID, 'expected_fingerprint': DIGEST, 'name': 'Updated'},
    'comment.create': {'item_id': UUID, 'text': 'Evidence'},
    'cycle.create': {'name': 'Next accepted outcome'},
    'cycle.update': {
        'cycle_id': UUID,
        'expected_fingerprint': DIGEST,
        'description': '',
    },
    'cycle.assign': {
        'cycle_id': UUID,
        'item_id': OTHER,
        'expected_item_fingerprint': DIGEST,
        'expected_cycle_id': None,
    },
    'cycle.remove': {
        'cycle_id': UUID,
        'item_id': OTHER,
        'expected_item_fingerprint': DIGEST,
    },
    'dependency.add': {
        'item_id': UUID,
        'dependency_id': OTHER,
        'expected_fingerprint': DIGEST,
    },
    'artifact.record': {'item_id': UUID, 'reference': 'commit:1234'},
    'resource.inspect': {'kind': 'project'},
}


@pytest.mark.parametrize('operation', VALID)
def test_supported_operations_validate_and_copy_arguments(operation):
    original = copy.deepcopy(VALID[operation])
    result = validate_arguments(operation, original)
    assert original == VALID[operation]
    assert result is not original
    assert all(result[key] == value for key, value in original.items())
    if operation in {'item.create', 'cycle.create', 'artifact.record'}:
        assert result['description'] == ''
    if operation == 'item.create':
        assert result['priority'] == 'none'


@pytest.mark.parametrize(
    'field',
    ['actor', 'context', 'api_key', 'operation_id', 'project_id', 'workspace_slug'],
)
def test_model_cannot_supply_authority_or_host_metadata(field):
    with pytest.raises(ContractError):
        validate_arguments('item.create', {'name': 'Safe', field: 'caller selected'})


def test_tool_schemas_match_the_validator_and_are_independent_copies():
    definitions = schemas(list(VALID))
    assert {TOOL_OPERATIONS[d['function']['name']] for d in definitions} == set(VALID)
    for definition in definitions:
        assert definition['type'] == 'function'
        function = definition['function']
        operation = TOOL_OPERATIONS[function['name']]
        spec = function['parameters']
        assert spec['type'] == 'object'
        assert spec['additionalProperties'] is False
        assert set(spec['required']) <= spec['properties'].keys()
        for required in spec['required']:
            data = dict(VALID[operation])
            data.pop(required, None)
            with pytest.raises(ContractError):
                validate_arguments(operation, data)
        for field in spec['properties']:
            assert field not in {
                'actor',
                'context',
                'api_key',
                'operation_id',
                'workspace_slug',
                'project_id',
            }
    definitions[0]['function']['parameters']['properties'].clear()
    assert schemas(list(VALID))[0]['function']['parameters']['properties']


def test_schemas_disclose_only_requested_operations():
    definitions = schemas({'item.create', 'resource.inspect'})
    assert [d['function']['name'] for d in definitions] == [
        'plane_item_create',
        'plane_resource_inspect',
    ]
    assert schemas([]) == []
    with pytest.raises(ContractError):
        schemas(['item.create', 'arbitrary.request'])


def test_fingerprint_is_canonical_and_order_independent():
    record = {'name': 'é', 'nested': {'values': [None, True, 1, 0.5]}}
    encoded = json.dumps(
        record,
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()
    assert fingerprint(record) == hashlib.sha256(encoded).hexdigest()
    assert fingerprint(dict(reversed(list(record.items())))) == fingerprint(record)
    assert fingerprint({**record, 'name': 'changed'}) != fingerprint(record)


@pytest.mark.parametrize(
    'operation,arguments',
    [
        ('item.update', {'item_id': UUID, 'expected_fingerprint': DIGEST}),
        ('cycle.update', {'cycle_id': UUID, 'expected_fingerprint': DIGEST}),
        ('resource.inspect', {'kind': 'project', 'resource_id': UUID}),
        ('resource.inspect', {'kind': 'item'}),
        ('resource.inspect', {'kind': 'cycle'}),
    ],
)
def test_cross_field_constraints_reject_empty_updates_and_wrong_inspection_shape(
    operation, arguments
):
    with pytest.raises(ContractError):
        validate_arguments(operation, arguments)


@pytest.mark.parametrize('kind', ['item', 'cycle'])
def test_inspection_accepts_required_scoped_resource_identity(kind):
    args = {'kind': kind, 'resource_id': UUID}
    assert validate_arguments('resource.inspect', args) == args


def test_schema_exposes_update_and_inspection_cross_field_rules():
    definitions = {
        TOOL_OPERATIONS[d['function']['name']]: d['function']['parameters']
        for d in schemas(list(VALID))
    }
    for operation in ['item.update', 'cycle.update']:
        choices = definitions[operation]['anyOf']
        edit_fields = set(definitions[operation]['properties']) - set(
            definitions[operation]['required']
        )
        assert {entry['required'][0] for entry in choices} == edit_fields
    assert len(definitions['resource.inspect']['oneOf']) == 2


@pytest.mark.parametrize('operation', [None, [], {}, True, 1, 'secret-operation-value'])
def test_unknown_operation_rejected_without_echoing(operation):
    with pytest.raises(ContractError, match='^Invalid operation arguments$'):
        validate_arguments(operation, {'name': 'secret-body-value'})


@pytest.mark.parametrize('arguments', [None, [], (), True, 1, 'name=secret'])
def test_arguments_must_be_json_object(arguments):
    with pytest.raises(ContractError, match='^Invalid operation arguments$'):
        validate_arguments('item.create', arguments)


@pytest.mark.parametrize(
    'value', [None, True, 0, 1.0, float('nan'), float('inf'), [], {}, b'name']
)
def test_never_coerces_non_text_to_name(value):
    with pytest.raises(ContractError):
        validate_arguments('item.create', {'name': value})


@pytest.mark.parametrize(
    'operation,field,limit',
    [
        ('item.create', 'name', 255),
        ('cycle.create', 'name', 255),
        ('project.update', 'description', 16000),
        ('item.update', 'description', 16000),
        ('comment.create', 'text', 8000),
        ('artifact.record', 'reference', 2048),
    ],
)
def test_text_length_boundary(operation, field, limit):
    args = {**VALID[operation], field: 'x' * limit}
    assert validate_arguments(operation, args)[field] == args[field]
    args[field] += 'x'
    with pytest.raises(ContractError):
        validate_arguments(operation, args)


@pytest.mark.parametrize(
    'operation,field',
    [
        ('item.create', 'name'),
        ('cycle.create', 'name'),
        ('comment.create', 'text'),
        ('artifact.record', 'reference'),
    ],
)
@pytest.mark.parametrize('value', ['', ' \t\n', '\u2003'])
def test_required_text_rejects_blank_unicode_whitespace(operation, field, value):
    with pytest.raises(ContractError):
        validate_arguments(operation, {**VALID[operation], field: value})


@pytest.mark.parametrize(
    'value',
    [
        UUID.upper(),
        UUID.replace('-', ''),
        '{' + UUID + '}',
        UUID + '\n',
        True,
        123,
        None,
        'not-a-uuid',
    ],
)
def test_uuid_is_canonical_and_never_coerced(value):
    with pytest.raises(ContractError):
        validate_arguments('item.update', {**VALID['item.update'], 'item_id': value})


@pytest.mark.parametrize(
    'value', ['A' * 64, 'a' * 63, 'a' * 65, 'g' * 64, 'a' * 64 + '\n', True, None]
)
def test_fingerprint_argument_has_exact_lowercase_hex(value):
    with pytest.raises(ContractError):
        validate_arguments(
            'project.update', {**VALID['project.update'], 'expected_fingerprint': value}
        )


def test_nullable_prior_cycle_is_required_and_only_prior_cycle_is_nullable():
    assert (
        validate_arguments(
            'cycle.assign', {**VALID['cycle.assign'], 'expected_cycle_id': UUID}
        )['expected_cycle_id']
        == UUID
    )
    with pytest.raises(ContractError):
        validate_arguments(
            'cycle.assign',
            {
                k: v
                for k, v in VALID['cycle.assign'].items()
                if k != 'expected_cycle_id'
            },
        )
    with pytest.raises(ContractError):
        validate_arguments('cycle.assign', {**VALID['cycle.assign'], 'cycle_id': None})


@pytest.mark.parametrize('priority', ['urgent', 'high', 'medium', 'low', 'none'])
def test_supported_priority_values(priority):
    assert (
        validate_arguments('item.create', {'name': 'Work', 'priority': priority})[
            'priority'
        ]
        == priority
    )


def test_unknown_priority_rejected():
    with pytest.raises(ContractError):
        validate_arguments('item.create', {'name': 'Work', 'priority': 'critical'})


def test_plain_text_preserved_for_adapter_to_escape():
    text = ' <script>alert("x")</script> & <b>not markup</b> '
    assert (
        validate_arguments('comment.create', {'item_id': UUID, 'text': text})['text']
        == text
    )


def test_argument_budget_counts_utf8_bytes_instead_of_codepoints():
    with pytest.raises(ContractError, match='^Invalid operation arguments$'):
        validate_arguments(
            'item.create', {'name': 'Work', 'description': '\U0001f600' * 9000}
        )
    assert (
        validate_arguments(
            'item.create', {'name': 'Work', 'description': '\U0001f600' * 7000}
        )['name']
        == 'Work'
    )


def test_argument_budget_exact_boundary():
    args = {'name': 'Work', 'description': '\U0001f600' * 8000}

    def encode(value):
        return json.dumps(
            value,
            sort_keys=True,
            separators=(',', ':'),
            ensure_ascii=False,
            allow_nan=False,
        ).encode('utf-8')

    remaining = 32768 - len(encode({**args, 'priority': 'none'}))
    args['description'] += 'x' * remaining
    assert len(encode(validate_arguments('item.create', args))) == 32768
    args['description'] += 'x'
    with pytest.raises(ContractError):
        validate_arguments('item.create', args)


def test_invalid_unicode_is_safe_error():
    with pytest.raises(ContractError, match='^Invalid operation arguments$'):
        validate_arguments('item.create', {'name': '\ud800 secret'})


@pytest.mark.parametrize(
    'operations',
    [None, 'item.create', {'item.create': True}, [None], [['item.create']]],
)
def test_schemas_reject_invalid_selection(operations):
    with pytest.raises(ContractError):
        schemas(operations)


@pytest.mark.parametrize(
    'record',
    [
        None,
        [],
        {'secret': float('nan')},
        {'secret': float('inf')},
        {1: 'secret'},
        {'secret': b'value'},
        {'secret': object()},
        {'secret': ('tuple',)},
        {'secret': '\ud800'},
    ],
)
def test_fingerprint_rejects_non_json_records_with_safe_error(record):
    with pytest.raises(ContractError, match='^Invalid fingerprint metadata$'):
        fingerprint(record)


def test_fingerprint_rejects_oversized_metadata():
    with pytest.raises(ContractError, match='^Invalid fingerprint metadata$'):
        fingerprint({'secret': 'x' * (1024 * 1024)})


def test_fingerprint_rejects_deep_circular_and_excessive_metadata():
    deep = {}
    node = deep
    for _ in range(20):
        node['next'] = {}
        node = node['next']
    cycle = {}
    cycle['cycle'] = cycle
    for record in [deep, cycle, {'values': [None] * 10001}]:
        with pytest.raises(ContractError, match='^Invalid fingerprint metadata$'):
            fingerprint(record)
