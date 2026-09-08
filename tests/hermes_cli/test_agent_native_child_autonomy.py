"""A parent may tune a direct child's eagerness without widening authority."""
import pytest

from agent_native.identity import OWNER, create_root, get_root
from agent.work_policy import tool_schemas
from tests.hermes_cli.test_agent_native_child_delegation import delegate, prepare_frozen_parent
from tests.hermes_cli.test_agent_native_work_effects import broker, effect  # noqa: F401


def invoke(s, call_id, arguments):
    params = effect(s, call_id, 'child_autonomy_configure', arguments)
    params['arguments'] = arguments
    return s.run._effect(s.conn, s.planning, params)


def child(s):
    prepare_frozen_parent(s)
    return delegate(s)['child_id']


def test_managed_parent_configures_direct_child_autonomy_for_future_attempts(broker):
    from agent_native.autonomy import snapshot_attempt

    s = broker
    child_id = child(s)
    child_before = get_root(s.conn, actor=OWNER, agent_id=child_id)
    frozen = snapshot_attempt(
        s.conn, child_id, child_before['work']['id'], 'child-frozen-admission',
    )
    schema = next(tool['function'] for tool in tool_schemas()
                  if tool['function']['name'] == 'child_autonomy_configure')
    assert schema['parameters']['required'] == [
        'child_id', 'level', 'expected_revision', 'reason',
    ]

    changed = invoke(s, 'configure-child-autonomy', {
        'child_id': child_id, 'level': 5, 'expected_revision': 1,
        'reason': 'The delegated research is reversible and should continue independently.',
    })

    assert changed['status'] == 'configured'
    assert changed['parent_id'] == s.root['id'] and changed['child_id'] == child_id
    assert changed['previous_revision'] == 1
    assert changed['autonomy'] == {
        **get_root(s.conn, actor=OWNER, agent_id=child_id)['autonomy'],
        'require_owner_review': False,
    }
    assert changed['autonomy']['level'] == 5 and changed['autonomy']['revision'] == 2
    assert snapshot_attempt(
        s.conn, child_id, child_before['work']['id'], 'child-frozen-admission',
    ) == frozen
    assert frozen['level'] == 3
    assert get_root(s.conn, actor=OWNER, agent_id=s.root['id'])['autonomy']['level'] == 3
    event = s.conn.execute(
        'SELECT actor,level,revision FROM agent_native_autonomy_events '
        'WHERE agent_id=? ORDER BY sequence DESC LIMIT 1', (child_id,),
    ).fetchone()
    assert tuple(event) == (f'parent:{s.root["id"]}', 5, 2)


def test_parent_child_autonomy_change_is_idempotent_and_stale_safe(broker):
    s = broker
    child_id = child(s)
    arguments = {
        'child_id': child_id, 'level': 4, 'expected_revision': 1,
        'reason': 'The child can take more reversible initiative.',
    }
    first = invoke(s, 'stable-change', arguments)
    assert invoke(s, 'stable-change', arguments) == first
    with pytest.raises(Exception, match='reused|changed'):
        invoke(s, 'stable-change', {**arguments, 'level': 2})
    with pytest.raises(Exception, match='changed|reload'):
        invoke(s, 'stale-change', {**arguments, 'level': 2})


def test_parent_cannot_clear_owner_review_policy_while_changing_level(broker):
    from agent_native.autonomy import change_settings

    s = broker
    child_id = child(s)
    change_settings(
        s.conn, actor=OWNER, agent_id=child_id, level=3, expected_revision=1,
        require_owner_review=True,
    )

    changed = invoke(s, 'preserve-owner-policy', {
        'child_id': child_id, 'level': 5, 'expected_revision': 2,
        'reason': 'Increase initiative while retaining the explicit owner gate.',
    })

    assert changed['autonomy']['level'] == 5
    assert changed['autonomy']['require_owner_review'] is True
    assert changed['autonomy']['revision'] == 3


def test_parent_cannot_configure_grandchild_or_unrelated_agent(broker):
    s = broker
    child_id = child(s)
    grandchild = create_root(
        s.conn, actor=OWNER, request_id='autonomy-grandchild', name='Grandchild',
        purpose='Check sources.', parent_id=child_id,
    )
    unrelated = create_root(
        s.conn, actor=OWNER, request_id='autonomy-unrelated', name='Unrelated',
        purpose='Unrelated work.',
    )
    for call_id, target in [('grandchild-change', grandchild['id']),
                            ('unrelated-change', unrelated['id'])]:
        with pytest.raises(PermissionError, match='direct child'):
            invoke(s, call_id, {
                'child_id': target, 'level': 5, 'expected_revision': 1,
                'reason': 'Attempt to exceed the direct-child administration boundary.',
            })
