from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from email.utils import format_datetime
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest

from app.modules.elaborazioni.capacitas import request_policy as policy_module
from app.modules.elaborazioni.capacitas.request_policy import (
    CapacitasPoliteTransport,
    CapacitasRequestPolicy,
    polite_http_client,
    polite_transport,
    retry_after_seconds,
    source_failed,
    source_outcome,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def clock(monkeypatch):
    now = [1000.0]
    sleeps = []

    async def sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    monkeypatch.setattr(policy_module.time, "time", lambda: now[0])
    monkeypatch.setattr(policy_module.asyncio, "sleep", sleep)
    return now, sleeps


def policy(path: Path):
    return CapacitasRequestPolicy(path, interval=3, cooldown=60, maximum=900)


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("120", 120),
        ("-1", 0),
        ("invalid", 0),
        ("", 0),
        (format_datetime(datetime.fromtimestamp(1120, UTC), usegmt=True), 120),
        (format_datetime(datetime.fromtimestamp(900, UTC), usegmt=True), 0),
    ],
)
def test_retry_after(header, expected):
    assert retry_after_seconds(header, 1000) == expected


@pytest.mark.parametrize(
    ("status", "payload", "failed"),
    [
        (429, "", True),
        (500, "", True),
        (503, "", True),
        (200, "NOSessione+scaduta", True),
        (200, "NOsessione%20scaduta", True),
        (200, "NOnessuno storico presente", False),
        (200, "SZdati", False),
        (404, "", False),
    ],
)
def test_source_failure_keeps_empty_results_valid(status, payload, failed):
    assert source_failed(httpx.Response(status, text=payload)) is failed


@pytest.mark.parametrize(
    "path", ["login.aspx", "main.aspx", "ajaxTiles.aspx", "handlerKeepSessionAlive.ashx"]
)
def test_session_maintenance_does_not_reset_failure_streak(path):
    request = httpx.Request("GET", "https://involture.example/pages/" + path)
    assert source_outcome(request, httpx.Response(200)) is None
    assert source_outcome(request, httpx.Response(503)) is True


@pytest.mark.anyio
async def test_backoff_is_shared_and_respects_retry_after(tmp_path, clock):
    path = tmp_path / "shared.json"
    first = policy(path)
    second = policy(path)
    async with first.acquire() as state:
        first.record(state, "involture.example", True)
    async with second.acquire() as state:
        assert clock[0][0] == 1060
        second.record(state, "involture.example", True)
    async with first.acquire() as state:
        assert clock[0][0] == 1180
        first.record(state, "involture.example", None)
        assert state["failures"]["involture.example"] == 2
        first.record(state, "involture.example", True, "1800")
        assert state["next_at"] == 2980
    assert json.loads(path.read_text())["failures"]["involture.example"] == 3


@pytest.mark.anyio
async def test_cooldown_caps_and_only_real_success_resets_host(tmp_path, clock):
    limiter = policy(tmp_path / "policy.json")
    async with limiter.acquire() as state:
        for _ in range(12):
            limiter.record(state, "involture.example", True)
        assert state["next_at"] == 1900
        assert state["failures"]["involture.example"] == 10
        limiter.record(state, "sso.example", False)
        assert state["failures"]["involture.example"] == 10
        limiter.record(state, "involture.example", False)
        assert state["failures"]["involture.example"] == 0
        assert state["next_at"] == 1003


@pytest.mark.anyio
async def test_lock_waits_without_blocking_event_loop_and_releases_on_cancel(tmp_path):
    path = tmp_path / "policy.json"
    first = policy(path)
    second = policy(path)
    entered = asyncio.Event()

    async def competing_request():
        async with second.acquire():
            entered.set()

    async with first.acquire():
        waiting = asyncio.create_task(competing_request())
        await asyncio.sleep(0.01)
        assert not entered.is_set()
        waiting.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiting
    await competing_request()
    assert entered.is_set()


@pytest.mark.anyio
async def test_corrupt_policy_fails_closed_and_releases_lock(tmp_path):
    path = tmp_path / "policy.json"
    path.write_text("invalid")
    with pytest.raises(json.JSONDecodeError):
        async with policy(path).acquire():
            pytest.fail("A corrupted policy must not permit a request")
    path.write_text('{"next_at": 0, "failures": {}}')
    async with policy(path).acquire() as state:
        assert state["failures"] == {}


