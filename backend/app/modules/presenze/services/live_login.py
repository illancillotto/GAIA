from __future__ import annotations

import asyncio
import json
import sys
from datetime import date
from pathlib import Path
from time import monotonic
from typing import Any, Callable, Iterable

from app.core.config import settings

ProgressCallback = Callable[[dict[str, Any]], None]
CompletedTimesheetCallback = Callable[[dict[str, Any]], None]


def _ensure_scraper_src_on_path() -> None:
    scraper_root = Path(settings.presenze_scraper_project_path).expanduser()
    scraper_src_path = scraper_root / "src"
    if not scraper_src_path.exists():
        raise RuntimeError(
            f"Presenze scraper project not found at {scraper_root}. "
            "Ensure the repository is available and mounted inside the backend container."
        )
    scraper_src = str(scraper_src_path)
    if scraper_src not in sys.path:
        sys.path.insert(0, scraper_src)


async def test_login_with_credentials(*, username: str, password: str) -> dict[str, str | None]:
    _ensure_scraper_src_on_path()

    from playwright.async_api import async_playwright
    from presenze_scraper.cli import LOGIN_URL, login, wait_for_portal_idle

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
    employee_codes: Iterable[str] | None = None,
    completed_employee_codes: Iterable[str] | None = None,
    progress_callback: ProgressCallback | None = None,
    completed_timesheet_callback: CompletedTimesheetCallback | None = None,
    employee_timeout_seconds: int = 150,
) -> dict[str, Any]:
    _ensure_scraper_src_on_path()

    from playwright.async_api import async_playwright
    from presenze_scraper.cli import LOGIN_URL, find_login_frame, login, wait_for_portal_idle
    from presenze_scraper.collaborators import (
        EmployeeTimesheet,
        extract_collaborators,
        open_collaborator_list,
        open_collaborators_wizard,
        scrape_one_employee,
        timesheet_to_jsonable,
        write_timesheets_json,
    )

    def emit(event_type: str, **payload: Any) -> None:
        if progress_callback is None:
            return
        progress_callback({"type": event_type, **payload})

    def load_checkpoint() -> tuple[list[EmployeeTimesheet], list[dict[str, str]]]:
        if not json_output.exists():
            return [], []
        try:
            payload = json.loads(json_output.read_text(encoding="utf-8"))
        except Exception:
            return [], []
        if not isinstance(payload, dict):
            return [], []
        if payload.get("period_start") != period_start.strftime("%d/%m/%Y"):
            return [], []
        if payload.get("period_end") != period_end.strftime("%d/%m/%Y"):
            return [], []

        employees = payload.get("employees")
        errors = payload.get("errors")
        if not isinstance(employees, list):
            return [], []

        results: list[EmployeeTimesheet] = []
        for item in employees:
            if not isinstance(item, dict) or not isinstance(item.get("collaborator"), dict):
                continue
            from presenze_scraper.collaborators import Collaborator, DailyRow, SummaryRow

            results.append(
                EmployeeTimesheet(
                    collaborator=Collaborator(**item["collaborator"]),
                    company_label=item.get("company_label"),
                    period_start=item.get("period_start") or period_start.strftime("%d/%m/%Y"),
                    period_end=item.get("period_end") or period_end.strftime("%d/%m/%Y"),
                    daily_rows=[DailyRow(**row) for row in item.get("daily_rows", []) if isinstance(row, dict)],
                    summary_rows=[SummaryRow(**row) for row in item.get("summary_rows", []) if isinstance(row, dict)],
                )
            )
        parsed_errors = [item for item in errors if isinstance(item, dict)] if isinstance(errors, list) else []
        return results, parsed_errors

    def upsert_error(errors: list[dict[str, str]], employee_code: str, name: str, error: str) -> None:
        for item in errors:
            if item.get("employee_code") == employee_code:
                item["name"] = name
                item["error"] = error
                return
        errors.append({"employee_code": employee_code, "name": name, "error": error})

    def remove_error(errors: list[dict[str, str]], employee_code: str) -> list[dict[str, str]]:
        return [item for item in errors if item.get("employee_code") != employee_code]

    async def restore_portal_page(context, current_page):
        try:
            await current_page.close()
        except Exception:
            pass
        page = await context.new_page()
        await page.goto(LOGIN_URL, wait_until="domcontentloaded")
        try:
            await find_login_frame(page)
        except Exception:
            pass
        else:
            await login(page, username, password)
        await wait_for_portal_idle(page)
        await open_collaborators_wizard(page)
        return page

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
            selected_codes = {str(code).strip() for code in (employee_codes or []) if str(code).strip()}
            if selected_codes:
                collaborators = [item for item in collaborators if item.employee_code in selected_codes]
            if limit is not None:
                collaborators = collaborators[:limit]

            results, errors = load_checkpoint()
            completed_codes = {item.collaborator.employee_code for item in results}
            completed_codes.update(str(code).strip() for code in (completed_employee_codes or []) if str(code).strip())
            already_completed_count = len(completed_codes)
            pending_collaborators = [item for item in collaborators if item.employee_code not in completed_codes]

            resumed_from_checkpoint = bool(already_completed_count or errors)

            emit(
                "resume_state",
                total_collaborators=len(collaborators),
                completed_collaborators=already_completed_count,
                pending_collaborators=len(pending_collaborators),
                error_count=len(errors),
                resumed=resumed_from_checkpoint,
            )

            for index, collaborator in enumerate(pending_collaborators, start=already_completed_count + 1):
                print(f"[{index}/{len(collaborators)}] {collaborator.employee_code} {collaborator.name}", flush=True)
                emit(
                    "collaborator_started",
                    index=index,
                    total=len(collaborators),
                    employee_code=collaborator.employee_code,
                    name=collaborator.name,
                )
                started_at = monotonic()
                try:
                    timesheet = await asyncio.wait_for(
                        scrape_one_employee(page, collaborator, period_start, period_end, progress_callback=emit),
                        timeout=employee_timeout_seconds,
                    )
                    results.append(timesheet)
                    completed_codes.add(collaborator.employee_code)
                    errors = remove_error(errors, collaborator.employee_code)
                    write_timesheets_json(json_output, period_start, period_end, results, errors)
                    if completed_timesheet_callback is not None:
                        completed_timesheet_callback(timesheet_to_jsonable(timesheet))
                    emit(
                        "collaborator_completed",
                        index=index,
                        total=len(collaborators),
                        employee_code=collaborator.employee_code,
                        name=collaborator.name,
                        elapsed_seconds=round(monotonic() - started_at, 2),
                        completed_collaborators=len(completed_codes),
                        error_count=len(errors),
                        daily_rows=len(timesheet.daily_rows),
                        summary_rows=len(timesheet.summary_rows),
                    )
                except Exception as exc:
                    error_text = f"{type(exc).__name__}: {exc}"
                    upsert_error(errors, collaborator.employee_code, collaborator.name, error_text)
                    print(
                        f"  ERRORE {collaborator.employee_code} {collaborator.name}: {error_text}",
                        flush=True,
                    )
                    write_timesheets_json(json_output, period_start, period_end, results, errors)
                    emit(
                        "collaborator_failed",
                        index=index,
                        total=len(collaborators),
                        employee_code=collaborator.employee_code,
                        name=collaborator.name,
                        elapsed_seconds=round(monotonic() - started_at, 2),
                        completed_collaborators=len(completed_codes),
                        error_count=len(errors),
                        error=error_text,
                    )
                    page = await restore_portal_page(context, page)

            if not json_output.exists():
                write_timesheets_json(json_output, period_start, period_end, results, errors)

            return {
                "authenticated_url": page.url,
                "errors": errors,
                "total_collaborators": len(collaborators),
                "completed_collaborators": len(completed_codes),
                "failed_collaborators": len(errors),
                "resumed_from_checkpoint": resumed_from_checkpoint,
                "employees": [timesheet_to_jsonable(item) for item in results],
            }
        finally:
            await context.close()
            await browser.close()


def run_scrape_with_credentials(**kwargs: Any) -> dict[str, Any]:
    return asyncio.run(scrape_with_credentials(**kwargs))
