"""Bounded, verified managed reads of exact saved output versions."""
from agent_native.output_store import read_output


def read_chunk(conn, *, agent_id, workspace, arguments):
    required = {'output_id', 'version'}
    if not required <= set(arguments) or set(arguments) - required - {'offset', 'limit'}:
        raise ValueError('Output read requires output_id and version, with optional offset and limit')
    offset, limit = arguments.get('offset', 0), arguments.get('limit', 16000)
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 32000:
        raise ValueError('Output offset must be nonnegative and limit must be between 1 and 32000 characters')
    if type(arguments['output_id']) is not str:
        raise ValueError('Output identity must be a string')
    saved = read_output(conn, agent_id, arguments['output_id'], arguments['version'], workspace=workspace)
    content = saved.pop('content')
    if offset > len(content):
        raise ValueError('Output offset exceeds content length')
    end = min(offset + limit, len(content))
    return {**saved, 'content': content[offset:end], 'offset': offset,
            'total_characters': len(content), 'next_offset': end if end < len(content) else None}
