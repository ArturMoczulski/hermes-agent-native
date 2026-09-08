"""Focused autonomy persistence, revision, and admitted-attempt policy tests."""
from tests.hermes_cli.test_agent_native_model_settings import configured, client, URL, BODY  # noqa: F401


def test_creation_defaults_to_balanced_autonomy_and_owner_can_change_it(configured):
    c = configured
    root = c.post(URL, json=BODY).json()
    path = URL + '/' + root['id'] + '/autonomy'
    assert root['autonomy']['level'] == 3
    assert root['autonomy']['require_owner_review'] is False
    initial = c.get(path).json()
    changed = c.put(path, json={'level': 2, 'require_owner_review': True,
                                'expected_revision': initial['revision']})
    assert changed.status_code == 200
    assert changed.json()['autonomy']['level'] == 2
    assert changed.json()['autonomy']['require_owner_review'] is True
    assert c.put(path, json={'level': 3, 'require_owner_review': False,
                             'expected_revision': initial['revision']}).status_code == 409
    assert c.put(path, json={'level': 6, 'require_owner_review': False,
                             'expected_revision': 2}).status_code == 422


def test_creation_idempotency_includes_autonomy_level(configured):
    c = configured
    body = {**BODY, 'autonomy_level': 2}
    first = c.post(URL, json=body)
    assert first.status_code == 201
    assert c.post(URL, json=body).json()['id'] == first.json()['id']
    assert c.post(URL, json={**body, 'autonomy_level': 5}).status_code == 409


def test_attempt_keeps_admitted_autonomy_after_setting_changes(configured):
    from agent_native import autonomy
    from hermes_cli.kanban_db_connect import connect_closing
    from agent_native.identity import OWNER
    root = configured.post(URL, json={**BODY, 'autonomy_level': 4,
                                     'work': {'timeout_seconds': 60, 'max_iterations': 2}}).json()
    run_id = root['work']['id']
    with connect_closing(board='default') as conn:
        first = autonomy.snapshot_attempt(conn, root['id'], run_id, 'admission-one')
        autonomy.change_settings(conn, actor=OWNER, agent_id=root['id'], level=1,
                                 require_owner_review=True, expected_revision=1)
        assert autonomy.snapshot_attempt(conn, root['id'], run_id, 'admission-one') == first
        second=autonomy.snapshot_attempt(conn, root['id'], run_id, 'admission-two')
        assert second['level'] == 1 and second['require_owner_review'] is True
