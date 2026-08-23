from __future__ import annotations

from dataclasses import dataclass
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Awaitable, Callable

from sister_exceptions import DocumentNonEvadibileError, DocumentNotYetProducedError, SisterDocumentNotReadyError, SisterNotFoundError

if TYPE_CHECKING:
    from browser_session import BrowserSession

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ManualCaptchaDecision:
    text: str | None
    skip: bool = False


@dataclass(slots=True)
class VisuraFlowResult:
    status: str
    file_path: Path | None = None
    file_size: int | None = None
    captcha_image_path: Path | None = None
    captcha_method: str | None = None
    last_ocr_text: str | None = None
    error_message: str | None = None
    ade_status_payload: dict | None = None
    remote_request_id: str | None = None
    remote_request_url: str | None = None


@dataclass(frozen=True, slots=True)
class VisuraFlowCallbacks:
    update_operation: Callable[[str], None] | None = None
    update_remote_state: Callable[[str | None, str | None, str], None] | None = None
    update_correlation_baseline: Callable[[list[str]], None] | None = None

    def operation(self, value: str) -> None:
        if self.update_operation is not None:
            self.update_operation(value)

    def remote_state(self, remote_id: str | None, remote_url: str | None, state: str) -> None:
        if self.update_remote_state is not None:
            self.update_remote_state(remote_id, remote_url, state)

    def correlation_baseline(self, keys: list[str]) -> None:
        if self.update_correlation_baseline is not None:
            self.update_correlation_baseline(keys)


@dataclass(frozen=True, slots=True)
class CaptchaSubmission:
    image_path: Path | None = None
    method: str | None = None
    text: str | None = None


def _current_correlation(browser: "BrowserSession"):
    getter = getattr(browser, "get_request_correlation", None)
    if callable(getter):
        return getter()
    return getattr(browser, "_active_request_correlation", None)


async def _poll_and_download(
    browser: "BrowserSession",
    document_path: Path,
    submission: CaptchaSubmission,
    richieste_url: str | None,
    callbacks: VisuraFlowCallbacks,
    remote_id: str | None = None,
    *,
    max_attempts: int | None = None,
) -> VisuraFlowResult:
    callbacks.operation("Documento in elaborazione SISTER, attesa ConsultazioneRichieste...")
    logger.info("Documento non ancora prodotto, avvio polling ConsultazioneRichieste")
    callbacks.remote_state(remote_id, richieste_url, "pending")
    try:
        file_size = await browser.poll_richieste_for_download(document_path, richieste_url, max_attempts=max_attempts)
    except SisterDocumentNotReadyError:
        # Documento non ancora pronto dopo i poll iniziali ridotti:
        # la richiesta viene messa in coda SISTER e ripresa successivamente.
        resolved_id = _resolved_remote_id(browser, remote_id)
        callbacks.remote_state(resolved_id, richieste_url, "pending")
        logger.info("Documento SISTER non pronto ai poll iniziali — richiesta messa in coda: url=%s", richieste_url)
        return VisuraFlowResult(
            status="queued_sister",
            captcha_image_path=submission.image_path,
            captcha_method=submission.method,
            last_ocr_text=submission.text,
            remote_request_id=resolved_id,
            remote_request_url=richieste_url,
            error_message=None,
        )
    except DocumentNonEvadibileError:
        return _non_evadibile_result(submission, richieste_url, callbacks, _resolved_remote_id(browser, remote_id))
    return _completed_remote_result(
        document_path, file_size, submission, richieste_url, callbacks, _resolved_remote_id(browser, remote_id)
    )



def _resolved_remote_id(browser: "BrowserSession", remote_id: str | None) -> str | None:
    return getattr(_current_correlation(browser), "remote_id", None) or remote_id


def _non_evadibile_result(
    submission: CaptchaSubmission,
    richieste_url: str | None,
    callbacks: VisuraFlowCallbacks,
    remote_id: str | None,
) -> VisuraFlowResult:
    logger.warning("Richiesta non evadibile rilevata in ConsultazioneRichieste")
    callbacks.remote_state(remote_id, richieste_url, "deleted")
    return VisuraFlowResult(
        status="non_evadibile",
        captcha_image_path=submission.image_path,
        captcha_method=submission.method,
        error_message="Richiesta non evadibile da SISTER",
        remote_request_id=remote_id,
        remote_request_url=richieste_url,
    )


