from __future__ import annotations

import asyncio
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)
from sqlalchemy import select

from app.models.wc_sync_job import WCSyncJob
from app.modules.operazioni.models.vehicles import Vehicle

logger = logging.getLogger(__name__)

AUTODOC_SYNC_ENTITY = "autodoc_vehicle_details"
AUTODOC_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/136.0.0.0 Safari/537.36"
)
AUTODOC_CHALLENGE_TITLE = "Just a moment..."
AUTODOC_WAIT_AFTER_GOTO_MS = 5000
AUTODOC_MAX_CHALLENGE_WAIT_SEC = 45
AUTODOC_BASE_URL = "https://www.auto-doc.it/"
AUTODOC_PLATE_SEARCH_PATH = "/ajax/selector/vehicle/search-number"
AUTODOC_RICAMBI_PATH_FRAGMENT = "/ricambi-auto/"
AUTODOC_DISCOVERY_RESPONSE_TIMEOUT_MS = 8000
AUTODOC_DISCOVERY_SETTLE_TIMEOUT_MS = 10000
AUTODOC_ENABLE_PLATE_DISCOVERY = False


def _parse_vehicle_page_text(title: str, heading: str, image_url: str | None) -> dict[str, str]:
    source = heading or title
    data: dict[str, str] = {
        "Titolo pagina": title.strip(),
        "Scheda veicolo": heading.strip(),
    }
    if image_url:
        data["Immagine veicolo"] = image_url

    years_match = re.search(r"da anno\s+(\d{4})\s*-\s*(\d{4})", source, re.IGNORECASE)
    if years_match:
        data["Anno da"] = years_match.group(1)
        data["Anno a"] = years_match.group(2)

    power_match = re.search(
        r"\((\d+)\s*CV\s*/\s*(\d+)\s*kW\s*([^,)]*)",
        source,
        re.IGNORECASE,
    )
    if power_match:
        data["Potenza [CV]"] = power_match.group(1)
        data["Potenza [kW]"] = power_match.group(2)
        engine_code = power_match.group(3).strip()
        if engine_code:
            data["Codice motore"] = engine_code

    fuel_match = re.search(
        r"\b(Diesel|Benzina|GPL|Metano|Ibrido|Elettrico|Plug-in Hybrid)\b",
        source,
        re.IGNORECASE,
    )
    if fuel_match:
        data["Carburante"] = fuel_match.group(1)

    normalized = re.sub(r"^Ricambi\s+", "", source, flags=re.IGNORECASE).strip()
    normalized = re.sub(r"\s*\(.*$", "", normalized).strip()
    parts = normalized.split()
    if parts:
        data["Marca"] = parts[0].title()
    if len(parts) > 1:
        data["Modello"] = " ".join(parts[1:])

    body_match = re.search(
        r"\b(Hatchback|Station Wagon|Coupe|Cabrio|SUV|Van|Pick-up|Bus|Liftback|Fastback|Monovolume)\b",
        source,
        re.IGNORECASE,
    )
    if body_match:
        data["Tipo carrozzeria"] = body_match.group(1)

    return data


