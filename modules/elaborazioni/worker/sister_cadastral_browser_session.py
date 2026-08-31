from __future__ import annotations

from collections.abc import Awaitable, Callable
import logging

from browser_session import BrowserSession


logger = logging.getLogger(__name__)
_REQUIRED_SECTION_MARKERS = ("LA SEZIONE È OBBLIGATORIA", "LA SEZIONE E' OBBLIGATORIA")
_PATCH_MARKER = "_gaia_cadastral_section_recovery"
WaitDelegate = Callable[[BrowserSession, str], Awaitable[None]]


async def _recover_required_section(
    session: BrowserSession,
    request_id: str,
    delegate: WaitDelegate,
) -> None:
    try:
        await delegate(session, request_id)
        return
    except RuntimeError as error:
        expected_prefix = f"Submit visura non avanzato per richiesta {request_id}:"
        if not str(error).startswith(expected_prefix):
            raise
        selected = await _select_recoverable_section(session, request_id, error)
        if not selected:
            raise
    logger.info(
        "Richiesta %s: selezionata automaticamente l'unica sezione catastale disponibile",
        request_id,
    )
    await session.page.click(session.selectors.visura_button_selector)
    await delegate(session, request_id)


async def _select_recoverable_section(
    session: BrowserSession,
    request_id: str,
    batch_error: RuntimeError,
) -> bool:
    try:
        if not await _requires_cadastral_section(session):
            return False
        return await _select_unique_cadastral_section(session, request_id)
    except Exception as recovery_error:
        raise batch_error from recovery_error


async def _requires_cadastral_section(session: BrowserSession) -> bool:
    return bool(
        await session.page.evaluate(
            """markers => {
                const text = String(document.body?.innerText || '').toUpperCase();
                return markers.some(marker => text.includes(marker));
            }""",
            arg=list(_REQUIRED_SECTION_MARKERS),
        )
    )


async def _select_unique_cadastral_section(session: BrowserSession, request_id: str) -> bool:
    await session._ensure_sezione_options_loaded(request_id)
    selector = session.selectors.sezione_select_selector
    values = await session.page.evaluate(
        """selector => Array.from(document.querySelector(selector)?.options || [])
            .map(option => String(option.value || '').trim())
            .filter(Boolean)""",
        arg=selector,
    )
    valid_values = [str(value).strip() for value in values if str(value).strip()]
    if len(valid_values) != 1:
        return False
    await session.page.select_option(selector, value=valid_values[0])
    return True


def install_cadastral_section_recovery() -> None:
    current = getattr(BrowserSession, "_wait_for_visura_submission_state", None)
    if current is None or getattr(current, _PATCH_MARKER, False):
        return

    async def patched(self: BrowserSession, request_id: str) -> None:
        await _recover_required_section(self, request_id, current)

    setattr(patched, _PATCH_MARKER, True)
    BrowserSession._wait_for_visura_submission_state = patched
