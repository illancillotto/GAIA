from __future__ import annotations

import asyncio
from dataclasses import dataclass
import html
import logging
import random
import re
from typing import Any

from playwright.async_api import Browser, BrowserContext, Page, Playwright, TimeoutError, async_playwright

logger = logging.getLogger(__name__)

POSTA_ONLINE_HOME_URL = "https://posta-online.poste.it/"
POSTA_ONLINE_LOGIN_URL = "https://idp-business.poste.it/jod-idp-business/cas/login.html"
POSTA_ONLINE_ARCHIVE_URL = "https://corrispondenza.poste.it/col/archivio.do"
POSTA_ONLINE_CONTACTS_URL = "https://corrispondenza.poste.it/col/gestioneListeContatti.do"
POSTA_ONLINE_DETAIL_URL = "https://corrispondenza.poste.it/col/dettaglio.do"

_INVIO_ID_RE = re.compile(r"(?:idInvio|id_invio)[^0-9]{0,40}([0-9]{4,})", re.IGNORECASE)
_COOKIE_BUTTON_SELECTORS = (
    "#truste-consent-button",
    "#truste-consent-required",
    "#truste-consent-required2",
    "button:has-text('Accetta')",
    "button:has-text('Accetto')",
    "button:has-text('Accetta tutti')",
    "button:has-text('Rifiuta')",
    "button:has-text('Continua')",
)
_OVERLAY_SELECTORS = (
    ".pageLoader",
    "#trustarc-banner-overlay",
    "#truste-consent-track",
    ".truste_box_overlay",
    ".content-alert-browser",
)
_INTERACTIVE_AUTH_MARKERS = ("otp", "codice temporaneo", "notifica", "autorizza", "posteid")
_LOGIN_ERROR_MARKERS = (
    "credenziali",
    "password errata",
    "nome utente o la password",
    "utenza bloccata",
    "accesso non riuscito",
    "mancato accesso",
    "errore",
)


@dataclass(slots=True)
class PostaOnlineScrapeConfig:
    min_delay_ms: int = 3500
    max_delay_ms: int = 9000
    max_pages: int | None = None
    max_details: int | None = None
    include_contacts: bool = True
    include_details: bool = True
    continue_on_error: bool = True
    headless: bool = True


class PoliteThrottle:
    def __init__(self, *, min_delay_ms: int, max_delay_ms: int) -> None:
        self.min_delay_ms = max(1000, min_delay_ms)
        self.max_delay_ms = max(self.min_delay_ms, max_delay_ms)

    async def wait(self, label: str) -> None:
        delay_ms = random.randint(self.min_delay_ms, self.max_delay_ms)
        logger.info("Poste Online throttle %s: attesa %.1fs", label, delay_ms / 1000)
        await asyncio.sleep(delay_ms / 1000)


