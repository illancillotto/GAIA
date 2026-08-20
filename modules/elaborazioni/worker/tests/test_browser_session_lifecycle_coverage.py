from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


WORKER_ROOT = Path(__file__).resolve().parents[1]
if str(WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKER_ROOT))

import browser_session as browser_module
from browser_session import BrowserSession, BrowserSessionConfig
from browser_test_support import (
    ScriptedLocator,
    ScriptedPage,
    false_async,
    make_session,
    noop_async,
    true_async,
)
from sister_exceptions import SisterConventionSelectionError, SisterServerError


def run(coro):
    return asyncio.run(coro)


class FakeContext:
    def __init__(self, page: ScriptedPage) -> None:
        self.page = page
        self.routes: list[str] = []
        self.closed = False

    async def route(self, pattern: str, _handler) -> None:
        self.routes.append(pattern)

    async def new_page(self) -> ScriptedPage:
        return self.page

    async def close(self) -> None:
        self.closed = True


class FakeBrowser:
    def __init__(self, context: FakeContext) -> None:
        self.context = context
        self.closed = False

    async def new_context(self, **_kwargs) -> FakeContext:
        return self.context

    async def close(self) -> None:
        self.closed = True


class FakePlaywright:
    def __init__(self, browser: FakeBrowser) -> None:
        self.browser = browser
        self.stopped = False
        self.chromium = SimpleNamespace(launch=self.launch)

    async def launch(self, **_kwargs) -> FakeBrowser:
        return self.browser

    async def stop(self) -> None:
        self.stopped = True


class FakePlaywrightManager:
    def __init__(self, playwright: FakePlaywright) -> None:
        self.playwright = playwright

    async def start(self) -> FakePlaywright:
        return self.playwright


def test_lifecycle_start_initialize_and_stop(monkeypatch: pytest.MonkeyPatch) -> None:
    page = ScriptedPage()
    context = FakeContext(page)
    browser = FakeBrowser(context)
    playwright = FakePlaywright(browser)
    monkeypatch.setattr(browser_module, "async_playwright", lambda: FakePlaywrightManager(playwright))
    session = BrowserSession(BrowserSessionConfig())
    session._trace_state = noop_async

    run(session.start())
    run(session.stop())

    assert page.default_timeout == 60000
    assert context.routes == ["**/etws-analytics.sogei.it/**"]
    assert context.closed and browser.closed and playwright.stopped


def test_lifecycle_empty_guards_and_page_property() -> None:
    session = BrowserSession(BrowserSessionConfig())
    with pytest.raises(RuntimeError, match="page not initialized"):
        _ = session.page
    with pytest.raises(RuntimeError, match="context not initialized"):
        run(session._initialize_page())
    run(session.stop())


def test_authentication_reuse_and_login_fallback() -> None:
    session = make_session()
    calls: list[tuple[str, str]] = []

    async def login(username: str, password: str) -> None:
        calls.append((username, password))

    session.login = login
    session._session_state.authenticate(
        "cached",
        session.selectors.convention_id,
        datetime.now(timezone.utc) + timedelta(minutes=1),
    )
    run(session.ensure_authenticated("cached", "secret"))
    run(session.ensure_authenticated("new", "secret"))
    assert calls == [("new", "secret")]


def test_open_and_prepare_visura_area_branches() -> None:
    session = make_session()
    session._maybe_accept_privacy_notice = noop_async
    session._goto_visura_menu_with_retry = noop_async
    session._confirm_visura_informativa_if_present = noop_async
    session._select_convention_if_present = true_async
    session._is_visura_area_ready = false_async
    with pytest.raises(SisterConventionSelectionError):
        run(session._open_authenticated_visura_area())
    run(session._prepare_visura_form_area())

    session._is_visura_area_ready = true_async
    run(session._open_authenticated_visura_area())
    run(session._prepare_visura_form_area())


def _probe_session(page: ScriptedPage) -> BrowserSession:
    session = make_session(page)
    page.roles[("link", session.selectors.consultazioni_link_name)] = ScriptedLocator()
    session._maybe_click_xpath = noop_async
    session._open_authenticated_visura_area = noop_async
    session.logout = noop_async
    return session