def _normalize_plate_number(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def _coerce_autodoc_url(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if cleaned.startswith("http://") or cleaned.startswith("https://"):
        return cleaned
    if AUTODOC_RICAMBI_PATH_FRAGMENT in cleaned:
        return urljoin(AUTODOC_BASE_URL, cleaned.lstrip("/"))
    return None


def _extract_autodoc_url_from_object(payload: Any) -> str | None:
    if isinstance(payload, dict):
        for value in payload.values():
            candidate = _extract_autodoc_url_from_object(value)
            if candidate:
                return candidate
        return None
    if isinstance(payload, list):
        for value in payload:
            candidate = _extract_autodoc_url_from_object(value)
            if candidate:
                return candidate
        return None
    if isinstance(payload, str):
        match = re.search(r"https?://[^\"'\\s]+/ricambi-auto/[^\"'\\s<]+", payload)
        if match:
            return _coerce_autodoc_url(match.group(0))
        match = re.search(r"/ricambi-auto/[^\"'\\s<]+", payload)
        if match:
            return _coerce_autodoc_url(match.group(0))
    return None


async def _prepare_page(page: Page, url: str) -> None:
    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(AUTODOC_WAIT_AFTER_GOTO_MS)
    waited = 0
    while waited < AUTODOC_MAX_CHALLENGE_WAIT_SEC:
        if (await page.title()).strip() != AUTODOC_CHALLENGE_TITLE:
            return
        await page.wait_for_timeout(5000)
        waited += 5
    raise RuntimeError("Challenge Cloudflare AUTODOC non superato entro il timeout")


async def _dismiss_cookie_overlays(page: Page) -> None:
    reject = page.locator("text=/Rifiutare tutti i cookie/i").first
    try:
        if await reject.count():
            await reject.click(timeout=3000)
            await page.wait_for_timeout(500)
    except Exception:
        pass
    await page.evaluate(
        """
        () => {
          document
            .querySelectorAll(
              [
                '[data-popup-cookies]',
                '.notification-popup',
                '.notification-popup__content',
                '.popup',
                '.popup--notification',
                '.overlay',
                '.header-search__overlay-wrap',
              ].join(',')
            )
            .forEach((node) => node.remove());
          document.body.style.overflow = 'auto';
          document.documentElement.style.overflow = 'auto';
        }
        """
    )


async def _set_plate_search_value(page: Page, normalized_plate: str) -> None:
    input_locator = page.locator("#kba1").first
    try:
        await input_locator.fill(normalized_plate, timeout=5000)
        return
    except Exception:
        logger.info("AUTODOC fill standard fallita, provo input via DOM per targa %s", normalized_plate)

    await input_locator.evaluate(
        """
        (element, value) => {
          element.focus();
          element.value = value;
          element.dispatchEvent(new Event('input', { bubbles: true }));
          element.dispatchEvent(new Event('change', { bubbles: true }));
        }
        """,
        normalized_plate,
    )


async def _trigger_plate_search(page: Page, normalized_plate: str) -> None:
    button = page.locator("[data-selector-number-button]").first
    try:
        await button.click(timeout=5000)
        return
    except Exception:
        logger.info("AUTODOC click standard fallito, provo click via DOM per targa %s", normalized_plate)

    await button.evaluate(
        """
        (element) => {
          element.click();
        }
        """
    )


async def _extract_vehicle_snapshot(page: Page, url: str) -> tuple[str, dict[str, str]]:
    await _prepare_page(page, url)
    await _dismiss_cookie_overlays(page)
    title = (await page.title()).strip()
    heading = (await page.locator("h1").first.text_content() or "").strip()
    image_url = await page.locator(".head-page__image img").first.get_attribute("src")
    data = _parse_vehicle_page_text(title=title, heading=heading, image_url=image_url)
    data["URL sorgente"] = url
    if not heading and not title:
        raise RuntimeError("Pagina AUTODOC priva di titolo leggibile")
    return heading or title, data


async def _discover_vehicle_url_by_plate(page: Page, plate_number: str) -> str:
    normalized_plate = _normalize_plate_number(plate_number)
    if not normalized_plate:
        raise RuntimeError("Targa mezzo mancante o non valida per ricerca AUTODOC")

    logger.info("AUTODOC discovery avviata per targa %s", normalized_plate)
    await _prepare_page(page, AUTODOC_BASE_URL)
    await _dismiss_cookie_overlays(page)
    await _set_plate_search_value(page, normalized_plate)

    response = None

    try:
        async with page.expect_response(
            lambda response: AUTODOC_PLATE_SEARCH_PATH in response.url,
            timeout=AUTODOC_DISCOVERY_RESPONSE_TIMEOUT_MS,
        ) as response_info:
            await _trigger_plate_search(page, normalized_plate)
        response = await response_info.value
    except PlaywrightTimeoutError:
        logger.info(
            "AUTODOC discovery senza response AJAX per targa %s, verifico navigazione/DOM",
            normalized_plate,
        )
        await _trigger_plate_search(page, normalized_plate)

    if response is not None:
        if response.status >= 400:
            logger.warning(
                "AUTODOC discovery bloccata per targa %s con status %s",
                normalized_plate,
                response.status,
            )
            raise RuntimeError(
                f"Ricerca targa AUTODOC bloccata da Cloudflare ({response.status})"
            )

        try:
            payload = await response.json()
        except Exception:
            payload = await response.text()
        discovered_url = _extract_autodoc_url_from_object(payload)
        if discovered_url:
            logger.info(
                "AUTODOC discovery completata per targa %s -> %s",
                normalized_plate,
                discovered_url,
            )
            return discovered_url

    deadline = asyncio.get_running_loop().time() + (AUTODOC_DISCOVERY_SETTLE_TIMEOUT_MS / 1000)
    while asyncio.get_running_loop().time() < deadline:
        if AUTODOC_RICAMBI_PATH_FRAGMENT in page.url:
            normalized = _coerce_autodoc_url(page.url)
            if normalized:
                logger.info(
                    "AUTODOC discovery completata da page.url per targa %s -> %s",
                    normalized_plate,
                    normalized,
                )
                return normalized
        await page.wait_for_timeout(500)

    title = (await page.title()).strip()
    current_url = page.url
    logger.warning(
        "AUTODOC discovery senza risultati per targa %s url=%s title=%s",
        normalized_plate,
        current_url,
        title,
    )
    raise RuntimeError(
        f"Nessun risultato AUTODOC trovato per {normalized_plate} (url={current_url}, title={title})"
    )


async def _build_browser() -> tuple[Playwright, Browser, BrowserContext, Page]:
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=True,
        args=["--disable-blink-features=AutomationControlled"],
    )
    context = await browser.new_context(
        user_agent=AUTODOC_USER_AGENT,
        viewport={"width": 1366, "height": 900},
        locale="it-IT",
        timezone_id="Europe/Rome",
    )
    await context.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
    )
    page = await context.new_page()
    page.set_default_timeout(60000)
    return playwright, browser, context, page


