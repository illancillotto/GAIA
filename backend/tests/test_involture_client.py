from __future__ import annotations

import base64
import json
import zlib

import httpx
import pytest

from app.modules.elaborazioni.capacitas.apps.involture import client as involture
from app.modules.elaborazioni.capacitas.apps.involture.client import (
    CapacitasSessionExpiredError,
    InVoltureClient,
    _is_retryable_invalid_certificato,
    _is_session_expired_text,
    _parse_search_result,
)
from app.modules.elaborazioni.capacitas.models import (
    CapacitasTerreniSearchRequest,
    CapacitasTerrenoCertificato,
)
from app.modules.elaborazioni.capacitas.session import CapacitasSession, CapacitasSessionManager


def _encoded(payload: object) -> str:
    compressor = zlib.compressobj(wbits=-15)
    raw = compressor.compress(json.dumps(payload).encode()) + compressor.flush()
    return base64.b64encode(raw).decode()


def _client(handler) -> tuple[InVoltureClient, CapacitasSessionManager]:
    manager = CapacitasSessionManager("user", "pass")
    manager._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    manager._session = CapacitasSession(token="tok-123")
    return InVoltureClient(manager), manager


def _always(text: str):
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=text)

    return handler


@pytest.mark.parametrize(
    ("text", "expired"),
    [
        ("NOSessione scaduta", True),
        ("NOSessione+scaduta", True),
        ("  Sessione   scaduta per inattività", True),
        ("NOErrore generico", False),
        ("[]", False),
    ],
)
def test_is_session_expired_text(text: str, expired: bool) -> None:
    assert _is_session_expired_text(text) is expired


@pytest.mark.anyio
async def test_relogin_renews_session_and_keepalive(monkeypatch) -> None:
    calls: list[str] = []
    client, manager = _client(_always(""))

    async def login():
        calls.append("login")

    async def activate_app(app: str):
        calls.append(f"activate:{app}")

    async def start_keepalive(app: str):
        calls.append(f"keepalive:{app}")

    monkeypatch.setattr(manager, "stop_keepalive", lambda app: calls.append(f"stop:{app}"))
    monkeypatch.setattr(manager, "login", login)
    monkeypatch.setattr(manager, "activate_app", activate_app)
    monkeypatch.setattr(manager, "start_keepalive", start_keepalive)

    await client.relogin()

    assert calls == ["stop:involture", "login", "activate:involture", "keepalive:involture"]
    await manager.close()


@pytest.mark.anyio
async def test_search_anagrafica_parses_rows_and_variants() -> None:
    seen: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, text=_encoded([{"IDXANA": "A1", "CCO": "123"}]))

    client, manager = _client(handler)

    by_cf = await client.search_by_cf("RSSMRA80A01H501U")
    by_cco = await client.search_by_cco("123", "F1", "S1")

    assert by_cf.total == 1 and by_cf.rows[0].id_ana == "A1"
    assert by_cco.rows[0].cco == "123"
    assert seen[0].url.params["opz"] == "2" and seen[0].url.params["tipo"] == "ricanag"
    assert seen[1].url.params["q"] == "123~F1~S1" and seen[1].url.params["opz"] == "3"
    assert "token=tok-123" in seen[0].headers["Referer"]
    await manager.close()


@pytest.mark.anyio
async def test_search_anagrafica_raises_on_expired_session_before_decoding() -> None:
    client, manager = _client(_always("NOSessione scaduta"))

    with pytest.raises(CapacitasSessionExpiredError, match="scaduta"):
        await client.search_anagrafica("X")

    await manager.close()


def test_parse_search_result_shapes(caplog) -> None:
    from_dict = _parse_search_result({"rows": [{"IDXANA": "A"}, "bad-row"], "total": "7"})
    from_records = _parse_search_result({"Rows": [], "records": 3})
    unexpected = _parse_search_result("SI-text")

    assert (from_dict.total, [row.id_ana for row in from_dict.rows]) == (7, ["A"])
    assert (from_records.total, from_records.rows) == (3, [])
    assert (unexpected.total, unexpected.rows) == (0, [])
    assert "Parse row Capacitas fallito" in caplog.text
    assert "Struttura risposta inattesa" in caplog.text


@pytest.mark.anyio
async def test_lookups_accept_list_dict_and_text_payloads() -> None:
    payloads = {
        "/pages/ajax/ajaxFrazioni.aspx": _encoded([{"ID": "1", "Display": "Uras"}]),
        "/pages/ajax/ajaxSezioni.aspx": _encoded({"rows": [{"ID": "A", "Display": "Sez+A"}]}),
        "/pages/ajax/ajaxFogli.aspx": "SI[{ID:'7',Display:'Foglio 7'}]",
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=payloads[request.url.path])

    client, manager = _client(handler)

    frazioni = await client.search_frazioni("uras")
    sezioni = await client.load_sezioni("1")
    fogli = await client.load_fogli("1", "A")

    assert [(o.id, o.display) for o in frazioni] == [("1", "Uras")]
    assert [(o.id, o.display) for o in sezioni] == [("A", "Sez A")]
    assert [o.id for o in fogli] == ["7"]
    await manager.close()


