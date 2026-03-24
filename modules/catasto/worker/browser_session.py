from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from playwright.async_api import Browser, BrowserContext, Download, Page, Playwright, TimeoutError, async_playwright

from sister_selectors import SisterSelectorsConfig


@dataclass(slots=True)
class BrowserSessionConfig:
    headless: bool = True
    session_timeout_sec: int = 1680
    debug_pause: bool = False


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
            and datetime.now(UTC) < self._authenticated_until
        ):
            return

        await self.login(username, password)

    async def test_connection(self, username: str, password: str) -> BrowserConnectionProbeResult:
        page = self.page
        reachable = False
        try:
            await page.goto(self.selectors.login_url, wait_until="domcontentloaded")
            reachable = True
            await page.click(self.selectors.login_tab_selector)
            await page.fill(self.selectors.username_selector, username)
            await page.fill(self.selectors.password_selector, password)
            await page.click(self.selectors.login_button_selector)
            await self._maybe_click_xpath(self.selectors.confirm_button_xpath)
            await page.get_by_role("link", name=self.selectors.consultazioni_link_name).wait_for(timeout=12000)
            return BrowserConnectionProbeResult(
                reachable=True,
                authenticated=True,
                message="Autenticazione SISTER confermata dal worker.",
            )
        except TimeoutError:
            return BrowserConnectionProbeResult(
                reachable=reachable,
                authenticated=False,
                message="Portale raggiunto ma autenticazione SISTER non confermata.",
            )
        except Exception as exc:
            return BrowserConnectionProbeResult(
                reachable=reachable,
                authenticated=False,
                message=f"Errore probe SISTER: {exc}",
            )

    async def login(self, username: str, password: str) -> None:
        page = self.page
        await page.goto(self.selectors.login_url, wait_until="domcontentloaded")
        await page.click(self.selectors.login_tab_selector)
        await page.fill(self.selectors.username_selector, username)
        await page.fill(self.selectors.password_selector, password)
        await page.click(self.selectors.login_button_selector)
        await self._maybe_click_xpath(self.selectors.confirm_button_xpath)
        await self._goto_visura_menu()
        self._username = username
        self._authenticated_until = datetime.now(UTC) + timedelta(seconds=self.config.session_timeout_sec)

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

    @staticmethod
    def tipo_visura_value(tipo_visura: str) -> str:
        return "3" if tipo_visura == "Sintetica" else "2"