def _completed_remote_result(
    document_path: Path,
    file_size: int,
    submission: CaptchaSubmission,
    richieste_url: str | None,
    callbacks: VisuraFlowCallbacks,
    remote_id: str | None,
) -> VisuraFlowResult:
    callbacks.remote_state(remote_id, richieste_url, "downloaded")
    return VisuraFlowResult(
        status="completed", file_path=document_path, file_size=file_size,
        captcha_image_path=submission.image_path, captcha_method=submission.method,
        last_ocr_text=submission.text, remote_request_id=remote_id,
        remote_request_url=richieste_url,
    )


async def _submit_captcha_then_download(
    browser: "BrowserSession",
    submission: CaptchaSubmission,
    document_path: Path,
    callbacks: VisuraFlowCallbacks,
    *,
    initial_remote_poll_attempts: int | None = None,
) -> VisuraFlowResult | None:
    """Invia CAPTCHA e scarica il PDF. Restituisce None se CAPTCHA rifiutato."""
    try:
        accepted = await _send_captcha(browser, submission, callbacks)
    except DocumentNotYetProducedError as exc:
        return await _poll_and_download(
            browser, document_path, submission, exc.richieste_url, callbacks, exc.remote_id,
            max_attempts=initial_remote_poll_attempts,
        )
    return await _download_submitted_captcha(browser, submission, document_path, callbacks) if accepted else None



async def _send_captcha(
    browser: "BrowserSession",
    submission: CaptchaSubmission,
    callbacks: VisuraFlowCallbacks,
) -> bool:
    begin_submission = getattr(browser, "begin_remote_submission", None)
    if callable(begin_submission):
        begin_submission(callbacks.update_remote_state)
    return await browser.submit_captcha(submission.text or "")


async def _download_submitted_captcha(
    browser: "BrowserSession",
    submission: CaptchaSubmission,
    document_path: Path,
    callbacks: VisuraFlowCallbacks,
) -> VisuraFlowResult:
    callbacks.operation("Download PDF in corso")
    file_size = await browser.download_pdf(document_path)
    return VisuraFlowResult(
        status="completed",
        file_path=document_path,
        file_size=file_size,
        captcha_image_path=submission.image_path,
        captcha_method=submission.method,
        last_ocr_text=submission.text,
    )


async def _resume_remote_request(
    browser: "BrowserSession",
    request,
    document_path: Path,
    callbacks: VisuraFlowCallbacks,
) -> VisuraFlowResult | None:
    begin_correlation = getattr(browser, "begin_request_correlation", None)
    if callable(begin_correlation):
        await begin_correlation(request)
    correlation = _current_correlation(browser)
    if correlation is not None:
        callbacks.correlation_baseline(sorted(correlation.baseline_keys))

    remote_state = str(getattr(request, "sister_remote_state", "") or "").lower()
    remote_url = getattr(request, "sister_remote_request_url", None)
    if remote_state not in {"submitted", "pending", "ready"} or not remote_url:
        return None
    return await _poll_and_download(
        browser,
        document_path,
        CaptchaSubmission(),
        remote_url,
        callbacks,
        getattr(request, "sister_remote_request_id", None),
    )


async def _download_if_ready(
    browser: "BrowserSession",
    request,
    document_path: Path,
    callbacks: VisuraFlowCallbacks,
    mode_label: str,
) -> VisuraFlowResult | None:
    prepare = getattr(browser, "prepare_captcha_or_download", None)
    if not callable(prepare):
        return None
    try:
        next_step = await prepare()
    except DocumentNotYetProducedError as exc:
        return await _poll_and_download(
            browser,
            document_path,
            CaptchaSubmission(),
            exc.richieste_url,
            callbacks,
            exc.remote_id,
        )
    if next_step != "download":
        return None

    callbacks.operation("Download PDF in corso")
    logger.info("Richiesta %s pronta al download senza CAPTCHA%s", request.id, mode_label)
    file_size = await browser.download_pdf(document_path)
    return VisuraFlowResult(status="completed", file_path=document_path, file_size=file_size)


async def _prepare_subject_request(
    browser: "BrowserSession",
    request,
    document_path: Path,
    callbacks: VisuraFlowCallbacks,
) -> VisuraFlowResult | None:
    callbacks.operation("Apertura form visura per soggetto")
    logger.info("Richiesta %s apertura form soggetto", request.id)
    await browser.open_subject_form(getattr(request, "subject_kind", "PF") or "PF")
    callbacks.operation("Compilazione dati soggetto")
    logger.info("Richiesta %s compilazione form soggetto", request.id)
    await browser.fill_subject_form(request)
    callbacks.operation("Ricerca soggetto")
    subject_not_found = await browser.search_subject_and_open_visura(request)
    if subject_not_found:
        return VisuraFlowResult(status="not_found", error_message=subject_not_found)
    return await _download_if_ready(browser, request, document_path, callbacks, " (soggetto)")