@pytest.mark.anyio
async def test_transport_preserves_payload_and_serializes_clients(tmp_path):
    path = tmp_path / "policy.json"
    started = []
    active = 0
    maximum_active = 0

    async def handler(request):
        nonlocal active, maximum_active
        active += 1
        maximum_active = max(maximum_active, active)
        started.append(asyncio.get_running_loop().time())
        await asyncio.sleep(0.01)
        active -= 1
        return httpx.Response(200, content=b"unchanged", headers={"X-Source": "capacitas"})

    transports = [
        CapacitasPoliteTransport(
            CapacitasRequestPolicy(path, 0.03, 60, 900), httpx.MockTransport(handler)
        )
        for _ in range(2)
    ]
    async with (
        httpx.AsyncClient(transport=transports[0]) as first,
        httpx.AsyncClient(transport=transports[1]) as second,
    ):
        responses = await asyncio.gather(
            first.get("https://involture.example/data"),
            second.get("https://involture.example/data"),
        )
    assert maximum_active == 1
    assert started[1] - started[0] >= 0.03
    assert all(response.content == b"unchanged" for response in responses)
    assert all(response.headers["X-Source"] == "capacitas" for response in responses)


@pytest.mark.anyio
@pytest.mark.parametrize("exception", [httpx.ReadTimeout("timeout"), asyncio.CancelledError()])
async def test_transport_failure_or_cancellation_keeps_admission_safe(tmp_path, clock, exception):
    async def handler(request):
        raise exception

    path = tmp_path / "policy.json"
    transport = CapacitasPoliteTransport(policy(path), httpx.MockTransport(handler))
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(type(exception)):
            await client.get("https://involture.example/data")
    state = json.loads(path.read_text())
    assert state["next_at"] == (1060 if isinstance(exception, httpx.TransportError) else 1003)
    async with policy(path).acquire():
        pass


@pytest.mark.anyio
async def test_body_read_error_closes_response_and_backs_off(tmp_path, clock):
    class FailingStream(httpx.AsyncByteStream):
        closed = False

        async def __aiter__(self):
            raise httpx.ReadError("body interrupted")
            yield b""

        async def aclose(self):
            self.closed = True

    stream = FailingStream()
    transport = CapacitasPoliteTransport(
        policy(tmp_path / "policy.json"),
        httpx.MockTransport(lambda request: httpx.Response(200, stream=stream)),
    )
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(httpx.ReadError):
            await client.get("https://involture.example/data")
    assert stream.closed


@pytest.mark.anyio
async def test_factory_uses_validated_settings(tmp_path, monkeypatch):
    monkeypatch.setattr(
        policy_module.settings, "capacitas_request_policy_path", str(tmp_path / "policy.json")
    )
    transport = polite_transport()
    assert transport.policy.interval == 3
    assert transport.policy.cooldown == 60
    assert transport.policy.maximum == 900
    await transport.aclose()
    async with polite_http_client() as client:
        assert client.follow_redirects
        assert client.timeout.read == 30
        assert "Chrome/148" in client.headers["User-Agent"]


@pytest.mark.anyio
async def test_keepalive_is_also_throttled_and_does_not_clear_errors(tmp_path, clock):
    path = tmp_path / "policy.json"
    handler = AsyncMock(
        side_effect=[httpx.Response(200, text="NOSessione scaduta"), httpx.Response(200)]
    )
    transport = CapacitasPoliteTransport(policy(path), httpx.MockTransport(handler))
    async with httpx.AsyncClient(transport=transport) as client:
        await client.get("https://involture.example/data")
        await client.post("https://involture.example/pages/handlerKeepSessionAlive.ashx")
    assert clock[0][0] == 1060
    assert json.loads(path.read_text())["failures"]["involture.example"] == 1


@pytest.mark.anyio
async def test_http_rate_limit_preserves_status_and_server_retry_after(tmp_path, clock):
    path = tmp_path / "policy.json"
    transport = CapacitasPoliteTransport(
        policy(path),
        httpx.MockTransport(lambda request: httpx.Response(429, headers={"Retry-After": "1800"})),
    )
    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.get("https://involture.example/data")
        with pytest.raises(httpx.HTTPStatusError):
            response.raise_for_status()
    assert json.loads(path.read_text())["next_at"] == 2800
