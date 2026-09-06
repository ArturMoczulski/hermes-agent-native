"""Host-bound Plane inspection through Hermes dispatch, including nested RPC.

The host keeps adapters, credentials and opaque contexts outside generated code.
This is a tool boundary, not managed-run admission or a sandbox. Native tools
outside the reserved namespace still need the execution controls in AN-24/7.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
import json
from threading import Event

from agent_native.identity import _require_owner
from agent_native.plane_write_contracts import ContractError, validate_arguments
from agent_native.plane_reads import PlaneReadError


class _LiveReadAuthority:
    def __init__(self, authority, binding):
        self.authority, self.binding = authority, binding

    def resolve(self, context):
        self.binding.require_active()
        return self.authority.resolve(context)


class _Binding:
    """Serialize adapter use on the thread that owns its SQLite connection."""
    def __init__(self):
        self.active = Event()
        self.active.set()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='plane-tools')

    def require_active(self):
        if not self.active.is_set():
            raise PermissionError('Plane tool binding has ended')

    def open(self, open_service):
        self.resources = ExitStack()
        try:
            self.service, self.context = self.resources.enter_context(open_service())
            self.service.authority.resolve(self.context)
            # Inspection revalidates before and after every HTTP request, including
            # item membership/dependency follow-ups. Retiring this binding joins
            # those checks without changing durable grants or minting new ones.
            authority = _LiveReadAuthority(self.service.authority, self)
            self.service.authority = self.service._reads.authority = authority
        except BaseException:
            self.resources.close()
            raise

    def inspect(self, args):
        self.require_active()
        result = self.service.inspect(self.context, **args)
        self.require_active()
        return result


_binding = ContextVar('agent_native_plane_binding', default=None)


@contextmanager
def bind_plane_tools(*, actor, open_service):
    """Bind a fresh host-owned (PlaneWrites, opaque context) context manager.

    The factory opens and closes its control connection on our worker thread.
    It is trusted host code, never supplied by tool arguments. SQLite thread
    checks stay enabled. Binding exit revokes queued/copied-context reads before
    waiting for in-flight I/O to settle and closing the connection.
    """
    _require_owner(actor)
    binding = _Binding()
    try:
        binding.executor.submit(binding.open, open_service).result()
        token = _binding.set(binding)
        try:
            yield
        finally:
            binding.active.clear()
            _binding.reset(token)
    finally:
        binding.active.clear()
        try:
            if hasattr(binding, 'resources'):
                binding.executor.submit(binding.resources.close).result()
        finally:
            binding.executor.shutdown(wait=True)


def is_plane_tool(name):
    return isinstance(name, str) and name.startswith('plane_')


def dispatch_plane_tool(name, arguments):
    if not is_plane_tool(name):
        return None
    binding = _binding.get()
    if binding is None or not binding.active.is_set():
        return json.dumps({'error': 'A host-bound Plane context is required'})
    if name != 'plane_resource_inspect':
        return json.dumps({'error': 'This Plane operation is not available through managed tools'})
    try:
        args = validate_arguments('resource.inspect', arguments)
        result = binding.executor.submit(binding.inspect, args).result()
        binding.require_active()
        return json.dumps(result)
    except PermissionError:
        return json.dumps({'error': 'Plane authority is missing, revoked or out of date'})
    except ContractError:
        return json.dumps({'error': 'Invalid Plane tool arguments'})
    except PlaneReadError:
        return json.dumps({'error': 'Plane resource is unavailable; no result was returned'})
    except Exception:
        # Never expose adapter/SQLite exception text to the model or RPC client.
        return json.dumps({'error': 'Plane tool failed; no result was returned'})
