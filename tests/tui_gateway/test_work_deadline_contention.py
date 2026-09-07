"""Native worker deadlines remain effective while the control writer is locked."""
from contextlib import ExitStack, contextmanager
import time

from agent_native.identity import OWNER, create_root
from agent_native.work_service import WorkService, _Run
from hermes_cli.kanban_db_connect import connect_closing, write_txn
from tests.tui_gateway.test_work_worker import (
    eventually, model as model_fixture, worker as worker_fixture,
)


def test_two_native_workers_expire_while_control_db_settlement_is_blocked(tmp_path):
    with ExitStack() as resources:
        workers = []
        models = []
        for index in range(2):
            model = resources.enter_context(contextmanager(model_fixture.__wrapped__)())
            model.hold = True
            area = tmp_path / str(index)
            area.mkdir()
            worker = resources.enter_context(contextmanager(worker_fixture.__wrapped__)(area, model))
            workers.append(worker)
            models.append(model)

        db_path = tmp_path / 'control.db'
        service = WorkService(db_path, tmp_path / 'control-home' / 'agent-native')
        runs = []
        with connect_closing(db_path) as conn:
            for index, worker in enumerate(workers):
                model = models[index]
                root = create_root(conn, actor=OWNER, request_id=str(index), name='Writer',
                                   purpose='Write a fantasy story.',
                                   work={'timeout_seconds': 12, 'max_iterations': 8})
                with write_txn(conn):
                    conn.execute("UPDATE agent_native_work_runs SET state='running' WHERE id=?",
                                 (root['work']['id'],))
                run = _Run(service, root['work'])
                # Reuse the real native-worker fixture's isolated provider setup
                # and private admission transport. The production _Run owns its
                # actual HostSupervisor; no worker/model loop is substituted.
                run.host = worker.host
                worker.attempt['deadline_monotonic'] = run.deadline
                worker.start()
                eventually(lambda: model.entered.is_set() or worker.result, bool)
                assert model.entered.is_set(), worker.result
                runs.append(run)
                service.runs[run.work['id']] = run

        processes = [worker.host._proc for worker in workers]
        assert all(proc is not None and proc.poll() is None for proc in processes)
        # Exercise the existing shared monitor too: it will kill the first run,
        # then wait for this real SQLite writer before persisting its stop state.
        with connect_closing(db_path) as blocker:
            blocker.execute('BEGIN IMMEDIATE')
            service.thread.start()
            try:
                remaining = max(run.deadline for run in runs) - time.monotonic()
                codes = eventually(lambda: [proc.poll() for proc in processes],
                                   lambda values: all(code is not None for code in values),
                                   timeout=max(0, remaining) + 2)
                assert all(code is not None for code in codes)
                assert all(model.disconnected.wait(1) for model in models)
                assert blocker.in_transaction
                assert [row[0] for row in blocker.execute(
                    'SELECT state FROM agent_native_work_runs ORDER BY created_at'
                )] == ['running', 'running']
            finally:
                blocker.rollback()
                service.stop()
        with connect_closing(db_path) as conn:
            states = conn.execute('SELECT state,summary FROM agent_native_work_runs').fetchall()
            assert all(state == 'paused' and 'time limit' in summary for state, summary in states)
        assert all(not worker.effects for worker in workers)
