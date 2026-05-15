from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
from pathlib import Path
import re

from playwright.async_api import Browser, BrowserContext, Download, Page, Playwright, TimeoutError, async_playwright

from sister_exceptions import DocumentNonEvadibileError, DocumentNotYetProducedError, SisterServerError
from sister_selectors import SisterSelectorsConfig

logger = logging.getLogger(__name__)
MENU_NAVIGATION_RETRIES = 3
MENU_NAVIGATION_RETRY_DELAY_SEC = 2
SESSION_RECOVERY_WAIT_SEC = 120
RICHIESTE_POLL_ATTEMPTS = 10
RICHIESTE_POLL_INTERVAL_SEC = 30


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
        logger.info("Avvio sessione browser Playwright")
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.config.headless)
        self._context = await self._browser.new_context(accept_downloads=True)
        # Blocco analytics Matomo — nessun impatto sul flusso visura
        await self._context.route(
            "**/etws-analytics.sogei.it/**",
            lambda route: route.abort()
        )
        self._page = await self._context.new_page()
        # Timeout globale aumentato per gestire la lentezza del portale SISTER nelle ore di punta
        self._page.set_default_timeout(60000)
        logger.info("Sessione browser Playwright pronta")
        await self._trace_state("browser-started")

    async def stop(self) -> None:
        logger.info("Chiusura sessione browser Playwright")
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
            logger.info("Riutilizzo sessione SISTER esistente per %s", username)
            return

        await self.login(username, password)

    async def test_connection(self, username: str, password: str) -> BrowserConnectionProbeResult:
        page = self.page
        reachable = False
        authenticated = False
        try:
            logger.info("Avvio probe connessione SISTER")
            await page.goto(self.selectors.login_url, wait_until="domcontentloaded")
            reachable = True
            logger.info("Pagina login SISTER raggiunta")
            await self._trace_state("connection-probe-login-page")
            await page.click(self.selectors.login_tab_selector)
            await page.fill(self.selectors.username_selector, username)
            await page.fill(self.selectors.password_selector, password)
            await page.click(self.selectors.login_button_selector)
            await self._maybe_click_xpath(self.selectors.confirm_button_xpath)
            await self._trace_state("connection-probe-after-submit")
            await page.get_by_role("link", name=self.selectors.consultazioni_link_name).wait_for(timeout=12000)
            authenticated = True
            logger.info("Probe connessione SISTER autenticato con successo")
            await self._trace_state("connection-probe-authenticated")
            await self.logout()
            return BrowserConnectionProbeResult(
                reachable=True,
                authenticated=True,
                message="Autenticazione SISTER confermata dal worker e logout finale eseguito.",
            )
        except TimeoutError:
            if authenticated:
                with contextlib.suppress(Exception):
                    await self.logout()
            url, title, body_excerpt = await self._read_page_state()
            issue_message = self._classify_login_issue(url, title, body_excerpt)
            debug_context = await self._collect_debug_context("connection-probe-timeout", url, title, body_excerpt)
            logger.warning("Timeout probe connessione SISTER: %s", debug_context)
            if authenticated:
                issue_message = "Autenticazione SISTER riuscita, ma logout finale non confermato entro il timeout"
            return BrowserConnectionProbeResult(
                reachable=reachable,
                authenticated=False,
                message=f"{issue_message or 'Portale raggiunto ma autenticazione SISTER non confermata.'} {debug_context}",
            )
        except Exception as exc:
            if authenticated:
                with contextlib.suppress(Exception):
                    await self.logout()
            url, title, body_excerpt = await self._read_page_state()
            issue_message = self._classify_login_issue(url, title, body_excerpt)
            debug_context = await self._collect_debug_context("connection-probe-error", url, title, body_excerpt)
            logger.exception("Probe connessione SISTER fallito: %s", debug_context)
            if authenticated:
                issue_message = f"Autenticazione SISTER riuscita, ma logout finale non confermato: {exc}"
            return BrowserConnectionProbeResult(
                reachable=reachable,
                authenticated=False,
                message=f"{issue_message or f'Errore probe SISTER: {exc}.'} {debug_context}",
            )

    async def login(self, username: str, password: str, allow_session_recovery: bool = True) -> None:
        page = self.page
        try:
            logger.info("Avvio login SISTER per %s", username)
            await page.goto(self.selectors.login_url, wait_until="domcontentloaded")
            await self._trace_state("login-page")
            await page.click(self.selectors.login_tab_selector)
            await page.fill(self.selectors.username_selector, username)
            await page.fill(self.selectors.password_selector, password)
            await page.click(self.selectors.login_button_selector)
            await self._maybe_click_xpath(self.selectors.confirm_button_xpath)
            post_login_state = await self._wait_for_post_login_state()
            await self._trace_state("login-after-submit")
            if post_login_state == "locked":
                if allow_session_recovery:
                    logger.warning("Sessione SISTER bloccata rilevata subito dopo il login, avvio unico recovery")
                    await self._recover_locked_session()
                    return await self.login(username, password, allow_session_recovery=False)
                await self._raise_locked_session_error("login-locked-after-recovery")
            await self._maybe_accept_privacy_notice()
            await self._goto_visura_menu_with_retry()
        except TimeoutError as exc:
            url, title, body_excerpt = await self._read_page_state()
            issue_message = self._classify_login_issue(url, title, body_excerpt)
            if allow_session_recovery and self._is_session_locked_issue(issue_message):
                logger.warning("Sessione SISTER bloccata rilevata durante il login, avvio unico recovery")
                await self._recover_locked_session()
                return await self.login(username, password, allow_session_recovery=False)
            if self._is_session_locked_issue(issue_message):
                await self._raise_locked_session_error("login-timeout-locked", exc)
            debug_context = await self._collect_debug_context("login-timeout", url, title, body_excerpt)
            if issue_message:
                raise RuntimeError(f"{issue_message} {debug_context}") from exc
            raise RuntimeError(f"Login timeout. {debug_context}") from exc
        except Exception as exc:
            if isinstance(exc, RuntimeError) and str(exc) == "SISTER_SESSION_LOCKED":
                raise
            url, title, body_excerpt = await self._read_page_state()
            issue_message = self._classify_login_issue(url, title, body_excerpt)
            if allow_session_recovery and self._is_session_locked_issue(issue_message):
                logger.warning("Sessione SISTER bloccata rilevata dopo eccezione login, avvio unico recovery")
                await self._recover_locked_session()
                return await self.login(username, password, allow_session_recovery=False)
            if self._is_session_locked_issue(issue_message):
                await self._raise_locked_session_error("login-error-locked", exc)
            debug_context = await self._collect_debug_context("login-error", url, title, body_excerpt)
            raise RuntimeError(f"SISTER login failed: {exc}. {debug_context}") from exc

        self._username = username
        self._authenticated_until = datetime.now(timezone.utc) + timedelta(seconds=self.config.session_timeout_sec)
        logger.info("Login SISTER completato per %s", username)
        await self._trace_state("login-completed")

        if self.config.debug_pause:
            await page.pause()

    async def logout(self) -> None:
        page = self.page
        logger.info("Logout SISTER / chiusura sessione applicativa")
        close_session_url = "https://sister3.agenziaentrate.gov.it/Servizi/CloseSessionsSis"
        if not await self._click_close_sessions_link(prefer_text="Chiudi"):
            await page.goto(close_session_url, wait_until="domcontentloaded")
        await page.wait_for_load_state("domcontentloaded")
        await self._trace_state("sister-logout-completed")

    async def open_visura_form(self) -> None:
        page = self.page
        logger.info("Apertura form visura SISTER")
        await self._maybe_accept_privacy_notice()
        if not await self._is_visura_area_ready():
            await self._goto_visura_menu_with_retry()
        await self._confirm_visura_informativa_if_present()
        if await page.locator(self.selectors.territorio_selector).count() > 0:
            await page.select_option(self.selectors.territorio_selector, value=self.selectors.territorio_value)
            await page.get_by_role("button", name=self.selectors.territorio_apply_button_name).click()
            await self._trace_state("visura-after-territorio")
        immobile_link = page.get_by_role("link", name=self.selectors.immobile_link_name)
        if await immobile_link.count() > 0:
            logger.info("Click link '%s'", self.selectors.immobile_link_name)
            await immobile_link.first.click()
        await page.wait_for_selector(self.selectors.catasto_selector)
        logger.info("Form visura SISTER pronto")
        await self._trace_state("visura-form-ready")

    async def open_subject_form(self, subject_kind: str) -> None:
        page = self.page
        normalized_kind = (subject_kind or "PF").strip().upper()
        subject_url = self.selectors.subject_pf_url if normalized_kind == "PF" else self.selectors.subject_pnf_url
        logger.info("Apertura form visura soggetto kind=%s", normalized_kind)
        await self._maybe_accept_privacy_notice()
        await page.goto(subject_url, wait_until="domcontentloaded")
        if await page.locator(self.selectors.territorio_selector).count() > 0:
            await page.select_option(self.selectors.territorio_selector, value=self.selectors.territorio_value)
            await page.get_by_role("button", name=self.selectors.territorio_apply_button_name).click()
            await self._trace_state(f"subject-after-territorio-{normalized_kind}")
        await self._trace_state(f"subject-form-ready-{normalized_kind}")

    async def fill_visura_form(self, request) -> None:
        page = self.page
        logger.info(
            "Compilazione form visura per richiesta %s comune=%s foglio=%s particella=%s subalterno=%s tipo=%s",
            request.id,
            request.comune,
            request.foglio,
            request.particella,
            request.subalterno,
            request.tipo_visura,
        )
        await self._select_request_type_if_present(getattr(request, "request_type", None) or "ATTUALITA")
        await page.select_option(self.selectors.catasto_selector, label=request.catasto)
        await page.select_option(self.selectors.comune_selector, value=request.comune_codice)

        if request.sezione:
            if await page.locator(self.selectors.sezione_select_selector).count() > 0:
                await self._ensure_sezione_options_loaded(request.id)
                await page.select_option(self.selectors.sezione_select_selector, value=request.sezione)
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
        logger.info("Form visura inviato per richiesta %s", request.id)
        await self._trace_state(f"visura-form-submitted-{request.id}")

    async def search_immobile_status(self, request) -> dict[str, object]:
        page = self.page
        logger.info(
            "Ricerca stato AdE per richiesta %s comune=%s foglio=%s particella=%s subalterno=%s",
            request.id,
            request.comune,
            request.foglio,
            request.particella,
            request.subalterno,
        )
        await page.select_option(self.selectors.catasto_selector, label=request.catasto)
        await page.select_option(self.selectors.comune_selector, value=request.comune_codice)

        if request.sezione:
            if await page.locator(self.selectors.sezione_select_selector).count() > 0:
                await self._ensure_sezione_options_loaded(request.id)
                await page.select_option(self.selectors.sezione_select_selector, value=request.sezione)
            elif await page.locator(self.selectors.sezione_input_selector).count() > 0:
                await page.fill(self.selectors.sezione_input_selector, request.sezione)

        await page.fill(self.selectors.foglio_selector, request.foglio)
        await page.fill(self.selectors.particella_selector, request.particella)
        if request.subalterno:
            await page.fill(self.selectors.subalterno_selector, request.subalterno)
        await page.select_option(self.selectors.motivo_selector, value=self.selectors.motivo_value)
        await page.click(self.selectors.visura_button_selector)
        await page.wait_for_timeout(1500)
        payload = await self._read_immobile_status_payload()
        await self._trace_state(f"ade-status-scan-{request.id}-{payload.get('classification')}")
        return payload

    async def fill_subject_form(self, request) -> None:
        page = self.page
        logger.info(
            "Compilazione form soggetto per richiesta %s kind=%s subject_id=%s request_type=%s",
            request.id,
            request.subject_kind,
            request.subject_id,
            request.request_type,
        )
        await self._select_request_type_if_present(request.request_type or "ATTUALITA")
        await self._fill_subject_identifier(request.subject_id or "")
        await page.select_option(self.selectors.motivo_selector, value=self.selectors.motivo_value)
        await self._trace_state(f"subject-form-filled-{request.id}")

    async def search_subject_and_open_visura(self, request) -> str | None:
        logger.info("Ricerca soggetto per richiesta %s", request.id)
        await self._click_first_visible(
            self.selectors.subject_search_button_selectors
            or ["input[value='Ricerca']", "button:has-text('Ricerca')", "text=Ricerca"]
        )
        await self.page.wait_for_timeout(1500)
        subject_not_found = await self.detect_subject_not_found_message(request.subject_kind, request.subject_id)
        if subject_not_found:
            await self._trace_state(f"subject-not-found-{request.id}")
            return subject_not_found

        for selector in (
            self.selectors.subject_result_selector_candidates
            or [
                "input[name='omonimoSelezionato'][type='radio']",
                "input[name='omonimoSelezionato'][type='checkbox']",
                "table input[type='radio']",
                "input[type='radio']",
                "table input[type='checkbox']",
                "input[type='checkbox']",
            ]
        ):
            locator = self.page.locator(selector).first
            if await locator.count() > 0 and await locator.is_visible():
                with contextlib.suppress(Exception):
                    await locator.check(timeout=5000)
                break

        await self._click_first_visible(
            self.selectors.subject_open_visura_button_selectors
            or [
                "input[name='visura']",
                "input[value='Visura per Soggetto']",
                "input[value='VISURA PER SOGGETTO']",
                "button:has-text('Visura per Soggetto')",
                "button:has-text('VISURA PER SOGGETTO')",
                "text=Visura per Soggetto",
                "text=VISURA PER SOGGETTO",
            ]
        )
        await self.page.wait_for_timeout(1500)
        await self._trace_state(f"subject-visura-open-{request.id}")
        return None

    async def detect_subject_not_found_message(self, subject_kind: str | None, subject_id: str | None) -> str | None:
        try:
            page_text = await self.page.locator("body").inner_text(timeout=2000)
        except Exception:
            page_text = ""
        normalized_text = re.sub(r"\s+", " ", page_text).upper()
        markers = [
            "NESSUNA CORRISPONDENZA TROVATA",
            "NESSUN RISULTATO",
            "NESSUN DATO TROVATO",
            "SOGGETTO NON TROVATO",
            "NON RISULTANO DATI",
        ]
        if any(marker in normalized_text for marker in markers):
            return f"Nessuna corrispondenza catastale per {(subject_kind or 'SOGGETTO').strip()} '{(subject_id or '').strip()}'"
        return None

    async def _read_immobile_status_payload(self) -> dict[str, object]:
        url, title, body_excerpt = await self._read_page_state()
        try:
            body_text = await self.page.locator("body").inner_text(timeout=3000)
        except Exception:
            body_text = body_excerpt
        normalized = re.sub(r"\s+", " ", body_text).strip()
        haystack = normalized.upper()

        if self._classify_login_issue(url, title, body_excerpt):
            return {
                "classification": "blocked",
                "message": self._classify_login_issue(url, title, body_excerpt),
                "url": url,
                "title": title,
                "raw_text_excerpt": normalized[:1000],
            }

        if await self.page.locator(self.selectors.tipo_visura_selector).count() > 0:
            return {
                "classification": "current",
                "message": "Particella valida: AdE ha aperto la scelta tipo visura.",
                "url": url,
                "title": title,
                "raw_text_excerpt": normalized[:1000],
            }

        immobili_count = self._extract_immobili_count(normalized)
        if "SOPPRESSO" in haystack:
            return {
                "classification": "suppressed",
                "message": "Particella presente in AdE ma soppressa.",
                "immobili_count": immobili_count,
                "suppressed_at": self._extract_suppressed_date(normalized),
                "url": url,
                "title": title,
                "raw_text_excerpt": normalized[:1000],
            }

        not_found_markers = [
            "IMMOBILI INDIVIDUATI: 0",
            "NESSUN IMMOBILE",
            "NESSUNA CORRISPONDENZA",
            "NON SONO STATI TROVATI",
            "NESSUN DATO TROVATO",
        ]
        if any(marker in haystack for marker in not_found_markers):
            return {
                "classification": "not_found",
                "message": "Nessun immobile individuato da AdE.",
                "immobili_count": immobili_count,
                "url": url,
                "title": title,
                "raw_text_excerpt": normalized[:1000],
            }

        if "ELENCO IMMOBILI" in haystack or (immobili_count is not None and immobili_count > 0):
            return {
                "classification": "current",
                "message": "Particella presente in elenco immobili AdE.",
                "immobili_count": immobili_count,
                "url": url,
                "title": title,
                "raw_text_excerpt": normalized[:1000],
            }

        return {
            "classification": "unknown",
            "message": "Risposta AdE non classificata automaticamente.",
            "url": url,
            "title": title,
            "raw_text_excerpt": normalized[:1000],
        }

    @staticmethod
    def _extract_immobili_count(text: str) -> int | None:
        match = re.search(r"Immobili\s+individuati\s*:\s*(\d+)", text, re.IGNORECASE)
        return int(match.group(1)) if match else None

    @staticmethod
    def _extract_suppressed_date(text: str) -> str | None:
        suppressed_index = text.upper().find("SOPPRESSO")
        if suppressed_index < 0:
            return None
        window = text[max(0, suppressed_index - 120): suppressed_index + 180]
        match = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", window)
        return match.group(1) if match else None

    async def reload_captcha(self) -> None:
        """Ricarica immagine CAPTCHA e attende il riallineamento del codice in sessione server."""
        with contextlib.suppress(Exception):
            await self.page.evaluate(
                "(function(){"
                "  if(typeof reload === 'function') reload();"
                "  else if(typeof reloadImg === 'function') reloadImg();"
                "})()"
            )
        # reload() usa setTimeout('StartMeUp()', 1000) lato server — attendere riallineamento
        await asyncio.sleep(1.2)

    async def capture_captcha_image(self) -> bytes:
        await self.page.wait_for_selector(self.selectors.captcha_image_selector)
        return await self.page.locator(self.selectors.captcha_image_selector).screenshot(type="png")

    async def prepare_captcha_or_download(self) -> str:
        page = self.page
        if await self._first_visible_count(self.selectors.save_button_selector) > 0:
            return "download"
        if await self._first_visible_count(self.selectors.captcha_image_selector) > 0:
            return "captcha"

        inoltra = page.locator(self.selectors.inoltra_button_selector).first
        if await inoltra.count() > 0 and await inoltra.is_visible():
            logger.info("Pagina tipo visura senza CAPTCHA visibile, click preliminare su Inoltra")
            await inoltra.click(timeout=10000)
            with contextlib.suppress(Exception):
                await page.wait_for_load_state("domcontentloaded", timeout=5000)

        for iteration in range(30):
            if await self._first_visible_count(self.selectors.save_button_selector) > 0:
                return "download"
            if await self._first_visible_count(self.selectors.captcha_image_selector) > 0:
                return "captcha"
            if iteration % 4 == 3:
                await self._raise_if_server_error()
                await self._raise_if_document_not_yet_produced()
            await asyncio.sleep(0.5)

        await self._trace_state("captcha-or-download-timeout")
        await self._raise_if_server_error()
        await self._raise_if_document_not_yet_produced()
        raise TimeoutError("SISTER non ha mostrato ne CAPTCHA ne pulsante Salva dopo Inoltra")

    async def submit_captcha(self, text: str) -> bool:
        page = self.page
        logger.info("Invio candidato CAPTCHA con %s caratteri", len(text))
        await page.click(self.selectors.captcha_field_selector)
        await page.fill(self.selectors.captcha_field_selector, "")
        await page.type(self.selectors.captcha_field_selector, text, delay=80)
        # Il bottone Inoltra è un plain submit senza onclick — la validazione CAPTCHA
        # avviene server-side su InoltraRichiestaVis.do (non via checkCode JS).
        await page.click(self.selectors.inoltra_button_selector)

        try:
            await page.wait_for_selector(self.selectors.save_button_selector, timeout=12000)
            logger.info("CAPTCHA accettato da SISTER")
            return True
        except TimeoutError:
            await self._trace_state("captcha-rejected")
            if await page.locator(self.selectors.save_button_selector).count() > 0:
                logger.info("CAPTCHA accettato da SISTER (fallback count)")
                return True
            await self._raise_if_server_error()
            await self._raise_if_document_not_yet_produced()
            logger.info("CAPTCHA rifiutato da SISTER (save button non trovato)")
            return False

    async def download_pdf(self, destination: Path) -> int:
        page = self.page
        destination.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Avvio download PDF su %s", destination)
        async with page.expect_download(timeout=20000) as download_info:
            await page.click(self.selectors.save_button_selector)
        download: Download = await download_info.value
        await download.save_as(str(destination))
        logger.info("Download PDF completato: %s", destination)
        return destination.stat().st_size

    async def capture_debug_snapshot(self, target_dir: Path, label: str) -> list[str]:
        target_dir.mkdir(parents=True, exist_ok=True)
        return await self._write_artifacts_to_dir(target_dir, label)

    async def poll_richieste_for_download(self, destination: Path, richieste_url: str | None = None) -> int:
        """Poll ConsultazioneRichieste.do fino a che il documento è pronto o non evadibile."""
        base_url = "https://sister3.agenziaentrate.gov.it"
        url = richieste_url or f"{base_url}/Visure/ConsultazioneRichieste.do?metodo=lista"
        page = self.page
        destination.parent.mkdir(parents=True, exist_ok=True)

        for poll in range(1, RICHIESTE_POLL_ATTEMPTS + 1):
            logger.info("Poll ConsultazioneRichieste %s/%s url=%s", poll, RICHIESTE_POLL_ATTEMPTS, url)
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_timeout(1500)
            await self._trace_state(f"richieste-poll-{poll}")

            body_text = ""
            with contextlib.suppress(Exception):
                body_text = await page.locator("body").inner_text(timeout=3000)
            normalized = re.sub(r"\s+", " ", body_text)
            upper = normalized.upper()

            await self._raise_if_server_error()

            non_evad = re.search(r"NON EVADIBIL[^0-9]*([0-9]+)", upper)
            if non_evad and int(non_evad.group(1)) > 0:
                logger.warning("Richiesta SISTER non evadibile (poll %s): count=%s", poll, non_evad.group(1))
                raise DocumentNonEvadibileError("Richiesta SISTER non evadibile in ConsultazioneRichieste")

            espletate = re.search(r"ESPLETATE?[^0-9]*([0-9]+)", upper)
            if espletate and int(espletate.group(1)) > 0:
                logger.info("Documento espletato rilevato (poll %s): count=%s", poll, espletate.group(1))
                try:
                    return await self._download_from_richieste_espletate(destination)
                except Exception as exc:
                    logger.warning("Download da espletate fallito (poll %s): %s — check salva diretto", poll, exc)
                    if await self._first_visible_count(self.selectors.save_button_selector) > 0:
                        return await self.download_pdf(destination)

            if await self._first_visible_count(self.selectors.save_button_selector) > 0:
                return await self.download_pdf(destination)

            if poll < RICHIESTE_POLL_ATTEMPTS:
                logger.info("Documento non ancora disponibile, attesa %ss", RICHIESTE_POLL_INTERVAL_SEC)
                await asyncio.sleep(RICHIESTE_POLL_INTERVAL_SEC)

        raise TimeoutError(
            f"Documento SISTER non disponibile dopo {RICHIESTE_POLL_ATTEMPTS} poll "
            f"({RICHIESTE_POLL_ATTEMPTS * RICHIESTE_POLL_INTERVAL_SEC}s)"
        )

    async def _download_from_richieste_espletate(self, destination: Path) -> int:
        """Naviga nella tab espletate e scarica il primo documento disponibile."""
        page = self.page

        for tab_text in ("Espletate", "espletate"):
            tab = page.locator(f"a:has-text('{tab_text}'), td:has-text('{tab_text}')").first
            if await tab.count() > 0 and await tab.is_visible():
                with contextlib.suppress(Exception):
                    await tab.click(timeout=5000)
                    await page.wait_for_load_state("domcontentloaded", timeout=5000)
                break

        await page.wait_for_timeout(1000)

        if await self._first_visible_count(self.selectors.save_button_selector) > 0:
            return await self.download_pdf(destination)

        row_link_selectors = [
            "table a[href*='ConsultazioneRichieste']",
            "table tr td:not(:empty) a",
            "table a[href*='Visure']",
        ]
        for selector in row_link_selectors:
            link = page.locator(selector).first
            if await link.count() > 0 and await link.is_visible():
                with contextlib.suppress(Exception):
                    await link.click(timeout=8000)
                    await page.wait_for_load_state("domcontentloaded", timeout=8000)
                    await page.wait_for_timeout(1000)
                if await self._first_visible_count(self.selectors.save_button_selector) > 0:
                    return await self.download_pdf(destination)
                break

        raise TimeoutError("Salva button non trovato in ConsultazioneRichieste espletate")

    async def _raise_if_server_error(self) -> None:
        """Solleva SisterServerError se la pagina corrente mostra un errore 500."""
        url = self.page.url
        with contextlib.suppress(Exception):
            body_text = await self.page.locator("body").inner_text(timeout=1500)
            upper = re.sub(r"\s+", " ", body_text).upper()
            if "ERROR 500" in upper or "NULLPOINTEREXCEPTION" in upper or "HTTP STATUS 500" in upper:
                logger.error("Errore SISTER 500 rilevato: url=%s", url)
                raise SisterServerError(f"SISTER 500 su {url}")

    async def _raise_if_document_not_yet_produced(self) -> None:
        """Solleva DocumentNotYetProducedError se siamo su CheckRichiesta.do o equivalente."""
        page = self.page
        url = page.url
        body_text = ""
        with contextlib.suppress(Exception):
            body_text = await page.locator("body").inner_text(timeout=2000)
        upper = re.sub(r"\s+", " ", body_text).upper()
        if (
            "NON E' STATO ANCORA PRODOTTO" in upper
            or "NON È STATO ANCORA PRODOTTO" in upper
            or "CHECKRICHIESTA.DO" in url.upper()
        ):
            richieste_url: str | None = None
            with contextlib.suppress(Exception):
                href = await page.locator("a[href*='ConsultazioneRichieste']").first.get_attribute("href", timeout=2000)
                if href:
                    base = "https://sister3.agenziaentrate.gov.it"
                    richieste_url = href if href.startswith("http") else base + href
            logger.info("Documento SISTER non ancora prodotto, richieste_url=%s", richieste_url)
            raise DocumentNotYetProducedError(richieste_url)

    async def _goto_visura_menu(self) -> None:
        page = self.page
        logger.info("Navigazione verso menu visure SISTER")
        logger.info("Click link '%s'", self.selectors.consultazioni_link_name)
        await page.get_by_role("link", name=self.selectors.consultazioni_link_name).click()
        logger.info("Link '%s' aperto", self.selectors.consultazioni_link_name)
        await self._trace_state("menu-after-consultazioni-click")
        logger.info("Click link '%s'", self.selectors.visure_link_name)
        await page.get_by_role("link", name=self.selectors.visure_link_name).click()
        logger.info("Link '%s' aperto", self.selectors.visure_link_name)
        await self._trace_state("menu-after-visure-click")
        await self._confirm_visura_informativa_if_present()

    async def _is_visura_area_ready(self) -> bool:
        page = self.page
        if await page.locator(self.selectors.catasto_selector).count() > 0:
            return True
        return "/Visure/" in page.url or "Visure/" in page.url

    async def _confirm_visura_informativa_if_present(self) -> None:
        page = self.page
        body_text = ""
        with contextlib.suppress(Exception):
            body_text = await page.locator("body").inner_text(timeout=2000)

        if "Informativa.do" not in page.url and self.selectors.conferma_lettura_button_name not in body_text:
            return

        logger.info("Informativa visure rilevata, click su '%s'", self.selectors.conferma_lettura_button_name)
        await self._trace_state("visura-informativa-detected")
        await self._click_first_visible(
            [
                f"input[type='submit'][value='{self.selectors.conferma_lettura_button_name}']",
                f"input[type='button'][value='{self.selectors.conferma_lettura_button_name}']",
                f"input[value='{self.selectors.conferma_lettura_button_name}']",
                f"button:has-text('{self.selectors.conferma_lettura_button_name}')",
                f"a:has-text('{self.selectors.conferma_lettura_button_name}')",
                f"text={self.selectors.conferma_lettura_button_name}",
                "input[type='submit'][value*='Conferma']",
                "button:has-text('Conferma')",
            ]
        )
        await page.wait_for_load_state("domcontentloaded")
        await self._trace_state("visura-informativa-confirmed")

    async def _goto_visura_menu_with_retry(self) -> None:
        last_error: TimeoutError | None = None
        for attempt in range(1, MENU_NAVIGATION_RETRIES + 1):
            try:
                logger.info("Tentativo apertura menu visure %s/%s", attempt, MENU_NAVIGATION_RETRIES)
                await self._goto_visura_menu()
                return
            except TimeoutError as exc:
                last_error = exc
                url, title, body_excerpt = await self._read_page_state()
                issue_message = self._classify_login_issue(url, title, body_excerpt)
                debug_context = await self._collect_debug_context(
                    f"visura-menu-timeout-attempt-{attempt}",
                    url,
                    title,
                    body_excerpt,
                )
                logger.warning(
                    "Timeout apertura menu visure tentativo %s/%s: %s",
                    attempt,
                    MENU_NAVIGATION_RETRIES,
                    debug_context,
                )
                if issue_message:
                    raise RuntimeError(f"{issue_message} {debug_context}") from exc
                if attempt >= MENU_NAVIGATION_RETRIES:
                    raise
                await asyncio.sleep(MENU_NAVIGATION_RETRY_DELAY_SEC)

        if last_error is not None:
            raise last_error

    async def _maybe_click_xpath(self, xpath: str) -> None:
        locator = self.page.locator(f"xpath={xpath}")
        if await locator.count() > 0:
            await locator.first.click()

    async def _maybe_click_text(self, text: str) -> None:
        locator = self.page.get_by_role("button", name=text)
        if await locator.count() > 0:
            await locator.first.click()

    async def _click_first_visible(self, selectors: list[str]) -> None:
        last_error: Exception | None = None
        for selector in selectors:
            locator = self.page.locator(selector).first
            try:
                if await locator.count() == 0:
                    continue
                if not await locator.is_visible():
                    continue
                await locator.click(timeout=15000)
                return
            except Exception as exc:
                last_error = exc
                continue
        if last_error is not None:
            raise last_error
        raise TimeoutError(f"No clickable selector found in candidates: {selectors}")

    async def _first_visible_count(self, selector: str) -> int:
        try:
            locator = self.page.locator(selector).first
            if await locator.count() == 0:
                return 0
            return 1 if await locator.is_visible() else 0
        except Exception:
            return 0

    async def _fill_subject_identifier(self, subject_id: str) -> None:
        normalized = (subject_id or "").strip().upper()
        if not normalized:
            raise RuntimeError("Campo identificativo soggetto mancante")

        radio_candidates = [
            "input[name='selDatiAna'][value='CF_PF']",
            "input[name='selCfDn'][value='CF_PNF']",
        ]
        for radio_selector in radio_candidates:
            radio = self.page.locator(radio_selector).first
            if await radio.count() > 0:
                with contextlib.suppress(Exception):
                    await radio.check(timeout=3000)

        candidates = [
            "input[name*='cod' i][name*='fisc' i]",
            "input[id*='cod' i][id*='fisc' i]",
            "input[name*='codice' i][name*='fisc' i]",
            "input[name*='partita' i][name*='iva' i]",
            "input[id*='partita' i][id*='iva' i]",
            "input[name*='piva' i]",
            "input[id*='piva' i]",
            "input[type='text']",
        ]
        for selector in candidates:
            locator = self.page.locator(selector).first
            if await locator.count() == 0:
                continue
            name_attr = ((await locator.get_attribute("name")) or "").lower()
            if "captcha" in name_attr or "sicurezza" in name_attr:
                continue
            if not await locator.is_visible():
                continue
            await locator.fill(normalized, timeout=5000)
            return
        raise RuntimeError("Campo identificativo soggetto non trovato (CF/P.IVA)")

    async def _select_request_type_if_present(self, request_type: str) -> None:
        desired = "Storica" if (request_type or "").strip().upper() == "STORICA" else "Attualità"
        label_candidates = [
            f"label:has-text('{desired}')",
            f"input[type='radio'] >> xpath=following-sibling::label[contains(., '{desired}')]",
        ]
        for selector in label_candidates:
            locator = self.page.locator(selector).first
            if await locator.count() == 0:
                continue
            if not await locator.is_visible():
                continue
            with contextlib.suppress(Exception):
                await locator.click(timeout=1500)
                return

    async def _maybe_accept_privacy_notice(self) -> None:
        page = self.page
        body_text = ""
        try:
            body_text = await page.locator("body").inner_text(timeout=2000)
        except Exception:
            body_text = ""

        if "Informativa trattamento dei dati personali" not in body_text:
            return

        logger.info("Informativa privacy rilevata, click su 'Conferma'")
        await self._trace_state("privacy-notice-detected")
        confirm_button = page.get_by_role("button", name="Conferma")
        if await confirm_button.count() == 0:
            confirm_button = page.locator("input[type='submit'][value='Conferma'], button:has-text('Conferma')")
        await confirm_button.first.click()
        await page.wait_for_load_state("domcontentloaded")
        logger.info("Informativa privacy confermata")
        await self._trace_state("privacy-notice-confirmed")

    async def _recover_locked_session(self) -> None:
        logger.info("Tentativo chiusura sessione SISTER gia' attiva")
        await self.logout()
        await self._trace_state("session-recovery-close")
        logger.info("Richiesta chiusura sessione SISTER inviata")
        logger.info("Attendo %s secondi per il rilascio della sessione SISTER", SESSION_RECOVERY_WAIT_SEC)
        await asyncio.sleep(SESSION_RECOVERY_WAIT_SEC)
        logger.info("Riavvio sessione browser dopo chiusura sessione SISTER")
        await self.stop()
        await self.start()
        await self.page.goto(self.selectors.login_url, wait_until="domcontentloaded")
        await self._trace_state("session-recovery-wait-complete")

    async def _click_close_sessions_link(self, prefer_text: str = "Chiudi") -> bool:
        locator = self.page.locator(f"a[href*='CloseSessionsSis']:has-text('{prefer_text}')")
        count = await locator.count()
        if count == 0:
            return False

        for index in range(count):
            candidate = locator.nth(index)
            if not await candidate.is_visible():
                continue
            text = ""
            with contextlib.suppress(Exception):
                text = (await candidate.inner_text(timeout=1000)).strip()
            if prefer_text.lower() in text.lower():
                await candidate.click(timeout=5000)
                return True
        return False

    async def _ensure_sezione_options_loaded(self, request_id: str) -> None:
        """Clicca 'scegli la sezione' se il select sezione è vuoto (popolazione server-side via submit)."""
        page = self.page
        options_count = await page.evaluate(
            """selector => {
                const el = document.querySelector(selector);
                return el ? el.options.length : 0;
            }""",
            arg=self.selectors.sezione_select_selector,
        )
        if options_count > 1:
            return
        sel_sezione = page.locator("input[name='selSezione']")
        if await sel_sezione.count() == 0:
            return
        logger.info("Richiesta %s click 'scegli la sezione' per popolare opzioni sezione", request_id)
        await sel_sezione.click()
        await page.wait_for_load_state("domcontentloaded")
        await self._trace_state(f"visura-after-sel-sezione-{request_id}")

    async def _wait_for_post_login_state(self) -> str:
        page = self.page
        for attempt in range(1, 16):
            url, title, body_excerpt = await self._read_page_state()
            if "Consultazioni e Certificazioni" in body_excerpt or "Home dei Servizi" in title:
                logger.info("Stato post-login SISTER pronto al tentativo %s", attempt)
                return "ready"
            if "Informativa trattamento dei dati personali" in body_excerpt:
                logger.info("Stato post-login con informativa privacy al tentativo %s", attempt)
                return "privacy"
            if "Utente gia' in sessione" in body_excerpt or "Utente bloccato" in title or "error_locked.jsp" in url:
                logger.info("Stato post-login con sessione bloccata al tentativo %s", attempt)
                return "locked"
            await asyncio.sleep(1)
        logger.warning("Stato post-login SISTER non stabilizzato entro il timeout di attesa")
        return "unknown"

    async def _trace_state(self, label: str) -> None:
        url, title, body_excerpt = await self._read_page_state()
        logger.info("Traccia browser %s: url=%s title=%s body=%s", label, url, title, body_excerpt)
        if self.config.debug_artifacts_path is not None:
            await self._write_debug_artifacts(f"trace-{label}")

    async def _raise_locked_session_error(self, reason: str, cause: Exception | None = None) -> None:
        url, title, body_excerpt = await self._read_page_state()
        issue_message = self._classify_login_issue(url, title, body_excerpt) or "Sessione SISTER bloccata."
        debug_context = await self._collect_debug_context(reason, url, title, body_excerpt)
        logger.error("Sessione SISTER non recuperabile automaticamente: %s %s", issue_message, debug_context)
        if cause is None:
            raise RuntimeError("SISTER_SESSION_LOCKED")
        raise RuntimeError("SISTER_SESSION_LOCKED") from cause

    @staticmethod
    def _is_session_locked_issue(issue_message: str | None) -> bool:
        if not issue_message:
            return False
        return "gia' in sessione" in issue_message.lower() or "già in sessione" in issue_message.lower() or "utente sister bloccato" in issue_message.lower()

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
            return (
                "Utente SISTER bloccato sul portale Agenzia delle Entrate. "
                "Verificare se esiste gia' una sessione attiva su un'altra postazione o browser."
            )
        if "credenzial" in haystack and (
            "errat" in haystack or "non valide" in haystack or "non sono valide" in haystack
        ):
            return "Credenziali SISTER rifiutate dal portale Agenzia delle Entrate."
        return None

    async def _write_debug_artifacts(self, reason: str) -> list[str]:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        target_dir = self.config.debug_artifacts_path / "connection-tests" / timestamp
        return await self._write_artifacts_to_dir(target_dir, reason)

    async def _write_artifacts_to_dir(self, target_dir: Path, reason: str) -> list[str]:
        target_dir.mkdir(parents=True, exist_ok=True)

        screenshot_path = target_dir / f"{reason}.png"
        html_path = target_dir / f"{reason}.html"
        artifacts: list[str] = []

        try:
            await self.page.screenshot(path=str(screenshot_path), full_page=True)
            artifacts.append(str(screenshot_path))
        except Exception:
            logger.exception("Impossibile salvare screenshot debug SISTER")

        try:
            html_path.write_text(await self.page.content(), encoding="utf-8")
            artifacts.append(str(html_path))
        except Exception:
            logger.exception("Impossibile salvare HTML debug SISTER")

        return artifacts

    @staticmethod
    def tipo_visura_value(tipo_visura: str) -> str:
        normalized = (tipo_visura or "").strip().lower()
        if normalized == "sintetica":
            return "4"
        if normalized == "analitica":
            return "3"
        return "0"
