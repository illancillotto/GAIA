from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from app.modules.presenze.services import live_login


@dataclass
class _FakeCollaborator:
    employee_code: str
    name: str


@dataclass
class _FakeDailyRow:
    work_date: str


@dataclass
class _FakeSummaryRow:
    code: str
    minutes: int


@dataclass
class _FakeEmployeeTimesheet:
    collaborator: _FakeCollaborator
    company_label: str | None = None
    period_start: str = ""
    period_end: str = ""
    daily_rows: list[_FakeDailyRow] = field(default_factory=list)
    summary_rows: list[_FakeSummaryRow] = field(default_factory=list)


class _FakePage:
    def __init__(self, name: str) -> None:
        self.name = name
        self.url = ""
        self.closed = False
        self.goto_calls: list[tuple[str, str]] = []

    async def goto(self, url: str, *, wait_until: str) -> None:
        self.url = url
        self.goto_calls.append((url, wait_until))

    async def close(self) -> None:
        self.closed = True


class _FakeContext:
    def __init__(self) -> None:
        self.pages: list[_FakePage] = []
        self.closed = False

    async def new_page(self) -> _FakePage:
        page = _FakePage(f"page-{len(self.pages) + 1}")
        self.pages.append(page)
        return page

    async def cookies(self) -> list[dict[str, str]]:
        return [{"name": "SESSION"}, {"name": "XSRF"}]

    async def close(self) -> None:
        self.closed = True


class _FakeBrowser:
    def __init__(self, context: _FakeContext) -> None:
        self.context = context
        self.closed = False

    async def new_context(self) -> _FakeContext:
        return self.context

    async def close(self) -> None:
        self.closed = True


class _FakeChromium:
    def __init__(self, browser: _FakeBrowser) -> None:
        self.browser = browser
        self.launch_calls: list[bool] = []

    async def launch(self, *, headless: bool) -> _FakeBrowser:
        self.launch_calls.append(headless)
        return self.browser


class _FakePlaywrightContextManager:
    def __init__(self, chromium: _FakeChromium) -> None:
        self.playwright = type("Playwright", (), {"chromium": chromium})()

    async def __aenter__(self) -> Any:
        return self.playwright

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


def _timesheet_to_jsonable(item: _FakeEmployeeTimesheet) -> dict[str, Any]:
    return {
        "collaborator": asdict(item.collaborator),
        "company_label": item.company_label,
        "period_start": item.period_start,
        "period_end": item.period_end,
        "daily_rows": [asdict(row) for row in item.daily_rows],
        "summary_rows": [asdict(row) for row in item.summary_rows],
    }


def _write_timesheets_json(
    json_output: Path,
    period_start: date,
    period_end: date,
    results: list[_FakeEmployeeTimesheet],
    errors: list[dict[str, str]],
) -> None:
    payload = {
        "period_start": period_start.strftime("%d/%m/%Y"),
        "period_end": period_end.strftime("%d/%m/%Y"),
        "employees": [_timesheet_to_jsonable(item) for item in results],
        "errors": errors,
    }
    json_output.write_text(json.dumps(payload), encoding="utf-8")


