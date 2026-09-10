"""Host-issued conversation authority for framework agents using native Hermes.

The binding survives constructor context and mutable tool snapshots. Native
request, execution, and lifecycle middleware remain responsible for their
existing enforcement; this restriction only narrows the permitted operations.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from inspect import signature
import os

_binding = ContextVar('managed_native_chat_binding', default=None)


def current_binding(agent=None):
    return vars(agent).get('_managed_chat_binding') if agent is not None else _binding.get()


@contextmanager
def bind_managed_chat(binding):
    from agent_native.chat import Binding
    if not isinstance(binding, Binding):
        raise PermissionError('Host-issued conversation binding required')
    binding.validate()
    token = _binding.set(binding)
    try:
        yield binding
    finally:
        _binding.reset(token)


def assert_current(agent):
    from agent.work_policy import admit
    admit(agent, 'persist')
    from agent.managed_chat_attempt import assert_active
    attempt = assert_active(agent)
    binding = current_binding(agent)
    if attempt is not None and binding is None:
        raise PermissionError('Managed attempt requires a protected conversation binding')
    if binding is not None:
        binding.validate()
        if agent.session_id != binding.session_id:
            raise PermissionError('Managed conversation session cannot be reassigned')
    return binding


def deny_tools(agent, name=None):
    """Reject ambient native tools while allowing the bound Plane surface.

    A managed conversation is still not an autonomous work run.  Its one
    exception is the host-owned project surface attached during construction;
    it revalidates the existing agent/project grant for every call.
    """
    if current_binding(agent) is not None:
        from agent_native.chat_project import current
        context = current(agent)
        if context is not None and name in context.authorized_tools:
            return
        raise PermissionError('Managed conversation does not authorize this tool')


def protected_prompt(binding):
    return (
        f'You are {binding.name}. Your protected purpose is:\n{binding.purpose}\n\n'
        'This is a conversation with your human owner. Discuss your purpose, answer '
        'questions, and clarify plans. You may use only the supplied Plane tools '
        'to inspect and maintain this agent\'s already-authorized planning project. '
        'This conversation does not start autonomous project work, grant new '
        'permissions, change your purpose, or resume paused work. Be honest about '
        'that scope; never claim that project actions were performed without a '
        'confirmed tool result.'
    )


def managed_turn(fn):
    turn_signature = signature(fn)

    @wraps(fn)
    def run(agent, *args, **kwargs):
        from agent.work_policy import current as current_work, run_turn
        if current_work(agent) is not None:
            return run_turn(fn, agent, args, kwargs, turn_signature)
        from agent.managed_chat_attempt import current_attempt
        if attempt := current_attempt():
            previous = vars(agent).get('_managed_chat_attempt')
            if previous is not None and previous != attempt:
                raise PermissionError('Managed native agent cannot change attempts')
            # Keep the exact host-issued attempt after this context unwinds. A
            # delayed persistence callback must never borrow a later receipt.
            agent._managed_chat_attempt = attempt
        binding = assert_current(agent)
        if binding is None:
            return fn(agent, *args, **kwargs)
        if os.environ.get('HERMES_KANBAN_TASK', '').strip():
            raise PermissionError('Managed conversation cannot run inside a kanban worker process')
        # Native text transports can encode a hidden /moa instruction. Managed
        # chat admits conversation text only, including for direct native callers.
        from hermes_cli.moa_config import MOA_MARKER_PREFIX
        turn = turn_signature.bind(agent, *args, **kwargs).arguments
        message = turn.get('user_message')
        if (
            not isinstance(message, str)
            or message.startswith(MOA_MARKER_PREFIX)
            or turn.get('moa_config') is not None
            or turn.get('system_message') is not None
        ):
            raise PermissionError('Managed conversation accepts plain owner messages only')
        with bind_managed_chat(binding):
            result = fn(agent, *args, **kwargs)
            assert_current(agent)
            return result
    return run
