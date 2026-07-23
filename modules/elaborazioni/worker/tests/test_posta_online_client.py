from __future__ import annotations

import asyncio
from pathlib import Path
import sys
import types

import pytest


WORKER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = next((path for path in WORKER_ROOT.parents if (path / "backend").exists()), WORKER_ROOT.parents[-1])
BACKEND_ROOT = REPO_ROOT / "backend"

for path in (WORKER_ROOT, REPO_ROOT, BACKEND_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

playwright_module = types.ModuleType("playwright")
playwright_async_api = types.ModuleType("playwright.async_api")
playwright_async_api.Browser = object
playwright_async_api.BrowserContext = object
playwright_async_api.Page = object
playwright_async_api.Playwright = object
playwright_async_api.TimeoutError = TimeoutError
playwright_async_api.async_playwright = lambda: None
playwright_module.async_api = playwright_async_api
sys.modules.setdefault("playwright", playwright_module)
sys.modules.setdefault("playwright.async_api", playwright_async_api)

import posta_online_client
from posta_online_client import (
    POSTA_ONLINE_ARCHIVE_URL,
    POSTA_ONLINE_CONTACTS_URL,
    POSTA_ONLINE_DETAIL_URL,
    POSTA_ONLINE_LOGIN_URL,
    PoliteThrottle,
    PostaOnlineBrowserClient,
    PostaOnlineScrapeConfig,
    _diagnose_login_failure,
    _extract_invio_ids,
    _suppress_scrape_error,
)


class FakeResponse:
    def __init__(self, status: int, payload=None, text: str = "") -> None:
        self.status = status
        self.payload = payload
        self._text = text

    async def json(self):
        return self.payload

    async def text(self) -> str:
        return self._text


class FakeLocator:
    def __init__(
        self,
        *,
        count: int = 1,
        text: str = "",
        href: str | None = "#",
        timeout_on_click: bool = False,
    ) -> None:
        self._count = count
        self.text = text
        self.href = href
        self.timeout_on_click = timeout_on_click
        self.filled: list[str] = []
        self.clicked = False
        self.evaluated: list[str] = []

    @property
    def first(self) -> "FakeLocator":
        return self

    @property
    def last(self) -> "FakeLocator":
        return self

    def filter(self, **_kwargs) -> "FakeLocator":
        return self

    async def count(self) -> int:
        return self._count

    async def fill(self, value: str) -> None:
        self.filled.append(value)

    async def click(self, **_kwargs) -> None:
        if self.timeout_on_click:
            raise TimeoutError("timeout")
        self.clicked = True

    async def is_visible(self, **_kwargs) -> bool:
        return self._count > 0

    async def wait_for(self, **_kwargs) -> None:
        return None

    async def evaluate(self, expression: str) -> None:
        self.evaluated.append(expression)

    async def get_attribute(self, name: str) -> str | None:
        return self.href if name == "href" else None

    async def inner_text(self, **_kwargs) -> str:
        return self.text


class FakePage:
    def __init__(self, *, body_text: str = "Archivio", html_pages: list[str] | None = None) -> None:
        self.url = POSTA_ONLINE_ARCHIVE_URL
        self.body = FakeLocator(text=body_text)
        self.html_pages = html_pages or []
        self.goto_calls: list[str] = []
        self.state_calls: list[str] = []
        self.timeout_waits: list[int] = []
        self.default_timeout: int | None = None
        self.locators: dict[str, FakeLocator] = {
            "input[name='username']": FakeLocator(),
            "input[name='password']": FakeLocator(),
            "button[type='submit']": FakeLocator(),
            "body": self.body,
            "ul.pagination a": FakeLocator(count=0),
        }

    def set_default_timeout(self, timeout: int) -> None:
        self.default_timeout = timeout

    async def goto(self, url: str, **_kwargs) -> None:
        self.goto_calls.append(url)
        self.url = url

    async def wait_for_load_state(self, state: str) -> None:
        self.state_calls.append(state)

    async def wait_for_timeout(self, timeout: int) -> None:
        self.timeout_waits.append(timeout)

    async def content(self) -> str:
        if self.html_pages:
            return self.html_pages.pop(0)
        return ""

    def locator(self, selector: str) -> FakeLocator:
        return self.locators.get(selector, FakeLocator(count=0))


def test_polite_throttle_clamps_and_waits(monkeypatch: pytest.MonkeyPatch) -> None:
    delays: list[float] = []
    monkeypatch.setattr(posta_online_client.random, "randint", lambda left, right: right)

    async def fake_sleep(delay: float) -> None:
        delays.append(delay)

    monkeypatch.setattr(posta_online_client.asyncio, "sleep", fake_sleep)
    throttle = PoliteThrottle(min_delay_ms=10, max_delay_ms=5)

    asyncio.run(throttle.wait("unit"))

    assert throttle.min_delay_ms == 1000
    assert throttle.max_delay_ms == 1000
    assert delays == [1.0]


def test_browser_client_context_manager_and_uninitialized_properties(monkeypatch: pytest.MonkeyPatch) -> None:
    page = FakePage()
    events: list[str] = []

    class FakeContext:
        async def new_page(self):
            events.append("new_page")
            return page

        async def close(self):
            events.append("context_close")

    class FakeBrowser:
        async def new_context(self, **kwargs):
            events.append(f"context:{kwargs['accept_downloads']}")
            return FakeContext()

        async def close(self):
            events.append("browser_close")

    class FakeChromium:
        async def launch(self, **kwargs):
            events.append(f"launch:{kwargs['headless']}")
            return FakeBrowser()

    class FakePlaywright:
        chromium = FakeChromium()

        async def stop(self):
            events.append("stop")

    class FakePlaywrightStarter:
        async def start(self):
            events.append("start")
            return FakePlaywright()

    monkeypatch.setattr(posta_online_client, "async_playwright", lambda: FakePlaywrightStarter())
    client = PostaOnlineBrowserClient(PostaOnlineScrapeConfig(headless=False))
    with pytest.raises(RuntimeError, match="Pagina Poste Online non inizializzata"):
        _ = client.page
    with pytest.raises(RuntimeError, match="Context Poste Online non inizializzato"):
        _ = client.context

    async def run_context() -> None:
        async with client as entered:
            assert entered.page is page
            assert entered.context is not None

    asyncio.run(run_context())

    assert page.default_timeout == 60000
    assert events == ["start", "launch:False", "context:False", "new_page", "context_close", "browser_close", "stop"]


def test_login_success_and_interactive_failure() -> None:
    client = PostaOnlineBrowserClient(PostaOnlineScrapeConfig())
    page = FakePage(body_text="Archivio spedizioni")
    client._page = page
    waits: list[str] = []

    async def fake_wait(label: str) -> None:
        waits.append(label)

    client.throttle.wait = fake_wait

    asyncio.run(client.login("user", "secret"))

    assert page.goto_calls == [POSTA_ONLINE_LOGIN_URL, POSTA_ONLINE_ARCHIVE_URL]
    assert page.locators["input[name='username']"].filled == ["user"]
    assert page.locators["input[name='password']"].filled == ["secret"]
    assert page.locators["button[type='submit']"].clicked is True
    assert waits == ["post-login"]

    interactive = PostaOnlineBrowserClient(PostaOnlineScrapeConfig())
    interactive._page = FakePage(body_text="Inserisci OTP PosteID")
    interactive.throttle.wait = fake_wait
    with pytest.raises(RuntimeError, match="autenticazione interattiva"):
        asyncio.run(interactive.login("user", "secret"))


def test_login_helpers_raise_when_fields_or_archive_are_missing() -> None:
    page = FakePage()
    with pytest.raises(RuntimeError, match="Campo login"):
        asyncio.run(PostaOnlineBrowserClient._fill_first_available(page, ["missing"], "x"))
    with pytest.raises(RuntimeError, match="Pulsante login"):
        asyncio.run(PostaOnlineBrowserClient._click_first_available(page, ["missing"]))

    page.url = POSTA_ONLINE_LOGIN_URL
    page.body.text = "Accedi"
    with pytest.raises(RuntimeError, match="Archivio Poste Online non raggiunto"):
        asyncio.run(PostaOnlineBrowserClient._ensure_authenticated_archive(page))


def test_login_page_preparation_handles_trustarc_overlays() -> None:
    page = FakePage()
    consent = FakeLocator()
    overlay = FakeLocator()
    page.locators["#truste-consent-button"] = consent
    page.locators["#trustarc-banner-overlay"] = overlay

    asyncio.run(PostaOnlineBrowserClient._prepare_login_page(page))

    assert consent.clicked is True
    assert page.timeout_waits == [500]

    blocked_page = FakePage()
    blocked_overlay = FakeLocator()
    blocked_page.locators["#trustarc-banner-overlay"] = blocked_overlay

    asyncio.run(PostaOnlineBrowserClient._prepare_login_page(blocked_page))

    assert blocked_overlay.evaluated == ["element => element.style.pointerEvents = 'none'"]


def test_fetch_contacts_detail_and_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps: list[int] = []

    async def fake_sleep(delay: int) -> None:
        sleeps.append(delay)

    monkeypatch.setattr(posta_online_client.asyncio, "sleep", fake_sleep)

    class FakeRequest:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        async def post(self, url: str, **kwargs):
            self.calls.append({"url": url, **kwargs})
            if url == POSTA_ONLINE_CONTACTS_URL:
                return FakeResponse(200, payload=[{"id": "1"}, "bad"])
            if url == POSTA_ONLINE_DETAIL_URL:
                return FakeResponse(200, text="<html>detail</html>")
            return FakeResponse(404)

    request = FakeRequest()
    client = PostaOnlineBrowserClient(PostaOnlineScrapeConfig())
    client._context = types.SimpleNamespace(request=request)

    assert asyncio.run(client.fetch_contacts()) == [{"id": "1"}]
    assert asyncio.run(client.fetch_detail_html("11280322")) == "<html>detail</html>"
    assert request.calls[0]["url"] == POSTA_ONLINE_CONTACTS_URL
    assert request.calls[1]["url"] == POSTA_ONLINE_DETAIL_URL

    responses = iter([FakeResponse(429), FakeResponse(503), FakeResponse(200, text="ok")])

    async def retry_factory():
        return next(responses)

    result = asyncio.run(client._request_with_backoff("retry", retry_factory))
    assert result.status == 200
    assert sleeps == [30, 60]

    async def forbidden_factory():
        return FakeResponse(403)

    async def throttled_factory():
        return FakeResponse(429)

    with pytest.raises(RuntimeError, match="HTTP 403"):
        asyncio.run(client._request_with_backoff("fatal", forbidden_factory))
    with pytest.raises(RuntimeError, match="HTTP 429"):
        asyncio.run(client._request_with_backoff("exhausted", throttled_factory))


def test_fetch_contacts_returns_empty_for_non_list_payload() -> None:
    class FakeRequest:
        async def post(self, *_args, **_kwargs):
            return FakeResponse(200, payload={"id": "not-list"})

    client = PostaOnlineBrowserClient(PostaOnlineScrapeConfig())
    client._context = types.SimpleNamespace(request=FakeRequest())

    assert asyncio.run(client.fetch_contacts()) == []


def test_discover_archive_invii_and_pagination_branches() -> None:
    client = PostaOnlineBrowserClient(PostaOnlineScrapeConfig(max_pages=2, max_details=3))
    page = FakePage(
        html_pages=[
            "idInvio=1111 idInvio=1111 id_invio:2222",
            "idInvio=3333 idInvio=4444",
        ]
    )
    page.locators["ul.pagination a"] = FakeLocator(href="/next")
    client._page = page
    client.throttle.wait = lambda _label: asyncio.sleep(0)

    assert asyncio.run(client.discover_archive_invii()) == ["1111", "2222", "3333", "4444"]

    no_next_page = FakePage()
    assert asyncio.run(client._goto_next_archive_page(no_next_page)) is False

    no_href_page = FakePage()
    no_href_page.locators["ul.pagination a"] = FakeLocator(href=None)
    assert asyncio.run(client._goto_next_archive_page(no_href_page)) is False

    timeout_page = FakePage()
    timeout_page.locators["ul.pagination a"] = FakeLocator(href="/next", timeout_on_click=True)
    assert asyncio.run(client._goto_next_archive_page(timeout_page)) is False

    single_page_client = PostaOnlineBrowserClient(PostaOnlineScrapeConfig(max_pages=2, max_details=10))
    single_page = FakePage(html_pages=["idInvio=9999"])
    single_page_client._page = single_page
    single_page_client.throttle.wait = lambda _label: asyncio.sleep(0)
    assert asyncio.run(single_page_client.discover_archive_invii()) == ["9999"]


def test_scrape_registered_mails_handles_success_and_errors() -> None:
    class FakeClient(PostaOnlineBrowserClient):
        def __init__(self, config: PostaOnlineScrapeConfig) -> None:
            super().__init__(config)
            self.detail_calls: list[str] = []

        async def fetch_contacts(self):
            return [{"id": "contact"}]

        async def discover_archive_invii(self):
            return ["A", "B", "C"]

        async def fetch_detail_html(self, id_invio: str) -> str:
            self.detail_calls.append(id_invio)
            if id_invio == "B":
                raise RuntimeError("detail boom")
            return f"<html>{id_invio}</html>"

    client = FakeClient(PostaOnlineScrapeConfig(max_details=2, continue_on_error=True))
    client.throttle.wait = lambda _label: asyncio.sleep(0)
    payload = asyncio.run(client.scrape_registered_mails())

    assert payload["contacts"] == [{"id": "contact"}]
    assert payload["details"] == [{"idInvio": "A", "html": "<html>A</html>"}]
    assert payload["errors"] == [{"scope": "detail:B", "error": "detail boom"}]

    no_limit = FakeClient(PostaOnlineScrapeConfig(continue_on_error=True))
    no_limit.throttle.wait = lambda _label: asyncio.sleep(0)
    full_payload = asyncio.run(no_limit.scrape_registered_mails())
    assert no_limit.detail_calls == ["A", "B", "C"]
    assert full_payload["details"] == [
        {"idInvio": "A", "html": "<html>A</html>"},
        {"idInvio": "C", "html": "<html>C</html>"},
    ]

    failing = FakeClient(PostaOnlineScrapeConfig(max_details=2, continue_on_error=False))
    failing.throttle.wait = lambda _label: asyncio.sleep(0)
    with pytest.raises(RuntimeError, match="detail boom"):
        asyncio.run(failing.scrape_registered_mails())

    class FailingContacts(FakeClient):
        async def fetch_contacts(self):
            raise RuntimeError("contacts boom")

    contacts_error = FailingContacts(PostaOnlineScrapeConfig(include_details=False, continue_on_error=True))
    assert asyncio.run(contacts_error.scrape_registered_mails())["errors"] == [
        {"scope": "contacts", "error": "contacts boom"}
    ]


def test_static_helpers_extract_ids_interactive_and_suppress_errors() -> None:
    assert _extract_invio_ids("idInvio=12345 idInvio=12345 id_invio xyz 67890") == ["12345", "67890"]
    assert _diagnose_login_failure("https://example.test/login", "Username Password Credenziali non valide") == (
        "url=https://example.test/login; segnali=redirect_login,messaggio_login,form_login_visibile; "
        "testo=Username Password Credenziali non valide"
    )
    page = FakePage(body_text="Serve autorizza da app")
    assert asyncio.run(PostaOnlineBrowserClient._requires_interactive_authentication(page)) is True

    errors: list[dict[str, str]] = []
    with _suppress_scrape_error(errors, "scope", True):
        raise RuntimeError("boom")
    assert errors == [{"scope": "scope", "error": "boom"}]
    with pytest.raises(RuntimeError, match="boom"):
        with _suppress_scrape_error(errors, "scope", False):
            raise RuntimeError("boom")
    with _suppress_scrape_error(errors, "none", True):
        pass