def test_connection_probe_locked_and_timeout_paths() -> None:
    page = ScriptedPage()
    session = _probe_session(page)

    async def locked() -> str:
        return "locked"

    session._wait_for_post_login_state = locked
    result = run(session.test_connection("user", "password"))
    assert result.reachable and not result.authenticated
    assert "SISTER_SESSION_LOCKED" in result.message

    async def timeout() -> str:
        raise browser_module.TimeoutError("timeout")

    session._wait_for_post_login_state = timeout
    original_timeout_result = session._connection_probe_timeout_result
    timeout_helper_calls: list[tuple[bool, bool]] = []

    async def delayed_timeout_result(reachable: bool, authenticated: bool):
        timeout_helper_calls.append((reachable, authenticated))
        await asyncio.sleep(0)
        return await original_timeout_result(reachable, authenticated)

    session._connection_probe_timeout_result = delayed_timeout_result
    result = run(session.test_connection("user", "password"))
    assert result.reachable and not result.authenticated
    assert timeout_helper_calls == [(True, False)]


def test_connection_probe_result_helpers_cover_authenticated_logout(monkeypatch: pytest.MonkeyPatch) -> None:
    session = make_session(ScriptedPage(url="https://sister", title="Portale", body="body"))
    session.config = BrowserSessionConfig(debug_artifacts_path=None)
    session.logout = noop_async
    timeout_result = run(session._connection_probe_timeout_result(True, True))
    error_result = run(session._connection_probe_error_result(True, True, RuntimeError("boom")))
    assert "logout finale" in timeout_result.message
    assert "boom" in error_result.message

    session._read_page_state = lambda: _async_value(("url", "title", "credenziali errate"))
    plain_timeout = run(session._connection_probe_timeout_result(False, False))
    plain_error = run(session._connection_probe_error_result(False, False, RuntimeError("x")))
    assert "Credenziali" in plain_timeout.message
    assert "Credenziali" in plain_error.message


async def _async_value(value):
    return value


def _login_session(*, debug_pause: bool = False) -> BrowserSession:
    session = make_session(ScriptedPage())
    session.config = BrowserSessionConfig(debug_pause=debug_pause)
    session._maybe_click_xpath = noop_async
    session._open_authenticated_visura_area = noop_async
    session._collect_debug_context = lambda *_args: _async_value("debug")
    session._read_page_state = lambda: _async_value(("url", "title", "body"))
    return session


def test_login_success_pause_and_locked_recovery() -> None:
    session = _login_session(debug_pause=True)
    states = iter(("locked", "ready"))
    session._wait_for_post_login_state = lambda: _async_value(next(states))
    recovered: list[bool] = []

    async def recover() -> None:
        recovered.append(True)

    session._recover_locked_session = recover
    run(session.login("user", "password"))
    assert recovered == [True]
    assert session.page.paused
    assert session._session_state.username == "user"

    session = _login_session()
    session._wait_for_post_login_state = lambda: _async_value("locked")
    session._raise_locked_session_error = lambda *_args: _raise_async(RuntimeError("SISTER_SESSION_LOCKED"))
    with pytest.raises(RuntimeError, match="SISTER_SESSION_LOCKED"):
        run(session.login("user", "password", allow_session_recovery=False))


async def _raise_async(exc: Exception):
    raise exc


@pytest.mark.parametrize(
    ("allow_recovery", "body", "expected"),
    [
        (True, "Utente gia' in sessione", None),
        (False, "Utente gia' in sessione", "SISTER_SESSION_LOCKED"),
        (False, "credenziali errate", "Credenziali SISTER"),
        (False, "pagina generica", "Login timeout"),
    ],
)
def test_login_timeout_classification(
    monkeypatch: pytest.MonkeyPatch,
    allow_recovery: bool,
    body: str,
    expected: str | None,
) -> None:
    session = _login_session()
    session._wait_for_post_login_state = lambda: _raise_async(browser_module.TimeoutError("timeout"))
    session._read_page_state = lambda: _async_value(("url", "title", body))
    session._recover_locked_session = noop_async
    if allow_recovery:
        states = iter((browser_module.TimeoutError("timeout"), "ready"))

        async def wait_state():
            value = next(states)
            if isinstance(value, Exception):
                raise value
            return value

        session._wait_for_post_login_state = wait_state
        run(session.login("user", "password", allow_session_recovery=True))
        return
    if expected == "SISTER_SESSION_LOCKED":
        session._raise_locked_session_error = lambda *_args: _raise_async(RuntimeError(expected))
    with pytest.raises(RuntimeError, match=expected):
        run(session.login("user", "password", allow_session_recovery=False))