class PostaOnlineBrowserClient:
    def __init__(self, config: PostaOnlineScrapeConfig) -> None:
        self.config = config
        self.throttle = PoliteThrottle(min_delay_ms=config.min_delay_ms, max_delay_ms=config.max_delay_ms)
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("Pagina Poste Online non inizializzata")
        return self._page

    @property
    def context(self) -> BrowserContext:
        if self._context is None:
            raise RuntimeError("Context Poste Online non inizializzato")
        return self._context

    async def __aenter__(self) -> "PostaOnlineBrowserClient":
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.config.headless)
        self._context = await self._browser.new_context(accept_downloads=False)
        self._page = await self._context.new_page()
        self._page.set_default_timeout(60000)
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        if self._context is not None:
            await self._context.close()
        if self._browser is not None:
            await self._browser.close()
        if self._playwright is not None:
            await self._playwright.stop()

    async def login(self, username: str, password: str) -> None:
        page = self.page
        await page.goto(POSTA_ONLINE_LOGIN_URL, wait_until="domcontentloaded")
        await self._prepare_login_page(page)
        await self._fill_first_available(page, ["input[name='username']", "#username", "input[type='text']"], username)
        await self._fill_first_available(page, ["input[name='password']", "#password", "input[type='password']"], password)
        await self._prepare_login_page(page)
        await self._click_first_available(page, ["button[type='submit']", "input[type='submit']", "button:has-text('Accedi')"])
        await page.wait_for_load_state("domcontentloaded")
        await self.throttle.wait("post-login")

        if await self._requires_interactive_authentication(page):
            raise RuntimeError("Login Poste Online richiede autenticazione interattiva o OTP non gestibile dal worker")

        await page.goto(POSTA_ONLINE_ARCHIVE_URL, wait_until="domcontentloaded")
        await self._ensure_authenticated_archive(page)

    async def scrape_registered_mails(self) -> dict[str, Any]:
        details: list[dict[str, Any]] = []
        contacts: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []

        if self.config.include_contacts:
            with _suppress_scrape_error(errors, "contacts", self.config.continue_on_error):
                contacts = await self.fetch_contacts()

        id_invii = await self.discover_archive_invii()
        if self.config.include_details:
            detail_ids = id_invii if self.config.max_details is None else id_invii[: self.config.max_details]
            for id_invio in detail_ids:
                try:
                    await self.throttle.wait(f"detail:{id_invio}")
                    html = await self.fetch_detail_html(id_invio)
                    details.append({"idInvio": id_invio, "html": html})
                except Exception as exc:
                    errors.append({"scope": f"detail:{id_invio}", "error": str(exc)})
                    if not self.config.continue_on_error:
                        raise

        return {
            "source": "posta_online_worker",
            "details": details,
            "contacts": contacts,
            "errors": errors,
            "archive_ids": id_invii,
        }

    async def fetch_contacts(self) -> list[dict[str, Any]]:
        response = await self._request_with_backoff(
            "contacts",
            lambda: self.context.request.post(
                POSTA_ONLINE_CONTACTS_URL,
                headers={
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": POSTA_ONLINE_ARCHIVE_URL,
                },
            ),
        )
        payload = await response.json()
        return [item for item in payload if isinstance(item, dict)] if isinstance(payload, list) else []

    async def discover_archive_invii(self) -> list[str]:
        page = self.page
        await page.goto(POSTA_ONLINE_ARCHIVE_URL, wait_until="domcontentloaded")
        seen: set[str] = set()
        ordered_ids: list[str] = []
        page_index = 0
        while self.config.max_pages is None or page_index < self.config.max_pages:
            page_index += 1
            await self.throttle.wait(f"archive-page:{page_index}")
            html = await page.content()
            for id_invio in _extract_invio_ids(html):
                if id_invio not in seen:
                    seen.add(id_invio)
                    ordered_ids.append(id_invio)
            if self.config.max_details is not None and len(ordered_ids) >= self.config.max_details:
                break
            if not await self._goto_next_archive_page(page):
                break
        return ordered_ids

    async def fetch_detail_html(self, id_invio: str) -> str:
        response = await self._request_with_backoff(
            f"detail:{id_invio}",
            lambda: self.context.request.post(
                POSTA_ONLINE_DETAIL_URL,
                multipart={
                    "idInvio": id_invio,
                    "numrows": "",
                    "controller": "archivio.do",
                },
                headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Referer": POSTA_ONLINE_ARCHIVE_URL,
                },
            ),
        )
        return await response.text()

    async def _request_with_backoff(self, label: str, factory):
        delays = (0, 30, 60, 120)
        last_error: Exception | None = None
        for attempt, delay in enumerate(delays, start=1):
            if delay:
                logger.warning("Poste Online %s retry %d dopo %ds", label, attempt, delay)
                await asyncio.sleep(delay)
            response = await factory()
            if response.status < 400:
                return response
            last_error = RuntimeError(f"Poste Online {label} HTTP {response.status}")
            if response.status not in {429, 500, 502, 503, 504}:
                break
        raise last_error or RuntimeError(f"Poste Online {label} fallito")

    async def _goto_next_archive_page(self, page: Page) -> bool:
        for locator in (
            page.locator("ul.pagination a").filter(has_text="›").last,
            page.locator("ul.pagination a").filter(has_text=">").last,
        ):
            try:
                if await locator.count() == 0:
                    continue
                href = await locator.get_attribute("href")
                if not href:
                    continue
                await locator.click()
                await page.wait_for_load_state("domcontentloaded")
                return True
            except TimeoutError:
                return False
        return False

    @staticmethod
    async def _fill_first_available(page: Page, selectors: list[str], value: str) -> None:
        for selector in selectors:
            locator = page.locator(selector).first
            if await locator.count() > 0:
                await locator.fill(value)
                return
        raise RuntimeError("Campo login Poste Online non trovato")

    @staticmethod
    async def _click_first_available(page: Page, selectors: list[str]) -> None:
        for selector in selectors:
            locator = page.locator(selector).first
            if await locator.count() > 0:
                await locator.click()
                return
        raise RuntimeError("Pulsante login Poste Online non trovato")

    @classmethod
    async def _prepare_login_page(cls, page: Page) -> None:
        await cls._wait_for_loader(page)
        await cls._dismiss_cookie_overlays(page)
        await cls._wait_for_loader(page)

    @staticmethod
    async def _wait_for_loader(page: Page) -> None:
        for selector in (".pageLoader",):
            try:
                await page.locator(selector).first.wait_for(state="hidden", timeout=10000)
            except TimeoutError:
                await page.locator(selector).first.evaluate("element => element.style.pointerEvents = 'none'")

    @staticmethod
    async def _dismiss_cookie_overlays(page: Page) -> None:
        for selector in _COOKIE_BUTTON_SELECTORS:
            locator = page.locator(selector).first
            try:
                if await locator.count() == 0:
                    continue
                if not await locator.is_visible(timeout=1000):
                    continue
                await locator.click(timeout=3000)
                await page.wait_for_timeout(500)
                return
            except TimeoutError:
                continue
        for selector in _OVERLAY_SELECTORS:
            locator = page.locator(selector).first
            try:
                if await locator.count() > 0:
                    await locator.evaluate("element => element.style.pointerEvents = 'none'")
            except Exception:
                logger.debug("Poste Online: overlay non neutralizzato: %s", selector, exc_info=True)

    @staticmethod
    async def _requires_interactive_authentication(page: Page) -> bool:
        text = (await page.locator("body").inner_text(timeout=5000)).lower()
        return any(marker in text for marker in _INTERACTIVE_AUTH_MARKERS)

    @staticmethod
    async def _ensure_authenticated_archive(page: Page) -> None:
        url = page.url.lower()
        text = (await page.locator("body").inner_text(timeout=10000)).lower()
        if "login" in url or "accedi" in text and "archivio" not in text:
            diagnostics = _diagnose_login_failure(page.url, text)
            raise RuntimeError(f"Archivio Poste Online non raggiunto dopo login: {diagnostics}")