async def _close_browser(
    playwright: Playwright, browser: Browser, context: BrowserContext
) -> None:
    await context.close()
    await browser.close()
    await playwright.stop()


async def run_autodoc_sync_job_by_id(session_factory, job_id: str | uuid.UUID) -> None:
    db = session_factory()
    playwright: Playwright | None = None
    browser: Browser | None = None
    context: BrowserContext | None = None
    page: Page | None = None

    try:
        job_uuid = uuid.UUID(str(job_id))
        job = db.get(WCSyncJob, job_uuid)
        if job is None or job.entity != AUTODOC_SYNC_ENTITY:
            return

        params = dict(job.params_json or {})
        selected_ids = [uuid.UUID(item) for item in params.get("vehicle_ids", []) if item]
        force_refresh = bool(params.get("force_refresh", False))
        vehicles = db.scalars(
            select(Vehicle).where(Vehicle.id.in_(selected_ids)).order_by(Vehicle.name.asc())
        ).all()

        total = len(vehicles)
        params["selected_total"] = total
        params["processed_items"] = 0
        params["success_items"] = 0
        params["failed_items"] = 0
        params["skipped_items"] = 0
        params["current_vehicle"] = None
        params["progress_percent"] = 0
        params["recent_results"] = []
        job.status = "running"
        job.params_json = params
        db.commit()

        if total == 0:
            job.status = "completed"
            job.finished_at = datetime.now(timezone.utc)
            job.records_synced = 0
            job.records_skipped = 0
            job.records_errors = 0
            job.params_json = {**params, "completed_at": job.finished_at.isoformat()}
            db.commit()
            return

        playwright, browser, context, page = await _build_browser()
        synced = 0
        skipped = 0
        errors = 0
        error_messages: list[str] = []

        for index, vehicle in enumerate(vehicles, start=1):
            params = dict(job.params_json or {})
            params["current_vehicle"] = vehicle.name
            params["processed_items"] = index - 1
            job.params_json = params
            db.commit()

            now = datetime.now(timezone.utc)
            try:
                logger.info(
                    "AUTODOC sync mezzo %s/%s id=%s code=%s plate=%s",
                    index,
                    total,
                    vehicle.id,
                    vehicle.code,
                    vehicle.plate_number,
                )
                autodoc_url = vehicle.autodoc_url
                had_saved_autodoc_url = bool(autodoc_url)
                if not autodoc_url and AUTODOC_ENABLE_PLATE_DISCOVERY and vehicle.plate_number:
                    assert page is not None
                    autodoc_url = await _discover_vehicle_url_by_plate(page, vehicle.plate_number)
                    vehicle.autodoc_url = autodoc_url

                if not autodoc_url:
                    skipped += 1
                    vehicle.autodoc_sync_error = (
                        "Link AUTODOC mancante: la sync massiva aggiorna solo i mezzi con URL AUTODOC gia salvato"
                    )
                    result = {
                        "vehicle_id": str(vehicle.id),
                        "status": "skipped",
                        "reason": "missing_autodoc_url",
                    }
                elif not force_refresh and vehicle.autodoc_synced_at and vehicle.autodoc_data:
                    skipped += 1
                    result = {"vehicle_id": str(vehicle.id), "status": "skipped", "reason": "already_synced"}
                else:
                    assert page is not None
                    logger.info(
                        "AUTODOC snapshot avviata per mezzo %s url=%s",
                        vehicle.code,
                        autodoc_url,
                    )
                    title, data = await _extract_vehicle_snapshot(page, autodoc_url)
                    vehicle.autodoc_title = title
                    vehicle.autodoc_data = data
                    vehicle.autodoc_synced_at = now
                    vehicle.autodoc_sync_error = None
                    if not vehicle.brand and data.get("Marca"):
                        vehicle.brand = data["Marca"]
                    if not vehicle.fuel_type and data.get("Carburante"):
                        vehicle.fuel_type = data["Carburante"]
                    if vehicle.year_of_manufacture is None and data.get("Anno da", "").isdigit():
                        vehicle.year_of_manufacture = int(data["Anno da"])
                    synced += 1
                    result = {
                        "vehicle_id": str(vehicle.id),
                        "status": "synced",
                        "autodoc_url_discovered": not had_saved_autodoc_url,
                    }
                    logger.info(
                        "AUTODOC sync completata per mezzo %s discovered=%s",
                        vehicle.code,
                        not had_saved_autodoc_url,
                    )
            except Exception as exc:
                errors += 1
                message = str(exc)
                error_messages.append(f"{vehicle.name}: {message}")
                vehicle.autodoc_synced_at = now
                vehicle.autodoc_sync_error = message
                result = {"vehicle_id": str(vehicle.id), "status": "failed", "reason": message}
                logger.warning(
                    "AUTODOC sync fallita per mezzo %s: %s",
                    vehicle.code,
                    message,
                )

            recent_results = list((job.params_json or {}).get("recent_results", []))
            recent_results.append(result)
            params = dict(job.params_json or {})
            params["recent_results"] = recent_results[-10:]
            params["processed_items"] = index
            params["success_items"] = synced
            params["failed_items"] = errors
            params["skipped_items"] = skipped
            params["progress_percent"] = round(index / total * 100)
            params["current_vehicle"] = None
            job.params_json = params
            job.records_synced = synced
            job.records_skipped = skipped
            job.records_errors = errors
            db.commit()

        job.status = "failed" if synced == 0 and errors > 0 else "completed"
        job.finished_at = datetime.now(timezone.utc)
        job.error_detail = "\n".join(error_messages[:20]) if error_messages else None
        params = dict(job.params_json or {})
        params["completed_at"] = job.finished_at.isoformat()
        job.params_json = params
        db.commit()
    finally:
        if playwright is not None and browser is not None and context is not None:
            await _close_browser(playwright, browser, context)
        db.close()
