from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
from pathlib import Path
import re

from playwright.async_api import Browser, BrowserContext, Download, Page, Playwright, TimeoutError, async_playwright

from sister_selectors import SisterSelectorsConfig

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class BrowserSessionConfig:
    headless: bool = True
    session_timeout_sec: int = 1680
    debug_pause: bool = False
    debug_artifacts_path: Path | None = None


@dataclass(slots=True)
class BrowserConnectionProbeResult:
    reachable: bool
    authenticated: bool
    message: str


class BrowserSession:
    def __init__(self, config: BrowserSessionConfig, selectors: SisterSelectorsConfig | None = None) -> None:
        self.config = config
        self.selectors = selectors or SisterSelectorsConfig.load()
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._authenticated_until: datetime | None = None
        self._username: str | None = None

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("Browser page not initialized")
        return self._page

    async def start(self) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.config.headless)
        self._context = await self._browser.new_context(accept_downloads=True)
        self._page = await self._context.new_page()

    async def stop(self) -> None:
        if self._context is not None:
            await self._context.close()
        if self._browser is not None:
            await self._browser.close()
        if self._playwright is not None:
            await self._playwright.stop()

    async def ensure_authenticated(self, username: str, password: str) -> None:
        if (
            self._username == username
            and self._authenticated_until is not None
            and datetime.now(timezone.utc) < self._authenticated_until
        ):
            return

        await self.login(username, password)

    async def test_connection(self, username: str, password: str) -> BrowserConnectionProbeResult:
        page = self.page
        reachable = False
        try:
            logger.info("Starting SISTER connection probe")
            await page.goto(self.selectors.login_url, wait_until="domcontentloaded")
            reachable = True
            logger.info("SISTER login page reached")
            await page.click(self.selectors.login_tab_selector)
            await page.fill(self.selectors.username_selector, username)
            await page.fill(self.selectors.password_selector, password)
            await page.click(self.selectors.login_button_selector)
            await self._maybe_click_xpath(self.selectors.confirm_button_xpath)
            await page.get_by_role("link", name=self.selectors.consultazioni_link_name).wait_for(timeout=12000)
            logger.info("SISTER connection probe authenticated successfully")
            return BrowserConnectionProbeResult(
                reachable=True,
                authenticated=True,
                message="Autenticazione SISTER confermata dal worker.",
            )
        except TimeoutError:
            url, title, body_excerpt = await self._read_page_state()
            issue_message = self._classify_login_issue(url, title, body_excerpt)
            debug_context = await self._collect_debug_context("connection-probe-timeout", url, title, body_excerpt)
            logger.warning("SISTER connection probe timed out: %s", debug_context)
            return BrowserConnectionProbeResult(
                reachable=reachable,
                authenticated=False,
                message=f"{issue_message or 'Portale raggiunto ma autenticazione SISTER non confermata.'} {debug_context}",
            )
        except Exception as exc:
            url, title, body_excerpt = await self._read_page_state()
            issue_message = self._classify_login_issue(url, title, body_excerpt)
            debug_context = await self._collect_debug_context("connection-probe-error", url, title, body_excerpt)
            logger.exception("SISTER connection probe failed: %s", debug_context)
            return BrowserConnectionProbeResult(
                reachable=reachable,
                authenticated=False,
                message=f"{issue_message or f'Errore probe SISTER: {exc}.'} {debug_context}",
            )

    async def login(self, username: str, password: str) -> None:
        page = self.page
        try:
            await page.goto(self.selectors.login_url, wait_until="domcontentloaded")
            await page.click(self.selectors.login_tab_selector)
            await page.fill(self.selectors.username_selector, username)
            await page.fill(self.selectors.password_selector, password)
            await page.click(self.selectors.login_button_selector)
            await self._maybe_click_xpath(self.selectors.confirm_button_xpath)
            await self._goto_visura_menu()
        except TimeoutError as exc:
            url, title, body_excerpt = await self._read_page_state()
            issue_message = self._classify_login_issue(url, title, body_excerpt)
            if issue_message:
                raise RuntimeError(issue_message) from exc
            raise

        self._username = username
        self._authenticated_until = datetime.now(timezone.utc) + timedelta(seconds=self.config.session_timeout_sec)

        if self.config.debug_pause:
            await page.pause()

    async def open_visura_form(self) -> None:
        page = self.page
        await self._goto_visura_menu()
        if await page.locator(self.selectors.territorio_selector).count() > 0:
            await page.select_option(self.selectors.territorio_selector, value=self.selectors.territorio_value)
            await page.get_by_role("button", name=self.selectors.territorio_apply_button_name).click()
        await page.get_by_role("link", name=self.selectors.immobile_link_name).click()
        await page.wait_for_selector(self.selectors.catasto_selector)

    async def fill_visura_form(self, request) -> None:
        page = self.page
        await page.select_option(self.selectors.catasto_selector, label=request.catasto)
        await page.select_option(self.selectors.comune_selector, value=request.comune_codice)

        if request.sezione:
            if await page.locator(self.selectors.sezione_select_selector).count() > 0:
                await page.select_option(self.selectors.sezione_select_selector, label=request.sezione)
            elif await page.locator(self.selectors.sezione_input_selector).count() > 0:
                await page.fill(self.selectors.sezione_input_selector, request.sezione)

        await page.fill(self.selectors.foglio_selector, request.foglio)
        await page.fill(self.selectors.particella_selector, request.particella)
        if request.subalterno:
            await page.fill(self.selectors.subalterno_selector, request.subalterno)
        await page.select_option(self.selectors.motivo_selector, value=self.selectors.motivo_value)
        await page.click(self.selectors.visura_button_selector)
        await page.wait_for_selector(self.selectors.tipo_visura_selector)
        await page.check(f"{self.selectors.tipo_visura_selector}[value='{self.tipo_visura_value(request.tipo_visura)}']")

    async def capture_captcha_image(self) -> bytes:
        await self.page.wait_for_selector(self.selectors.captcha_image_selector)
        return await self.page.locator(self.selectors.captcha_image_selector).screenshot(type="png")

    async def submit_captcha(self, text: str) -> bool:
        page = self.page
        await page.fill(self.selectors.captcha_field_selector, text)
        await page.click(self.selectors.inoltra_button_selector)

        try:
            await page.wait_for_selector(self.selectors.save_button_selector, timeout=12000)
            return True
        except TimeoutError:
            return await page.locator(self.selectors.save_button_selector).count() > 0

    async def download_pdf(self, destination: Path) -> int:
        page = self.page
        destination.parent.mkdir(parents=True, exist_ok=True)
        async with page.expect_download(timeout=20000) as download_info:
            await page.click(self.selectors.save_button_selector)
        download: Download = await download_info.value
        await download.save_as(str(destination))
        return destination.stat().st_size

    async def _goto_visura_menu(self) -> None:
        page = self.page
        await page.get_by_role("link", name=self.selectors.consultazioni_link_name).click()
        await page.get_by_role("link", name=self.selectors.visure_link_name).click()
        await self._maybe_click_text(self.selectors.conferma_lettura_button_name)

    async def _maybe_click_xpath(self, xpath: str) -> None:
        locator = self.page.locator(f"xpath={xpath}")
        if await locator.count() > 0:
            await locator.first.click()

    async def _maybe_click_text(self, text: str) -> None:
        locator = self.page.get_by_role("button", name=text)
        if await locator.count() > 0:
            await locator.first.click()

    async def _collect_debug_context(
        self,
        reason: str,
        url: str | None = None,
        title: str | None = None,
        body_excerpt: str | None = None,
    ) -> str:
        artifacts: list[str] = []

        if url is None or title is None or body_excerpt is None:
            url, title, body_excerpt = await self._read_page_state()

        if self.config.debug_artifacts_path is not None:
            artifacts = await self._write_debug_artifacts(reason)

        parts = [f"url={url}", f"title={title}"]
        if body_excerpt:
            parts.append(f"body={body_excerpt}")
        if artifacts:
            parts.append("artifacts=" + ", ".join(artifacts))
        return " | ".join(parts)

    async def _read_page_state(self) -> tuple[str, str, str]:
        url = "unknown"
        title = "unknown"
        body_excerpt = ""

        try:
            url = self.page.url or "unknown"
        except Exception:
            pass

        try:
            title = await self.page.title()
        except Exception:
            pass

        try:
            body_text = await self.page.locator("body").inner_text(timeout=2000)
            body_excerpt = re.sub(r"\s+", " ", body_text).strip()[:240]
        except Exception:
            body_excerpt = ""

        return url, title, body_excerpt

    @staticmethod
    def _classify_login_issue(url: str, title: str, body_excerpt: str) -> str | None:
        haystack = f"{url} {title} {body_excerpt}".lower()
        if "gia' in sessione" in haystack or "già in sessione" in haystack or "altra postazione" in haystack:
            return "Utente SISTER gia' in sessione su un'altra postazione o browser."
        if "error_locked.jsp" in haystack or "utente bloccato" in haystack:
            return "Utente SISTER bloccato sul portale Agenzia delle Entrate."
        if "credenzial" in haystack and (
            "errat" in haystack or "non valide" in haystack or "non sono valide" in haystack
        ):
            return "Credenziali SISTER rifiutate dal portale Agenzia delle Entrate."
        return None

    async def _write_debug_artifacts(self, reason: str) -> list[str]:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        target_dir = self.config.debug_artifacts_path / "connection-tests" / timestamp
        target_dir.mkdir(parents=True, exist_ok=True)

        screenshot_path = target_dir / f"{reason}.png"
        html_path = target_dir / f"{reason}.html"
        artifacts: list[str] = []

        try:
            await self.page.screenshot(path=str(screenshot_path), full_page=True)
            artifacts.append(str(screenshot_path))
        except Exception:
            logger.exception("Unable to save SISTER debug screenshot")

        try:
            html_path.write_text(await self.page.content(), encoding="utf-8")
            artifacts.append(str(html_path))
        except Exception:
            logger.exception("Unable to save SISTER debug HTML")

        return artifacts

    @staticmethod
    def tipo_visura_value(tipo_visura: str) -> str:
        return "3" if tipo_visura == "Sintetica" else "2"
