"""Real Kanban database acceptance for the first protected identity slice."""
import pytest
from hermes_cli import kanban_db_connect as kanban_db
from agent_native.identity import OWNER, ConflictError, create_root, get_root, revise_soul, events


@pytest.fixture
def db(tmp_path):
    with kanban_db.connect_closing(tmp_path / 'control.db') as conn:
        yield conn


def create(conn, **changes):
    args = dict(actor=OWNER, request_id='first', name='Artist', purpose='Create metal music')
    args.update(changes)
    return create_root(conn, **args)


def test_creation_survives_restart_and_is_idempotent(tmp_path):
    path = tmp_path / 'control.db'
    with kanban_db.connect_closing(path) as conn:
        first = create(conn)
        assert create(conn) == first
        assert first['execution'] == 'not_started'
        assert len(events(conn, actor=OWNER, agent_id=first['id'])) == 1
    with kanban_db.connect_closing(path) as conn:
        assert get_root(conn, actor=OWNER, agent_id=first['id']) == first
        second = create(conn, request_id='second')
        assert second['id'] != first['id']
        assert second['name'] == first['name']


@pytest.mark.parametrize('actor', [None, 'human', {'role': 'owner'}, object()])
def test_untrusted_actors_cannot_create_read_or_revise(db, actor):
    root = create(db)
    for operation in [
        lambda: create(db, actor=actor),
        lambda: get_root(db, actor=actor, agent_id=root['id']),
        lambda: revise_soul(db, actor=actor, agent_id=root['id'], expected_revision=1, purpose='Changed'),
        lambda: events(db, actor=actor, agent_id=root['id']),
    ]:
        with pytest.raises(PermissionError):
            operation()
    assert get_root(db, actor=OWNER, agent_id=root['id']) == root


def test_reused_creation_request_cannot_change_purpose(db):
    root = create(db)
    with pytest.raises(ConflictError):
        create(db, purpose='Something else')
    assert get_root(db, actor=OWNER, agent_id=root['id']) == root


def test_owner_revision_is_compare_and_swap_and_retains_history(db):
    root = create(db)
    updated = revise_soul(db, actor=OWNER, agent_id=root['id'], expected_revision=1, purpose='Compose an album')
    assert updated['purpose'] == 'Compose an album'
    assert updated['soul_revision'] == 2
    with pytest.raises(ConflictError):
        revise_soul(db, actor=OWNER, agent_id=root['id'], expected_revision=1, purpose='Stale change')
    history = events(db, actor=OWNER, agent_id=root['id'])
    assert [e['kind'] for e in history] == ['agent.created', 'agent.soul_revised']
    assert [e['purpose'] for e in history] == ['Create metal music', 'Compose an album']


@pytest.mark.parametrize('field', ['request_id', 'name', 'purpose'])
def test_blank_input_rejected(db, field):
    with pytest.raises(ValueError):
        create(db, **{field: '  '})


def test_event_failure_rolls_back_identity(db):
    # Force an actual database failure at the event boundary, not a mocked transaction.
    db.execute("CREATE TRIGGER reject_agent_event BEFORE INSERT ON agent_native_events BEGIN SELECT RAISE(ABORT, 'event unavailable'); END")
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        create(db)
    assert db.execute('SELECT count(*) FROM agent_native_agents').fetchone()[0] == 0
    assert db.execute('SELECT count(*) FROM agent_native_initial_activations').fetchone()[0] == 0


def test_failed_revision_event_preserves_previous_soul(db):
    root = create(db)
    db.execute("CREATE TRIGGER reject_revision_event BEFORE INSERT ON agent_native_events BEGIN SELECT RAISE(ABORT, 'event unavailable'); END")
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        revise_soul(db, actor=OWNER, agent_id=root['id'], expected_revision=1, purpose='Unsaved')
    assert get_root(db, actor=OWNER, agent_id=root['id']) == root
    assert len(events(db, actor=OWNER, agent_id=root['id'])) == 1


