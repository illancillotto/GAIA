"""Capture failures while the execution claim still owns the request."""

import asyncio
import logging
from pathlib import Path

from sqlalchemy import select

from app.models.catasto import CatastoVisuraRequest

logger = logging.getLogger(__name__)


async def capture_request_error(session_factory, browser, selection, error, write_error) -> None:
    try:
        with session_factory() as db:
            request = db.scalar(
                select(CatastoVisuraRequest)
                .where(
                    CatastoVisuraRequest.id == selection.request_id,
                    CatastoVisuraRequest.execution_token == selection.execution_token,
                    CatastoVisuraRequest.status == "processing",
                )
                .with_for_update()
            )
            if request is None or selection.execution_token is None:
                return
            request.error_message = str(error)
            if request.artifact_dir:
                await _capture_files(browser, Path(request.artifact_dir), error, write_error)
            db.commit()
    except Exception:
        logger.exception("Cattura diagnostica SISTER fallita per %s", selection.request_id)


async def _capture_files(browser, directory: Path, error: Exception, write_error) -> None:
    try:
        write_error(directory, error)
    except OSError:
        logger.exception("Scrittura errore SISTER fallita")
    try:
        # Bound the DB row lock even when the browser has stopped responding.
        await asyncio.wait_for(
            browser.capture_debug_snapshot(directory, "final-failed"), timeout=10
        )
    except Exception:
        logger.exception("Screenshot errore SISTER non disponibile")
