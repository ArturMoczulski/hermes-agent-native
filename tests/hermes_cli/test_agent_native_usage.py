"""Focused acceptance tests for durable Agent Native model usage."""

import json
from uuid import uuid4

import pytest

from agent_native.identity import OWNER, create_root, get_root
from agent_native.usage import record
from agent_native.work_state import read_work
from hermes_cli.kanban_db_connect import connect_closing, write_txn


@pytest.fixture
def db(tmp_path):
    with connect_closing(tmp_path / 'control.db') as conn:
        yield conn


def _run(conn, agent_id):
    activation = conn.execute(
        'SELECT id FROM agent_native_initial_activations WHERE agent_id=?', (agent_id,)).fetchone()[0]
    run_id = str(uuid4())
    with write_txn(conn):
        conn.execute(
            'INSERT INTO agent_native_work_runs '
            '(id,agent_id,activation_id,soul_revision,session_id,limits,state,created_at) '
            'VALUES (?,?,?,?,?,?,?,?)',
            (run_id, agent_id, activation, 1, 'usage_' + uuid4().hex,
             json.dumps({'timeout_seconds': 180, 'max_iterations': 50}),
             'completed', '2026-09-10T12:00:00+00:00'))
    return run_id


def _usage(**changes):
    value = dict(provider='openai-codex', model='gpt-5.6-sol', api_calls=2,
                 input_tokens=120, output_tokens=30, cache_read_tokens=80,
                 cache_write_tokens=0, reasoning_tokens=10,
                 estimated_cost_usd=0.0, actual_cost_usd=None,
                 cost_status='included', cost_source='subscription')
    value.update(changes)
    return value


def test_absolute_run_usage_is_idempotent_and_visible_with_work(db):
    root = create_root(db, actor=OWNER, request_id='usage-root', name='Builder', purpose='Build.')
    run_id = _run(db, root['id'])

    record(db, run_id=run_id, agent_id=root['id'], usage=_usage())
    record(db, run_id=run_id, agent_id=root['id'], usage=_usage(input_tokens=150, api_calls=3))

    work = read_work(db, root['id'])
    assert work['usage']['input_tokens'] == 150
    assert work['usage']['api_calls'] == 3
    assert get_root(db, actor=OWNER, agent_id=root['id'])['usage']['agent'] == {
        'record_count': 1, 'api_calls': 3, 'input_tokens': 150, 'output_tokens': 30,
        'cache_read_tokens': 80, 'cache_write_tokens': 0, 'reasoning_tokens': 10,
        'estimated_cost_usd': 0.0, 'actual_cost_usd': None, 'cost_kind': 'included'}


def test_subtree_usage_rolls_up_descendants_but_direct_usage_stays_separate(db):
    root = create_root(db, actor=OWNER, request_id='usage-parent', name='Leader', purpose='Lead.')
    child = create_root(db, actor=OWNER, request_id='usage-child', name='Worker', purpose='Work.',
                        parent_id=root['id'])
    root_run, child_run = _run(db, root['id']), _run(db, child['id'])
    record(db, run_id=root_run, agent_id=root['id'], usage=_usage(input_tokens=100))
    record(db, run_id=child_run, agent_id=child['id'], usage=_usage(
        provider='minimax', model='MiniMax-M3', input_tokens=250,
        estimated_cost_usd=None, cost_status='unknown', cost_source='none'))

    totals = get_root(db, actor=OWNER, agent_id=root['id'])['usage']
    assert totals['agent']['input_tokens'] == 100
    assert totals['agent']['record_count'] == 1
    assert totals['subtree']['input_tokens'] == 350
    assert totals['subtree']['record_count'] == 2
    assert totals['subtree']['cost_kind'] == 'estimated'


def test_usage_rejects_mismatched_agent_and_invalid_counters(db):
    root = create_root(db, actor=OWNER, request_id='usage-owner', name='Owner', purpose='Own.')
    other = create_root(db, actor=OWNER, request_id='usage-other', name='Other', purpose='Other.')
    run_id = _run(db, root['id'])

    with pytest.raises(PermissionError):
        record(db, run_id=run_id, agent_id=other['id'], usage=_usage())
    with pytest.raises(ValueError):
        record(db, run_id=run_id, agent_id=root['id'], usage=_usage(input_tokens=-1))
