"""Managed output reads retain exact versions and verified host scope."""
import json
import time
from types import SimpleNamespace

import pytest

from agent.work_policy import WorkContext, tool_schemas
from agent_native.story_store import StoryIntegrityError
from tests.hermes_cli.test_agent_native_work_effects import broker, effect  # noqa: F401
from tests.hermes_cli.test_agent_native_output_progress import publish


def test_managed_tool_reads_complete_unicode_output_in_versioned_chunks(broker):
    s = broker
    content = ('A wizard meets a dragon. 🐉\n' * 1500) + 'THE END'
    saved = publish(s, content=content)
    publish(s, 'revision', output_id=saved['output_id'], content='New revision')
    schema = next(t['function'] for t in tool_schemas() if t['function']['name'] == 'output_read')
    assert {'output_id', 'version'} <= set(schema['parameters']['required'])
    context = WorkContext(run_id=s.work['id'], agent_id=s.root['id'], soul_revision=1,
        name='Writer', purpose='Write', workspace=str(s.run.workspace), session_id='native-read',
        native_db=str(s.home / 'native.db'), deadline_monotonic=time.monotonic()+60,
        max_iterations=16, max_tokens=4096, initial_context='Read prior output', skill_text='Review work',
        request=lambda method, params, deadline: s.run._effect(s.conn, s.planning, params))
    pieces, offset = [], 0
    while True:
        result = json.loads(context.tool(SimpleNamespace(session_id='native-read'), 'output_read',
            {'output_id':saved['output_id'], 'version':1, 'offset':offset, 'limit':8000}, f'read-{offset}'))
        assert result['version'] == 1 and result['total_characters'] == len(content)
        assert len(result['content']) <= 8000
        pieces.append(result['content'])
        if result['next_offset'] is None:
            break
        offset = result['next_offset']
    assert ''.join(pieces) == content
    assert len(pieces) > 1


def test_output_read_checks_scope_arguments_and_file_integrity(broker):
    s = broker
    saved = publish(s)
    args = {'output_id':saved['output_id'], 'version':1}
    for index, changes in enumerate(({'version':True}, {'offset':-1}, {'limit':1000000}, {'path':'../../secret'})):
        with pytest.raises(ValueError):
            s.run._effect(s.conn, s.planning, effect(s, f'invalid-{index}', 'output_read', {**args, **changes}))
    s.conn.execute('UPDATE agent_native_output_versions SET agent_id=? WHERE output_id=?', ('other', saved['output_id']))
    with pytest.raises(LookupError):
        s.run._effect(s.conn, s.planning, effect(s, 'foreign', 'output_read', args))
    s.conn.execute('UPDATE agent_native_output_versions SET agent_id=? WHERE output_id=?', (s.root['id'], saved['output_id']))
    path = s.run.workspace / saved['relative_path']
    path.chmod(0o600)
    path.write_text('tampered')
    with pytest.raises(StoryIntegrityError):
        s.run._effect(s.conn, s.planning, effect(s, 'tampered', 'output_read', args))


def test_saved_output_remains_readable_after_coding_workspace_is_granted(broker, tmp_path):
    s = broker
    saved = publish(s)
    private_output = s.run.output_workspace / saved['relative_path']
    project = tmp_path / 'fantasy-game'
    project.mkdir()

    s.run.workspace = project
    result = s.run._effect(s.conn, s.planning, effect(s, 'read-after-grant', 'output_read', {
        'output_id': saved['output_id'], 'version': saved['version'],
    }))
    revised = publish(s, 'publish-after-grant', output_id=saved['output_id'], content='# Findings\nRevised result.')

    assert result['content'] == '# Findings\nA saved result.'
    assert private_output.is_file()
    assert (s.run.output_workspace / revised['relative_path']).is_file()
    assert not (project / saved['relative_path']).exists()
    assert not (project / revised['relative_path']).exists()