async def _prepare_immobile_request(
    browser: "BrowserSession",
    request,
    document_path: Path,
    callbacks: VisuraFlowCallbacks,
) -> VisuraFlowResult | None:
    callbacks.operation("Apertura form visura")
    logger.info("Richiesta %s apertura form visura", request.id)
    await browser.open_visura_form()
    callbacks.operation("Compilazione dati visura")
    logger.info("Richiesta %s compilazione form visura", request.id)
    try:
        await browser.fill_visura_form(request)
    except SisterNotFoundError as exc:
        return VisuraFlowResult(status="not_found", error_message=str(exc))
    return await _download_if_ready(browser, request, document_path, callbacks, "")


async def _prepare_request(
    browser: "BrowserSession",
    request,
    document_path: Path,
    callbacks: VisuraFlowCallbacks,
) -> VisuraFlowResult | None:
    search_mode = str(getattr(request, "search_mode", "immobile") or "immobile").strip().lower()
    purpose = str(getattr(request, "purpose", "visura_pdf") or "visura_pdf").strip().lower()
    if purpose == "ade_status_scan" and search_mode != "immobile":
        return VisuraFlowResult(
            status="failed",
            error_message="La scansione storica AdE supporta solo ricerche per immobile.",
        )
    if search_mode == "soggetto":
        return await _prepare_subject_request(browser, request, document_path, callbacks)
    return await _prepare_immobile_request(browser, request, document_path, callbacks)


