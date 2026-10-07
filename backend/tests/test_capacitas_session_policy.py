from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock

import httpx
import pytest

from app.modules.elaborazioni.capacitas import session as session_module
from app.modules.elaborazioni.capacitas.session import CapacitasSession, CapacitasSessionManager

TOKEN = "123e4567-e89b-12d3-a456-426614174000"
FORM = """<input type="hidden" name="__VIEWSTATE" id="__VIEWSTATE" value="view" />
<input type="hidden" name="__EVENTVALIDATION" id="__EVENTVALIDATION" value="validation" />
<input name="username" id="ContentMain_txtUsername" />
<input name="password" id="ContentMain_txtPassword" />
<input type="submit" name="submit" value="Accedi" id="ContentMain_btnAccedi" />
<input name="gau" id="ContentMain_txtGAUerInput" />"""


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
@pytest.mark.parametrize("result", ["url", "cookie", "html", "missing", "no_viewstate"])
async def test_login_uses_transport_and_preserves_token_sources(tmp_path, monkeypatch, result):
    requests = []

    def handler(request):
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(200, text=FORM if result != "no_viewstate" else "no form")
        if result == "url":
            return httpx.Response(
                302, headers={"location": "https://sso.example/main?token=" + TOKEN}
            )
        if result == "cookie":
            return httpx.Response(200, headers={"set-cookie": "AUTH_COOKIE=" + TOKEN})
        return httpx.Response(
            200,
            text="'token'='" + TOKEN + "'"
            if result == "html"
            else "<title>Login</title>Credenziali errate",
        )

    def redirects(request):
        if request.url.host == "sso.example":
            return httpx.Response(200, text="main")
        return handler(request)

    monkeypatch.setattr(
        session_module,
        "polite_http_client",
        lambda: httpx.AsyncClient(transport=httpx.MockTransport(redirects), follow_redirects=True),
    )
    monkeypatch.setattr(session_module.settings, "capacitas_debug_storage_path", str(tmp_path))
    manager = CapacitasSessionManager("synthetic", "synthetic")
    previous = httpx.AsyncClient()
    manager._http = previous
    keepalive = asyncio.create_task(asyncio.Event().wait())
    manager._keepalive_tasks["involture"] = keepalive
    try:
        if result in {"missing", "no_viewstate"}:
            with pytest.raises(RuntimeError, match=r"token non trovato|VIEWSTATE"):
                await manager.login()
            if result == "missing":
                assert list(tmp_path.glob("*/metadata.json"))
        else:
            assert (await manager.login()).token == TOKEN
            assert manager.get_token() == TOKEN
            assert manager.get_http_client() is manager._http
    finally:
        await manager.close()
    assert previous.is_closed
    assert keepalive.done()
    assert manager._keepalive_tasks == {}


@pytest.mark.anyio
async def test_context_and_uninitialized_session(monkeypatch):
    manager = CapacitasSessionManager("synthetic", "synthetic")
    with pytest.raises(RuntimeError, match="non inizializzata"):
        manager.get_token()
    with pytest.raises(RuntimeError, match="non inizializzata"):
        manager.get_http_client()
    with pytest.raises(RuntimeError, match="non inizializzata"):
        await manager.activate_app("involture")
    with pytest.raises(RuntimeError, match="non inizializzata"):
        await manager._resolve_app_launch_url("involture")
    await manager._keepalive_loop("involture", "https://example.invalid")
    assert manager._extract_token_from_cookies() is None
    assert manager._snapshot_cookies() == []
    assert manager._list_cookie_names() == ""
    monkeypatch.setattr(manager, "login", AsyncMock())
    monkeypatch.setattr(manager, "close", AsyncMock())
    async with manager as entered:
        assert entered is manager
    manager.login.assert_awaited_once()
    manager.close.assert_awaited_once()
    assert CapacitasSession(token=TOKEN).is_alive()
    assert not CapacitasSession(token="").is_alive()