def test_handle_login_exception_classification() -> None:
    session = _login_session()
    server_error = SisterServerError("500")
    with pytest.raises(SisterServerError):
        run(session._handle_login_exception("u", "p", True, server_error))
    with pytest.raises(RuntimeError, match="SISTER_SESSION_LOCKED"):
        run(session._handle_login_exception("u", "p", True, RuntimeError("SISTER_SESSION_LOCKED")))

    session._read_page_state = lambda: _async_value(("url", "title", "Utente gia' in sessione"))
    session._recover_locked_session = noop_async
    session.login = noop_async
    run(session._handle_login_exception("u", "p", True, RuntimeError("x")))

    session._raise_locked_session_error = lambda *_args: _raise_async(RuntimeError("SISTER_SESSION_LOCKED"))
    with pytest.raises(RuntimeError, match="SISTER_SESSION_LOCKED"):
        run(session._handle_login_exception("u", "p", False, RuntimeError("x")))

    session._read_page_state = lambda: _async_value(("url", "title", "generic"))
    with pytest.raises(RuntimeError, match="login failed"):
        run(session._handle_login_exception("u", "p", False, RuntimeError("boom")))


def test_logout_direct_and_link_paths() -> None:
    session = make_session(ScriptedPage())
    session._click_close_sessions_link = false_async
    run(session.logout())
    assert session.page.gotos
    session._click_close_sessions_link = true_async
    session.page.gotos.clear()
    run(session.logout())
    assert not session.page.gotos


def test_post_login_state_variants(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(browser_module.asyncio, "sleep", noop_async)
    session = make_session()
    session._raise_if_server_error = noop_async
    for state, page_state in (
        ("ready", ("url", "Home dei Servizi", "")),
        ("privacy", ("url", "title", "Informativa trattamento dei dati personali")),
        ("locked", ("error_locked.jsp", "title", "")),
    ):
        session._read_page_state = lambda value=page_state: _async_value(value)
        assert run(session._wait_for_post_login_state()) == state
    session._read_page_state = lambda: _async_value(("url", "title", "body"))
    assert run(session._wait_for_post_login_state()) == "unknown"


def test_debug_state_helpers_and_locked_error(tmp_path: Path) -> None:
    page = ScriptedPage(url="https://x", title="Title", body="many   spaces")
    session = make_session(page, debug_path=tmp_path)
    session._trace_state = browser_module.BrowserSession._trace_state.__get__(session)
    run(session._trace_state("label"))
    context = run(session._collect_debug_context("reason"))
    assert "artifacts=" in context and "body=many spaces" in context

    session.config = BrowserSessionConfig(debug_artifacts_path=None)
    run(session._trace_state("plain"))
    context = run(session._collect_debug_context("reason", "u", "t", ""))
    assert context == "url=u | title=t"
    with pytest.raises(RuntimeError, match="SISTER_SESSION_LOCKED"):
        run(session._raise_locked_session_error("locked"))
    with pytest.raises(RuntimeError, match="SISTER_SESSION_LOCKED"):
        run(session._raise_locked_session_error("locked", ValueError("cause")))


def test_read_page_state_failures_and_issue_helpers() -> None:
    class BrokenPage(ScriptedPage):
        @property
        def url(self):
            raise RuntimeError("url")

        @url.setter
        def url(self, _value):
            return None

    page = BrokenPage()
    page.title_error = RuntimeError("title")
    page.body_error = RuntimeError("body")
    session = make_session(page)
    assert run(session._read_page_state()) == ("unknown", "unknown", "")
    assert not session._is_session_locked_issue(None)
    assert session._is_session_locked_issue("Utente già in sessione")
    assert session._classify_login_issue("", "", "altra postazione")
    assert session._classify_login_issue("error_locked.jsp", "", "")
    assert session._classify_login_issue("", "", "credenziali non valide")
    assert session._classify_login_issue("", "", "ok") is None


def test_debug_artifact_success_and_failures(tmp_path: Path) -> None:
    session = make_session(ScriptedPage(), debug_path=tmp_path)
    artifacts = run(session._write_debug_artifacts("reason"))
    assert len(artifacts) == 2

    session.page.screenshot_error = RuntimeError("shot")
    session.page.content_error = RuntimeError("html")
    assert run(session._write_artifacts_to_dir(tmp_path / "broken", "reason")) == []
