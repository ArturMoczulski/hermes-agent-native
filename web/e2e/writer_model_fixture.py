"""External scripted model for real shared work; no framework paths are mocked."""
import json
import re

SHARED_TOOLS = {'plane_resource_inspect', 'plane_operation_execute', 'output_publish', 'result_record', 'work_item_select'}
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


def next_reply(messages, purpose):
    results = _results(messages)
    index = len(results)
    result = lambda step: results[f'writer_fixture_{step}']
    item = lambda: result(3)['resource']['id']
    operation = lambda name, arguments: ('plane_operation_execute', {'operation': name, 'arguments': arguments})
    analyst = 'E2E_ANALYST_' in purpose
    plaintext = 'E2E_ANALYST_TEXT' in purpose
    file_free = ('discovery' if 'E2E_ANALYST_DISCOVERY' in purpose else
                 'waiting' if 'E2E_ANALYST_WAITING' in purpose else None)
    title = 'Operations sample analysis' if analyst else STORY_TITLE
    content = ('# Operations sample analysis\n\n'
               'Supplied fictional sample: 12 fulfilled orders, revenue 150 credits, costs 90 credits.\n\n'
               'Profit: 60 credits (150 - 90).\n\nMargin: 40% (60 / 150).\n\n'
               'This sample does not establish trends or forecast future results.\n') if analyst else STORY_CONTENT
    if plaintext:
        title = 'Literal operations notes'
        content = '# Literal heading\n<script>window.outputScriptRan = true</script>\n**These are literal characters.**\n'
    brief = ('Analyze only the supplied fictional operations sample and explain the arithmetic and its limits.'
             if analyst else BRIEF)
    criteria = ('Acceptance criteria: correct profit and margin from the supplied sample; show calculations; '
                'state that no trend is established; no external actions.' if analyst else CRITERIA)
    evaluation = ('Profit is 150 - 90 = 60 credits; margin is 60 / 150 = 40%. '
                  'The report uses only the supplied sample and makes no trend claim.' if analyst else
                  'The story has a protagonist, dragon, moonlit citadel, and complete hopeful ending. '
                  'Its original text is ready for owner review.')
    if index == 0:
        name, arguments = 'plane_resource_inspect', {'kind': 'project'}
    elif index == 1:
        name, arguments = operation('project.update', {'description': brief, 'expected_fingerprint': result(0)['fingerprint']})
    elif index == 2:
        name, arguments = operation('cycle.create', {
            'name': 'Understand the supplied operations sample' if analyst else CYCLE_NAME,
            'description': 'Plan, perform and evaluate the first bounded assignment. No estimated dates.'})
    elif index == 3:
        name, arguments = operation('item.create', {
            'name': 'Analyze the supplied operations sample' if analyst else 'Write The Silver Gate',
            'description': criteria, 'priority': 'high'})
    elif index == 4:
        name, arguments = 'plane_resource_inspect', {'kind': 'item', 'resource_id': item()}
    elif index == 5:
        name, arguments = operation('cycle.assign', {'cycle_id': result(2)['resource']['id'], 'item_id': item(),
                                    'expected_item_fingerprint': result(4)['fingerprint'],
                                    'expected_cycle_id': result(4)['cycle_id']})
    elif index == 6:
        name, arguments = 'work_item_select', {'item_id': item()}
    elif 'E2E_PLAN_RESELECT' in purpose and index == 7:
        name, arguments = 'work_item_select', {'item_id': item()}
    elif 'E2E_PLAN_RESELECT' in purpose and index == 8:
        return {'role': 'assistant', 'content': 'Requirements were selected again.'}
    elif file_free and index == 7:
        summary = ('The supplied sample supports arithmetic, but no trend or forecast. Scope the next work to '
                   'obtaining a comparable sample before any growth claim.' if file_free == 'discovery' else
                   'Waiting for the owner to provide the comparison period before evaluating a trend.')
        name, arguments = 'result_record', {'item_id': item(), 'summary': summary, 'outcome': file_free,
                                            'evaluation': 'No trend can be established from one sample.', 'outputs': []}
    elif file_free and index == 8:
        return {'role': 'assistant', 'content': 'I recorded the ' + file_free + ' result without creating an unnecessary file.'}
    elif index == 7:
        name, arguments = 'output_publish', {'title': title, 'content': content, 'item_id': item(), 'format': 'text' if plaintext else 'markdown'}
    elif index == 8:
        name, arguments = operation('artifact.record', {'item_id': item(), 'reference': result(7)['relative_path'],
                                    'description': 'Saved output version ' + str(result(7)['version'])})
    elif index == 9:
        name, arguments = 'plane_resource_inspect', {'kind': 'item', 'resource_id': item()}
    elif index == 10:
        name, arguments = operation('item.update', {'item_id': item(), 'expected_fingerprint': result(9)['fingerprint'],
                                    'description': criteria + '\nResult: saved ' + title + '; ready for owner review.'})
    elif index == 11:
        name, arguments = 'result_record', {'item_id': item(), 'summary': 'Completed ' + title + ' for owner review.',
            'outcome': 'submitted', 'evaluation': evaluation,
            'outputs': [{'output_id': result(7)['output_id'], 'version': result(7)['version']}]}
    elif index == 12:
        return {'role': 'assistant', 'content': 'I planned the first cycle, completed ' + title + ', saved its output, '
                'recorded an evaluation, and updated its Plane task. The result awaits owner review.'}
    else:
        raise ValueError('Unexpected extra shared-work model request')
    return {'role': 'assistant', 'content': None, 'tool_calls': [{'id': f'writer_fixture_{index}', 'type': 'function',
            'function': {'name': name, 'arguments': json.dumps(arguments)}}]}


