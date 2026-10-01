"""Independent polling thread, so bulk sync never delays interactive refreshes."""

from __future__ import annotations

import asyncio
import logging
import threading

import httpx

from app.core.config import settings
from app.core.database import SessionLocal
from app.modules.presenze.services.gate_collaborator_refresh import process_collaborator_refreshes

logger = logging.getLogger(__name__)
POLL_SECONDS = 3


async def _poll_once() -> None:
    with SessionLocal() as db:
        async with httpx.AsyncClient(
            base_url=settings.gate_mobile_gateway_base_url.rstrip("/"), timeout=30
        ) as client:
            await process_collaborator_refreshes(
                db, client, {"Authorization": f"Bearer {settings.gate_mobile_connector_token}"}
            )


def _run(stop: threading.Event) -> None:
    while not stop.is_set():
        try:
            asyncio.run(_poll_once())
        except Exception:
            logger.exception("Collaborator refresh poll failed; retry on next poll")
        if stop.wait(POLL_SECONDS):
            break


def start_refresh_polling(stop: threading.Event) -> threading.Thread | None:
    if not settings.gate_mobile_gateway_base_url or not settings.gate_mobile_connector_token:
        return None
    thread = threading.Thread(
        target=_run, args=(stop,), name="gate-collaborator-refresh", daemon=True
    )
    thread.start()
    return thread