@pytest.mark.anyio
@pytest.mark.parametrize("payload", [[], {}, ValueError("bad tiles")])
async def test_app_launch_fallback(monkeypatch, payload):
    manager = CapacitasSessionManager("synthetic", "synthetic")
    manager._session = CapacitasSession(token=TOKEN)
    manager._http = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, text="tiles"))
    )

    def decode(_payload):
        if isinstance(payload, Exception):
            raise payload
        return payload

    monkeypatch.setattr(session_module, "decode_response", decode)
    assert TOKEN in await manager._resolve_app_launch_url("involture")
    await manager.close()


def test_launch_tiles_and_html_attributes():
    from app.modules.elaborazioni.capacitas.apps import get_capacitas_app

    manager = CapacitasSessionManager("synthetic", "synthetic")
    manager._session = CapacitasSession(token=TOKEN)
    invalid = [
        "invalid",
        {},
        {"tile": 4},
        {"tile": ""},
        {"tile": "data-app='other'"},
        {"tile": "data-app='involture'"},
    ]
    tile = "data-app='involture' data-url='https://example.test/login' data-codcons='090' data-idrun='run'"
    result = manager._match_app_launch_url(
        [*invalid, {"tile": tile}], get_capacitas_app("involture")
    )
    assert result == f"https://example.test/login?token={TOKEN}&codConsApp=090&idRun=run"
    assert manager._extract_tile_attr("data-app='in&amp;volture'", "app") == "in&volture"
    assert manager._extract_tile_attr("missing", "app") == ""


@pytest.mark.anyio
@pytest.mark.parametrize("case", ["error", "missing_cookie", "cookie"])
async def test_activation_checks_portal_and_cookies(monkeypatch, case):
    manager = CapacitasSessionManager("synthetic", "synthetic")
    manager._session = CapacitasSession(token=TOKEN)
    path = "errore.aspx" if case == "error" else "main.aspx"
    monkeypatch.setattr(
        manager,
        "_resolve_app_launch_url",
        AsyncMock(return_value="https://involture.example/pages/" + path),
    )
    manager._http = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200))
    )
    if case == "cookie":
        from app.modules.elaborazioni.capacitas.apps import get_capacitas_app

        manager._http.cookies.set(get_capacitas_app("involture").auth_cookie_name, TOKEN)
    if case == "error":
        with pytest.raises(RuntimeError, match=r"errore\.aspx"):
            await manager.activate_app("involture")
    else:
        await manager.activate_app("involture")
        assert "involture" in manager._session.app_cookies
    await manager.close()


@pytest.mark.anyio
@pytest.mark.parametrize("status", [200, 503])
async def test_keepalive_interval_cancellation_and_status(monkeypatch, status):
    manager = CapacitasSessionManager("synthetic", "synthetic")
    manager._session = CapacitasSession(token=TOKEN)
    manager._http = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(status))
    )
    calls = []

    async def sleep(seconds):
        calls.append(seconds)
        if len(calls) == 2:
            raise asyncio.CancelledError()

    monkeypatch.setattr(session_module.asyncio, "sleep", sleep)
    await manager.start_keepalive("involture")
    task = manager._keepalive_tasks["involture"]
    await manager.start_keepalive("involture")
    assert manager._keepalive_tasks["involture"] is task
    with pytest.raises(asyncio.CancelledError):
        await task
    assert calls == [120, 120]
    assert ("involture" in manager._session.last_keepalive) == (status == 200)
    await manager.start_keepalive("involture")
    pending = manager._keepalive_tasks["involture"]
    manager.stop_keepalive("involture")
    with pytest.raises(asyncio.CancelledError):
        await pending
    await manager.close()
    await manager.close()
    manager.stop_keepalive("incass")


