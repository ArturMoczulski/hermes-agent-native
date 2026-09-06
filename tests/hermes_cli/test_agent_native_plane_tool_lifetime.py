"""An ended host binding cannot disclose a held response or continue inspecting."""

from contextlib import contextmanager
from contextvars import copy_context
import json
from queue import Queue
from threading import Event, Thread
from time import monotonic

from agent_native.identity import OWNER
from tests.hermes_cli import test_agent_native_plane_writes as fixtures
from tests.hermes_cli.test_agent_native_plane_tools import open_service

setup = fixtures.setup
upstream = fixtures.upstream


def test_binding_exit_discards_inflight_item_and_prevents_followup_reads(
    setup, upstream, open_service
):
    from agent_native import plane_tools
    from model_tools import handle_function_call

    item = fixtures.put_item(setup, upstream)
    item_path = setup.path + f"work-items/{item['id']}/"
    entered, release, leave_scope, closed = (Event() for _ in range(4))
    contexts, results, failures = Queue(), Queue(), Queue()

    @contextmanager
    def tracked_service():
        try:
            with open_service() as service:
                yield service
        finally:
            closed.set()

    def hold_response(_):
        entered.set()
        if not release.wait(timeout=15):
            return 503, {}, {"error": "fixture response was not released"}
        return 200, {}, item

    upstream.routes['GET', item_path] = hold_response

    def host_scope():
        try:
            with plane_tools.bind_plane_tools(actor=OWNER, open_service=tracked_service):
                # The private event is observed only to synchronize with retirement;
                # no authority or service implementation is replaced by this test.
                contexts.put((copy_context(), copy_context(), plane_tools._binding.get().active))
                if not leave_scope.wait(timeout=15):
                    raise AssertionError('Host scope was not instructed to exit')
        except BaseException as exc:
            failures.put(exc)

    def inspect(ctx):
        try:
            value = ctx.run(handle_function_call, 'plane_resource_inspect',
                            {'kind': 'item', 'resource_id': item['id']})
            results.put(json.loads(value))
        except BaseException as exc:
            failures.put(exc)

    host = Thread(target=host_scope, daemon=True)
    caller = None
    host.start()
    try:
        current, expired, active = contexts.get(timeout=5)
        caller = Thread(target=inspect, args=(current,), daemon=True)
        caller.start()
        assert entered.wait(timeout=5), 'Inspection never reached the real HTTP server'
        assert upstream.requests[-1]['path'] == item_path

        leave_scope.set()
        # Exit must revoke the copied binding before waiting for held HTTP cleanup.
        deadline = monotonic() + 5
        while active.is_set() and monotonic() < deadline:
            closed.wait(timeout=0.01)
        assert not active.is_set(), 'Binding exit waited for HTTP before revoking authority'
        assert not closed.is_set(), 'Service closed while its HTTP read was still running'

        stale = json.loads(expired.run(handle_function_call, 'plane_resource_inspect',
                                      {'kind': 'item', 'resource_id': item['id']}))
        assert 'error' in stale
        release.set()
        caller.join(timeout=5)
        host.join(timeout=5)
        assert not caller.is_alive()
        assert not host.is_alive()
        assert failures.empty(), list(failures.queue)
        result = results.get(timeout=5)
        assert 'error' in result
        assert 'resource' not in result and 'fingerprint' not in result
        assert item['name'] not in json.dumps(result)
        assert closed.is_set()
        assert [(request['method'], request['path']) for request in upstream.requests] == [
            ('GET', item_path)
        ], 'An ended binding started item membership/dependency follow-up reads'
    finally:
        leave_scope.set()
        release.set()
        if caller is not None:
            caller.join(timeout=5)
        host.join(timeout=5)
        assert caller is None or not caller.is_alive()
        assert not host.is_alive()
