"""Owner work configuration and durable activation through the real HTTP boundary."""
from tests.hermes_cli.test_agent_native_api import client, URL, BODY  # noqa: F401

LIMITS = {'timeout_seconds': 300, 'max_iterations': 20}


def test_creation_configures_one_initial_attempt_and_pause_is_durable(client):
    body = {**BODY, 'work': LIMITS}
    created = client.post(URL, json=body)
    assert created.status_code == 201
    agent = created.json()
    work = agent['work']
    assert work['state'] == 'queued' and work['limits'] == LIMITS
    assert work['model_calls'] == 0 and work['session_id'].startswith('an_work_')
    assert client.post(URL, json=body).json()['work']['id'] == work['id']
    changed = {**body, 'work': {**LIMITS, 'max_iterations': 10}}
    assert client.post(URL, json=changed).status_code == 409
    paused = client.post(URL+'/'+agent['id']+'/work/pause')
    assert paused.status_code == 200 and paused.json()['work']['state'] == 'paused'
    assert client.get(URL+'/'+agent['id']).json()['work']['state'] == 'paused'
    again = client.post(URL+'/'+agent['id']+'/work/pause').json()['work']
    assert len(again['events']) == len(paused.json()['work']['events'])


def test_configure_existing_agent_requires_current_owner_revision(client):
    agent = client.post(URL, json=BODY).json()
    assert agent['work'] is None
    path = URL+'/'+agent['id']+'/work'
    assert client.post(path, json={**LIMITS, 'expected_revision': 2}).status_code == 409
    configured = client.post(path, json={**LIMITS, 'expected_revision': 1})
    assert configured.status_code == 200
    assert configured.json()['work']['limits'] == LIMITS
    client.headers.pop('X-Hermes-Session-Token')
    assert client.post(path, json={**LIMITS, 'expected_revision': 1}).status_code == 401
    assert client.post(path+'/pause').status_code == 401


def test_invalid_limits_and_forged_run_authority_are_rejected(client):
    for bad in [{'timeout_seconds': 0, 'max_iterations': 20}, {'timeout_seconds': True, 'max_iterations': 20},
                {'timeout_seconds': 300, 'max_iterations': -1}, {**LIMITS, 'actor': 'owner'}]:
        assert client.post(URL, json={**BODY, 'work': bad}).status_code == 422
    assert client.get(URL).json() == []


def test_creation_retry_uses_original_chat_only_input_after_later_work_configuration(client):
    agent = client.post(URL, json=BODY).json()
    configured = client.post(URL + '/' + agent['id'] + '/work',
                             json={**LIMITS, 'expected_revision': 1}).json()
    paused = client.post(URL + '/' + agent['id'] + '/work/pause').json()
    retry = client.post(URL, json=BODY)
    assert retry.status_code == 201, retry.text
    assert retry.json()['id'] == agent['id']
    assert retry.json()['work']['id'] == configured['work']['id']
    assert retry.json()['work'] == paused['work']
    # Matching today's run limits is still different from the original request.
    assert client.post(URL, json={**BODY, 'work': LIMITS}).status_code == 409
    assert len(client.get(URL).json()) == 1


def test_creation_retry_keeps_original_work_limits_after_pause(client):
    original = {**BODY, 'work': LIMITS}
    agent = client.post(URL, json=original).json()
    paused = client.post(URL + '/' + agent['id'] + '/work/pause').json()
    retry = client.post(URL, json={**BODY, 'work': dict(reversed(list(LIMITS.items())))})
    assert retry.status_code == 201
    assert retry.json()['work'] == paused['work']
    assert client.post(URL, json=BODY).status_code == 409
    assert client.post(URL, json={**BODY, 'work': {**LIMITS, 'timeout_seconds': 200}}).status_code == 409


def test_pre_upgrade_creation_without_original_work_record_still_retries_as_chat_only(client):
    from uuid import uuid4
    from hermes_cli.kanban_db_connect import connect_closing
    agent_id, activation_id = str(uuid4()), str(uuid4())
    with connect_closing(board='default') as conn:
        # The pre-work schema stored identity and its activation, but no original
        # work configuration. Reopening installs additive tables, not new intent.
        conn.execute('INSERT INTO agent_native_agents '
                     '(id,request_id,name,initial_purpose,purpose,soul_revision,execution,created_at) '
                     'VALUES (?,?,?,?,?,1,?,?)',
                     (agent_id, BODY['request_id'], BODY['name'], BODY['purpose'], BODY['purpose'],
                      'not_started', '2026-09-07T00:00:00+00:00'))
        conn.execute('INSERT INTO agent_native_initial_activations '
                     '(id,agent_id,cause,soul_revision,requested_at) VALUES (?,?,?,1,?)',
                     (activation_id, agent_id, 'creation', '2026-09-07T00:00:00+00:00'))
    configured = client.post(URL + '/' + agent_id + '/work',
                             json={**LIMITS, 'expected_revision': 1})
    assert configured.status_code == 200
    retry = client.post(URL, json=BODY)
    assert retry.status_code == 201, retry.text
    assert retry.json()['work']['id'] == configured.json()['work']['id']
    assert retry.json()['setup'] is None
    assert client.post(URL, json={**BODY, 'work': LIMITS}).status_code == 409


def test_execution_summary_tracks_the_durable_work_state(client):
    agent = client.post(URL, json={**BODY, 'work': LIMITS}).json()
    assert agent['execution'] == 'queued'
    paused = client.post(URL+'/'+agent['id']+'/work/pause').json()
    assert paused['execution'] == 'paused'


def test_output_reader_scopes_agent_and_version_and_requires_owner(client, tmp_path):
    from agent_native.output_store import publish
    from hermes_cli.kanban_db_connect import connect_closing
    agent = client.post(URL, json={**BODY, 'work': LIMITS}).json()
    other = client.post(URL, json={**BODY, 'request_id': 'another-agent'}).json()
    workspace = tmp_path / 'outputs-workspace'
    workspace.mkdir(mode=0o700)
    with connect_closing(board='default') as conn:
        output = publish(conn, validate=lambda conn: None, workspace=workspace,
                         agent_id=agent['id'], run_id=agent['work']['id'], call_id='seed-output',
                         item_id='isolated-fixture-item', title='Supplied analysis', content='Growth: 25%', format='text')
    suffix = '/outputs/'+output['output_id']+'/versions/1'
    own = client.get(URL+'/'+agent['id']+suffix)
    assert own.status_code == 200 and own.json()['content'] == 'Growth: 25%'
    assert own.json()['format'] == 'text'
    assert client.get(URL+'/'+other['id']+suffix).status_code == 404
    assert client.get(URL+'/'+agent['id']+suffix[:-1]+'2').status_code == 404
    client.headers.pop('X-Hermes-Session-Token')
    assert client.get(URL+'/'+agent['id']+suffix).status_code == 401