def test_form_and_token_extraction_branches(monkeypatch):
    manager = CapacitasSessionManager("synthetic", "synthetic")
    monkeypatch.setattr(session_module.settings, "capacitas_cod_cons", "")
    assert manager._build_login_url() == session_module.LOGIN_URL
    monkeypatch.setattr(session_module.settings, "capacitas_cod_cons", "090")
    assert "codCons=090" in manager._build_login_url()
    assert manager._extract_aspnet_fields(FORM) == ("view", "validation")
    assert manager._extract_aspnet_fields("") == ("", "")
    assert manager._build_login_form_data("", "synthetic", "synthetic")["__EVENTTARGET"] == ""
    alternate = '<input id="alternate" name="alt" />'
    assert manager._extract_input_name_by_id(alternate, "alternate") == "alt"
    assert manager._extract_input_name_by_id("", "alternate") == ""
    alternate_submit = '<input type="submit" id="submit" name="submitName" value="Go" />'
    assert manager._extract_submit_name_and_value(alternate_submit, "submit") == (
        "submitName",
        "Go",
    )
    assert manager._extract_submit_name_and_value("", "submit") == ("", "")
    empty_submit = '<input type="submit" name="submit" value="" id="ContentMain_btnAccedi" />'
    assert (
        manager._build_login_form_data(empty_submit, "synthetic", "synthetic")["submit"] == "Accedi"
    )
    assert manager._extract_token_from_html("none") is None
    for markup in [
        f"?token={TOKEN}",
        f"'token'='{TOKEN}'",
        f'<input name="token" value="{TOKEN}">',
        f'<input id="token" value="{TOKEN}">',
    ]:
        assert manager._extract_token_from_html(markup) == TOKEN
    response = httpx.Response(200, request=httpx.Request("GET", "https://example.test"))
    response.history = [
        httpx.Response(302, request=httpx.Request("GET", "https://example.test?token=" + TOKEN))
    ]
    assert manager._extract_token_from_response(response) == TOKEN
    response.history = []
    assert manager._extract_token_from_response(response) is None


@pytest.mark.anyio
async def test_cookie_fallbacks_and_diagnostics_artifacts(tmp_path, monkeypatch):
    manager = CapacitasSessionManager("synthetic", "synthetic")
    manager._http = httpx.AsyncClient()
    manager._http.cookies.set("other", "unrelated")
    manager._http.cookies.set("AUTH_COOKIE", "plain")
    assert manager._extract_token_from_cookies() is None
    manager._http.cookies.set("AUTH_COOKIE", "opaque|remainder")
    assert manager._extract_token_from_cookies() == "opaque"
    manager._http.cookies.set("AUTH_COOKIE", "|empty")
    assert manager._extract_token_from_cookies() is None
    manager._http.cookies.set("APP_AUTH_COOKIE", TOKEN)
    assert manager._extract_token_from_cookies() == TOKEN
    assert manager._snapshot_cookies()
    assert "APP_AUTH_COOKIE" in manager._list_cookie_names()
    html = "<title> Login &amp; errore </title> __VIEWSTATE txtUsername txtPassword token=abc credenziali errore sessione"
    response = httpx.Response(200, text=html, request=httpx.Request("GET", "https://example.test"))
    diagnostics = manager._build_login_diagnostics(response)
    assert "segnali=" in diagnostics and "snippet=" in diagnostics
    assert manager._extract_html_title(html) == "Login & errore"
    assert manager._extract_html_title("") == ""
    assert manager._extract_html_snippet("<p>plain</p>") == "plain"
    assert manager._clean_html_fragment("a" * 250).endswith("...")
    monkeypatch.setattr(session_module.settings, "capacitas_debug_storage_path", str(tmp_path))
    output = manager._write_login_debug_artifacts(response, diagnostics)
    assert json.loads((tmp_path / output / "metadata.json").read_text())["status_code"] == 200
    await manager.close()
    empty = httpx.Response(200, text="", request=httpx.Request("GET", "https://example.test"))
    assert "title=n/d" in manager._build_login_diagnostics(empty)
    assert manager._write_login_debug_artifacts(empty, "empty")
