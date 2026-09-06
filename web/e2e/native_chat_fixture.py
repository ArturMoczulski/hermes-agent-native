"""Disposable external provider fixture for the real native Hermes chat stack."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread

import yaml

OPENER = 'Native browser test: remember the moonlit citadel.'
REPLY = 'The moonlit citadel is remembered in this conversation.'
FOLLOWUP = 'Native browser test: what place did I mention?'
RECALLED = 'You mentioned the moonlit citadel before reloading the browser.'
MODEL = 'native-browser-fixture'
MANAGED_PURPOSES = ('Write original stories about the moonlit citadel.', 'Write original stories about the glass ocean.')


def _text(message):
    content = message.get('content') or ''
    return content if isinstance(content, str) else '\n'.join(
        part.get('text', '') for part in content if isinstance(part, dict))


@contextmanager
def native_model_server():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            # Native runtime may inspect a local provider's model catalog.
            self._send({'object': 'list', 'data': [
                {'id': MODEL, 'object': 'model', 'context_length': 128000}]})

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            messages = body.get('messages') or []
            user_messages = [_text(m) for m in messages if m.get('role') == 'user']
            last_user = user_messages[-1] if user_messages else ''
            history_present = (any(OPENER in m for m in user_messages[:-1])
                               and any(REPLY in _text(m) for m in messages if m.get('role') == 'assistant'))
            system_text = '\n'.join(_text(m) for m in messages if m.get('role') in ('system', 'developer'))
            purposes = [p for p in MANAGED_PURPOSES if p in system_text]
            server.requests.append({'path': self.path, 'model': body.get('model'), 'last_user': last_user,
                                    'history_has_first_exchange': history_present,
                                    'managed_purposes': purposes,
                                    'tool_names': [t.get('function', {}).get('name') for t in body.get('tools', [])]})
            if self.path != '/v1/chat/completions' or body.get('model') != MODEL:
                self._send({'error': {'message': 'Unexpected native test provider request'}}, status=400)
                return
            if 'Managed conversation test: what is your purpose?' in last_user and len(purposes) == 1:
                answer = 'My purpose: ' + purposes[0]
            elif ('Managed conversation test: remember our conversation?' in last_user and len(purposes) == 1
                  and any(m.get('role') == 'assistant' and _text(m) == 'My purpose: ' + purposes[0] for m in messages)):
                answer = 'Our conversation is retained.'
            elif FOLLOWUP in last_user and history_present:
                answer = RECALLED
            elif OPENER in last_user:
                answer = REPLY
            else:
                self._send({'error': {'message': 'Test prompt or retained history did not reach provider'}}, status=400)
                return
            if body.get('stream') is True:
                frames = [
                    {'index': 0, 'delta': {'role': 'assistant', 'content': ''}, 'finish_reason': None},
                    {'index': 0, 'delta': {'content': answer[:24]}, 'finish_reason': None},
                    {'index': 0, 'delta': {'content': answer[24:]}, 'finish_reason': None},
                    {'index': 0, 'delta': {}, 'finish_reason': 'stop'},
                ]
                data = ''.join('data: ' + json.dumps({
                    'id': 'native-fixture', 'object': 'chat.completion.chunk', 'created': 1,
                    'model': MODEL, 'choices': [frame],
                }) + '\n\n' for frame in frames) + 'data: [DONE]\n\n'
                self._send(data.encode(), content_type='text/event-stream')
            else:
                self._send({'id': 'native-fixture', 'object': 'chat.completion', 'created': 1,
                            'model': MODEL, 'choices': [{'index': 0, 'finish_reason': 'stop',
                                'message': {'role': 'assistant', 'content': answer}}],
                            'usage': {'prompt_tokens': 50, 'completion_tokens': 20, 'total_tokens': 70}})

        def _send(self, body, *, status=200, content_type='application/json'):
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            try:
                self.wfile.write(data)
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.daemon_threads = True
    server.requests = []
    server.url = f'http://127.0.0.1:{server.server_port}/v1'
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def configure_native_chat(home, model):
    """Normal native config in temporary HERMES_HOME; no production monkeypatches."""
    root = Path(home)
    workspace = root / 'workspace'
    workspace.mkdir()
    (root / 'config.yaml').write_text(yaml.safe_dump({
        'model': {'default': MODEL, 'provider': 'browser-fixture', 'base_url': model.url, 'context_length': 128000},
        'custom_providers': [{'name': 'browser-fixture', 'base_url': model.url,
                              'api_key': 'native-browser-fixture-only', 'model': MODEL}],
        'agent': {'max_turns': 3},
        'terminal': {'cwd': str(workspace)},
        'memory': {'memory_enabled': False, 'user_profile_enabled': False, 'nudge_interval': 0},
        'compression': {'enabled': False},
        'auxiliary': {'title_generation': {'enabled': False}},
        'plugins': {'enabled': []},
        'mcp_servers': {},
    }))
    (root / 'config.yaml').chmod(0o600)
    (root / '.env').write_text('')
    (root / '.env').chmod(0o600)