def test_concurrent_retries_create_one_agent(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    path = tmp_path / 'control.db'
    kanban_db.init_db(path)

    def attempt(_):
        with kanban_db.connect_closing(path) as conn:
            return create(conn)['id']

    with ThreadPoolExecutor(max_workers=4) as pool:
        ids = list(pool.map(attempt, range(4)))
    assert len(set(ids)) == 1
    with kanban_db.connect_closing(path) as conn:
        assert len(events(conn, actor=OWNER, agent_id=ids[0])) == 1


def test_creation_records_initial_review_once_across_retries_and_restart(tmp_path):
    path = tmp_path / 'activation.db'
    with kanban_db.connect_closing(path) as conn:
        root = create(conn)
        startup = root.get('startup')
        assert startup is not None, 'Creating an agent must durably request its first review'
        assert startup['cause'] == 'creation'
        assert startup['soul_revision'] == root['soul_revision']
        assert startup['requested_at']
        assert create(conn)['startup'] == startup
        assert root['execution'] == 'not_started'  # A request is not observed execution.
    with kanban_db.connect_closing(path) as conn:
        assert get_root(conn, actor=OWNER, agent_id=root['id'])['startup'] == startup
        assert conn.execute('SELECT COUNT(*) FROM agent_native_initial_activations WHERE agent_id = ?', (root['id'],)).fetchone()[0] == 1


def test_concurrent_creation_retries_share_one_initial_review(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    path = tmp_path / 'activation-race.db'
    kanban_db.init_db(path)
    def attempt(_):
        with kanban_db.connect_closing(path) as conn:
            return create(conn)
    with ThreadPoolExecutor(max_workers=4) as pool:
        roots = list(pool.map(attempt, range(4)))
    assert all(root.get('startup') is not None for root in roots)
    assert len({root['startup']['id'] for root in roots}) == 1


def test_retried_creation_after_purpose_edit_does_not_request_old_work(db):
    root = create(db)
    startup = root.get('startup')
    assert startup is not None
    revise_soul(db, actor=OWNER, agent_id=root['id'], expected_revision=1, purpose='Write mysteries')
    retry = create(db)
    assert retry['purpose'] == 'Write mysteries'
    assert retry['startup'] == startup  # Historical request stays bound to its original revision.
    assert retry['startup']['soul_revision'] != retry['soul_revision']
    assert db.execute('SELECT COUNT(*) FROM agent_native_initial_activations').fetchone()[0] == 1


def test_failed_initial_review_rolls_back_entire_creation(db):
    import sqlite3
    db.execute("CREATE TRIGGER reject_startup BEFORE INSERT ON agent_native_initial_activations BEGIN SELECT RAISE(ABORT, 'startup unavailable'); END")
    with pytest.raises(sqlite3.IntegrityError):
        create(db)
    assert db.execute('SELECT COUNT(*) FROM agent_native_agents').fetchone()[0] == 0
    assert db.execute('SELECT COUNT(*) FROM agent_native_events').fetchone()[0] == 0
    assert db.execute('SELECT COUNT(*) FROM agent_native_initial_activations').fetchone()[0] == 0


def test_existing_inactive_record_is_not_activated_by_read_or_creation_retry(db):
    # An existing pre-startup record has identity/history but no initial intent.
    db.execute("INSERT INTO agent_native_agents VALUES ('old-agent', 'first', 'Artist', 'Create metal music', 'Create metal music', 1, 'not_started', '2026-09-05T12:00:00+00:00')")
    db.execute("INSERT INTO agent_native_events (agent_id, kind, soul_revision, purpose, actor, created_at) VALUES ('old-agent', 'agent.created', 1, 'Create metal music', 'owner', '2026-09-05T12:00:00+00:00')")
    assert get_root(db, actor=OWNER, agent_id='old-agent')['startup'] is None
    assert create(db)['startup'] is None
    assert db.execute('SELECT COUNT(*) FROM agent_native_initial_activations').fetchone()[0] == 0
    assert len(events(db, actor=OWNER, agent_id='old-agent')) == 1