def _install_fake_live_login_modules(
    monkeypatch: pytest.MonkeyPatch,
    *,
    tmp_path: Path,
    collaborators: list[_FakeCollaborator],
    scrape_results: dict[str, _FakeEmployeeTimesheet | Exception] | None = None,
    login_url: str = "https://fake-inaz/login",
    close_raises: bool = False,
    find_login_frame_raises: bool = False,
) -> dict[str, Any]:
    scraper_root = tmp_path / "presenze-scraper"
    scraper_src = scraper_root / "src"
    scraper_src.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(live_login.settings, "presenze_scraper_project_path", str(scraper_root))

    state: dict[str, Any] = {
        "login_calls": [],
        "idle_calls": [],
        "wizard_calls": [],
        "list_calls": [],
        "extract_calls": 0,
        "find_login_frame_calls": 0,
        "scrape_calls": [],
    }

    context = _FakeContext()
    browser = _FakeBrowser(context)
    chromium = _FakeChromium(browser)

    async_api_module = ModuleType("playwright.async_api")
    async_api_module.async_playwright = lambda: _FakePlaywrightContextManager(chromium)

    playwright_module = ModuleType("playwright")
    playwright_module.async_api = async_api_module

    cli_module = ModuleType("presenze_scraper.cli")
    cli_module.LOGIN_URL = login_url

    async def login(page: _FakePage, username: str, password: str) -> None:
        state["login_calls"].append((page.name, username, password))
        page.url = f"{login_url}/home"

    async def wait_for_portal_idle(page: _FakePage) -> None:
        state["idle_calls"].append(page.name)

    async def find_login_frame(page: _FakePage) -> str:
        state["find_login_frame_calls"] += 1
        if find_login_frame_raises:
            raise RuntimeError("frame not found")
        return "frame"

    cli_module.login = login
    cli_module.wait_for_portal_idle = wait_for_portal_idle
    cli_module.find_login_frame = find_login_frame

    collaborators_module = ModuleType("presenze_scraper.collaborators")
    collaborators_module.Collaborator = _FakeCollaborator
    collaborators_module.DailyRow = _FakeDailyRow
    collaborators_module.SummaryRow = _FakeSummaryRow
    collaborators_module.EmployeeTimesheet = _FakeEmployeeTimesheet
    collaborators_module.timesheet_to_jsonable = _timesheet_to_jsonable
    collaborators_module.write_timesheets_json = _write_timesheets_json

    async def open_collaborators_wizard(page: _FakePage) -> None:
        state["wizard_calls"].append(page.name)

    async def open_collaborator_list(page: _FakePage, period_start: date, period_end: date) -> str:
        state["list_calls"].append((page.name, period_start, period_end))
        return "frame-list"

    async def extract_collaborators(_frame: str) -> list[_FakeCollaborator]:
        state["extract_calls"] += 1
        return collaborators

    async def scrape_one_employee(
        page: _FakePage,
        collaborator: _FakeCollaborator,
        period_start: date,
        period_end: date,
        progress_callback=None,
    ) -> _FakeEmployeeTimesheet:
        state["scrape_calls"].append((page.name, collaborator.employee_code, period_start, period_end))
        if progress_callback is not None:
            progress_callback({"type": "opening_timesheet", "employee_code": collaborator.employee_code})
        result = (scrape_results or {}).get(collaborator.employee_code)
        if isinstance(result, Exception):
            raise result
        if result is not None:
            return result
        return _FakeEmployeeTimesheet(
            collaborator=collaborator,
            company_label="Consorzio",
            period_start=period_start.strftime("%d/%m/%Y"),
            period_end=period_end.strftime("%d/%m/%Y"),
            daily_rows=[_FakeDailyRow(work_date=period_start.strftime("%d/%m/%Y"))],
            summary_rows=[_FakeSummaryRow(code="TOT", minutes=420)],
        )

    collaborators_module.open_collaborators_wizard = open_collaborators_wizard
    collaborators_module.open_collaborator_list = open_collaborator_list
    collaborators_module.extract_collaborators = extract_collaborators
    collaborators_module.scrape_one_employee = scrape_one_employee

    presenze_scraper_module = ModuleType("presenze_scraper")
    presenze_scraper_module.cli = cli_module
    presenze_scraper_module.collaborators = collaborators_module

    monkeypatch.setitem(live_login.sys.modules, "playwright", playwright_module)
    monkeypatch.setitem(live_login.sys.modules, "playwright.async_api", async_api_module)
    monkeypatch.setitem(live_login.sys.modules, "presenze_scraper", presenze_scraper_module)
    monkeypatch.setitem(live_login.sys.modules, "presenze_scraper.cli", cli_module)
    monkeypatch.setitem(live_login.sys.modules, "presenze_scraper.collaborators", collaborators_module)

    state["context"] = context
    state["browser"] = browser
    state["chromium"] = chromium
    if close_raises:
        original_new_page = context.new_page

        async def new_page_with_bad_close() -> _FakePage:
            page = await original_new_page()

            async def bad_close() -> None:
                raise RuntimeError("close failed")

            page.close = bad_close  # type: ignore[method-assign]
            return page

        context.new_page = new_page_with_bad_close  # type: ignore[method-assign]
    return state


