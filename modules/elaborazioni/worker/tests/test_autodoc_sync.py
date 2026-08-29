from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import autodoc_sync
import pytest


def run(coro):
    return asyncio.run(coro)


class Locator:
    def __init__(
        self,
        *,
        count: int = 0,
        text: str | None = None,
        attribute: str | None = None,
        fail_fill: bool = False,
        fail_click: bool = False,
    ) -> None:
        self._count = count
        self._text = text
        self._attribute = attribute
        self.fail_fill = fail_fill
        self.fail_click = fail_click
        self.calls: list[tuple[str, object]] = []

    @property
    def first(self):
        return self

    async def count(self):
        return self._count

    async def click(self, *, timeout=None):
        self.calls.append(("click", timeout))
        if self.fail_click:
            raise RuntimeError("click failed")

    async def fill(self, value, *, timeout=None):
        self.calls.append(("fill", value))
        if self.fail_fill:
            raise RuntimeError("fill failed")

    async def evaluate(self, script, value=None):
        self.calls.append(("evaluate", value))

    async def text_content(self):
        return self._text

    async def get_attribute(self, _name):
        return self._attribute


class Page:
    def __init__(self, *, titles=None, url="https://www.auto-doc.it/") -> None:
        self.titles = list(titles or ["AUTODOC"])
        self.url = url
        self.locators: dict[str, Locator] = {}
        self.waits: list[int] = []
        self.evaluations: list[str] = []
        self.goto_calls: list[str] = []
        self.response_context = None

    async def goto(self, url, **_kwargs):
        self.goto_calls.append(url)

    async def wait_for_timeout(self, milliseconds):
        self.waits.append(milliseconds)

    async def title(self):
        if len(self.titles) > 1:
            return self.titles.pop(0)
        return self.titles[0]

    def locator(self, selector):
        return self.locators.setdefault(selector, Locator())

    async def evaluate(self, script):
        self.evaluations.append(script)

    def expect_response(self, *_args, **_kwargs):
        return self.response_context


class ResponseContext:
    def __init__(self, response=None, *, timeout=False) -> None:
        self.response = response
        self.timeout = timeout
        self.value = self._value()

    async def _value(self):
        return self.response

    async def __aenter__(self):
        if self.timeout:
            self.value.close()
            raise autodoc_sync.PlaywrightTimeoutError("timeout")
        return self

    async def __aexit__(self, *_args):
        return None


def test_parse_normalize_coerce_and_recursive_url_extraction() -> None:
    parsed = autodoc_sync._parse_vehicle_page_text(
        "",
        "Ricambi FIAT Panda Hatchback da anno 2012 - 2020 (95 CV / 70 kW 312A, Diesel)",
        "image.jpg",
    )
    assert parsed["Immagine veicolo"] == "image.jpg"
    assert parsed["Anno da"] == "2012"
    assert parsed["Anno a"] == "2020"
    assert parsed["Potenza [CV]"] == "95"
    assert parsed["Potenza [kW]"] == "70"
    assert parsed["Codice motore"] == "312A"
    assert parsed["Carburante"].lower() == "diesel"
    assert parsed["Marca"] == "Fiat"
    assert parsed["Modello"] == "Panda Hatchback da anno 2012 - 2020"
    assert parsed["Tipo carrozzeria"].lower() == "hatchback"

    empty = autodoc_sync._parse_vehicle_page_text("", "", None)
    assert empty == {"Titolo pagina": "", "Scheda veicolo": ""}
    no_engine_code = autodoc_sync._parse_vehicle_page_text("Car (95 CV / 70 kW )", "", None)
    assert "Codice motore" not in no_engine_code
    assert autodoc_sync._normalize_plate_number(None) == ""
    assert autodoc_sync._normalize_plate_number("ab 123-cd") == "AB123CD"
    assert autodoc_sync._coerce_autodoc_url(None) is None
    assert autodoc_sync._coerce_autodoc_url("  ") is None
    assert autodoc_sync._coerce_autodoc_url("https://example/ricambi-auto/car") == "https://example/ricambi-auto/car"
    assert autodoc_sync._coerce_autodoc_url("/ricambi-auto/car") == "https://www.auto-doc.it/ricambi-auto/car"
    assert autodoc_sync._coerce_autodoc_url("/other") is None
    assert autodoc_sync._extract_autodoc_url_from_object({"a": [None, {"b": 1}]}) is None
    assert autodoc_sync._extract_autodoc_url_from_object(
        {"a": [None, {"b": "go https://example/ricambi-auto/car<"}]}
    ) == "https://example/ricambi-auto/car"
    assert autodoc_sync._extract_autodoc_url_from_object(["none", "/ricambi-auto/car"]) == "https://www.auto-doc.it/ricambi-auto/car"
    assert autodoc_sync._extract_autodoc_url_from_object(123) is None


