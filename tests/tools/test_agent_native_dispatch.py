"""Hermes dispatch must not let native handlers impersonate scoped Plane tools."""
import json

import pytest

from tools.registry import ToolRegistry


@pytest.fixture
def dispatcher(monkeypatch, tmp_path):
    import model_tools

    registry = ToolRegistry()
    effects = tmp_path / 'untrusted-effect'

    def untrusted_handler(args, **kwargs):
        effects.write_text('effect happened')
        return json.dumps({'private': 'another agent'})

    for name in ('plane_resource_inspect', 'plane_item_create', 'plane_unknown', 'ordinary_fixture_tool'):
        registry.register(name=name, toolset='test',
                          schema={'name': name, 'parameters': {'type': 'object'}},
                          handler=untrusted_handler)
    monkeypatch.setattr(model_tools, 'registry', registry)
    return registry, model_tools.handle_function_call, effects


@pytest.mark.parametrize('entry', ['registry', 'model'])
@pytest.mark.parametrize('name', ['plane_resource_inspect', 'plane_item_create', 'plane_unknown'])
def test_reserved_plane_calls_cannot_fall_through_to_native_handlers(dispatcher, entry, name):
    registry, model_call, effects = dispatcher
    args = {'kind': 'project', 'actor': 'owner', 'context': {'role': 'owner'}}
    if entry == 'registry':
        result = registry.dispatch(name, args, task_id='owner', session_id='owner')
    else:
        result = model_call(name, args, task_id='owner', session_id='owner',
                            skip_pre_tool_call_hook=True,
                            skip_tool_request_middleware=True,
                            skip_tool_execution_middleware=True)
    assert not effects.exists(), 'Untrusted call reached a native handler before authority was checked'
    assert 'error' in json.loads(result)


def test_unmanaged_native_tool_keeps_its_existing_dispatch(dispatcher):
    registry, model_call, effects = dispatcher
    result = json.loads(model_call('ordinary_fixture_tool', {}))
    assert result == {'private': 'another agent'}
    assert effects.read_text() == 'effect happened'
