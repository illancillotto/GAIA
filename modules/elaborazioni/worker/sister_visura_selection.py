from __future__ import annotations

from typing import Any

from sister_exceptions import SisterInvalidDocumentError


def expected_request_type(request_type: str | None, tipo_visura_value: str) -> str:
    if request_type:
        return "STORICA" if request_type.strip().upper() == "STORICA" else "ATTUALITA"
    return "ATTUALITA" if tipo_visura_value == "0" else "STORICA"


async def select_request_type(page: Any, request_type: str) -> None:
    is_historical = (request_type or "").strip().upper() == "STORICA"
    desired = "Storica" if is_historical else "Attualità"
    selected = await _click_and_verify_request_type(page, desired)
    if is_historical and not selected:
        raise SisterInvalidDocumentError(
            "SISTER non ha confermato la selezione della richiesta storica"
        )


async def _click_and_verify_request_type(page: Any, desired: str) -> bool:
    candidates = (
        f"label:has-text('{desired}')",
        f"input[type='radio'] >> xpath=following-sibling::label[contains(., '{desired}')]",
    )
    for selector in candidates:
        locator = page.locator(selector).first
        if await locator.count() == 0 or not await locator.is_visible():
            continue
        try:
            await locator.click(timeout=1500)
        except Exception:
            continue
        if await request_type_selection_matches(page, desired):
            return True
    return False


async def request_type_selection_matches(page: Any, desired: str) -> bool:
    try:
        selected = await page.evaluate(
            """desired => {
                const normalize = value => (value || '').normalize('NFD')
                    .replace(/[\u0300-\u036f]/g, '').toLowerCase();
                const expected = normalize(desired);
                return Array.from(document.querySelectorAll("input[type='radio']:checked"))
                    .some(input => {
                        const labels = input.labels ? Array.from(input.labels) : [];
                        const text = labels.map(label => label.textContent || '').join(' ');
                        return normalize(text).includes(expected)
                            || normalize(input.value).includes(expected)
                            || normalize(input.id).includes(expected);
                    });
            }""",
            desired,
        )
    except Exception:
        return False
    return selected is True


async def select_visura_type(
    page: Any,
    base_selector: str,
    tipo_visura: str,
    value: str,
    *,
    required: bool,
) -> None:
    locator = page.locator(f"{base_selector}[value='{value}']").first
    if await locator.count() == 0 or not await locator.is_visible():
        if required:
            raise SisterInvalidDocumentError(
                f"SISTER non ha esposto il tipo di visura storica richiesto ({tipo_visura})"
            )
        return
    try:
        await locator.check(timeout=5000)
        selected = await locator.is_checked()
    except Exception as exc:
        raise SisterInvalidDocumentError(
            f"SISTER non ha selezionato il tipo di visura richiesto ({tipo_visura})"
        ) from exc
    if not selected:
        raise SisterInvalidDocumentError(
            f"SISTER non ha confermato il tipo di visura richiesto ({tipo_visura})"
        )


async def reconfirm_visura_type(
    page: Any,
    base_selector: str,
    pending: tuple[str, str] | None,
) -> None:
    if pending is None:
        return
    tipo_visura, value = pending
    locator = page.locator(f"{base_selector}[value='{value}']").first
    if await locator.count() == 0 or not await locator.is_visible():
        return
    await select_visura_type(page, base_selector, tipo_visura, value, required=True)


__all__ = [
    "expected_request_type",
    "reconfirm_visura_type",
    "request_type_selection_matches",
    "select_request_type",
    "select_visura_type",
]
