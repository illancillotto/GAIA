from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import re
from typing import Callable
from urllib.parse import urlparse
import uuid

from playwright.async_api import Page, Response, TimeoutError

from sister_exceptions import (
    DocumentNonEvadibileError,
    DocumentNotYetProducedError,
    SisterInvalidDocumentError,
    SisterRequestCorrelationError,
    SisterServerError,
)
from sister_request_rows import (
    SisterRemoteRequestRow,
    SisterRequestCorrelation,
    build_correlation,
    correlate_remote_row,
    expected_request_tokens,
    extract_remote_id,
    parse_remote_rows,
)

logger = logging.getLogger(__name__)
RICHIESTE_POLL_ATTEMPTS = 10
RICHIESTE_POLL_INTERVAL_SEC = 30
SISTER_BASE_URL = "https://sister3.agenziaentrate.gov.it"
SISTER_REQUESTS_URL = f"{SISTER_BASE_URL}/Visure/ConsultazioneRichieste.do?metodo=lista"

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
            and datetime.now(timezone.utc) < self.authenticated_until
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
        callback = self.submission_callback
        if callback is None:
            return
        if self.correlation is not None:
            self.correlation = self.correlation.with_remote_id(remote_id)
        callback(remote_id, requests_url, "submitted")
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
        if is_sister and "CHECKRICHIESTA.DO" in url.upper():
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
    if "Informativa.do" in page.url or "SelezioneConvenzione.do" in page.url:
        return False
    if await page.locator(selectors.catasto_selector).count() > 0:
        return True
    if "SceltaLink.do" in page.url or "RicercaIMM.do" in page.url:
        return True
    return await page.get_by_role("link", name=selectors.immobile_link_name).count() > 0


