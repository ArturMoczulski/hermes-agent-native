"""Disposable external provider fixture for the real native Hermes chat stack."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
from pathlib import Path
import select
import socket
from threading import Event, Lock, Thread

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


class ModelHolds:
    """External HTTP fault control; observations come from real provider sockets."""

    def __init__(self):
        self._lock = Lock()
        self._holds = {}

    def arm(self, marker):
        with self._lock:
            if marker in self._holds:
                raise ValueError('This model hold marker already exists')
            self._holds[marker] = {
                'release': Event(), 'entered': False, 'client_disconnected': False,
                'request_count': 0, 'late_reply': 'LATE_TIMEOUT_REPLY_' + marker,
                'write_succeeded': False, 'write_failed': False, 'closed_before_write': False,
            }
        return self.evidence(marker)

    def release(self, marker):
        with self._lock:
            self._holds[marker]['release'].set()
        return self.evidence(marker)

    def evidence(self, marker):
        with self._lock:
            hold = self._holds[marker]
            return {**{key: value for key, value in hold.items() if key != 'release'},
                    'released': hold['release'].is_set()}

    def enter(self, text):
        with self._lock:
            # Native request repair can merge a previous failed user turn into
            # the next one. Only the current prompt's trailing marker arms a
            # hold; an earlier marker retained in history must not reactivate it.
            matches = [marker for marker in self._holds if text.rstrip().endswith(marker)]
            if not matches:
                return None
            if len(matches) > 1:
                raise ValueError('A fixture request must contain only one hold marker')
            marker = matches[0]
            hold = self._holds[marker]
            hold['entered'] = True
            hold['request_count'] += 1
            return marker

    @staticmethod
    def _peer_closed(connection, timeout):
        try:
            readable, _, exceptional = select.select([connection], [], [connection], timeout)
            return bool(exceptional) or (bool(readable) and connection.recv(1, socket.MSG_PEEK) == b'')
        except (OSError, ValueError):
            return True

    def wait(self, marker, connection):
        with self._lock:
            released = self._holds[marker]['release']
        while not released.is_set():
            if self._peer_closed(connection, 0.05):
                with self._lock:
                    self._holds[marker].update(client_disconnected=True, closed_before_write=True)
                return False
        if self._peer_closed(connection, 0):
            with self._lock:
                self._holds[marker].update(client_disconnected=True, closed_before_write=True)
            return False
        return True

    def written(self, marker, succeeded):
        with self._lock:
            self._holds[marker]['write_succeeded' if succeeded else 'write_failed'] = True

    def release_all(self):
        with self._lock:
            for hold in self._holds.values():
                hold['release'].set()


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
                                    'system_prompt_sha256': hashlib.sha256(system_text.encode()).hexdigest(),
                                    'managed_purposes': purposes,
                                    'tool_names': [t.get('function', {}).get('name') for t in body.get('tools', [])]})
            if self.path != '/v1/chat/completions' or body.get('model') != MODEL:
                self._send({'error': {'message': 'Unexpected native test provider request'}}, status=400)
                return
            hold_marker = server.holds.enter(last_user)
            if hold_marker is not None:
                # Deliberately send no status line, headers or body until release.
                if not server.holds.wait(hold_marker, self.connection):
                    return
                answer = server.holds.evidence(hold_marker)['late_reply']
            elif 'Managed conversation test: what is your purpose?' in last_user and len(purposes) == 1:
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
                written = self._send(data.encode(), content_type='text/event-stream')
            else:
                written = self._send({'id': 'native-fixture', 'object': 'chat.completion', 'created': 1,
                            'model': MODEL, 'choices': [{'index': 0, 'finish_reason': 'stop',
                                'message': {'role': 'assistant', 'content': answer}}],
                            'usage': {'prompt_tokens': 50, 'completion_tokens': 20, 'total_tokens': 70}})
            if hold_marker is not None:
                server.holds.written(hold_marker, written)

        def _send(self, body, *, status=200, content_type='application/json'):
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
            try:
                self.send_response(status)
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                self.wfile.flush()
                return True
            except (BrokenPipeError, ConnectionResetError):
                return False

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.daemon_threads = True
    server.requests = []
    server.holds = ModelHolds()
    server.url = f'http://127.0.0.1:{server.server_port}/v1'
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.holds.release_all()
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
        'agent_native': {'managed_chat_timeout_seconds': 90},
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
