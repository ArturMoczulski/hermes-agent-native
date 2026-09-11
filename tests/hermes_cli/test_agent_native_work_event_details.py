"""Per-operation detail survives on activity events for the dashboard Activity tab.

The Activity tab needs to render more than ``Repository operation: <tool>`` for
the three repository tools. ``state.event`` records an immutable event with a
human-readable ``summary``; the same row may carry an optional ``detail`` JSON
payload so the dashboard can show the actual path, argv, exit code, byte
count, and sha256 without re-reading the work run.
"""

import json
from uuid import uuid4

import pytest
from agent_native.identity import OWNER, create_root
from agent_native.startup import prepare, read_setup
from agent_native import work_state
from hermes_cli.kanban_db_connect import connect_closing, write_txn
from tests.hermes_cli.writer_plane_fixture import writer_plane_server


@pytest.fixture
def provisioned_agent(tmp_path, monkeypatch):
    """A minimal work run with no broker or planning context — just identity + work_state."""
    profile = tmp_path / 'native-profile'
    profile.mkdir()
    monkeypatch.setenv('HERMES_HOME', str(profile))
    (profile / 'config.yaml').write_text(json.dumps({
        'model': {'provider': 'custom:detail-fixture', 'default': 'fixture-model'},
        'custom_providers': [{'name': 'detail-fixture',
                              'base_url': 'http://127.0.0.1:18883/v1',
                              'api_key': 'fixture-only'}],
    }))
    with writer_plane_server() as plane:
        home = tmp_path / 'agent-native'
        home.mkdir(mode=0o700)
        config = home / 'plane-setup.json'
        config.write_text(json.dumps(plane.config))
        config.chmod(0o600)
        db_path = tmp_path / 'control.db'
        with connect_closing(db_path) as conn:
            root = create_root(conn, actor=OWNER, request_id='event-detail',
                               name='Detail', purpose='Test detail round-trip.')
            prepare(conn, actor=OWNER, agent_id=root['id'], home=home)
            work = work_state.configure(conn, actor=OWNER, agent_id=root['id'],
                                        expected_revision=1,
                                        limits={'timeout_seconds': 60, 'max_iterations': 8})
            yield type('S', (), {'home': home, 'db_path': db_path, 'conn': conn,
                                 'root': root, 'work': work})()


def test_state_event_persists_structured_detail_alongside_summary(provisioned_agent):
    """A ``detail`` kwarg on ``state.event`` is stored as JSON and round-trips through read_work."""
    s = provisioned_agent
    detail = {'path': 'package.json', 'bytes': 812, 'sha256': 'a' * 64,
              'operation': 'repository_file_write'}
    work_state.event(s.conn, s.work['id'], 'work.effect',
                     'Wrote package.json (812 bytes, sha256 aaaa…)', detail=detail)

    rows = s.conn.execute(
        'SELECT kind, summary, detail FROM agent_native_work_events '
        'WHERE run_id=? AND kind=? ORDER BY id DESC LIMIT 1',
        (s.work['id'], 'work.effect')).fetchall()
    assert len(rows) == 1
    kind, summary, raw_detail = rows[0]
    assert kind == 'work.effect'
    assert summary == 'Wrote package.json (812 bytes, sha256 aaaa…)'
    assert json.loads(raw_detail) == detail

    # read_work must expose the structured detail on each event.
    work = work_state.read_work(s.conn, s.root['id'])
    [event] = [e for e in work['events'] if e['kind'] == 'work.effect']
    assert event['detail'] == detail


def test_state_event_without_detail_remains_compatible(provisioned_agent):
    """Existing callers that omit ``detail`` see a None / no-detail event — no migration friction."""
    s = provisioned_agent
    work_state.event(s.conn, s.work['id'], 'work.model', 'Model step 1')
    [raw] = s.conn.execute(
        'SELECT detail FROM agent_native_work_events '
        'WHERE run_id=? AND kind=?', (s.work['id'], 'work.model')).fetchall()
    assert raw[0] is None


