"""Dashboard-owned setup worker. No model loop, cadence or browser-owned job."""
import logging
from pathlib import Path
import threading

from agent_native.identity import OWNER
from agent_native.plane_operation_lock import OperationBusy
from agent_native.startup import prepare
from hermes_cli.kanban_db_connect import connect_closing

_log = logging.getLogger(__name__)


class SetupService:
    def __init__(self, db_path, home):
        self.db_path, self.home = Path(db_path), Path(home)
        self.stop_requested = threading.Event()
        self.thread = threading.Thread(target=self._run, name='agent-native-setup', daemon=True)

    def start(self):
        self.thread.start()
        return self

    def stop(self):
        self.stop_requested.set()
        self.thread.join(timeout=1.0)

    def tick(self):
        with connect_closing(self.db_path) as conn:
            agents = conn.execute("SELECT agent_id FROM agent_native_setup WHERE status IN ('queued', 'preparing') "
                                  "AND agent_id NOT IN (SELECT agent_id FROM agent_native_first_builder) "
                                  'ORDER BY updated_at LIMIT 100').fetchall()
            for (agent_id,) in agents:
                if self.stop_requested.is_set():
                    break
                try:
                    prepare(conn, actor=OWNER, agent_id=agent_id, home=self.home,
                            stopped=self.stop_requested.is_set)
                except OperationBusy:
                    continue  # Another live host holds the OS lock, including after restart.
                except Exception as exc:
                    _log.warning('Agent setup service failed (%s); intent retained', type(exc).__name__)

    def _run(self):
        while not self.stop_requested.is_set():
            try:
                self.tick()
            except Exception as exc:
                _log.warning('Agent setup scan failed (%s); intents retained', type(exc).__name__)
            self.stop_requested.wait(1.0)


def start_service():
    from hermes_constants import get_hermes_home
    from hermes_cli.kanban_db import kanban_db_path
    return SetupService(kanban_db_path(board='default'), get_hermes_home() / 'agent-native').start()
