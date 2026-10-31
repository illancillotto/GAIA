"""Retry policy for the weekly Capacitas ruoli export: transient failures back off, the rest fail fast."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar

import httpx

from app.modules.elaborazioni.capacitas.apps.incass.client import CapacitasInCassSessionExpiredError
from app.modules.elaborazioni.capacitas.export_http import ExportStepError, SessionExpiredError
from app.services.google_drive import GoogleDriveError

logger = logging.getLogger(__name__)
T = TypeVar("T")


def is_session_error(exc: BaseException) -> bool:
    return isinstance(exc, SessionExpiredError | CapacitasInCassSessionExpiredError)


def is_retryable(exc: BaseException) -> bool:
    if is_session_error(exc):
        return True
    if isinstance(exc, ExportStepError | GoogleDriveError):
        return exc.retryable
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return status in {408, 429} or status >= 500
    return isinstance(exc, httpx.TransportError)


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int
    base_delay_seconds: float
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep

    def delay_for(self, attempt: int) -> float:
        return self.base_delay_seconds * (2 ** (attempt - 1))

    def should_retry(self, exc: BaseException, attempt: int) -> bool:
        return attempt < self.max_attempts and is_retryable(exc)

    async def _prepare_retry(
        self,
        exc: BaseException,
        attempt: int,
        label: str,
        on_session_lost: Callable[[], Awaitable[None]] | None,
    ) -> None:
        delay = self.delay_for(attempt)
        logger.warning(
            "%s: tentativo %d fallito (%s), nuovo tentativo tra %.0fs", label, attempt, exc, delay
        )
        await self.sleep(delay)
        if on_session_lost is not None and is_session_error(exc):
            await on_session_lost()

    async def run(
        self,
        operation: Callable[[], Awaitable[T]],
        *,
        label: str,
        on_session_lost: Callable[[], Awaitable[None]] | None = None,
    ) -> T:
        attempt = 1
        while True:
            try:
                return await operation()
            except Exception as exc:
                if not self.should_retry(exc, attempt):
                    raise
                await self._prepare_retry(exc, attempt, label, on_session_lost)
            attempt += 1
