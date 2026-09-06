from __future__ import annotations

import contextlib
import logging
import os
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from sister_exceptions import (
    DocumentNotYetProducedError,
    SisterInvalidDocumentError,
    SisterRequestCorrelationError,
    SisterServerError,
)
from sister_request_rows import SisterRequestCorrelation, extract_remote_id

logger = logging.getLogger(__name__)
UTC = timezone.utc  # noqa: UP017 - Production worker uses Python 3.10.

RemoteStateCallback = Callable[[str | None, str | None, str], None]


@dataclass(slots=True)
class SisterSessionState:
    username: str | None = None
    convention_id: str | None = None
    authenticated_until: datetime | None = None
    correlation: SisterRequestCorrelation | None = None
    pending_server_error: tuple[int, str] | None = None
    submission_callback: RemoteStateCallback | None = None

    def is_authenticated(self, username: str, convention_id: str) -> bool:
        return bool(
            self.username == username
            and self.convention_id == convention_id
            and self.authenticated_until is not None
            and datetime.now(UTC) < self.authenticated_until
        )

    def authenticate(self, username: str, convention_id: str, authenticated_until: datetime) -> None:
        self.username = username
        self.convention_id = convention_id
        self.authenticated_until = authenticated_until

    def begin_submission(self, callback: RemoteStateCallback | None) -> None:
        self.submission_callback = callback

    def clear_submission(self) -> None:
        self.submission_callback = None

    def mark_submitted(self, remote_id: str | None, requests_url: str) -> None:
        if self.correlation is not None:
            known_id = self.correlation.remote_id
            if remote_id and known_id and remote_id != known_id:
                raise SisterRequestCorrelationError("ID remoto SISTER diverso dalla richiesta corrente")
            self.correlation = self.correlation.with_remote_id(remote_id)
        callback = self.submission_callback
        if callback is None:
            return
        callback(remote_id, requests_url, "submitted")
        if remote_id:
            self.submission_callback = None

    def track_response(self, response, requests_url: str) -> None:
        try:
            status = response.status
            url = response.url
            resource_type = response.request.resource_type
        except Exception as exc:
            logger.debug("Risposta Playwright SISTER non classificabile: %s", exc)
            return

        hostname = (urlparse(url).hostname or "").lower()
        is_sister = hostname == "agenziaentrate.gov.it" or hostname.endswith(".agenziaentrate.gov.it")
        if is_sister and 500 <= status <= 599 and resource_type in {"document", "xhr", "fetch"}:
            self.pending_server_error = (status, url)
        if is_sister:
            self.observe_submission_response(url, requests_url)

    def observe_submission_response(self, url: str, requests_url: str) -> None:
        # Unarmed responses can belong to a previous request on this reused page.
        if self.submission_callback is not None and "CHECKRICHIESTA.DO" in url.upper():
            self.mark_submitted(extract_remote_id((url,)), requests_url)

    def pop_server_error(self) -> tuple[int, str] | None:
        pending_error = self.pending_server_error
        self.pending_server_error = None
        return pending_error


async def download_valid_pdf(page, save_button_selector: str, destination: Path) -> int:
    destination.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Avvio download PDF su %s", destination)
    temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.part")
    async with page.expect_download(timeout=20000) as download_info:
        await page.click(save_button_selector)
    download = await download_info.value
    await download.save_as(str(temporary))
    try:
        _validate_pdf(temporary)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    logger.info("Download PDF completato: %s", destination)
    return destination.stat().st_size


def _validate_pdf(path: Path) -> None:
    with path.open("rb") as handle:
        signature = handle.read(5)
    if path.stat().st_size < 8 or signature != b"%PDF-":
        raise SisterInvalidDocumentError("SISTER ha restituito un file non PDF o vuoto")


async def raise_if_sister_server_error(page, state: SisterSessionState) -> None:
    pending_error = state.pop_server_error()
    if pending_error is not None:
        status, response_url = pending_error
        if await _is_non_blocking_init_portale_error(page, status, response_url):
            logger.warning(
                "Errore HTTP SISTER initPortale non bloccante ignorato: status=%s url=%s page=%s",
                status,
                response_url,
                page.url,
            )
            return
        logger.error("Errore HTTP SISTER rilevato: status=%s url=%s", status, response_url)
        raise SisterServerError(f"SISTER HTTP {status} su {response_url}")

    try:
        body_text = await page.locator("body").inner_text(timeout=1500)
    except Exception as exc:
        logger.debug("Impossibile leggere la pagina durante il controllo errori SISTER: %s", exc)
        return
    upper = re.sub(r"\s+", " ", body_text).upper()
    if "ERROR 500" in upper or "NULLPOINTEREXCEPTION" in upper or "HTTP STATUS 500" in upper:
        logger.error("Errore SISTER 500 rilevato: url=%s", page.url)
        raise SisterServerError(f"SISTER 500 su {page.url}")


async def _is_non_blocking_init_portale_error(page, status: int, response_url: str) -> bool:
    if status != 501 or "/portale-rest/rs/initPortale" not in response_url:
        return False
    page_url = (getattr(page, "url", "") or "").lower()
    if "sister3.agenziaentrate.gov.it/servizi" not in page_url:
        return False
    try:
        title = await page.title()
        body_text = await page.locator("body").inner_text(timeout=1500)
    except Exception as exc:
        logger.debug("Impossibile validare initPortale 501 non bloccante: %s", exc)
        return False
    upper = re.sub(r"\s+", " ", f"{title} {body_text}").upper()
    if "UTENTE BLOCCATO" in upper or "GIA' IN SESSIONE" in upper or "GIÀ IN SESSIONE" in upper:
        return False
    return "HOME DEI SERVIZI" in upper and "CONSULTAZIONI E CERTIFICAZIONI" in upper


async def document_not_yet_produced_error(
    page,
    state: SisterSessionState,
    base_url: str,
    requests_url: str,
) -> DocumentNotYetProducedError | None:
    body_text = ""
    with contextlib.suppress(Exception):
        body_text = await page.locator("body").inner_text(timeout=2000)
    upper = re.sub(r"\s+", " ", body_text).upper()
    if not _is_pending_document_page(page.url, upper):
        return None

    remote_requests_url: str | None = None
    with contextlib.suppress(Exception):
        href = await page.locator("a[href*='ConsultazioneRichieste']").first.get_attribute("href", timeout=2000)
        if href:
            remote_requests_url = href if href.startswith("http") else base_url + href
    remote_id = extract_remote_id(tuple(value for value in (page.url, remote_requests_url or "") if value))
    state.mark_submitted(remote_id, requests_url)
    logger.info(
        "Documento SISTER non ancora prodotto, richieste_url=%s remote_id=%s",
        remote_requests_url,
        remote_id,
    )
    return DocumentNotYetProducedError.correlated(remote_requests_url, remote_id)


def _is_pending_document_page(url: str, upper_body: str) -> bool:
    return (
        "NON E' STATO ANCORA PRODOTTO" in upper_body
        or "NON È STATO ANCORA PRODOTTO" in upper_body
        or "CHECKRICHIESTA.DO" in url.upper()
    )


async def is_visura_area_ready(page, selectors) -> bool:
    if "Visure/SceltaServizio.do" in page.url or "Visure/SelezioneConvenzione.do" in page.url:
        return True
    if "Informativa.do" in page.url or "SelezioneConvenzione.do" in page.url:
        return False
    if await page.locator(selectors.catasto_selector).count() > 0:
        return True
    if "SceltaLink.do" in page.url or "RicercaIMM.do" in page.url:
        return True
    return await page.get_by_role("link", name=selectors.immobile_link_name).count() > 0