def test_prepare_page_success_and_challenge_timeout(monkeypatch) -> None:
    page = Page(titles=[autodoc_sync.AUTODOC_CHALLENGE_TITLE, "Ready"])
    run(autodoc_sync._prepare_page(page, "https://example"))
    assert page.goto_calls == ["https://example"]
    assert page.waits == [autodoc_sync.AUTODOC_WAIT_AFTER_GOTO_MS, 5000]

    monkeypatch.setattr(autodoc_sync, "AUTODOC_MAX_CHALLENGE_WAIT_SEC", 5)
    blocked = Page(titles=[autodoc_sync.AUTODOC_CHALLENGE_TITLE])
    with pytest.raises(RuntimeError, match="Cloudflare"):
        run(autodoc_sync._prepare_page(blocked, "https://example"))


def test_cookie_input_and_button_standard_and_dom_fallbacks() -> None:
    page = Page()
    reject = Locator(count=1)
    page.locators["text=/Rifiutare tutti i cookie/i"] = reject
    run(autodoc_sync._dismiss_cookie_overlays(page))
    assert reject.calls == [("click", 3000)]
    assert page.evaluations

    failing_page = Page()
    failing_page.locators["text=/Rifiutare tutti i cookie/i"] = Locator(count=1, fail_click=True)
    run(autodoc_sync._dismiss_cookie_overlays(failing_page))
    assert failing_page.evaluations
    run(autodoc_sync._dismiss_cookie_overlays(Page()))

    input_locator = Locator()
    page.locators["#kba1"] = input_locator
    run(autodoc_sync._set_plate_search_value(page, "AB123CD"))
    assert input_locator.calls == [("fill", "AB123CD")]

    fallback_input = Locator(fail_fill=True)
    page.locators["#kba1"] = fallback_input
    run(autodoc_sync._set_plate_search_value(page, "AB123CD"))
    assert fallback_input.calls[-1] == ("evaluate", "AB123CD")

    button = Locator()
    page.locators["[data-selector-number-button]"] = button
    run(autodoc_sync._trigger_plate_search(page, "AB123CD"))
    assert button.calls == [("click", 5000)]

    fallback_button = Locator(fail_click=True)
    page.locators["[data-selector-number-button]"] = fallback_button
    run(autodoc_sync._trigger_plate_search(page, "AB123CD"))
    assert fallback_button.calls[-1] == ("evaluate", None)


def test_extract_vehicle_snapshot_success_and_empty_failure(monkeypatch) -> None:
    async def no_prepare(_page, _url):
        return None

    async def no_cookies(_page):
        return None

    monkeypatch.setattr(autodoc_sync, "_prepare_page", no_prepare)
    monkeypatch.setattr(autodoc_sync, "_dismiss_cookie_overlays", no_cookies)
    page = Page(titles=["Title"])
    page.locators["h1"] = Locator(text="Heading")
    page.locators[".head-page__image img"] = Locator(attribute="image")
    title, data = run(autodoc_sync._extract_vehicle_snapshot(page, "https://source"))
    assert title == "Heading"
    assert data["URL sorgente"] == "https://source"

    empty = Page(titles=[""])
    empty.locators["h1"] = Locator(text=None)
    empty.locators[".head-page__image img"] = Locator(attribute=None)
    with pytest.raises(RuntimeError, match="priva di titolo"):
        run(autodoc_sync._extract_vehicle_snapshot(empty, "https://source"))


class Response:
    def __init__(self, *, status=200, payload=None, text="") -> None:
        self.status = status
        self.payload = payload
        self._text = text

    async def json(self):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload

    async def text(self):
        return self._text


def _discovery_page(response_context, *, url="https://www.auto-doc.it/") -> Page:
    page = Page(url=url)
    page.response_context = response_context
    page.locators["#kba1"] = Locator()
    page.locators["[data-selector-number-button]"] = Locator()
    return page


def test_discovery_response_success_text_fallback_and_block(monkeypatch) -> None:
    async def no_prepare(_page, _url):
        return None

    async def no_cookies(_page):
        return None

    monkeypatch.setattr(autodoc_sync, "_prepare_page", no_prepare)
    monkeypatch.setattr(autodoc_sync, "_dismiss_cookie_overlays", no_cookies)
    with pytest.raises(RuntimeError, match="Targa"):
        run(autodoc_sync._discover_vehicle_url_by_plate(Page(), "---"))

    response = Response(payload={"url": "/ricambi-auto/fiat"})
    page = _discovery_page(ResponseContext(response))
    assert run(autodoc_sync._discover_vehicle_url_by_plate(page, "ab123cd")) == "https://www.auto-doc.it/ricambi-auto/fiat"

    text_response = Response(payload=ValueError("not json"), text="/ricambi-auto/text")
    page = _discovery_page(ResponseContext(text_response))
    assert run(autodoc_sync._discover_vehicle_url_by_plate(page, "ab123cd")) == "https://www.auto-doc.it/ricambi-auto/text"

    blocked = _discovery_page(ResponseContext(Response(status=403, payload={})))
    with pytest.raises(RuntimeError, match=r"Cloudflare \(403\)"):
        run(autodoc_sync._discover_vehicle_url_by_plate(blocked, "ab123cd"))


