"""Read-only Playwright client for the STEP portal (Contribuenti).

Python port of the verified ``step-scraper``: login, paginated Contribuenti
list, scheda contribuente with every grid, tributi modal and document PDFs.
The client never changes data on STEP; it only clicks navigation, detail and
download links.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright

from step_browser_scripts import READ_CONTRIBUENTI, READ_SHEET, READ_TRIBUTI
from step_rules import (
    StepIntegrityError,
    TributiCollector,
    expected_tributi,
    grid_link_selector,
    sheet_documents,
)

logger = logging.getLogger(__name__)

_DATA_RESOURCE_TYPES = {"xhr", "fetch"}
_DEFAULT_CHROME_PATH = "/opt/google/chrome/chrome"
_COOKIE_BUTTON = re.compile(r"OK.*accetto i cookie", re.IGNORECASE)
_LOGIN_BUTTON = re.compile(r"^Accedi$", re.IGNORECASE)


class StepLoginError(RuntimeError):
    """The portal rejected the credentials (counts towards credential auto-disable)."""


@dataclass(frozen=True)
class StepClientConfig:
    portal_url: str
    headless: bool = True
    timeout_ms: int = 60000
    min_delay_ms: int = 600
    browser_path: str | None = None


def _browser_path(config: StepClientConfig) -> str | None:
    if config.browser_path:
        return config.browser_path
    configured = os.getenv("STEP_BROWSER_PATH")
    if configured:
        return configured
    return _DEFAULT_CHROME_PATH if Path(_DEFAULT_CHROME_PATH).exists() else None


class _NetworkTracker:
    """Counts in-flight XHR/fetch requests so the client can wait for SmartClient to settle."""

    def __init__(self) -> None:
        self.active: set[Any] = set()
        self.failures: list[str] = []
        self.last_activity = time.monotonic()

    def attach(self, page) -> None:
        page.on("request", self._started)
        page.on("requestfinished", self._finished)
        page.on("requestfailed", self._finished)

    def _started(self, request) -> None:
        if request.resource_type in _DATA_RESOURCE_TYPES:
            self.active.add(request)
            self.last_activity = time.monotonic()

    def _finished(self, request) -> None:
        if request not in self.active:
            return
        self.active.discard(request)
        self.last_activity = time.monotonic()
        if request.failure:
            self.failures.append(str(request.failure))

    def mark(self) -> int:
        return len(self.failures)

    async def wait_idle(self, since: int, timeout_s: float = 120.0) -> None:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if len(self.failures) > since:
                raise RuntimeError(f"Richiesta dati STEP fallita: {self.failures[-1]}")
            if not self.active and time.monotonic() - self.last_activity >= 0.4:
                return
            await asyncio.sleep(0.2)
        raise TimeoutError("Timeout in attesa del completamento delle richieste STEP")


class StepBrowserClient:
    def __init__(self, config: StepClientConfig, *, playwright_factory=async_playwright) -> None:
        self.config = config
        self._playwright_factory = playwright_factory
        self._playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.network = _NetworkTracker()

    async def __aenter__(self) -> StepBrowserClient:
        self._playwright = await self._playwright_factory().start()
        executable = _browser_path(self.config)
        self.browser = await self._playwright.chromium.launch(
            headless=self.config.headless,
            **({"executable_path": executable} if executable else {}),
        )
        self.context = await self.browser.new_context(
            accept_downloads=True, viewport={"width": 1600, "height": 1000}
        )
        self.page = await self.context.new_page()
        self.page.set_default_timeout(self.config.timeout_ms)
        self.network.attach(self.page)
        return self

    async def __aexit__(self, *_exc) -> None:
        for resource in (self.context, self.browser):
            if resource is not None:
                try:
                    await resource.close()
                except Exception:
                    logger.warning("STEP: chiusura browser non riuscita", exc_info=True)
        if self._playwright is not None:
            await self._playwright.stop()

    async def _pause(self) -> None:
        await asyncio.sleep(max(600, self.config.min_delay_ms) / 1000)

    async def _wait_state(self, script: str, timeout_s: float | None = None) -> dict:
        deadline = time.monotonic() + (
            timeout_s if timeout_s is not None else self.config.timeout_ms / 1000
        )
        while time.monotonic() < deadline:
            state = await self.page.evaluate(script)
            if state:
                return state
            await asyncio.sleep(0.3)
        raise TimeoutError("Stato atteso del portale STEP non raggiunto")

    async def login(self, username: str, password: str) -> None:
        page = self.page
        await page.goto(self.config.portal_url, wait_until="domcontentloaded")
        await page.locator('input[name="Utente"]').wait_for(state="visible")
        cookie_button = page.get_by_role("button", name=_COOKIE_BUTTON)
        if await cookie_button.is_visible():
            await cookie_button.click()
        await page.locator('input[name="Utente"]').fill(username)
        await page.locator('input[name="Password"]').fill(password)
        await page.get_by_role("button", name=_LOGIN_BUTTON).click()
        try:
            await page.locator('input[name="Password"]').wait_for(state="hidden", timeout=30000)
        except Exception as exc:
            raise StepLoginError(
                "Accesso STEP non riuscito: credenziali rifiutate o portale non disponibile"
            ) from exc

    async def open_contribuenti(self) -> dict:
        await self.page.get_by_role("button", name="Contribuenti", exact=True).click()
        await self.page.get_by_text("Ricerca", exact=True).click()
        state = await self._wait_state(READ_CONTRIBUENTI, timeout_s=120)
        await self.network.wait_idle(self.network.mark())
        return state

    async def go_to_page(self, target: int, previous: dict) -> dict:
        errors: list[str] = []

        def on_failed(request) -> None:
            if request.resource_type in _DATA_RESOURCE_TYPES:
                errors.append(str(request.failure or "richiesta fallita"))

        def on_response(response) -> None:
            if response.request.resource_type in _DATA_RESOURCE_TYPES and response.status >= 400:
                errors.append(f"HTTP {response.status}")

        self.page.on("requestfailed", on_failed)
        self.page.on("response", on_response)
        try:
            await self._pause()
            if target == previous["page"] + 1:
                await self.page.locator('img[src$="/successiva.gif"]').click()
            else:
                await self.page.locator('input[type="text"]:visible').last.fill(str(target))
                await self.page.locator('img[src$="/vai.gif"]').click()
            return await self._wait_page(target, previous["rows"], errors)
        finally:
            self.page.remove_listener("requestfailed", on_failed)
            self.page.remove_listener("response", on_response)

    async def _wait_page(self, target: int, previous_rows: list, errors: list[str]) -> dict:
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            if errors:
                raise RuntimeError(f"Errore di rete STEP a pagina {target}: {errors[-1]}")
            state = await self.page.evaluate(READ_CONTRIBUENTI)
            if state and state["page"] == target and state["rows"] != previous_rows:
                return state
            await asyncio.sleep(0.3)
        raise TimeoutError(f"Timeout nel caricamento della pagina STEP {target}")

    async def extract_scheda(self, summary: dict) -> dict:
        marker = self.network.mark()
        await self.page.get_by_role("link", name=summary["COD_FIS_NEW"], exact=True).click()
        await self._wait_state(READ_SHEET)
        await self.network.wait_idle(marker)
        state = await self.page.evaluate(READ_SHEET)
        if state["anagrafica"].get("Codice fiscale") != summary["COD_FIS_NEW"]:
            raise StepIntegrityError("La scheda STEP aperta appartiene a un altro contribuente")
        entries, reconciliation = sheet_documents(state["grids"], summary.get("NUMERODOC"))
        documents = []
        for entry in entries:
            tributi = await self._collect_tributi(entry)
            documents.append(
                {
                    "document": entry.document,
                    "tributi": tributi,
                    "pdf": await self._download_pdf(entry),
                }
            )
        if not state.get("closeId"):
            raise StepIntegrityError("Controllo di chiusura scheda STEP non trovato")
        await self.page.locator(f"#{state['closeId']}").click()
        return {
            "summary": summary,
            "anagrafica": state["anagrafica"],
            "situazioneContabile": state["situazioneContabile"],
            "sections": state["grids"],
            "documentReconciliation": reconciliation,
            "documents": documents,
        }

    async def _collect_tributi(self, entry) -> dict:
        collector = TributiCollector(
            num_doc=str(entry.document["NUM_DOC"]), expected=expected_tributi(entry.document)
        )
        if collector.expected == 0:
            return collector.result()
        marker = self.network.mark()
        await self.page.locator(grid_link_selector(entry.grid, entry.row_index, "NUM_TRIB")).click()
        await self._wait_state(READ_TRIBUTI)
        await self.network.wait_idle(marker)
        state = await self.page.evaluate(READ_TRIBUTI)
        try:
            collector.start(state)
            for page_number in range(1, collector.pages + 1):
                if page_number > 1:
                    await self._pause()
                    marker = self.network.mark()
                    await self.page.locator(
                        f'#{state["handleId"]} img[src$="/successiva.gif"]'
                    ).click()
                    await self.network.wait_idle(marker)
                    state = await self.page.evaluate(READ_TRIBUTI)
                collector.add(state, page_number)
            return collector.result()
        finally:
            if state and state.get("closeId"):
                await self.page.locator(f"#{state['closeId']}").click()

    async def _download_pdf(self, entry) -> dict:
        document = entry.document
        if not document.get("NOME_PDF") and not document.get("NOME_COMPLETO"):
            return {
                "status": "unavailable",
                "reason": "Nessun file PDF associato nel modello del sito STEP",
            }
        loop = asyncio.get_running_loop()
        received: asyncio.Future = loop.create_future()
        known_pages = set(self.context.pages)

        def on_download(download) -> None:
            if not received.done():
                received.set_result(download)

        def on_page(popup) -> None:
            popup.on("download", on_download)

        self.page.on("download", on_download)
        self.context.on("page", on_page)
        try:
            await self.page.locator(
                grid_link_selector(entry.grid, entry.row_index, "NUM_DOC")
            ).click()
            download = await asyncio.wait_for(received, timeout=60)
            content = Path(await download.path()).read_bytes()
            return {
                "status": "downloaded",
                "content": content,
                "originalFilename": download.suggested_filename,
            }
        finally:
            self.page.remove_listener("download", on_download)
            self.context.remove_listener("page", on_page)
            for popup in self.context.pages:
                if popup not in known_pages:
                    await popup.close()
