from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Awaitable, Callable

from sister_exceptions import DocumentNonEvadibileError, DocumentNotYetProducedError

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


async def _poll_and_download(
    browser: "BrowserSession",
    document_path: Path,
    captcha_path: Path | None,
    captcha_method: str | None,
    captcha_text: str | None,
    richieste_url: str | None,
    update_operation: Callable[[str], None] | None,
) -> VisuraFlowResult:
    if update_operation is not None:
        update_operation("Documento in elaborazione SISTER, attesa ConsultazioneRichieste...")
    logger.info("Documento non ancora prodotto, avvio polling ConsultazioneRichieste")
    try:
        file_size = await browser.poll_richieste_for_download(document_path, richieste_url)
        return VisuraFlowResult(
            status="completed",
            file_path=document_path,
            file_size=file_size,
            captcha_image_path=captcha_path,
            captcha_method=captcha_method,
            last_ocr_text=captcha_text,
        )
    except DocumentNonEvadibileError:
        logger.warning("Richiesta non evadibile rilevata in ConsultazioneRichieste")
        return VisuraFlowResult(
            status="non_evadibile",
            captcha_image_path=captcha_path,
            captcha_method=captcha_method,
            error_message="Richiesta non evadibile da SISTER",
        )


async def _submit_captcha_then_download(
    browser: "BrowserSession",
    text: str,
    document_path: Path,
    captcha_path: Path,
    captcha_method: str,
    update_operation: Callable[[str], None] | None,
) -> VisuraFlowResult | None:
    """Invia CAPTCHA e scarica il PDF. Restituisce None se CAPTCHA rifiutato."""
    try:
        accepted = await browser.submit_captcha(text)
    except DocumentNotYetProducedError as exc:
        return await _poll_and_download(
            browser, document_path, captcha_path, captcha_method, text,
            exc.richieste_url, update_operation,
        )

    if not accepted:
        return None

    if update_operation is not None:
        update_operation("Download PDF in corso")
    file_size = await browser.download_pdf(document_path)
    return VisuraFlowResult(
        status="completed",
        file_path=document_path,
        file_size=file_size,
        captcha_image_path=captcha_path,
        captcha_method=captcha_method,
        last_ocr_text=text,
    )


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
    update_operation: Callable[[str], None] | None = None,
) -> VisuraFlowResult:
    search_mode = str(getattr(request, "search_mode", "immobile") or "immobile").strip().lower()
    purpose = str(getattr(request, "purpose", "visura_pdf") or "visura_pdf").strip().lower()
    if purpose == "ade_status_scan":
        if search_mode != "immobile":
            return VisuraFlowResult(
                status="failed",
                error_message="La scansione storica AdE supporta solo ricerche per immobile.",
            )

    if search_mode == "soggetto":
        if update_operation is not None:
            update_operation("Apertura form visura per soggetto")
        logger.info("Richiesta %s apertura form soggetto", request.id)
        await browser.open_subject_form(getattr(request, "subject_kind", "PF") or "PF")
        if update_operation is not None:
            update_operation("Compilazione dati soggetto")
        logger.info("Richiesta %s compilazione form soggetto", request.id)
        await browser.fill_subject_form(request)
        if update_operation is not None:
            update_operation("Ricerca soggetto")
        subject_not_found = await browser.search_subject_and_open_visura(request)
        if subject_not_found:
            return VisuraFlowResult(status="not_found", error_message=subject_not_found)
    else:
        if update_operation is not None:
            update_operation("Apertura form visura")
        logger.info("Richiesta %s apertura form visura", request.id)
        await browser.open_visura_form()
        if update_operation is not None:
            update_operation("Compilazione dati visura")
        logger.info("Richiesta %s compilazione form visura", request.id)
        await browser.fill_visura_form(request)
        prepare_captcha_or_download = getattr(browser, "prepare_captcha_or_download", None)
        if callable(prepare_captcha_or_download):
            try:
                next_step = await prepare_captcha_or_download()
            except DocumentNotYetProducedError as exc:
                return await _poll_and_download(
                    browser, document_path, None, None, None,
                    exc.richieste_url, update_operation,
                )
            if next_step == "download":
                if update_operation is not None:
                    update_operation("Download PDF in corso")
                logger.info("Richiesta %s pronta al download senza CAPTCHA", request.id)
                file_size = await browser.download_pdf(document_path)
                return VisuraFlowResult(status="completed", file_path=document_path, file_size=file_size)

    # Catena: Agent locale × N → Anti-Captcha × M → Manuale

    if solve_llm_captcha is not None:
        for attempt in range(1, max_llm_attempts + 1):
            if update_operation is not None:
                update_operation(f"Tentativo CAPTCHA Agent ({attempt}/{max_llm_attempts})")
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
                browser, llm_text, document_path,
                captcha_path, "llm", update_operation,
            )
            if result is not None:
                logger.info("Richiesta %s CAPTCHA Agent (%s) terminale status=%s", request.id, attempt, result.status)
                return result
            logger.info("Richiesta %s CAPTCHA rifiutato dal portale dopo Agent (%s)", request.id, attempt)
            if attempt < max_llm_attempts:
                await browser.reload_captcha()

    if solve_external_captcha is not None:
        for attempt in range(1, max_external_attempts + 1):
            if update_operation is not None:
                update_operation(f"Tentativo CAPTCHA Anti-Captcha ({attempt}/{max_external_attempts})")
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
                browser, external_text, document_path,
                captcha_path, "external", update_operation,
            )
            if result is not None:
                logger.info("Richiesta %s CAPTCHA Anti-Captcha (%s) terminale status=%s", request.id, attempt, result.status)
                return result
            logger.info("Richiesta %s CAPTCHA rifiutato dal portale dopo Anti-Captcha (%s)", request.id, attempt)
            if attempt < max_external_attempts:
                await browser.reload_captcha()

    if update_operation is not None:
        update_operation("Richiesta CAPTCHA manuale")
    logger.info("Richiesta %s passaggio a CAPTCHA manuale", request.id)
    await browser.reload_captcha()
    captcha_bytes = await browser.capture_captcha_image()
    captcha_path = captcha_dir / f"{request.id}_manual.png"
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
            error_message="Manual CAPTCHA response missing",
        )

    result = await _submit_captcha_then_download(
        browser, decision.text, document_path,
        captcha_path, "manual", update_operation,
    )
    if result is not None:
        logger.info("Richiesta %s CAPTCHA manuale terminale status=%s", request.id, result.status)
        return result
    logger.warning("Richiesta %s CAPTCHA manuale rifiutato", request.id)
    return VisuraFlowResult(
        status="failed",
        captcha_image_path=captcha_path,
        captcha_method="manual",
        last_ocr_text=None,
        error_message="Manual CAPTCHA solution rejected by SISTER",
    )