def handle_writer_request(handler, body, server, model_name):
    tool_names = {tool.get('function', {}).get('name') for tool in body.get('tools', [])}
    if tool_names != SHARED_TOOLS:
        return False
    messages = body.get('messages') or []
    system_text = '\n'.join(_text(message) for message in messages if message.get('role') in ('system', 'developer'))
    marker = re.search(r'E2E_(?:WRITER|PLAN)_HOLD[A-Za-z0-9_-]*', system_text)
    try:
        phase = len(_results(messages))
    except (KeyError, ValueError) as exc:
        handler._send({'error': {'message': 'Shared-work fixture contract failed: ' + str(exc)}}, status=400)
        return True
    reselect = 'E2E_PLAN_RESELECT' in system_text
    key = ('E2E_PLAN_RESELECT_BEFORE' if phase == 7 else 'E2E_PLAN_RESELECT_AFTER') if reselect and phase in (7, 8) else (marker.group(0) if marker else None)
    hold = key is not None and (reselect or 'E2E_WRITER_' in key or phase >= 7)
    evidence = getattr(server, 'writer_requests', None)
    if evidence is None:
        evidence = server.writer_requests = []
    evidence.append({'tool_results': sum(message.get('role') == 'tool' for message in messages),
                     'hold_marker': key,
                     'tools': sorted(tool_names), 'system_text': system_text,
                     'initial_context': next((_text(m) for m in messages if m.get('role') == 'user'), '')})
    if hold:
        try:
            server.holds.evidence(key)
        except KeyError:
            server.holds.arm(key)
        server.holds.enter(key)
        if not server.holds.wait(key, handler.connection):
            return True
        message = (next_reply(messages, system_text) if reselect and phase == 7 else
                   {'role': 'assistant', 'content': server.holds.evidence(key)['late_reply']})
    else:
        try:
            message = next_reply(messages, system_text)
        except (KeyError, ValueError, StopIteration) as exc:
            handler._send({'error': {'message': 'Shared-work fixture contract failed: ' + str(exc)}}, status=400)
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
    if hold:
        server.holds.written(key, written)
    return True