@pytest.mark.anyio
async def test_lookup_rejects_dict_without_row_list() -> None:
    client, manager = _client(_always(_encoded({"rows": "none"})))

    with pytest.raises(RuntimeError, match="payload non riconosciuto"):
        await client.search_frazioni("uras")

    await manager.close()


@pytest.mark.anyio
async def test_search_terreni_posts_filters(monkeypatch) -> None:
    seen: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, text=_encoded([]))

    monkeypatch.setattr(
        involture, "parse_terreni_search_result", lambda decoded: ("parsed", decoded)
    )
    client, manager = _client(handler)

    result = await client.search_terreni(
        CapacitasTerreniSearchRequest(
            frazione_id="F1", foglio="3", in_essere=True, limita_risultati=True
        )
    )

    body = seen[0].content.decode()
    assert result == ("parsed", [])
    assert "inEssere=true" in body and "inDomIrr=false" in body and "limitaRisultati=true" in body
    await manager.close()


def _certificato(**fields) -> CapacitasTerrenoCertificato:
    return CapacitasTerrenoCertificato(**fields)


@pytest.mark.parametrize(
    ("certificato", "retryable"),
    [
        (_certificato(raw_text="Deadlock rilevato", partita_code="P"), True),
        (_certificato(raw_text="ripetere la transazione"), True),
        (_certificato(raw_text="ok", partita_code="P"), False),
        (_certificato(raw_text="errore nella transazione"), True),
        (_certificato(raw_text=None), True),
    ],
)
def test_is_retryable_invalid_certificato(certificato, retryable: bool) -> None:
    assert _is_retryable_invalid_certificato(certificato) is retryable


@pytest.mark.anyio
async def test_fetch_certificato_retries_with_relogin_then_succeeds(monkeypatch) -> None:
    responses = iter([_certificato(raw_text="deadlock"), _certificato(partita_code="P1")])
    relogins: list[int] = []
    monkeypatch.setattr(involture, "parse_certificato_html", lambda html: next(responses))
    monkeypatch.setattr(involture.asyncio, "sleep", _no_sleep)
    client, manager = _client(_always("<html/>"))

    async def relogin():
        relogins.append(1)

    monkeypatch.setattr(client, "relogin", relogin)

    certificato = await client.fetch_certificato(cco="1", com="2", pvc="3", fra="4", ccs="5")

    assert certificato.partita_code == "P1" and relogins == [1]
    await manager.close()


@pytest.mark.anyio
async def test_fetch_certificato_gives_up_after_three_invalid_answers(monkeypatch) -> None:
    monkeypatch.setattr(
        involture, "parse_certificato_html", lambda html: _certificato(raw_text="deadlock")
    )
    monkeypatch.setattr(involture.asyncio, "sleep", _no_sleep)
    client, manager = _client(_always("<html/>"))

    async def relogin():
        return None

    monkeypatch.setattr(client, "relogin", relogin)

    with pytest.raises(RuntimeError, match="attempt=3"):
        await client.fetch_certificato(cco="1", com="2", pvc="3", fra="4", ccs="5")

    await manager.close()


async def _no_sleep(_seconds: float) -> None:
    return None


@pytest.mark.anyio
async def test_detail_pages_are_parsed(monkeypatch) -> None:
    seen: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200, text="<html>detail</html>")

    monkeypatch.setattr(involture, "parse_terreno_detail_html", lambda html: ("terreno", html))
    monkeypatch.setattr(
        involture, "parse_anagrafica_detail_html", lambda html: ("anagrafica", html)
    )
    client, manager = _client(handler)

    assert (await client.fetch_terreno_detail(external_row_id="9"))[0] == "terreno"
    assert (await client.fetch_anagrafica_detail(history_id="H"))[0] == "anagrafica"
    assert (await client.fetch_current_anagrafica_detail(idxana="A", idxesa="E"))[0] == "anagrafica"
    assert seen == [
        "/pages/dettaglioTerreno.aspx",
        "/pages/dialog/dlgNuovaAnagrafica.aspx",
        "/pages/dettaglioAnagrafica.aspx",
    ]
    await manager.close()


@pytest.mark.anyio
async def test_fetch_anagrafica_history_parses_rows(monkeypatch) -> None:
    monkeypatch.setattr(
        involture, "parse_storico_anagrafica_rows", lambda decoded: ["row", decoded]
    )
    client, manager = _client(_always(_encoded([{"IDXAna": "A"}])))

    assert await client.fetch_anagrafica_history(idxana="A") == ["row", [{"IDXAna": "A"}]]
    await manager.close()


@pytest.mark.anyio
async def test_fetch_anagrafica_history_without_history_returns_empty() -> None:
    client, manager = _client(_always("NOStorico anagrafica non disponibile"))

    assert await client.fetch_anagrafica_history(idxana="A") == []
    await manager.close()


@pytest.mark.anyio
@pytest.mark.parametrize("text", ["NOErrore inatteso", "@@@"])
async def test_fetch_anagrafica_history_reraises_other_errors(text: str) -> None:
    client, manager = _client(_always(text))

    with pytest.raises(ValueError):
        await client.fetch_anagrafica_history(idxana="A")

    await manager.close()