def _diagnose_login_failure(url: str, body_text: str) -> str:
    signals: list[str] = []
    normalized = body_text.lower()
    if "login" in url.lower():
        signals.append("redirect_login")
    if any(marker in normalized for marker in _INTERACTIVE_AUTH_MARKERS):
        signals.append("autenticazione_interattiva")
    if any(marker in normalized for marker in _LOGIN_ERROR_MARKERS):
        signals.append("messaggio_login")
    if "username" in normalized and "password" in normalized:
        signals.append("form_login_visibile")
    signal_text = ",".join(signals) if signals else "nessun_segnale_specifico"
    return f"url={url}; segnali={signal_text}; testo={_clean_text_excerpt(body_text)}"


def _clean_text_excerpt(value: str, *, limit: int = 300) -> str:
    cleaned = html.unescape(value)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:limit]


def _extract_invio_ids(html: str) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()
    for match in _INVIO_ID_RE.finditer(html):
        id_invio = match.group(1)
        if id_invio not in seen:
            seen.add(id_invio)
            ids.append(id_invio)
    return ids


class _suppress_scrape_error:
    def __init__(self, errors: list[dict[str, str]], scope: str, continue_on_error: bool) -> None:
        self.errors = errors
        self.scope = scope
        self.continue_on_error = continue_on_error

    def __enter__(self) -> None:
        return None

    def __exit__(self, exc_type, exc, _traceback) -> bool:
        if exc is None:
            return False
        self.errors.append({"scope": self.scope, "error": str(exc)})
        return self.continue_on_error
