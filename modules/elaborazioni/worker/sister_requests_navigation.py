"""Apply ConsultazioneRichieste filters before correlating a remote document."""

import json
import logging
import re
from collections.abc import Awaitable, Callable
from pathlib import Path

from playwright.async_api import Page

from sister_exceptions import SisterRequestCorrelationError
from sister_request_rows import SisterRemoteRequestRow

logger = logging.getLogger(__name__)

CATEGORY_VALUES = {
    "Non evadibili": "nonEspletabili",
    "Espletate": "espletate",
    "Prelevate": "prelevate",
}


async def restore_portal_menu(page: Page, link_name: str) -> None:
    if await page.get_by_role("link", name=link_name).count() == 0:
        # Observed authenticated home, not the menu-less ConsultazioneRichieste view.
        await page.goto(
            "https://sister3.agenziaentrate.gov.it/Servizi/", wait_until="domcontentloaded"
        )
        await page.get_by_role("link", name=link_name).wait_for(timeout=12000)


async def open_portal_visure_menu(
    page: Page, selectors, trace: Callable[[str], Awaitable[None]]
) -> None:
    await restore_portal_menu(page, selectors.consultazioni_link_name)
    if await page.get_by_role("link", name=selectors.visure_link_name).count() == 0:
        await page.get_by_role("link", name=selectors.consultazioni_link_name).click()
        await trace("menu-after-consultazioni-click")
    await page.get_by_role("link", name=selectors.visure_link_name).click()
    await trace("menu-after-visure-click")


async def record_search_snapshot(
    page: Page, label: str, day: str, matched: bool, artifact_dir: str | None
) -> None:
    try:
        counts = await page.locator("table tr").count()
        logger.info(
            "SISTER ricerca categoria=%s giorno=%s righe=%s match=%s", label, day, counts, matched
        )
        if artifact_dir is None:
            return
        root = Path(artifact_dir)
        root.mkdir(parents=True, exist_ok=True)
        key = re.sub(r"[^a-zA-Z0-9_-]", "_", f"search-{label}-{day}")
        # Fixed names overwrite the previous poll; no row text or personal data in JSON.
        (root / f"{key}.json").write_text(
            json.dumps(
                {
                    "category": label,
                    "day": day,
                    "rows": counts,
                    "matched": matched,
                }
            ),
            encoding="utf-8",
        )
        if day == "-" or matched:
            (root / f"{key}.html").write_text(await page.content(), encoding="utf-8")
            await page.screenshot(path=str(root / f"{key}.png"), full_page=True)
    except Exception:
        logger.warning("Snapshot ricerca SISTER non salvato", exc_info=True)


async def select_requests_category(page: Page, label: str, day: str = "-") -> bool:
    value = CATEGORY_VALUES.get(label, label)
    radio = page.locator(f"input[name='radioCount'][value='{value}']")
    if await radio.count():
        await submit_requests_filter(page, value, day)
    else:
        tab = page.locator(f"a:has-text('{label}'), td:has-text('{label}')").first
        if await tab.count() == 0 or not await tab.is_visible():
            return False
        await tab.click(timeout=5000)
    await page.wait_for_load_state("domcontentloaded", timeout=5000)
    await page.wait_for_timeout(500)
    return True


async def submit_requests_filter(page: Page, category: str, day: str) -> None:
    radio = page.locator(f"input[name='radioCount'][value='{category}']")
    await radio.check(timeout=5000)
    period = page.locator("select[name='comboGiorni']")
    has_period = await period.count() > 0
    if has_period:
        await period.select_option(day, timeout=5000)
    await page.locator("input[name='metodo'][value='Aggiorna']").click(timeout=5000)
    await page.wait_for_load_state("domcontentloaded", timeout=5000)
    # A successful click alone does not prove SISTER applied the requested filter.
    if not await radio.is_checked(timeout=5000):
        raise SisterRequestCorrelationError(f"SISTER non ha applicato la categoria {category}")
    if has_period and await period.input_value(timeout=5000) != day:
        raise SisterRequestCorrelationError(f"SISTER non ha applicato il periodo {day}")


async def find_in_requests_category(
    page: Page,
    label: str,
    find_row: Callable[[], Awaitable[SisterRemoteRequestRow | None]],
    *,
    artifact_dir: str | None = None,
) -> SisterRemoteRequestRow | None:
    if not await select_requests_category(page, label):
        logger.warning("SISTER categoria %s non accessibile: ricerca incompleta", label)
        return None
    row = await find_row()
    await record_search_snapshot(page, label, "-", row is not None, artifact_dir)
    if row is not None:
        return row
    # Use only date controls exposed by SISTER, never guessed pagination URLs.
    days = await page.locator("select[name='comboGiorni'] option").evaluate_all(
        "options => options.filter(o => !o.disabled && o.value && o.value !== '-').map(o => o.value)"
    )
    for day in dict.fromkeys(days):
        logger.info("Ricerca richiesta SISTER: categoria=%s giorno=%s", label, day)
        if not await select_requests_category(page, label, day):
            break
        row = await find_row()
        await record_search_snapshot(page, label, day, row is not None, artifact_dir)
        if row is not None:
            return row
    logger.warning(
        "SISTER richiesta non trovata in %s dopo ricerca intero periodo e giorni disponibili; "
        "elenco potenzialmente limitato dal portale, nessun reinvio o cancellazione di altre richieste",
        label,
    )
    return None
