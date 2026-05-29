from __future__ import annotations

import asyncio
import sys
from datetime import date
from pathlib import Path
from typing import Any

from app.core.config import settings


def _ensure_scraper_src_on_path() -> None:
    scraper_src = str(Path(settings.inaz_scraper_project_path).expanduser() / "src")
    if scraper_src not in sys.path:
        sys.path.insert(0, scraper_src)


async def test_login_with_credentials(*, username: str, password: str) -> dict[str, str | None]:
    _ensure_scraper_src_on_path()

    from playwright.async_api import async_playwright
    from inaz_scraper.cli import LOGIN_URL, login, wait_for_portal_idle

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        try:
            page = await context.new_page()
            await page.goto(LOGIN_URL, wait_until="domcontentloaded")
            await login(page, username, password)
            await wait_for_portal_idle(page)
            cookies = await context.cookies()
            return {
                "authenticated_url": page.url,
                "cookies": ",".join(cookie["name"] for cookie in cookies[:12]) if cookies else None,
            }
        finally:
            await context.close()
            await browser.close()


async def scrape_with_credentials(
    *,
    username: str,
    password: str,
    period_start: date,
    period_end: date,
    json_output: Path,
    limit: int | None = None,
) -> dict[str, Any]:
    _ensure_scraper_src_on_path()

    from playwright.async_api import async_playwright
    from inaz_scraper.cli import LOGIN_URL, login, wait_for_portal_idle
    from inaz_scraper.collaborators import (
        extract_collaborators,
        open_collaborator_list,
        open_collaborators_wizard,
        scrape_one_employee,
        write_timesheets_json,
    )

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        try:
            await page.goto(LOGIN_URL, wait_until="domcontentloaded")
            await login(page, username, password)
            await wait_for_portal_idle(page)

            await open_collaborators_wizard(page)
            list_frame = await open_collaborator_list(page, period_start, period_end)
            collaborators = await extract_collaborators(list_frame)
            if limit is not None:
                collaborators = collaborators[:limit]

            results: list[Any] = []
            errors: list[dict[str, str]] = []
            for index, collaborator in enumerate(collaborators, start=1):
                print(f"[{index}/{len(collaborators)}] {collaborator.employee_code} {collaborator.name}", flush=True)
                try:
                    results.append(await scrape_one_employee(page, collaborator, period_start, period_end))
                except Exception as exc:
                    errors.append(
                        {
                            "employee_code": collaborator.employee_code,
                            "name": collaborator.name,
                            "error": f"{type(exc).__name__}: {exc}",
                        }
                    )
                    print(
                        f"  ERRORE {collaborator.employee_code} {collaborator.name}: {type(exc).__name__}: {exc}",
                        flush=True,
                    )
                write_timesheets_json(json_output, period_start, period_end, results, errors)

            if not json_output.exists():
                write_timesheets_json(json_output, period_start, period_end, results, errors)

            return {"authenticated_url": page.url, "errors": errors, "total_collaborators": len(results)}
        finally:
            await context.close()
            await browser.close()


def run_scrape_with_credentials(**kwargs: Any) -> dict[str, Any]:
    return asyncio.run(scrape_with_credentials(**kwargs))
