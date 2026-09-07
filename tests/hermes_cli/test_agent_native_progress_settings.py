"""Owner reporting settings through real routes and isolated storage."""
from tests.hermes_cli.test_agent_native_model_settings import configured, client, URL, BODY  # noqa: F401


def test_reporting_settings_reject_stale_invalid_and_untrusted_changes(configured):
    c = configured
    root = c.post(URL, json=BODY).json()
    path = URL + '/' + root['id'] + '/progress-settings'
    initial = c.get(path).json()
    assert initial['verbosity'] == 'standard'
    assert c.put(path, json={'verbosity': 'detailed', 'expected_revision': initial['revision']}).status_code == 200
    updated = c.get(path).json()
    assert updated['verbosity'] == 'detailed'
    assert c.put(path, json={'verbosity': 'concise', 'expected_revision': initial['revision']}).status_code == 409
    assert c.put(path, json={'verbosity': 'everything', 'expected_revision': updated['revision']}).status_code == 422
    assert c.get(path).json() == updated
    c.headers.pop('X-Hermes-Session-Token')
    assert c.get(path).status_code == 401
    assert c.put(path, json={'verbosity': 'concise', 'expected_revision': updated['revision']}).status_code == 401
