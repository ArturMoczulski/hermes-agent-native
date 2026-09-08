"""Atomic owner replacement creates a clean successor and retires obsolete work."""
import pytest

from agent_native import cadence
from agent_native.identity import OWNER, ConflictError, create_root, get_root
from agent_native.replacement import replace
from agent.work_policy import tool_schemas
from tests.hermes_cli.test_agent_native_child_delegation import delegate, prepare_frozen_parent
from tests.hermes_cli.test_agent_native_work_effects import broker, effect  # noqa: F401
from tests.hermes_cli.test_agent_native_api import BODY, URL, client  # noqa: F401,E402


def replacement(s, **changes):
    arguments = {
        'request_id': 'replace-root', 'name': 'Writer v2',
        'purpose': 'Continue the fantasy series with a clearer voice.',
        'reason': 'The ongoing role needs a clean operating context.', **changes,
        'handoff': 'Review the predecessor series outline and continue open planning items.',
    }
    return replace(s.conn, actor=OWNER, predecessor_id=s.root['id'], **arguments)


def test_replacement_creates_successor_and_retires_old_subtree_atomically(broker):
    s = broker
    child = create_root(
        s.conn, actor=OWNER, request_id='replacement-child', name='Researcher',
        purpose='Research the old series.', parent_id=s.root['id'],
        work={'timeout_seconds': 30, 'max_iterations': 3},
    )
    cadence.configure(
        s.conn, actor=OWNER, agent_id=s.root['id'], expected_revision=1,
        interval_seconds=90, enabled=True,
    )

    result = replacement(s)

    predecessor = result['predecessor']
    successor = result['successor']
    assert predecessor['retirement']['source'] == 'owner'
    assert predecessor['retirement']['replacement_id'] == result['replacement_id']
    assert get_root(s.conn, actor=OWNER, agent_id=child['id'])['retirement']['source'] == 'parent'
    assert successor['id'] != predecessor['id']
    assert successor['parent_id'] == predecessor['parent_id']
    assert successor['replacement'] == {
        'id': result['replacement_id'], 'predecessor_id': predecessor['id'],
        'reason': 'The ongoing role needs a clean operating context.',
        'handoff': 'Review the predecessor series outline and continue open planning items.',
        'created_at': successor['replacement']['created_at'], 'role': 'successor',
    }
    assert predecessor['replacement']['successor_id'] == successor['id']
    assert successor['work']['limits'] == predecessor['work']['limits']
    assert successor['model_selection']['provider'] == predecessor['model_selection']['provider']
    assert successor['autonomy']['level'] == predecessor['autonomy']['level']
    assert successor['cadence']['enabled'] is True
    assert successor['cadence']['interval_seconds'] == 90

    replay = replacement(s)
    assert replay['successor']['id'] == successor['id']


def test_replacement_is_all_or_nothing_when_descendant_needs_owner_answer(broker):
    s = broker
    child = create_root(
        s.conn, actor=OWNER, request_id='replacement-question-child', name='Researcher',
        purpose='Research the old series.', parent_id=s.root['id'],
    )
    s.conn.execute(
        'INSERT INTO agent_native_questions '
        '(id,agent_id,soul_revision,run_id,item_id,fingerprint,topic,question,created_at) '
        'VALUES(?,?,?,?,?,?,?,?,?)',
        ('replacement-question', child['id'], 1, 'child-run', 'child-item', 'fingerprint',
         'scope', 'Should this responsibility be transferred?', child['created_at']),
    )

    with pytest.raises(ValueError, match='descendant has an unanswered question'):
        replacement(s)

    assert get_root(s.conn, actor=OWNER, agent_id=s.root['id'])['retirement'] is None
    assert s.conn.execute('SELECT count(*) FROM agent_native_replacements').fetchone()[0] == 0


def test_replacement_request_cannot_be_reused_with_different_input(broker):
    s = broker
    replacement(s)

    with pytest.raises(ConflictError, match='different input'):
        replacement(s, reason='A different reason.')


def test_owner_api_replaces_agent_and_replays_after_predecessor_retires(client):
    predecessor = client.post(URL, json={
        **BODY, 'request_id': 'replacement-api-predecessor',
        'work': {'timeout_seconds': 30, 'max_iterations': 3},
    }).json()
    body = {
        'request_id': 'replacement-api', 'name': 'Successor',
        'purpose': 'Continue the role with a clean context.',
        'reason': 'Owner selected a new operating approach.',
        'handoff': 'Review retained strategy outputs and reconsider the open research item.',
    }

    response = client.post(f"{URL}/{predecessor['id']}/replace", json=body)

    assert response.status_code == 201
    result = response.json()
    assert result['predecessor']['retirement']['source'] == 'owner'
    assert result['successor']['replacement']['predecessor_id'] == predecessor['id']
    replay = client.post(f"{URL}/{predecessor['id']}/replace", json=body)
    assert replay.status_code == 201
    assert replay.json()['successor']['id'] == result['successor']['id']


def child_replacement(s, child_id, call_id='replace-child'):
    return s.run._effect(s.conn, s.planning, effect(s, call_id, 'child_replace', {
        'child_id': child_id, 'name': 'Lore researcher v2',
        'purpose': 'Continue delegated lore research with a clean context.',
        'reason': 'The parent selected a new research approach.',
        'handoff': 'Review the retained lore index and continue the open chronology task.',
    }))


def test_managed_parent_receives_bounded_direct_child_replacement_tool():
    schema = next(
        tool['function'] for tool in tool_schemas()
        if tool['function']['name'] == 'child_replace'
    )

    assert schema['parameters']['required'] == [
        'child_id', 'name', 'purpose', 'reason', 'handoff',
    ]
    assert schema['parameters']['additionalProperties'] is False


def test_accountable_parent_replaces_its_direct_child(broker):
    s = broker
    prepare_frozen_parent(s)
    child_id = delegate(s)['child_id']

    result = child_replacement(s, child_id)

    predecessor = get_root(s.conn, actor=OWNER, agent_id=child_id)
    successor = get_root(s.conn, actor=OWNER, agent_id=result['successor_id'])
    assert result['predecessor_id'] == child_id
    assert predecessor['retirement']['source'] == 'parent'
    assert predecessor['retirement']['decision_agent_id'] == s.root['id']
    assert successor['parent_id'] == s.root['id']
    assert successor['replacement']['handoff'] == result['handoff']
    assert successor['work']['limits'] == predecessor['work']['limits']
    assert child_replacement(s, child_id)['successor_id'] == successor['id']


def test_parent_cannot_replace_a_non_direct_descendant(broker):
    s = broker
    prepare_frozen_parent(s)
    child_id = delegate(s)['child_id']
    grandchild = create_root(
        s.conn, actor=OWNER, request_id='replacement-grandchild', name='Grandchild',
        purpose='Continue nested work.', parent_id=child_id,
    )

    with pytest.raises(PermissionError, match='direct child'):
        child_replacement(s, grandchild['id'])

    assert get_root(s.conn, actor=OWNER, agent_id=grandchild['id'])['retirement'] is None