def test_migration_adds_detail_column_to_a_pre_existing_event_row(tmp_path, monkeypatch):
    """A row written before the ``detail`` column exists survives the migration unchanged."""
    profile = tmp_path / 'native-profile'
    profile.mkdir()
    monkeypatch.setenv('HERMES_HOME', str(profile))
    (profile / 'config.yaml').write_text(json.dumps({
        'model': {'provider': 'custom:detail-migration', 'default': 'fixture-model'},
        'custom_providers': [{'name': 'detail-migration',
                              'base_url': 'http://127.0.0.1:18883/v1',
                              'api_key': 'fixture-only'}],
    }))
    with writer_plane_server() as plane:
        home = tmp_path / 'agent-native'
        home.mkdir(mode=0o700)
        (home / 'plane-setup.json').write_text(json.dumps(plane.config))
        db_path = tmp_path / 'control.db'
        with connect_closing(db_path) as conn:
            root = create_root(conn, actor=OWNER, request_id='detail-migration',
                               name='Migrator', purpose='Test schema migration.')
            prepare(conn, actor=OWNER, agent_id=root['id'], home=home)
            work = work_state.configure(conn, actor=OWNER, agent_id=root['id'],
                                        expected_revision=1,
                                        limits={'timeout_seconds': 60, 'max_iterations': 8})
            # Drop the column to simulate an older schema; insert an event.
            with write_txn(conn):
                conn.execute('ALTER TABLE agent_native_work_events DROP COLUMN detail')
                conn.execute(
                    "INSERT INTO agent_native_work_events(run_id,kind,summary,created_at) "
                    "VALUES (?,?,?,?)",
                    (work['id'], 'work.legacy', 'Legacy event before detail column.', '2099-01-01T00:00:00+00:00'))

        # Reopen: work_state must run the migration transparently and the legacy row must still be readable.
        with connect_closing(db_path) as conn:
            work_state.migrate_event_detail(conn)
            legacy = conn.execute(
                "SELECT summary FROM agent_native_work_events "
                "WHERE run_id=? AND kind='work.legacy'",
                (work['id'],)).fetchone()[0]
            assert legacy == 'Legacy event before detail column.'
            columns = {row[1] for row in conn.execute(
                "PRAGMA table_info(agent_native_work_events)").fetchall()}
            assert 'detail' in columns

            # And the column is nullable / usable for new events.
            work_state.event(conn, work['id'], 'work.effect', 'New event after migration.',
                             detail={'path': 'README.md'})
            [new] = conn.execute(
                "SELECT detail FROM agent_native_work_events "
                "WHERE run_id=? AND kind='work.effect'", (work['id'],)).fetchall()
            assert json.loads(new[0]) == {'path': 'README.md'}


def test_repository_file_write_event_carries_path_bytes_and_sha(provisioned_agent, tmp_path):
    """A real ``repository_file_write`` records an event whose ``detail`` exposes the path/bytes/sha.

    This is the contract the Activity tab renders against: it must not have to
    re-read the work run or guess at the file. The detail is structured JSON,
    not a free-form summary.
    """
    from agent_native.builder_repository import write_file as builder_write_file
    from agent_native.project_workspace import grant as grant_project
    from agent_native.repository_access import active_repository

    s = provisioned_agent
    project = tmp_path / 'fantasy-game'
    project.mkdir()

    # Grant the agent an isolated project workspace like the real path does.
    grant_project(s.conn, actor=OWNER, agent_id=s.root['id'],
                  expected_revision=1, root=str(project))
    workspace = active_repository(s.conn, s.root['id'])

    observed = builder_write_file(workspace, {'path': 'package.json',
                                              'content': '{"name":"y"}\n',
                                              'expected_sha256': 'missing'})

    # The work service is what produces the activity event in production.
    # Replay its summary-derivation logic against the real builder result.
    from agent_native.work_service import _derive_repository_event_detail
    detail = _derive_repository_event_detail('repository_file_write', observed, {}, workspace)
    work_state.event(s.conn, s.work['id'], 'work.effect',
                     f'Wrote package.json ({observed["bytes"]} bytes)', detail=detail)

    work = work_state.read_work(s.conn, s.root['id'])
    [event] = [e for e in work['events'] if e['kind'] == 'work.effect']
    assert event['detail']['operation'] == 'repository_file_write'
    assert event['detail']['path'] == 'package.json'
    assert event['detail']['bytes'] == observed['bytes']
    assert event['detail']['sha256'] == observed['sha256']
    # The activity row carries the workspace's short name, not the resolved path,
    # so the Activity tab stays readable regardless of where the project lives.
    assert event['detail']['workspace'] == project.resolve().name
