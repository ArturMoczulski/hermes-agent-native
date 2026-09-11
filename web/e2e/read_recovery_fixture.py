"""Model-side script only; reads, receipts, worker limits and cadence stay real."""
import json


def next_recovery_reply(planning, results):
    index = len(results)
    target = planning['discovery']['id']
    if planning.get('saved_outputs'):
        steps = [
            ('work_item_select', {'item_id': target}),
            ('result_record', {'item_id': target, 'outcome': 'discovery', 'outputs': [],
                               'summary': 'Continued automatically after the model-step limit.',
                               'evaluation': 'Previous draft is retained; this is a new attempt.'}),
        ]
    else:
        steps = [
            ('work_item_select', {'item_id': 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'}),
            ('work_item_select', {'item_id': target}),
            ('output_publish', {'item_id': target, 'title': 'Retained recovery draft',
                                'format': 'markdown', 'content': '# Draft\n\nDurable work before the step limit.'}),
            ('plane_resource_inspect', {'kind': 'project'}),
        ]
    if index >= len(steps):
        return {'role': 'assistant', 'content': 'The draft is retained; automatic continuation is verified.'}
    name, arguments = steps[index]
    return {'role': 'assistant', 'content': None, 'tool_calls': [
        {'id': f'writer_fixture_{index}', 'type': 'function',
         'function': {'name': name, 'arguments': json.dumps(arguments)}}]}