async def execute_visura_flow(
    browser: "BrowserSession",
    request,
    document_path: Path,
    captcha_dir: Path,
    get_manual_captcha_decision: Callable[[Path], Awaitable[ManualCaptchaDecision]],
    solve_external_captcha: Callable[[bytes], Awaitable[str | None]] | None = None,
    solve_llm_captcha: Callable[[bytes], Awaitable[str | None]] | None = None,
    max_llm_attempts: int = 3,
    max_external_attempts: int = 3,
    max_manual_attempts: int | None = None,
    initial_remote_poll_attempts: int | None = None,
    callbacks: VisuraFlowCallbacks | None = None,
) -> VisuraFlowResult:
    """Esegue il flusso completo di download visura SISTER.

    initial_remote_poll_attempts: se impostato, il polling ConsultazioneRichieste
    dopo il submit usa al massimo questo numero di tentativi. Se il documento non
    è pronto, restituisce status='queued_sister' invece di aspettare il timeout
    completo. Le richieste queued_sister vengono riprese nella sessione successiva
    con il numero completo di poll (RICHIESTE_POLL_ATTEMPTS).
    """
    callbacks = callbacks or VisuraFlowCallbacks()
    if max_manual_attempts is None:
        max_manual_attempts = int(os.getenv("CAPTCHA_MANUAL_ATTEMPTS", "5"))
    resumed = await _resume_remote_request(browser, request, document_path, callbacks)
    if resumed is not None:
        return resumed
    prepared = await _prepare_request(browser, request, document_path, callbacks)
    if prepared is not None:
        return prepared


    # Catena: Agent locale x N -> Anti-Captcha x M -> Manuale
    if solve_llm_captcha is not None:
        for attempt in range(1, max_llm_attempts + 1):
            callbacks.operation(f"Tentativo CAPTCHA Agent ({attempt}/{max_llm_attempts})")
            logger.info("Richiesta %s tentativo CAPTCHA Agent %s/%s", request.id, attempt, max_llm_attempts)
            captcha_bytes = await browser.capture_captcha_image()
            captcha_path = captcha_dir / f"{request.id}_llm_{attempt}.png"
            captcha_path.parent.mkdir(parents=True, exist_ok=True)
            captcha_path.write_bytes(captcha_bytes)

            try:
                llm_text = await solve_llm_captcha(captcha_bytes)
            except Exception:
                logger.exception("Richiesta %s Agent CAPTCHA solver (%s) fallito", request.id, attempt)
                if attempt < max_llm_attempts:
                    await browser.reload_captcha()
                continue
            if not llm_text:
                logger.info("Richiesta %s Agent (%s) ha restituito testo vuoto", request.id, attempt)
                if attempt < max_llm_attempts:
                    await browser.reload_captcha()
                continue
            result = await _submit_captcha_then_download(
                browser,
                CaptchaSubmission(captcha_path, "llm", llm_text),
                document_path,
                callbacks,
                initial_remote_poll_attempts=initial_remote_poll_attempts,
            )
            if result is not None:
                logger.info("Richiesta %s CAPTCHA Agent (%s) terminale status=%s", request.id, attempt, result.status)
                return result
            logger.info("Richiesta %s CAPTCHA rifiutato dal portale dopo Agent (%s)", request.id, attempt)
            if attempt < max_llm_attempts:
                await browser.reload_captcha()

    if solve_external_captcha is not None:
        for attempt in range(1, max_external_attempts + 1):
            callbacks.operation(f"Tentativo CAPTCHA Anti-Captcha ({attempt}/{max_external_attempts})")
            logger.info("Richiesta %s tentativo CAPTCHA Anti-Captcha %s/%s", request.id, attempt, max_external_attempts)
            captcha_bytes = await browser.capture_captcha_image()
            captcha_path = captcha_dir / f"{request.id}_external_{attempt}.png"
            captcha_path.parent.mkdir(parents=True, exist_ok=True)
            captcha_path.write_bytes(captcha_bytes)

            try:
                external_text = await solve_external_captcha(captcha_bytes)
            except Exception:
                logger.exception("Richiesta %s Anti-Captcha (%s) fallito", request.id, attempt)
                if attempt < max_external_attempts:
                    await browser.reload_captcha()
                continue
            if not external_text:
                logger.info("Richiesta %s Anti-Captcha (%s) ha restituito testo vuoto", request.id, attempt)
                if attempt < max_external_attempts:
                    await browser.reload_captcha()
                continue
            result = await _submit_captcha_then_download(
                browser,
                CaptchaSubmission(captcha_path, "external", external_text),
                document_path,
                callbacks,
                initial_remote_poll_attempts=initial_remote_poll_attempts,
            )
            if result is not None:
                logger.info("Richiesta %s CAPTCHA Anti-Captcha (%s) terminale status=%s", request.id, attempt, result.status)
                return result
            logger.info("Richiesta %s CAPTCHA rifiutato dal portale dopo Anti-Captcha (%s)", request.id, attempt)
            if attempt < max_external_attempts:
                await browser.reload_captcha()

    last_captcha_path: Path | None = None
    for attempt in range(1, max_manual_attempts + 1):
        callbacks.operation(f"Richiesta CAPTCHA manuale ({attempt}/{max_manual_attempts})")
        logger.info("Richiesta %s passaggio a CAPTCHA manuale %s/%s", request.id, attempt, max_manual_attempts)
        await browser.reload_captcha()
        captcha_bytes = await browser.capture_captcha_image()
        captcha_path = captcha_dir / f"{request.id}_manual_{attempt}.png"
        last_captcha_path = captcha_path
        captcha_path.parent.mkdir(parents=True, exist_ok=True)
        captcha_path.write_bytes(captcha_bytes)
        decision = await get_manual_captcha_decision(captcha_path)

        if decision.skip:
            return VisuraFlowResult(
                status="skipped",
                captcha_image_path=captcha_path,
                captcha_method="manual",
                last_ocr_text=None,
                error_message="Skipped after manual CAPTCHA request",
            )
        if not decision.text:
            logger.warning("Richiesta %s CAPTCHA manuale mancante", request.id)
            return VisuraFlowResult(
                status="failed",
                captcha_image_path=captcha_path,
                captcha_method="manual",
                last_ocr_text=None,
                error_message="Automatic CAPTCHA exhausted; manual CAPTCHA response missing",
            )

        result = await _submit_captcha_then_download(
            browser,
            CaptchaSubmission(captcha_path, "manual", decision.text),
            document_path,
            callbacks,
            initial_remote_poll_attempts=initial_remote_poll_attempts,
        )
        if result is not None:
            logger.info("Richiesta %s CAPTCHA manuale terminale status=%s", request.id, result.status)
            return result
        logger.warning("Richiesta %s CAPTCHA manuale rifiutato %s/%s", request.id, attempt, max_manual_attempts)

    return VisuraFlowResult(
        status="failed",
        captcha_image_path=last_captcha_path,
        captcha_method="manual",
        last_ocr_text=None,
        error_message="Manual CAPTCHA solution rejected by SISTER",
    )