class SisterRequestBrowserMixin:
    def _track_response(self, response: Response) -> None:
        """Registra errori HTTP e il primo riscontro remoto del submit corrente."""
        self._session_state.track_response(response, SISTER_REQUESTS_URL)

    def _mark_remote_submitted(self, remote_id: str | None) -> None:
        self._session_state.mark_submitted(remote_id, SISTER_REQUESTS_URL)

    async def download_pdf(self, destination: Path) -> int:
        return await download_valid_pdf(self.page, self.selectors.save_button_selector, destination)

    async def begin_request_correlation(self, request: object) -> None:
        remote_id = getattr(request, "sister_remote_request_id", None)
        remote_state = str(getattr(request, "sister_remote_state", "") or "").lower()
        baseline_keys = frozenset(str(value) for value in (getattr(request, "sister_remote_baseline_keys", None) or []))
        if remote_state in {"submitted", "pending", "ready"}:
            self._session_state.correlation = SisterRequestCorrelation(
                local_request_id=str(getattr(request, "id")),
                baseline_keys=baseline_keys,
                expected_tokens=expected_request_tokens(request),
                remote_id=str(remote_id) if remote_id else None,
            )
            logger.info("Ripristinata correlazione SISTER %s per richiesta %s", remote_id, getattr(request, "id", "-"))
            return
        rows: list[SisterRemoteRequestRow] = []
        try:
            rows = await self._snapshot_remote_request_rows()
        except SisterServerError:
            raise
        except Exception as exc:
            request_id = getattr(request, "id", "-")
            logger.error("Snapshot richieste SISTER non disponibile per %s: %s", request_id, exc)
            raise SisterRequestCorrelationError(
                f"Impossibile acquisire la baseline SISTER per richiesta {request_id}"
            ) from exc
        self._session_state.correlation = build_correlation(request, rows)
        logger.info(
            "Correlazione SISTER inizializzata per %s con %s righe preesistenti",
            self._session_state.correlation.local_request_id,
            len(rows),
        )

    def get_request_correlation(self) -> SisterRequestCorrelation | None:
        return self._session_state.correlation

    async def capture_debug_snapshot(self, target_dir: Path, label: str) -> list[str]:
        target_dir.mkdir(parents=True, exist_ok=True)
        return await self._write_artifacts_to_dir(target_dir, label)

    async def poll_richieste_for_download(self, destination: Path, richieste_url: str | None = None) -> int:
        """Poll ConsultazioneRichieste.do fino a che il documento è pronto o non evadibile."""
        url = richieste_url or SISTER_REQUESTS_URL
        page = self.page
        destination.parent.mkdir(parents=True, exist_ok=True)

        for poll in range(1, RICHIESTE_POLL_ATTEMPTS + 1):
            logger.info("Poll ConsultazioneRichieste %s/%s url=%s", poll, RICHIESTE_POLL_ATTEMPTS, url)
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_timeout(1500)
            await self._trace_state(f"richieste-poll-{poll}")
            await self._raise_if_server_error()
            downloaded = await self._poll_correlated_request(destination, await self._poll_body_upper())
            if downloaded is not None:
                return downloaded
            if poll < RICHIESTE_POLL_ATTEMPTS:
                logger.info("Documento non ancora disponibile, attesa %ss", RICHIESTE_POLL_INTERVAL_SEC)
                await asyncio.sleep(RICHIESTE_POLL_INTERVAL_SEC)

        raise TimeoutError(
            f"Documento SISTER non disponibile dopo {RICHIESTE_POLL_ATTEMPTS} poll "
            f"({RICHIESTE_POLL_ATTEMPTS * RICHIESTE_POLL_INTERVAL_SEC}s)"
        )

    async def _poll_body_upper(self) -> str:
        body_text = ""
        with contextlib.suppress(Exception):
            body_text = await self.page.locator("body").inner_text(timeout=3000)
        return re.sub(r"\s+", " ", body_text).upper()

    async def _poll_correlated_request(self, destination: Path, upper_body: str) -> int | None:
        row = await self._find_correlated_request_row()
        direct_result = await self._consume_correlated_row(row, destination)
        if direct_result is not None:
            return direct_result
        return await self._poll_correlated_tabs(upper_body, destination)

    async def _consume_correlated_row(
        self,
        row: SisterRemoteRequestRow | None,
        destination: Path,
    ) -> int | None:
        if row is not None and row.state == "non_evadibile":
            await self._delete_non_evadibile_row(row)
            raise DocumentNonEvadibileError("Richiesta SISTER correlata non evadibile ed eliminata")
        if row is not None and row.state == "ready":
            return await self._download_correlated_row(row, destination)
        return None

    async def _poll_correlated_tabs(self, upper_body: str, destination: Path) -> int | None:
        non_evad = re.search(r"NON EVADIBIL[^0-9]*([0-9]+)", upper_body)
        if non_evad and int(non_evad.group(1)) > 0:
            result = await self._consume_correlated_row(
                await self._find_correlated_row_in_tab("Non evadibili"), destination
            )
            if result is not None:
                return result
        espletate = re.search(r"ESPLETATE?[^0-9]*([0-9]+)", upper_body)
        if espletate and int(espletate.group(1)) > 0:
            row = await self._find_correlated_row_in_tab("Espletate")
            if row is not None:
                return await self._download_correlated_row(row, destination)
        return None

    async def _find_correlated_request_row(self) -> SisterRemoteRequestRow | None:
        correlation = self._session_state.correlation
        if correlation is None:
            raise SisterRequestCorrelationError("Correlazione SISTER non inizializzata")
        rows = await self._extract_remote_request_rows(self.page)
        row = correlate_remote_row(rows, correlation)
        if row is not None and row.remote_id:
            self._session_state.correlation = correlation.with_remote_id(row.remote_id)
        return row

    async def _find_correlated_row_in_tab(self, tab_text: str) -> SisterRemoteRequestRow | None:
        tab = self.page.locator(f"a:has-text('{tab_text}'), td:has-text('{tab_text}')").first
        if await tab.count() == 0 or not await tab.is_visible():
            return None
        await tab.click(timeout=5000)
        await self.page.wait_for_load_state("domcontentloaded", timeout=5000)
        await self.page.wait_for_timeout(500)
        return await self._find_correlated_request_row()

    async def _download_correlated_row(self, row: SisterRemoteRequestRow, destination: Path) -> int:
        if row.download_href:
            await self.page.goto(self._absolute_sister_url(row.download_href), wait_until="domcontentloaded")
        else:
            row_locator = self.page.locator("table tr").nth(row.index)
            link = row_locator.locator("a[href*='CheckRichiesta'], a[href*='ConsultazioneRichieste']").first
            if await link.count() != 1:
                raise SisterRequestCorrelationError("La riga SISTER correlata non espone un download univoco")
            await link.click(timeout=8000)
            await self.page.wait_for_load_state("domcontentloaded", timeout=8000)
        if await self._first_visible_count(self.selectors.save_button_selector) != 1:
            raise SisterRequestCorrelationError("Il dettaglio SISTER correlato non espone il pulsante Salva")
        return await self.download_pdf(destination)

    async def _delete_non_evadibile_row(self, row: SisterRemoteRequestRow) -> None:
        if row.delete_href:
            await self.page.goto(self._absolute_sister_url(row.delete_href), wait_until="domcontentloaded")
        else:
            row_locator = self.page.locator("table tr").nth(row.index)
            action = row_locator.locator("a:has-text('Elimina'), input[value*='Elimina'], button:has-text('Elimina')").first
            if await action.count() != 1:
                raise SisterRequestCorrelationError("La richiesta non evadibile correlata non espone Elimina")
            await action.click(timeout=8000)
            await self.page.wait_for_load_state("domcontentloaded", timeout=8000)
        confirm = self.page.locator("input[value='Conferma'], button:has-text('Conferma')").first
        if await confirm.count() == 1 and await confirm.is_visible():
            await confirm.click(timeout=5000)
            await self.page.wait_for_load_state("domcontentloaded", timeout=5000)
        await self._trace_state("sister-non-evadibile-deleted")
        remaining = await self._find_correlated_request_row()
        if remaining is not None and remaining.key == row.key:
            raise SisterRequestCorrelationError("SISTER non ha confermato l'eliminazione della richiesta non evadibile")

    async def _snapshot_remote_request_rows(self) -> list[SisterRemoteRequestRow]:
        if self._context is None:
            return []
        snapshot_page = await self._context.new_page()
        snapshot_page.on("response", self._track_response)
        try:
            await snapshot_page.goto(SISTER_REQUESTS_URL, wait_until="domcontentloaded")
            await raise_if_sister_server_error(snapshot_page, self._session_state)
            return await self._extract_remote_request_rows(snapshot_page)
        finally:
            await snapshot_page.close()

    @staticmethod
    async def _extract_remote_request_rows(page: Page) -> list[SisterRemoteRequestRow]:
        payload = await page.locator("table tr").evaluate_all(
            """rows => rows.map(row => ({
                text: row.innerText || '',
                hrefs: Array.from(row.querySelectorAll('a[href]')).map(link => link.getAttribute('href')),
                values: Array.from(row.querySelectorAll('input[value]')).map(input => `${input.getAttribute('name') || ''}=${input.getAttribute('value')}`)
            }))"""
        )
        return parse_remote_rows(payload)

    @staticmethod
    def _absolute_sister_url(href: str) -> str:
        if href.startswith("http://") or href.startswith("https://"):
            return href
        return f"{SISTER_BASE_URL}{href if href.startswith('/') else '/' + href}"