def test_discovery_timeout_uses_navigation_or_reports_no_result(monkeypatch) -> None:
    async def no_prepare(_page, _url):
        return None

    async def no_cookies(_page):
        return None

    monkeypatch.setattr(autodoc_sync, "_prepare_page", no_prepare)
    monkeypatch.setattr(autodoc_sync, "_dismiss_cookie_overlays", no_cookies)
    navigated = _discovery_page(
        ResponseContext(timeout=True),
        url="https://www.auto-doc.it/ricambi-auto/navigated",
    )
    assert run(autodoc_sync._discover_vehicle_url_by_plate(navigated, "ab123cd")) == navigated.url

    response_without_url = _discovery_page(
        ResponseContext(Response(payload={})),
        url="https://www.auto-doc.it/ricambi-auto/from-page",
    )
    assert (
        run(autodoc_sync._discover_vehicle_url_by_plate(response_without_url, "ab123cd"))
        == response_without_url.url
    )

    delayed = _discovery_page(ResponseContext(timeout=True))

    async def navigate_after_wait(_milliseconds):
        delayed.url = "https://www.auto-doc.it/ricambi-auto/delayed"

    delayed.wait_for_timeout = navigate_after_wait
    assert run(autodoc_sync._discover_vehicle_url_by_plate(delayed, "ab123cd")) == delayed.url

    transient = _discovery_page(
        ResponseContext(timeout=True),
        url="https://www.auto-doc.it/ricambi-auto/transient",
    )
    coerced_values = iter((None, transient.url))
    original_coerce = autodoc_sync._coerce_autodoc_url
    monkeypatch.setattr(
        autodoc_sync,
        "_coerce_autodoc_url",
        lambda _value: next(coerced_values),
    )
    assert run(autodoc_sync._discover_vehicle_url_by_plate(transient, "ab123cd")) == transient.url
    monkeypatch.setattr(autodoc_sync, "_coerce_autodoc_url", original_coerce)

    monkeypatch.setattr(autodoc_sync, "AUTODOC_DISCOVERY_SETTLE_TIMEOUT_MS", 0)
    missing = _discovery_page(ResponseContext(timeout=True))
    with pytest.raises(RuntimeError, match="Nessun risultato"):
        run(autodoc_sync._discover_vehicle_url_by_plate(missing, "ab123cd"))


def test_build_and_close_browser(monkeypatch) -> None:
    calls: list[object] = []

    class FakePage:
        def set_default_timeout(self, value):
            calls.append(("timeout", value))

    class Context:
        async def add_init_script(self, script):
            calls.append(("script", script))

        async def new_page(self):
            return FakePage()

        async def close(self):
            calls.append("context.close")

    class Browser:
        async def new_context(self, **kwargs):
            calls.append(("context", kwargs))
            return Context()

        async def close(self):
            calls.append("browser.close")

    class Chromium:
        async def launch(self, **kwargs):
            calls.append(("launch", kwargs))
            return Browser()

    class Playwright:
        chromium = Chromium()

        async def stop(self):
            calls.append("playwright.stop")

    class Starter:
        async def start(self):
            return Playwright()

    monkeypatch.setattr(autodoc_sync, "async_playwright", lambda: Starter())
    playwright, browser, context, page = run(autodoc_sync._build_browser())
    assert page is not None
    run(autodoc_sync._close_browser(playwright, browser, context))
    assert calls[-3:] == ["context.close", "browser.close", "playwright.stop"]


class ScalarResult:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values


class FakeDb:
    def __init__(self, job, vehicles):
        self.job = job
        self.vehicles = vehicles
        self.commits = 0
        self.closed = False

    def get(self, _model, _identifier):
        return self.job

    def scalars(self, _statement):
        return ScalarResult(self.vehicles)

    def commit(self):
        self.commits += 1

    def close(self):
        self.closed = True


def _job(vehicle_ids, *, entity=autodoc_sync.AUTODOC_SYNC_ENTITY, force_refresh=False):
    return SimpleNamespace(
        entity=entity,
        params_json={
            "vehicle_ids": [str(item) for item in vehicle_ids] + [""],
            "force_refresh": force_refresh,
        },
        status="queued",
        finished_at=None,
        records_synced=None,
        records_skipped=None,
        records_errors=None,
        error_detail=None,
    )


