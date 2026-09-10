"""Scoped Plane capability for a human's live conversation with one agent.

The native chat process keeps this object private.  It derives its scope from
the already-issued conversation binding and the existing owner-installed Plane
grant; it neither receives credentials nor creates or broadens a grant.
"""
import json
from uuid import NAMESPACE_URL, uuid5

from agent_native.identity import OWNER
from hermes_cli.kanban_db_connect import connect_closing
from hermes_constants import get_hermes_home


TOOLS = frozenset({'plane_resource_inspect', 'plane_operation_execute'})


class ChatProjectContext:
    """One agent-bound project capability used only during an owner chat turn."""

    authorized_tools = TOOLS

    def __init__(self, binding):
        self.binding = binding

    def _validate(self, conn):
        self.binding.validate()
        row = conn.execute(
            'SELECT id FROM agent_native_plane_access WHERE agent_id=? AND active=1 '
            'ORDER BY revision DESC, id DESC LIMIT 1',
            (self.binding.agent_id,),
        ).fetchone()
        if row is None:
            raise PermissionError('This agent has no active Plane project grant')
        return row[0]

    def tool(self, agent, name, arguments, tool_call_id):
        if name not in TOOLS or not isinstance(arguments, dict):
            raise PermissionError('This tool is not authorized for this agent conversation')
        if not isinstance(tool_call_id, str) or not tool_call_id or len(tool_call_id) > 256:
            raise PermissionError('Conversation project tools require a native tool-call identity')
        self.binding.validate()
        from agent_native.writer_planning import open_planning
        from agent_native.plane_writes import PlaneWriteError
        from agent_native.plane_write_contracts import ContractError

        def validate(conn):
            binding_id = self._validate(conn)
            return binding_id

        try:
            with connect_closing(self.binding._db_path) as conn:
                binding_id = validate(conn)
            with open_planning(
                db_path=self.binding._db_path,
                home=get_hermes_home() / 'agent-native',
                agent_id=self.binding.agent_id,
                binding_id=binding_id,
                validate=lambda conn: validate(conn),
            ) as planning:
                if name == 'plane_resource_inspect':
                    result = planning.inspect(arguments)
                else:
                    if set(arguments) != {'operation', 'arguments'}:
                        raise ContractError('Invalid operation envelope')
                    # This deterministic ID lets the Plane mutation journal make
                    # native retries of one model call idempotent.
                    operation_id = str(uuid5(
                        NAMESPACE_URL,
                        'agent-native:chat-plane:' + self.binding.session_id + ':' + tool_call_id,
                    ))
                    result = planning.execute(operation_id, arguments['operation'], arguments['arguments'])
            self.binding.validate()
            return json.dumps(result)
        except (PermissionError, ContractError, PlaneWriteError):
            # Keep adapter details, credentials and remote response bodies out
            # of the model transcript.  The agent can inspect again and explain
            # the bounded failure to its owner.
            return json.dumps({'error': 'The scoped Plane operation could not be confirmed.'})


def current(agent=None):
    return vars(agent).get('_chat_project_context') if agent is not None else None