def test_ensure_scraper_src_on_path_inserts_once_and_rejects_missing_project(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    missing_root = tmp_path / "missing-scraper"
    monkeypatch.setattr(live_login.settings, "presenze_scraper_project_path", str(missing_root))

    with pytest.raises(RuntimeError, match="Presenze scraper project not found"):
        live_login._ensure_scraper_src_on_path()

    scraper_root = tmp_path / "real-scraper"
    scraper_src = scraper_root / "src"
    scraper_src.mkdir(parents=True)
    monkeypatch.setattr(live_login.settings, "presenze_scraper_project_path", str(scraper_root))

    live_login._ensure_scraper_src_on_path()
    live_login._ensure_scraper_src_on_path()

    assert live_login.sys.path.count(str(scraper_src)) == 1


def test_test_login_with_credentials_returns_authenticated_url_and_cookie_names(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = _install_fake_live_login_modules(
        monkeypatch,
        tmp_path=tmp_path,
        collaborators=[],
    )

    result = asyncio.run(
        live_login.test_login_with_credentials(username="operator", password="secret")
    )

    assert result == {
        "authenticated_url": "https://fake-inaz/login/home",
        "cookies": "SESSION,XSRF",
    }
    assert state["login_calls"] == [("page-1", "operator", "secret")]
    assert state["idle_calls"] == ["page-1"]
    assert state["context"].closed is True
    assert state["browser"].closed is True


def test_scrape_with_credentials_resumes_from_checkpoint_and_clears_old_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    period_start = date(2026, 1, 1)
    period_end = date(2026, 1, 31)
    collaborator_a = _FakeCollaborator(employee_code="AA1", name="Alpha")
    collaborator_b = _FakeCollaborator(employee_code="BB2", name="Beta")
    checkpoint_employee = _FakeEmployeeTimesheet(
        collaborator=collaborator_a,
        company_label="Consorzio",
        period_start=period_start.strftime("%d/%m/%Y"),
        period_end=period_end.strftime("%d/%m/%Y"),
        daily_rows=[_FakeDailyRow(work_date="01/01/2026")],
        summary_rows=[_FakeSummaryRow(code="TOT", minutes=420)],
    )
    resumed_employee = _FakeEmployeeTimesheet(
        collaborator=collaborator_b,
        company_label="Consorzio",
        period_start=period_start.strftime("%d/%m/%Y"),
        period_end=period_end.strftime("%d/%m/%Y"),
        daily_rows=[_FakeDailyRow(work_date="02/01/2026")],
        summary_rows=[_FakeSummaryRow(code="TOT", minutes=385)],
    )
    state = _install_fake_live_login_modules(
        monkeypatch,
        tmp_path=tmp_path,
        collaborators=[collaborator_a, collaborator_b],
        scrape_results={"BB2": resumed_employee},
    )
    json_output = tmp_path / "checkpoint.json"
    json_output.write_text(
        json.dumps(
            {
                "period_start": period_start.strftime("%d/%m/%Y"),
                "period_end": period_end.strftime("%d/%m/%Y"),
                "employees": [_timesheet_to_jsonable(checkpoint_employee)],
                "errors": [{"employee_code": "BB2", "name": "Beta", "error": "old error"}],
            }
        ),
        encoding="utf-8",
    )

    events: list[dict[str, Any]] = []
    completed_payloads: list[dict[str, Any]] = []
    result = asyncio.run(
        live_login.scrape_with_credentials(
            username="operator",
            password="secret",
            period_start=period_start,
            period_end=period_end,
            json_output=json_output,
            progress_callback=events.append,
            completed_timesheet_callback=completed_payloads.append,
        )
    )

    saved = json.loads(json_output.read_text(encoding="utf-8"))
    assert result["completed_collaborators"] == 2
    assert result["failed_collaborators"] == 0
    assert result["resumed_from_checkpoint"] is True
    assert len(result["employees"]) == 2
    assert saved["errors"] == []
    assert [item["collaborator"]["employee_code"] for item in saved["employees"]] == ["AA1", "BB2"]
    assert completed_payloads == [_timesheet_to_jsonable(resumed_employee)]
    assert events[0]["type"] == "resume_state"
    assert events[0]["completed_collaborators"] == 1
    assert events[0]["pending_collaborators"] == 1
    assert events[-1]["type"] == "collaborator_completed"
    assert state["scrape_calls"] == [("page-1", "BB2", period_start, period_end)]


def test_scrape_with_credentials_recovers_after_employee_failure_and_rewrites_invalid_checkpoint(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    period_start = date(2026, 2, 1)
    period_end = date(2026, 2, 28)
    collaborator_a = _FakeCollaborator(employee_code="AA1", name="Alpha")
    collaborator_b = _FakeCollaborator(employee_code="BB2", name="Beta")
    state = _install_fake_live_login_modules(
        monkeypatch,
        tmp_path=tmp_path,
        collaborators=[collaborator_a, collaborator_b],
        scrape_results={"AA1": RuntimeError("portal boom")},
    )
    json_output = tmp_path / "invalid-checkpoint.json"
    json_output.write_text("{this is not valid json", encoding="utf-8")

    events: list[dict[str, Any]] = []
    result = asyncio.run(
        live_login.scrape_with_credentials(
            username="operator",
            password="secret",
            period_start=period_start,
            period_end=period_end,
            json_output=json_output,
            progress_callback=events.append,
            employee_timeout_seconds=30,
        )
    )

    saved = json.loads(json_output.read_text(encoding="utf-8"))
    assert result["completed_collaborators"] == 1
    assert result["failed_collaborators"] == 1
    assert result["resumed_from_checkpoint"] is False
    assert saved["errors"] == [{"employee_code": "AA1", "name": "Alpha", "error": "RuntimeError: portal boom"}]
    assert [item["collaborator"]["employee_code"] for item in saved["employees"]] == ["BB2"]
    assert events[0]["type"] == "resume_state"
    assert events[1]["type"] == "collaborator_started"
    assert any(event["type"] == "collaborator_failed" for event in events)
    assert any(event["type"] == "collaborator_completed" for event in events)
    assert len(state["context"].pages) == 2
    assert state["context"].pages[0].closed is True
    assert state["login_calls"] == [
        ("page-1", "operator", "secret"),
        ("page-2", "operator", "secret"),
    ]
    assert state["find_login_frame_calls"] == 1
    assert state["wizard_calls"] == ["page-1", "page-2"]
    assert state["scrape_calls"] == [
        ("page-1", "AA1", period_start, period_end),
        ("page-2", "BB2", period_start, period_end),
    ]


@pytest.mark.parametrize(
    ("checkpoint_payload", "filename"),
    [
        (["bad"], "not-a-dict.json"),
        ({"period_start": "01/02/2026", "period_end": "28/02/2026", "employees": []}, "mismatch-dates.json"),
        ({"period_start": "01/03/2026", "period_end": "28/02/2026", "employees": []}, "mismatch-end-date.json"),
        ({"period_start": "01/03/2026", "period_end": "31/03/2026", "employees": "not-a-list"}, "bad-employees.json"),
    ],
)
def test_scrape_with_credentials_ignores_invalid_checkpoint_payloads(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    checkpoint_payload: Any,
    filename: str,
) -> None:
    period_start = date(2026, 3, 1)
    period_end = date(2026, 3, 31)
    collaborator = _FakeCollaborator(employee_code="AA1", name="Alpha")
    _install_fake_live_login_modules(
        monkeypatch,
        tmp_path=tmp_path,
        collaborators=[collaborator],
    )
    json_output = tmp_path / filename
    json_output.write_text(json.dumps(checkpoint_payload), encoding="utf-8")

    result = asyncio.run(
        live_login.scrape_with_credentials(
            username="operator",
            password="secret",
            period_start=period_start,
            period_end=period_end,
            json_output=json_output,
            limit=0,
        )
    )

    assert result["completed_collaborators"] == 0
    assert result["failed_collaborators"] == 0
    assert result["resumed_from_checkpoint"] is False
    assert json.loads(json_output.read_text(encoding="utf-8")) == checkpoint_payload


def test_scrape_with_credentials_writes_empty_artifact_when_output_file_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    period_start = date(2026, 3, 1)
    period_end = date(2026, 3, 31)
    collaborator = _FakeCollaborator(employee_code="AA1", name="Alpha")
    _install_fake_live_login_modules(
        monkeypatch,
        tmp_path=tmp_path,
        collaborators=[collaborator],
    )
    json_output = tmp_path / "missing-output.json"

    result = asyncio.run(
        live_login.scrape_with_credentials(
            username="operator",
            password="secret",
            period_start=period_start,
            period_end=period_end,
            json_output=json_output,
            limit=0,
        )
    )

    assert result["completed_collaborators"] == 0
    assert result["failed_collaborators"] == 0
    assert result["resumed_from_checkpoint"] is False
    assert json.loads(json_output.read_text(encoding="utf-8")) == {
        "period_start": "01/03/2026",
        "period_end": "31/03/2026",
        "employees": [],
        "errors": [],
    }


def test_scrape_with_credentials_updates_existing_error_and_restores_even_if_close_or_frame_fail(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    period_start = date(2026, 4, 1)
    period_end = date(2026, 4, 30)
    collaborator = _FakeCollaborator(employee_code="AA1", name="Alpha")
    state = _install_fake_live_login_modules(
        monkeypatch,
        tmp_path=tmp_path,
        collaborators=[collaborator],
        scrape_results={"AA1": RuntimeError("new boom")},
        close_raises=True,
        find_login_frame_raises=True,
    )
    json_output = tmp_path / "existing-error.json"
    json_output.write_text(
        json.dumps(
            {
                "period_start": period_start.strftime("%d/%m/%Y"),
                "period_end": period_end.strftime("%d/%m/%Y"),
                "employees": [{"collaborator": "bad"}],
                "errors": [{"employee_code": "AA1", "name": "Old", "error": "old boom"}],
            }
        ),
        encoding="utf-8",
    )

    result = asyncio.run(
        live_login.scrape_with_credentials(
            username="operator",
            password="secret",
            period_start=period_start,
            period_end=period_end,
            json_output=json_output,
            completed_employee_codes=["", "  "],
            progress_callback=lambda event: None,
        )
    )

    saved = json.loads(json_output.read_text(encoding="utf-8"))
    assert result["resumed_from_checkpoint"] is True
    assert result["failed_collaborators"] == 1
    assert saved["errors"] == [{"employee_code": "AA1", "name": "Alpha", "error": "RuntimeError: new boom"}]
    assert state["find_login_frame_calls"] == 1
    assert state["login_calls"] == [("page-1", "operator", "secret")]


def test_run_scrape_with_credentials_delegates_to_asyncio_run(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, Any] = {}

    async def fake_scrape_with_credentials(**kwargs: Any) -> dict[str, Any]:
        called["kwargs"] = kwargs
        return {"status": "ok"}

    def fake_asyncio_run(coro):
        called["is_coroutine"] = asyncio.iscoroutine(coro)
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    monkeypatch.setattr(live_login, "scrape_with_credentials", fake_scrape_with_credentials)
    monkeypatch.setattr(live_login.asyncio, "run", fake_asyncio_run)

    result = live_login.run_scrape_with_credentials(username="operator", password="secret")

    assert result == {"status": "ok"}
    assert called["is_coroutine"] is True
    assert called["kwargs"] == {"username": "operator", "password": "secret"}
