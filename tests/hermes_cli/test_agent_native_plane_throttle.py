"""Transient read throttling backs off without retrying mutations or losing authority."""
import time
import pytest
from agent_native.identity import OWNER
from agent_native.plane_access import revoke_project
from agent_native.plane_reads import PlaneReadError
from tests.hermes_cli.test_agent_native_plane_reads import upstream, scoped, project_record  # noqa: F401


@pytest.mark.parametrize('status', [429, 502, 503, 504])
def test_get_honors_retry_after_then_returns_scoped_result(scoped, upstream, status):
    timestamps = []
    def route(_):
        timestamps.append(time.monotonic())
        return (status, {'Retry-After':'1'}, {}) if len(timestamps)==1 else (200, {}, project_record(scoped))
    upstream.routes[scoped[6]] = route
    assert scoped[5].get_project(scoped[4])['id'] == scoped[8]
    assert len(timestamps) == 2 and timestamps[1]-timestamps[0] >= 1


def test_throttle_retries_are_bounded_and_large_delay_is_not_ignored(scoped, upstream):
    upstream.routes[scoped[6]] = 429, {'Retry-After':'0'}, {}
    with pytest.raises(PlaneReadError) as caught:
        scoped[5].get_project(scoped[4])
    assert caught.value.status == 429 and len(upstream.requests) == 3
    upstream.requests.clear()
    upstream.routes[scoped[6]] = 429, {'Retry-After':'31'}, {}
    started = time.monotonic()
    with pytest.raises(PlaneReadError) as caught:
        scoped[5].get_project(scoped[4])
    assert caught.value.retry_after == 31 and len(upstream.requests) == 1
    assert time.monotonic()-started < 2


def test_revocation_during_throttle_wait_prevents_retry(scoped, upstream, monkeypatch):
    from agent_native import plane_reads
    upstream.routes[scoped[6]] = 429, {'Retry-After':'1'}, {}
    def revoke(_):
        revoke_project(scoped[0], actor=OWNER, binding_id=scoped[2]['id'])
    monkeypatch.setattr(plane_reads.time, 'sleep', revoke)
    with pytest.raises(PermissionError):
        scoped[5].get_project(scoped[4])
    assert len(upstream.requests) == 1
