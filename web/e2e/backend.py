"""Real dashboard backend with disposable storage and no inherited credentials."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
for key in list(os.environ):
    if key.startswith('HERMES_') or key.endswith(('_API_KEY', '_TOKEN', '_SECRET', '_PASSWORD')):
        os.environ.pop(key, None)
with tempfile.TemporaryDirectory(prefix='agent-native-e2e-') as home:
    os.environ.update(HERMES_HOME=home, HERMES_KANBAN_HOME=home,
                      HERMES_KANBAN_DB=str(Path(home) / 'kanban.db'),
                      HERMES_DASHBOARD_SESSION_TOKEN='agent-native-local-e2e-only')
    import uvicorn
    uvicorn.run('hermes_cli.web_server:app', host='127.0.0.1', port=19219, log_level='warning')
