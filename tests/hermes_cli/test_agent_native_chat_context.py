from agent_native.chat import issue_binding
from agent_native.identity import OWNER
from tests.hermes_cli.test_agent_native_work_effects import broker  # noqa: F401
from tests.hermes_cli.test_agent_native_output_progress import publish
from tests.hermes_cli.test_agent_native_work_focus import select


def test_chat_context_reads_current_work_without_tools_or_state_changes(broker):
    from agent_native.chat_context import snapshot
    s = broker
    select(s)
    saved = publish(s)
    binding = issue_binding(actor=OWNER, agent_id=s.root['id'], db_path=s.db_path,
                            storage_root=s.home/'agents')
    first = snapshot(binding)
    assert first['work']['state'] == 'running'
    assert first['work']['assignment']['item_id'] == s.setup['discovery_item_id']
    assert first['work']['outputs'][0]['output_id'] == saved['output_id']
    assert 'content' not in first['work']['outputs'][0]
    s.run.stop()
    requests = len(s.plane.requests)
    assert snapshot(binding)['work']['state'] == 'paused'
    assert len(s.plane.requests) == requests
    assert s.conn.execute('SELECT state FROM agent_native_work_runs WHERE id=?', (s.work['id'],)).fetchone()[0] == 'paused'


def test_context_preserves_transcript_and_isolates_other_agents_and_purpose(broker):
    from types import SimpleNamespace
    import pytest
    from agent_native import identity
    from agent_native.chat_context import snapshot, context_for
    from agent.turn_context import _stamp_api_content_sidecar
    s = broker
    binding = issue_binding(actor=OWNER, agent_id=s.root['id'], db_path=s.db_path,
                            storage_root=s.home/'agents')
    agent = SimpleNamespace(_managed_chat_binding=binding)
    messages = [{'role': 'user', 'content': 'What are you working on?'}]
    _stamp_api_content_sidecar(agent, messages, 0, '', context_for(agent), preflight_compressed=False)
    original_wire = messages[0]['api_content']
    assert messages[0]['content'] == 'What are you working on?'
    assert 'AGENT_NATIVE_WORK_SNAPSHOT' in original_wire
    s.run.stop()
    assert '"state": "paused"' in context_for(agent)
    assert messages[0]['api_content'] == original_wire
    other = identity.create_root(s.conn, actor=OWNER, request_id='other-context', name='Other', purpose='Another project')
    other_binding = issue_binding(actor=OWNER, agent_id=other['id'], db_path=s.db_path,
                                  storage_root=s.home/'agents')
    assert snapshot(other_binding)['work'] is None
    identity.revise_soul(s.conn, actor=OWNER, agent_id=s.root['id'], expected_revision=1, purpose='A changed purpose')
    with pytest.raises(identity.ConflictError):
        snapshot(binding)
    current = issue_binding(actor=OWNER, agent_id=s.root['id'], db_path=s.db_path,
                            storage_root=s.home/'agents')
    assert snapshot(current)['work'] is None
