from __future__ import annotations

import asyncio
import fcntl
import json
import logging
import time
from contextlib import asynccontextmanager
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import unquote_plus

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def retry_after_seconds(value: str, now: float) -> float:
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            return max(0.0, parsedate_to_datetime(value).timestamp() - now)
        except (ValueError, TypeError, OverflowError):
            return 0.0


def source_failed(response: httpx.Response) -> bool:
    if response.status_code == 429 or response.status_code >= 500:
        return True
    payload = unquote_plus(response.content[:512].decode("utf-8", errors="replace")).strip()
    normalized = payload.lower()
    return normalized.startswith("sessione scaduta") or (
        payload.startswith("NO") and "sessione scaduta" in normalized
    )


def source_outcome(request: httpx.Request, response: httpx.Response) -> bool | None:
    if source_failed(response):
        return True
    if request.url.path.endswith(
        ("login.aspx", "main.aspx", "ajaxTiles.aspx", "handlerKeepSessionAlive.ashx")
    ):
        return None
    return False


class CapacitasRequestPolicy:
    def __init__(self, path: Path, interval: float, cooldown: float, maximum: float) -> None:
        self.path = path
        self.interval = interval
        self.cooldown = cooldown
        self.maximum = maximum

    def _lock_available(self, state_file) -> bool:
        try:
            fcntl.flock(state_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except BlockingIOError:
            return False

    @asynccontextmanager
    async def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a+", encoding="utf-8") as state_file:
            while True:
                if not self._lock_available(state_file):
                    await asyncio.sleep(0.25)
                    continue
                try:
                    state_file.seek(0)
                    payload = state_file.read()
                    state = json.loads(payload) if payload else {"next_at": 0.0, "failures": {}}
                    delay = max(0.0, state["next_at"] - time.time())
                    if delay == 0:
                        yield state
                        return
                finally:
                    fcntl.flock(state_file, fcntl.LOCK_UN)
                await asyncio.sleep(delay)

    def record(self, state: dict, host: str, failed: bool | None, retry_after: str = "") -> None:
        now = time.time()
        failures = state["failures"].get(host, 0)
        if failed is not None:
            failures = min(failures + 1, 10) if failed else 0
        state["failures"][host] = failures
        delay = self.interval
        if failed:
            delay = max(
                delay,
                min(self.maximum, self.cooldown * 2 ** (failures - 1)),
                retry_after_seconds(retry_after, now),
            )
            logger.warning(
                "Capacitas rallentato: host=%s errori=%s pausa=%.0fs", host, failures, delay
            )
        state["next_at"] = now + delay
        with self.path.open("r+", encoding="utf-8") as state_file:
            state_file.seek(0)
            state_file.write(json.dumps(state))
            state_file.truncate()


class CapacitasPoliteTransport(httpx.AsyncBaseTransport):
    def __init__(self, policy: CapacitasRequestPolicy, transport: httpx.AsyncBaseTransport) -> None:
        self.policy = policy
        self.transport = transport

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        async with self.policy.acquire() as state:
            try:
                response = await self.transport.handle_async_request(request)
                try:
                    await response.aread()
                finally:
                    await response.aclose()
            except httpx.TransportError:
                self.policy.record(state, request.url.host, True)
                raise
            except asyncio.CancelledError:
                self.policy.record(state, request.url.host, None)
                raise
            self.policy.record(
                state,
                request.url.host,
                source_outcome(request, response),
                response.headers.get("Retry-After", ""),
            )
            return response

    async def aclose(self) -> None:
        await self.transport.aclose()


def polite_transport() -> CapacitasPoliteTransport:
    policy = CapacitasRequestPolicy(
        Path(settings.capacitas_request_policy_path),
        settings.capacitas_request_interval_seconds,
        settings.capacitas_request_cooldown_seconds,
        settings.capacitas_request_max_cooldown_seconds,
    )
    return CapacitasPoliteTransport(policy, httpx.AsyncHTTPTransport())


def polite_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=polite_transport(),
        follow_redirects=True,
        timeout=30.0,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/148.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
        },
    )
