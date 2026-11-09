"""Navigate the observed SISTER request list and retain bounded polling."""

from __future__ import annotations

import asyncio
import logging

from playwright.async_api import TimeoutError

from sister_browser_reliability import download_valid_pdf
from sister_exceptions import SisterDocumentNotReadyError, SisterServerError
from sister_submission_identity import (
    IDENTITY_VERSION,
    capture_submission_identity,
    observed_requests_url,
)
from sister_telemetry import SisterTelemetryRecord

logger = logging.getLogger(__name__)


async def poll_for_pdf(browser, destination, url, attempts, interval, deferred: bool) -> int:
    page = browser.page
    emit = getattr(browser, "_gaia_emit_sister_telemetry", None)
    url = await observed_requests_url(page, url, browser._session_state.convention_id)
    destination.parent.mkdir(parents=True, exist_ok=True)
    for poll in range(1, attempts + 1):
        logger.info("Poll ConsultazioneRichieste %s/%s url=%s", poll, attempts, url)
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)
        await browser._trace_state(f"richieste-poll-{poll}")
        await browser._raise_if_server_error()
        await validate_requests_page(page, emit)
        downloaded = await browser._poll_correlated_request(
            destination, await browser._poll_body_upper()
        )
        if downloaded is not None:
            return downloaded
        if poll < attempts:
            await asyncio.sleep(interval)
    polls = f"{attempts} poll" + (" iniziali" if deferred else "")
    message = f"Documento SISTER non disponibile dopo {polls} ({attempts * interval}s)"
    if deferred:
        raise SisterDocumentNotReadyError(message + " — richiesta messa in coda")
    raise TimeoutError(message)


async def validate_requests_page(page, emit) -> None:
    valid = await page.locator("input[name='radioCount']").count() > 0
    if emit is not None:
        emit(
            SisterTelemetryRecord(
                "recovery_navigation",
                IDENTITY_VERSION,
                outcome="success" if valid else "error",
                severity="info" if valid else "warning",
                endpoint=page.url,
            )
        )
    if not valid:
        raise SisterServerError("SISTER elenco richieste non disponibile: controlli assenti")


async def download_submission_pdf(browser, destination, requests_url: str) -> int:
    """Capture the submission before a download can fail or replace its page."""
    await capture_submission_identity(
        browser.page,
        browser._session_state,
        requests_url,
        getattr(browser, "_gaia_emit_sister_telemetry", None),
    )
    return await download_valid_pdf(
        browser.page, browser.selectors.save_button_selector, destination
    )
