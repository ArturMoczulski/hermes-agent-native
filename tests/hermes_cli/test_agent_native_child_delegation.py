"""A managed parent may create one auditable direct child per tool-call identity."""
import json

from agent_native import cadence
from agent_native.identity import OWNER, get_root
from agent.work_policy import tool_schemas
from tests.hermes_cli.test_agent_native_work_effects import broker, effect  # noqa: F401


def prepare_frozen_parent(s, *, cadence_enabled=True):
    from agent_native.autonomy import snapshot_attempt as snapshot_autonomy
    from agent_native.model_settings import snapshot_attempt as snapshot_model
    snapshot_model(s.conn, s.root['id'], 'work', s.work['id'])
    snapshot_autonomy(s.conn, s.root['id'], s.work['id'], 'delegation-admission')
    cadence.configure(s.conn, actor=OWNER, agent_id=s.root['id'], expected_revision=1,
                      interval_seconds=90, enabled=cadence_enabled)


def delegate(s, call_id='create-child', **changes):
    arguments = {
        'name': 'Lore researcher',
        'purpose': 'Research the history needed for the parent fantasy setting.',
        'reason': 'The research can proceed independently while the parent integrates the setting.',
        **changes,
    }
    return s.run._effect(s.conn, s.planning, effect(s, call_id, 'child_create', arguments))


def test_managed_worker_receives_bounded_child_creation_tool():
    schema = next(
        tool['function'] for tool in tool_schemas()
        if tool['function']['name'] == 'child_create'
    )

    assert schema['parameters']['required'] == ['name', 'purpose', 'reason']
    assert schema['parameters']['additionalProperties'] is False


def test_parent_creates_child_with_frozen_inherited_runtime_configuration(broker):
    s = broker
    prepare_frozen_parent(s)

    result = delegate(s)
    child = get_root(s.conn, actor=OWNER, agent_id=result['child_id'])

    assert child['parent_id'] == s.root['id']
    assert child['purpose'] == 'Research the history needed for the parent fantasy setting.'
    assert child['model_selection']['provider'] == s.root['model_selection']['provider']
    assert child['model_selection']['model'] == s.root['model_selection']['model']
    assert child['autonomy']['level'] == s.root['autonomy']['level']
    assert child['work']['limits'] == s.work['limits']
    assert child['work']['state'] == 'queued'
    assert child['cadence']['enabled'] is True
    assert child['cadence']['interval_seconds'] == 90
    record = s.conn.execute(
        'SELECT parent_id,parent_run_id,child_id,reason,configuration_json FROM agent_native_child_delegations '
        'WHERE parent_run_id=? AND call_id=?', (s.work['id'], 'create-child'),
    ).fetchone()
    assert record[:4] == (s.root['id'], s.work['id'], child['id'],
                          'The research can proceed independently while the parent integrates the setting.')
    assert json.loads(record[4])['work_limits'] == s.work['limits']
    assert 'api_key' not in record[4]


def test_child_delegation_replay_returns_the_same_child(broker):
    s = broker
    prepare_frozen_parent(s, cadence_enabled=False)
    first = delegate(s)
    second = delegate(s)

    assert second == first
    assert get_root(s.conn, actor=OWNER, agent_id=first['child_id'])['cadence']['enabled'] is False
    assert s.conn.execute('SELECT COUNT(*) FROM agent_native_agent_parents WHERE parent_id=?',
                          (s.root['id'],)).fetchone()[0] == 1


def test_child_creation_requires_frozen_parent_admission(broker):
    s = broker

    denied = delegate(s)
    assert denied['status'] == 'rejected' and denied['error'] == 'PermissionError'
    assert get_root(s.conn, actor=OWNER, agent_id=s.root['id'])['child_ids'] == []
