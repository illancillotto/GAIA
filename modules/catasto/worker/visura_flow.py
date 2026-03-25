from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable

from browser_session import BrowserSession
from captcha_solver import CaptchaSolver


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
    last_ocr_text: str | None = None
    error_message: str | None = None


async def execute_visura_flow(
    browser: BrowserSession,
    request,
    document_path: Path,
    captcha_dir: Path,
    captcha_solver: CaptchaSolver,
    max_ocr_attempts: int,
    get_manual_captcha_decision: Callable[[Path], Awaitable[ManualCaptchaDecision]],
) -> VisuraFlowResult:
    await browser.open_visura_form()
    await browser.fill_visura_form(request)

    last_ocr_text: str | None = None
    for attempt in range(1, max_ocr_attempts + 1):
        captcha_bytes = await browser.capture_captcha_image()
        captcha_path = captcha_dir / f"{request.id}_ocr_{attempt}.png"
        captcha_path.parent.mkdir(parents=True, exist_ok=True)
        captcha_path.write_bytes(captcha_bytes)

        ocr_text = captcha_solver.solve(captcha_bytes)
        last_ocr_text = ocr_text
        if not ocr_text:
            continue

        if await browser.submit_captcha(ocr_text):
            file_size = await browser.download_pdf(document_path)
            return VisuraFlowResult(
                status="completed",
                file_path=document_path,
                file_size=file_size,
                captcha_image_path=captcha_path,
                last_ocr_text=ocr_text,
            )

        await asyncio.sleep(1)

    captcha_bytes = await browser.capture_captcha_image()
    captcha_path = captcha_dir / f"{request.id}_manual.png"
    captcha_path.parent.mkdir(parents=True, exist_ok=True)
    captcha_path.write_bytes(captcha_bytes)
    decision = await get_manual_captcha_decision(captcha_path)

    if decision.skip:
        return VisuraFlowResult(
            status="skipped",
            captcha_image_path=captcha_path,
            last_ocr_text=last_ocr_text,
            error_message="Skipped after manual CAPTCHA request",
        )

    if not decision.text:
        return VisuraFlowResult(
            status="failed",
            captcha_image_path=captcha_path,
            last_ocr_text=last_ocr_text,
            error_message="Manual CAPTCHA response missing",
        )

    if not await browser.submit_captcha(decision.text):
        return VisuraFlowResult(
            status="failed",
            captcha_image_path=captcha_path,
            last_ocr_text=last_ocr_text,
            error_message="Manual CAPTCHA solution rejected by SISTER",
        )

    file_size = await browser.download_pdf(document_path)
    return VisuraFlowResult(
        status="completed",
        file_path=document_path,
        file_size=file_size,
        captcha_image_path=captcha_path,
        last_ocr_text=decision.text,
    )
