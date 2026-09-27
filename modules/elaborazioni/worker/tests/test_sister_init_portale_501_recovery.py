from __future__ import annotations

import asyncio

import pytest
from browser_test_support import ScriptedPage, make_session
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from sister_exceptions import SisterServerError

INIT_PORTALE_ERROR = "SISTER HTTP 501 su /portale-rest/rs/initPortale"


async def value(result):
    return result


def session_with_error(monkeypatch: pytest.MonkeyPatch, error: str = INIT_PORTALE_ERROR):
    page = ScriptedPage()
    session = make_session(page)
    reloads: list[tuple[str, int]] = []

    async def reload(*, wait_until: str, timeout: int) -> None:
        reloads.append((wait_until, timeout))

    async def raise_error():
        raise SisterServerError(error)

    monkeypatch.setattr(page, "reload", reload, raising=False)
    monkeypatch.setattr(session, "_maybe_click_xpath", lambda _xpath: value(None))
    monkeypatch.setattr(session, "_open_authenticated_visura_area", lambda: value(None))
    monkeypatch.setattr(session, "_trace_state", lambda _label: value(None))
    monkeypatch.setattr(session, "_wait_for_post_login_state", raise_error)
    monkeypatch.setattr(session, "_read_page_state", lambda: value(("url", "title", "body")))
    return session, page, reloads


@pytest.mark.parametrize("after_refresh", ["ready", "privacy"])
def test_login_recovers_501_only_when_page_is_ready(
    monkeypatch: pytest.MonkeyPatch, after_refresh: str
) -> None:
    session, _page, reloads = session_with_error(monkeypatch)
    states = iter((SisterServerError(INIT_PORTALE_ERROR), after_refresh))

    async def wait_state():
        state = next(states)
        if isinstance(state, Exception):
            raise state
        return state

    monkeypatch.setattr(session, "_wait_for_post_login_state", wait_state)
    asyncio.run(session.login("user", "password"))

    assert reloads == [("domcontentloaded", 15000)]
    assert session._session_state.username == "user"


@pytest.mark.parametrize(
    ("error", "page_state", "after_refresh", "expected_reloads"),
    [
        ("SISTER HTTP 503", ("url", "title", "body"), "ready", 0),
        ("SISTER HTTP 501 su /other", ("url", "title", "body"), "ready", 0),
        (INIT_PORTALE_ERROR, ("url", "title", "credenziali errate"), "ready", 0),
        (INIT_PORTALE_ERROR, ("url", "title", "body"), "unknown", 1),
        (INIT_PORTALE_ERROR, ("url", "title", "body"), "locked", 1),
    ],
)
def test_login_preserves_error_when_501_recovery_is_unsafe(
    monkeypatch: pytest.MonkeyPatch,
    error: str,
    page_state: tuple[str, str, str],
    after_refresh: str,
    expected_reloads: int,
) -> None:
    session, _page, reloads = session_with_error(monkeypatch, error)
    states = iter((SisterServerError(error), after_refresh))

    async def wait_state():
        state = next(states)
        if isinstance(state, Exception):
            raise state
        return state

    monkeypatch.setattr(session, "_wait_for_post_login_state", wait_state)
    monkeypatch.setattr(session, "_read_page_state", lambda: value(page_state))
    with pytest.raises(SisterServerError, match="HTTP"):
        asyncio.run(session.login("user", "password"))

    assert len(reloads) == expected_reloads
    assert session._session_state.username is None


@pytest.mark.parametrize("locked_twice", [False, True])
def test_init_portale_501_uses_one_locked_session_recovery(
    monkeypatch: pytest.MonkeyPatch, locked_twice: bool
) -> None:
    session, _page, reloads = session_with_error(monkeypatch)
    recovery_calls: list[bool] = []
    states = iter(
        (
            SisterServerError(INIT_PORTALE_ERROR),
            SisterServerError(INIT_PORTALE_ERROR) if locked_twice else "ready",
        )
    )

    async def wait_state():
        state = next(states)
        if isinstance(state, Exception):
            raise state
        return state

    async def recover() -> None:
        recovery_calls.append(True)

    monkeypatch.setattr(session, "_wait_for_post_login_state", wait_state)
    monkeypatch.setattr(
        session, "_read_page_state", lambda: value(("error_locked.jsp", "Utente bloccato", "body"))
    )
    monkeypatch.setattr(session, "_recover_locked_session", recover)

    if locked_twice:
        with pytest.raises(RuntimeError, match="SISTER_SESSION_LOCKED"):
            asyncio.run(session.login("user", "password"))
        assert session._session_state.username is None
    else:
        asyncio.run(session.login("user", "password"))
        assert session._session_state.username == "user"

    assert recovery_calls == [True]
    assert reloads == []


def test_init_portale_501_does_not_repeat_locked_recovery(monkeypatch: pytest.MonkeyPatch) -> None:
    session, _page, reloads = session_with_error(monkeypatch)
    monkeypatch.setattr(
        session, "_read_page_state", lambda: value(("error_locked.jsp", "Utente bloccato", "body"))
    )

    with pytest.raises(RuntimeError, match="SISTER_SESSION_LOCKED"):
        asyncio.run(session.login("user", "password", allow_session_recovery=False))

    assert reloads == []


def test_login_keeps_original_501_when_refresh_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    session, page, _reloads = session_with_error(monkeypatch)

    async def timeout(*, wait_until: str, timeout: int) -> None:
        raise PlaywrightTimeoutError("timeout")

    monkeypatch.setattr(page, "reload", timeout)
    with pytest.raises(SisterServerError, match="initPortale"):
        asyncio.run(session.login("user", "password"))

    assert session._session_state.username is None