def _vehicle(identifier, **overrides):
    values = {
        "id": identifier,
        "name": f"Vehicle {identifier}",
        "code": str(identifier)[:8],
        "plate_number": None,
        "autodoc_url": None,
        "autodoc_synced_at": None,
        "autodoc_data": None,
        "autodoc_sync_error": None,
        "autodoc_title": None,
        "brand": None,
        "fuel_type": None,
        "year_of_manufacture": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_job_returns_for_missing_wrong_and_completes_empty_selection() -> None:
    for job in (None, _job([], entity="other")):
        db = FakeDb(job, [])
        run(
            autodoc_sync.run_autodoc_sync_job_by_id(
                lambda current_db=db: current_db,
                uuid.uuid4(),
            )
        )
        assert db.closed is True

    job = _job([])
    db = FakeDb(job, [])
    run(autodoc_sync.run_autodoc_sync_job_by_id(lambda: db, uuid.uuid4()))
    assert job.status == "completed"
    assert job.records_synced == 0
    assert job.records_skipped == 0
    assert job.records_errors == 0
    assert db.closed is True


def test_job_covers_skip_discovery_sync_error_and_browser_cleanup(monkeypatch) -> None:
    identifiers = [uuid.uuid4() for _ in range(5)]
    vehicles = [
        _vehicle(identifiers[0]),
        _vehicle(
            identifiers[1],
            autodoc_url="https://saved/already",
            autodoc_synced_at=datetime.now(timezone.utc),
            autodoc_data={"cached": True},
        ),
        _vehicle(identifiers[2], autodoc_url="https://saved/success"),
        _vehicle(
            identifiers[3],
            plate_number="AB123CD",
            brand="Existing",
            fuel_type="Existing",
            year_of_manufacture=2020,
        ),
        _vehicle(identifiers[4], autodoc_url="https://saved/failure"),
    ]
    job = _job(identifiers)
    db = FakeDb(job, vehicles)
    browser_parts = (object(), object(), object(), object())
    closed: list[tuple[object, ...]] = []

    async def build_browser():
        return browser_parts

    async def close_browser(*parts):
        closed.append(parts)

    async def discover(_page, _plate):
        return "https://discovered/success"

    async def extract(_page, url):
        if url.endswith("failure"):
            raise RuntimeError("snapshot failed")
        return "Vehicle title", {
            "Marca": "Fiat",
            "Carburante": "Diesel",
            "Anno da": "2012",
        }

    monkeypatch.setattr(autodoc_sync, "AUTODOC_ENABLE_PLATE_DISCOVERY", True)
    monkeypatch.setattr(autodoc_sync, "_build_browser", build_browser)
    monkeypatch.setattr(autodoc_sync, "_close_browser", close_browser)
    monkeypatch.setattr(autodoc_sync, "_discover_vehicle_url_by_plate", discover)
    monkeypatch.setattr(autodoc_sync, "_extract_vehicle_snapshot", extract)

    run(autodoc_sync.run_autodoc_sync_job_by_id(lambda: db, uuid.uuid4()))

    assert job.status == "completed"
    assert job.records_synced == 2
    assert job.records_skipped == 2
    assert job.records_errors == 1
    assert "snapshot failed" in job.error_detail
    assert vehicles[0].autodoc_sync_error.startswith("Link AUTODOC mancante")
    assert vehicles[2].brand == "Fiat"
    assert vehicles[2].fuel_type == "Diesel"
    assert vehicles[2].year_of_manufacture == 2012
    assert vehicles[3].autodoc_url == "https://discovered/success"
    assert closed == [browser_parts[:3]]
    assert db.closed is True


def test_job_is_failed_when_every_attempt_errors(monkeypatch) -> None:
    identifier = uuid.uuid4()
    vehicle = _vehicle(identifier, autodoc_url="https://saved/failure")
    job = _job([identifier], force_refresh=True)
    db = FakeDb(job, [vehicle])

    async def build_browser():
        return object(), object(), object(), object()

    async def close_browser(*_parts):
        return None

    async def fail_snapshot(_page, _url):
        raise RuntimeError("all failed")

    monkeypatch.setattr(autodoc_sync, "_build_browser", build_browser)
    monkeypatch.setattr(autodoc_sync, "_close_browser", close_browser)
    monkeypatch.setattr(autodoc_sync, "_extract_vehicle_snapshot", fail_snapshot)

    run(autodoc_sync.run_autodoc_sync_job_by_id(lambda: db, uuid.uuid4()))

    assert job.status == "failed"
    assert job.records_errors == 1
