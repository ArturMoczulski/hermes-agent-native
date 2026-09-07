"""External scripted model for the real writer loop; no framework paths are mocked."""
import json
import re

WRITER_TOOLS = {'plane_resource_inspect', 'plane_operation_execute', 'story_publish'}
STORY_TITLE = 'The Silver Gate'
STORY_CONTENT = (
    '# The Silver Gate\n\n'
    'At moonrise, Mara found a dragon asleep beneath the citadel gate. Its scales '
    'held the names of every star the city had forgotten.\n\n'
    'She spoke the smallest name. The gate opened, and the dragon woke smiling. '
    'Beyond it waited a dawn that neither of them had ever seen.\n'
)
BRIEF = 'Write an original, complete fantasy story with a moonlit citadel, a dragon, and a hopeful ending.'
CRITERIA = 'Acceptance criteria: original fantasy; identifiable protagonist; complete ending; saved story artifact; evaluation against the brief.'
CYCLE_NAME = 'First complete fantasy story'


def _text(message):
    content = message.get('content') or ''
    if isinstance(content, str):
        return content
    return '\n'.join(part.get('text', '') for part in content if isinstance(part, dict))


def _planning(messages):
    def find(value):
        if isinstance(value, dict):
            if {'project', 'states', 'discovery'} <= value.keys():
                return value
            for child in value.values():
                if result := find(child):
                    return result
        return None
    decoder = json.JSONDecoder()
    for message in messages:
        if message.get('role') != 'user':
            continue
        text = _text(message)
        for match in re.finditer(r'\{', text):
            try:
                value, _ = decoder.raw_decode(text[match.start():])
            except ValueError:
                continue
            if snapshot := find(value):
                return snapshot
    raise ValueError('Writer planning snapshot did not reach the native model')


def _results(messages):
    results = {}
    for message in messages:
        if message.get('role') != 'tool':
            continue
        value = json.loads(_text(message))
        if not isinstance(value, dict) or value.get('error'):
            raise ValueError('Writer tool did not return a successful structured result')
        results[message['tool_call_id']] = value
    return results


def next_reply(messages):
    results = _results(messages)
    index = len(results)
    result = lambda step: results[f'writer_fixture_{step}']
    item = lambda: result(3)['resource']['id']
    operation = lambda name, arguments: ('plane_operation_execute', {'operation': name, 'arguments': arguments})
    if index == 0:
        name, arguments = 'plane_resource_inspect', {'kind': 'project'}
    elif index == 1:
        name, arguments = operation('project.update', {'description': BRIEF, 'expected_fingerprint': result(0)['fingerprint']})
    elif index == 2:
        name, arguments = operation('cycle.create', {'name': CYCLE_NAME, 'description': 'Plan, write, evaluate and save the first story. No estimated dates.'})
    elif index == 3:
        name, arguments = operation('item.create', {'name': 'Write The Silver Gate', 'description': CRITERIA, 'priority': 'high'})
    elif index == 4:
        name, arguments = 'plane_resource_inspect', {'kind': 'item', 'resource_id': item()}
    elif index == 5:
        name, arguments = operation('cycle.assign', {'cycle_id': result(2)['resource']['id'], 'item_id': item(),
                                    'expected_item_fingerprint': result(4)['fingerprint'],
                                    'expected_cycle_id': result(4)['cycle_id']})
    elif index == 6:
        name, arguments = 'story_publish', {'title': STORY_TITLE, 'content': STORY_CONTENT, 'item_id': item(),
                                            'evaluation': 'The story has a protagonist, dragon, moonlit citadel, and complete hopeful ending. Its original text is ready for owner review.'}
    elif index == 7:
        name, arguments = operation('artifact.record', {'item_id': item(), 'reference': result(6)['relative_path'],
                                    'description': 'Saved story version ' + str(result(6)['version'])})
    elif index == 8:
        name, arguments = 'plane_resource_inspect', {'kind': 'item', 'resource_id': item()}
    elif index == 9:
        name, arguments = operation('item.update', {'item_id': item(), 'expected_fingerprint': result(8)['fingerprint'],
                                    'description': CRITERIA + '\nResult: saved The Silver Gate and its evaluation; ready for owner review.'})
    elif index == 10:
        return {'role': 'assistant', 'content': 'I planned the first cycle, wrote The Silver Gate, saved its version and evaluation, and updated its Plane task.'}
    else:
        raise ValueError('Unexpected extra writer model request')
    return {'role': 'assistant', 'content': None, 'tool_calls': [{'id': f'writer_fixture_{index}', 'type': 'function',
            'function': {'name': name, 'arguments': json.dumps(arguments)}}]}


def handle_writer_request(handler, body, server, model_name):
    if {tool.get('function', {}).get('name') for tool in body.get('tools', [])} != WRITER_TOOLS:
        return False
    messages = body.get('messages') or []
    system_text = '\n'.join(_text(message) for message in messages if message.get('role') in ('system', 'developer'))
    marker = re.search(r'E2E_WRITER_HOLD[A-Za-z0-9_-]*', system_text)
    evidence = getattr(server, 'writer_requests', None)
    if evidence is None:
        evidence = server.writer_requests = []
    evidence.append({'tool_results': sum(message.get('role') == 'tool' for message in messages),
                     'hold_marker': marker.group(0) if marker else None})
    if marker:
        key = marker.group(0)
        try:
            server.holds.evidence(key)
        except KeyError:
            server.holds.arm(key)
        server.holds.enter(key)
        if not server.holds.wait(key, handler.connection):
            return True
        message = {'role': 'assistant', 'content': server.holds.evidence(key)['late_reply']}
    else:
        try:
            message = next_reply(messages)
        except (KeyError, ValueError, StopIteration) as exc:
            handler._send({'error': {'message': 'Writer fixture contract failed: ' + str(exc)}}, status=400)
            return True
    finish = 'tool_calls' if message.get('tool_calls') else 'stop'
    if body.get('stream'):
        delta = json.loads(json.dumps(message))
        for index, call in enumerate(delta.get('tool_calls', [])):
            call['index'] = index
        frames = [{'index': 0, 'delta': delta, 'finish_reason': None},
                  {'index': 0, 'delta': {}, 'finish_reason': finish}]
        data = ''.join('data: ' + json.dumps({'id': 'writer-fixture', 'object': 'chat.completion.chunk',
                    'created': 1, 'model': model_name, 'choices': [frame]}) + '\n\n' for frame in frames) + 'data: [DONE]\n\n'
        written = handler._send(data.encode(), content_type='text/event-stream')
    else:
        written = handler._send({'id': 'writer-fixture', 'object': 'chat.completion', 'created': 1, 'model': model_name,
                                 'choices': [{'index': 0, 'message': message, 'finish_reason': finish}],
                                 'usage': {'prompt_tokens': 100, 'completion_tokens': 100, 'total_tokens': 200}})
    if marker:
        server.holds.written(marker.group(0), written)
    return True
