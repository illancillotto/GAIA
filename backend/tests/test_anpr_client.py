from __future__ import annotations

import json
import ssl
from datetime import date
from types import SimpleNamespace

import httpx
import pytest

from app.modules.utenze.anpr.client import AnprClient


class AuthStub:
    async def get_voucher(self, purpose_id: str | None = None, tracking_digest: str | None = None) -> str:
        return "voucher-token"

    def build_agid_jwt_signature(self, payload_bytes: bytes, *, endpoint_url: str, digest_header: str) -> str:
        return "signature-token"

    def build_agid_jwt_tracking_evidence(self, *, endpoint_url: str, purpose_id: str | None = None) -> str:
        return f"tracking-{purpose_id or 'none'}"


class _JsonErrorResponse:
    status_code = 418
    text = "teapot"

    def json(self):
        raise ValueError("bad json")


@pytest.mark.anyio
async def test_c030_get_anpr_id_returns_success_payload() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "idOperazioneANPR": "anpr-op-1",
                "listaSoggetti": {
                    "datiSoggetto": [
                        {
                            "identificativi": {
                                "idANPR": "123456789",
                            }
                        }
                    ]
                },
            },
        )

    transport = httpx.MockTransport(handler)

    class FakeAsyncClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(transport=transport)

    client = AnprClient(auth_manager=AuthStub(), base_url="https://anpr.example.test")

    from app.modules.utenze.anpr import client as client_module

    original_async_client = client_module.httpx.AsyncClient
    client_module.httpx.AsyncClient = FakeAsyncClient
    try:
        result = await client.c030_get_anpr_id("RSSMRA80A01H501U", "SUBJ123")
    finally:
        client_module.httpx.AsyncClient = original_async_client

    assert result.success is True
    assert result.esito == "anpr_id_found"
    assert result.anpr_id == "123456789"
    assert requests[0].headers["Authorization"] == "Bearer voucher-token"
    assert requests[0].headers["Accept"] == "application/json"
    assert requests[0].headers["Digest"].startswith("SHA-256=")
    assert requests[0].headers["Agid-JWT-Signature"] == "signature-token"
    assert requests[0].headers["Agid-JWT-TrackingEvidence"].startswith("tracking-")
    payload = json.loads(requests[0].content.decode("utf-8"))
    assert payload["datiRichiesta"]["casoUso"] == "C030"
    assert payload["idOperazioneClient"].isdigit()
    assert len(payload["idOperazioneClient"]) <= 30


@pytest.mark.anyio
async def test_c030_get_anpr_id_returns_not_found_for_404_http_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"idOperazioneANPR": "anpr-404", "listaErrori": [{"testoErroreAnomalia": "Soggetto non trovato"}]})

    transport = httpx.MockTransport(handler)

    class FakeAsyncClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(transport=transport)

    client = AnprClient(auth_manager=AuthStub(), base_url="https://anpr.example.test")
    from app.modules.utenze.anpr import client as client_module

    original_async_client = client_module.httpx.AsyncClient
    client_module.httpx.AsyncClient = FakeAsyncClient
    try:
        result = await client.c030_get_anpr_id("RSSMRA80A01H501U", "SUBJ123")
    finally:
        client_module.httpx.AsyncClient = original_async_client

    assert result.esito == "not_found"
    assert result.id_operazione_anpr == "anpr-404"


@pytest.mark.anyio
async def test_c030_get_anpr_id_returns_error_for_non_404_http_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"idOperazioneANPR": "anpr-500", "listaErrori": [{"testoErroreAnomalia": "Errore tecnico"}]})

    transport = httpx.MockTransport(handler)

    class FakeAsyncClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(transport=transport)

    client = AnprClient(auth_manager=AuthStub(), base_url="https://anpr.example.test")
    from app.modules.utenze.anpr import client as client_module

    original_async_client = client_module.httpx.AsyncClient
    client_module.httpx.AsyncClient = FakeAsyncClient
    try:
        result = await client.c030_get_anpr_id("RSSMRA80A01H501U", "SUBJ123")
    finally:
        client_module.httpx.AsyncClient = original_async_client

    assert result.esito == "error"
    assert result.id_operazione_anpr == "anpr-500"


@pytest.mark.anyio
async def test_c030_get_anpr_id_returns_error_for_request_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    client = AnprClient(auth_manager=AuthStub(), base_url="https://anpr.example.test")

    async def fake_post_json(*args, **kwargs):
        request = httpx.Request("POST", "https://anpr.example.test")
        raise httpx.ReadTimeout("timeout", request=request)

    monkeypatch.setattr(client, "_post_json", fake_post_json)

    result = await client.c030_get_anpr_id("RSSMRA80A01H501U", "SUBJ123")

    assert result.esito == "error"
    assert "timeout" in (result.error_detail or "")


@pytest.mark.anyio
async def test_c030_get_anpr_id_handles_not_found_cancelled_and_missing_id_payloads(monkeypatch: pytest.MonkeyPatch) -> None:
    client = AnprClient(auth_manager=AuthStub(), base_url="https://anpr.example.test")
    payloads = [
        {"idOperazioneANPR": "op-a", "listaAnomalie": [{"testoErroreAnomalia": "Soggetto non trovato"}]},
        {"idOperazioneANPR": "op-b", "listaAnomalie": [{"testoErroreAnomalia": "Posizione cancellata per irreperibilita"}]},
        {"idOperazioneANPR": "op-c", "listaSoggetti": {"datiSoggetto": [{}]}},
    ]

    async def fake_post_json(*args, **kwargs):
        payload = payloads.pop(0)
        return httpx.Response(200, json=payload)

    monkeypatch.setattr(client, "_post_json", fake_post_json)

    not_found = await client.c030_get_anpr_id("RSSMRA80A01H501U", "SUBJ123")
    cancelled = await client.c030_get_anpr_id("RSSMRA80A01H501U", "SUBJ123")
    missing_id = await client.c030_get_anpr_id("RSSMRA80A01H501U", "SUBJ123")

    assert not_found.esito == "not_found"
    assert cancelled.esito == "cancelled"
    assert missing_id.esito == "error"


@pytest.mark.anyio
async def test_c004_check_death_returns_deceased_when_info_flag_present() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "idOperazioneANPR": "anpr-op-2",
                "listaSoggetti": {
                    "datiSoggetto": [
                        {
                            "infoSoggettoEnte": [
                                {
                                    "chiave": "dataDecesso",
                                    "valore": "S",
                                    "valoreData": "2025-01-15",
                                    "dettaglio": "soggetto deceduto",
                                }
                            ]
                        }
                    ]
                },
            },
        )

    transport = httpx.MockTransport(handler)

    class FakeAsyncClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(transport=transport)

    client = AnprClient(auth_manager=AuthStub(), base_url="https://anpr.example.test")

    from app.modules.utenze.anpr import client as client_module

    original_async_client = client_module.httpx.AsyncClient
    client_module.httpx.AsyncClient = FakeAsyncClient
    try:
        result = await client.c004_check_death("123456789", "SUBJ123")
    finally:
        client_module.httpx.AsyncClient = original_async_client

    assert result.success is True
    assert result.esito == "deceased"
    assert result.data_decesso == date(2025, 1, 15)
    assert result.id_operazione_anpr == "anpr-op-2"
    assert result.raw_response is not None


@pytest.mark.anyio
async def test_c004_check_death_returns_deceased_when_death_verification_is_mismatched() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "idOperazioneANPR": "anpr-op-2b",
                "listaSoggetti": {
                    "datiSoggetto": [
                        {
                            "infoSoggettoEnte": [
                                {
                                    "chiave": "Verifica dichiarazione morte",
                                    "dettaglio": "Dato non corrispondente",
                                    "id": "1007",
                                    "valore": "N",
                                }
                            ]
                        }
                    ]
                },
            },
        )

    transport = httpx.MockTransport(handler)

    class FakeAsyncClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(transport=transport)

    client = AnprClient(auth_manager=AuthStub(), base_url="https://anpr.example.test")

    from app.modules.utenze.anpr import client as client_module

    original_async_client = client_module.httpx.AsyncClient
    client_module.httpx.AsyncClient = FakeAsyncClient
    try:
        result = await client.c004_check_death(
            "123456789",
            "SUBJ123",
            reference_date=date(2025, 8, 22),
            death_event_date=date(2025, 8, 22),
        )
    finally:
        client_module.httpx.AsyncClient = original_async_client

    assert result.success is True
    assert result.esito == "deceased"
    assert result.data_decesso is None


@pytest.mark.anyio
async def test_c004_check_death_handles_cancelled_non_404_http_error_and_request_error(monkeypatch: pytest.MonkeyPatch) -> None:
    client = AnprClient(auth_manager=AuthStub(), base_url="https://anpr.example.test")
    responses = [
        httpx.Response(200, json={"idOperazioneANPR": "cancel-op", "listaAnomalie": [{"testoErroreAnomalia": "Soggetto cancellato per espatrio"}]}),
        httpx.Response(500, json={"idOperazioneANPR": "err-op", "listaErrori": [{"testoErroreAnomalia": "Errore tecnico"}]}),
    ]

    async def fake_post_json(*args, **kwargs):
        payload = responses.pop(0)
        if payload.status_code >= 400:
            raise httpx.HTTPStatusError("boom", request=httpx.Request("POST", "https://anpr.example.test"), response=payload)
        return payload

    monkeypatch.setattr(client, "_post_json", fake_post_json)

    cancelled = await client.c004_check_death("123456789", "SUBJ123")
    error_http = await client.c004_check_death("123456789", "SUBJ123")

    async def fake_post_json_request_error(*args, **kwargs):
        raise httpx.ConnectTimeout("timeout", request=httpx.Request("POST", "https://anpr.example.test"))

    monkeypatch.setattr(client, "_post_json", fake_post_json_request_error)
    error_request = await client.c004_check_death("123456789", "SUBJ123")

    assert cancelled.esito == "cancelled"
    assert error_http.esito == "error"
    assert error_http.id_operazione_anpr == "err-op"
    assert error_request.esito == "error"
    assert error_request.id_operazione_anpr is None


def test_resolve_verify_returns_system_cas_when_bundle_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.modules.utenze.anpr.client.settings.anpr_ssl_verify", True)
    monkeypatch.setattr("app.modules.utenze.anpr.client.settings.anpr_ca_bundle_path", "/tmp/does-not-exist.pem")

    verify = AnprClient._resolve_verify()

    assert verify is True


def test_resolve_verify_returns_false_when_ssl_verification_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.modules.utenze.anpr.client.settings.anpr_ssl_verify", False)

    assert AnprClient._resolve_verify() is False


def test_resolve_verify_returns_ssl_context_when_bundle_exists(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    bundle = tmp_path / "bundle.pem"
    bundle.write_text("dummy", encoding="utf-8")
    monkeypatch.setattr("app.modules.utenze.anpr.client.settings.anpr_ssl_verify", True)
    monkeypatch.setattr("app.modules.utenze.anpr.client.settings.anpr_ca_bundle_path", str(bundle))

    loaded: list[str] = []

    class FakeContext:
        def load_verify_locations(self, *, cafile: str) -> None:
            loaded.append(cafile)

    monkeypatch.setattr("app.modules.utenze.anpr.client.ssl.create_default_context", lambda cafile=None: FakeContext())

    verify = AnprClient._resolve_verify()

    assert isinstance(verify, FakeContext)
    assert loaded == [str(bundle)]


@pytest.mark.anyio
async def test_c004_check_death_returns_not_found_on_404() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            404,
            json={
                "idOperazioneANPR": "anpr-op-404",
                "listaErrori": [
                    {
                        "codiceErroreAnomalia": "404",
                        "testoErroreAnomalia": "Soggetto non trovato",
                    }
                ],
            },
        )

    transport = httpx.MockTransport(handler)

    class FakeAsyncClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(transport=transport)

    client = AnprClient(auth_manager=AuthStub(), base_url="https://anpr.example.test")

    from app.modules.utenze.anpr import client as client_module

    original_async_client = client_module.httpx.AsyncClient
    client_module.httpx.AsyncClient = FakeAsyncClient
    try:
        result = await client.c004_check_death("123456789", "SUBJ123")
    finally:
        client_module.httpx.AsyncClient = original_async_client

    assert result.success is False
    assert result.esito == "not_found"
    assert result.id_operazione_anpr == "anpr-op-404"


@pytest.mark.anyio
async def test_c004_check_death_sends_verifica_dati_decesso_payload() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "idOperazioneANPR": "anpr-op-3",
                "listaSoggetti": {
                    "datiSoggetto": [
                        {
                            "infoSoggettoEnte": []
                        }
                    ]
                },
            },
        )

    transport = httpx.MockTransport(handler)

    class FakeAsyncClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(transport=transport)

    client = AnprClient(auth_manager=AuthStub(), base_url="https://anpr.example.test")

    from app.modules.utenze.anpr import client as client_module

    original_async_client = client_module.httpx.AsyncClient
    client_module.httpx.AsyncClient = FakeAsyncClient
    try:
        result = await client.c004_check_death("123456789", "SUBJ123")
    finally:
        client_module.httpx.AsyncClient = original_async_client

    payload = json.loads(requests[0].content.decode("utf-8"))
    assert result.success is True
    assert payload["criteriRicerca"]["idANPR"] == "123456789"
    assert payload["datiRichiesta"]["casoUso"] == "C004"
    assert payload["idOperazioneClient"].isdigit()
    assert len(payload["idOperazioneClient"]) <= 30
    assert payload["verifica"]["datiDecesso"]["dataEvento"] == payload["datiRichiesta"]["dataRiferimentoRichiesta"]


def test_client_helpers_cover_fallback_and_edge_cases() -> None:
    assert AnprClient._safe_json(_JsonErrorResponse()) is None
    assert AnprClient._extract_id_operazione_anpr(_JsonErrorResponse()) is None
    assert AnprClient._extract_problem_detail(_JsonErrorResponse()) == "teapot"
    assert AnprClient._safe_json(SimpleNamespace(json=lambda: ["not", "a", "dict"])) is None
    assert AnprClient._extract_id_operazione_anpr(SimpleNamespace(json=lambda: {"idOperazioneANPR": "opx"})) == "opx"
    assert AnprClient._extract_problem_detail(SimpleNamespace(json=lambda: {"listaAnomalie": [{"testoErroreAnomalia": "x"}]}, text="fallback", status_code=400)) == "x"
    assert AnprClient._extract_problem_detail(SimpleNamespace(json=lambda: {"listaAnomalie": []}, text="fallback", status_code=400)) == "fallback"
    assert AnprClient._extract_info_soggetto_ente({}) == []
    assert AnprClient._extract_anomalies({"listaAnomalie": ["bad", {"ok": 1}]}) == [{"ok": 1}]
    assert AnprClient._anomalies_to_text([{}]) == "ANPR anomaly"
    assert AnprClient._contains_any({"foo": "bar"}, ["nope"]) is False
    assert AnprClient._contains_text("foo morto", ["morto"]) is True
    assert AnprClient._is_death_related_text("verifica morte") is True
    assert AnprClient._has_not_found_anomaly([{"testoErroreAnomalia": "utente assente"}]) is True
    assert AnprClient._has_cancelled_anomaly([{"testoErroreAnomalia": "soggetto cancellato"}]) is True
    assert AnprClient._has_cancelled_anomaly([{"testoErroreAnomalia": "soggetto cancellato per decesso"}]) is False
    assert AnprClient._has_deceased_anomaly([{"testoErroreAnomalia": "soggetto deceduto"}]) is True
    assert AnprClient._has_deceased_info([{"chiave": "stato", "valore": "S", "dettaglio": "evento morte registrato"}]) is True
    assert AnprClient._has_deceased_info([{"chiave": "verifica dichiarazione morte", "valore": "N", "dettaglio": "dato non corrispondente"}]) is True
    assert AnprClient._has_deceased_info([{"chiave": "data morte", "valore": "A", "valoreTesto": "si"}]) is True
    assert AnprClient._has_deceased_info([{"chiave": "data morte", "valore": "A", "dettaglio": ""}]) is True
    assert AnprClient._has_deceased_info([{"chiave": "data morte", "valore": "N", "dettaglio": "nessun match"}]) is False
    assert AnprClient._has_deceased_info([{"chiave": "stato", "valore": "N"}]) is False
    assert AnprClient._extract_death_date([{"valoreErroreAnomalia": "2025-02-01"}], []) == date(2025, 2, 1)
    assert AnprClient._extract_death_date([], [{"valoreData": "2025-01-31"}]) == date(2025, 1, 31)
    assert AnprClient._parse_iso_date("2025-13-99") is None


@pytest.mark.anyio
async def test_c004_check_death_skips_warning_when_response_map_marked_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    client = AnprClient(auth_manager=AuthStub(), base_url="https://anpr.example.test")

    async def fake_post_json(*args, **kwargs):
        return httpx.Response(200, json={"idOperazioneANPR": "alive-op", "listaSoggetti": {"datiSoggetto": [{"infoSoggettoEnte": []}]}})

    monkeypatch.setattr(client, "_post_json", fake_post_json)
    monkeypatch.setattr("app.modules.utenze.anpr.client._RESPONSE_MAP_VALIDATED", True)

    result = await client.c004_check_death("123456789", "SUBJ123")

    assert result.esito == "alive"


@pytest.mark.anyio
async def test_post_json_and_build_headers_cover_transport_and_verify(monkeypatch: pytest.MonkeyPatch) -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)

    class FakeAsyncClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs) -> None:
            assert kwargs["timeout"] == 30.0
            assert isinstance(kwargs["verify"], ssl.SSLContext) or kwargs["verify"] is True
            super().__init__(transport=transport)

    monkeypatch.setattr("app.modules.utenze.anpr.client.httpx.AsyncClient", FakeAsyncClient)
    monkeypatch.setattr("app.modules.utenze.anpr.client.settings.anpr_ssl_verify", True)
    monkeypatch.setattr("app.modules.utenze.anpr.client.settings.anpr_ca_bundle_path", "")

    client = AnprClient(auth_manager=AuthStub(), base_url="https://anpr.example.test")
    response = await client._post_json("/path", {"a": 1}, motivo_richiesta="x", purpose_id="p1")
    headers = await client._build_headers(b"{}", endpoint_url="https://anpr.example.test/path", motivo_richiesta="x", purpose_id="p2")

    assert response.status_code == 200
    assert requests[0].url.path == "/path"
    assert headers["Authorization"] == "Bearer voucher-token"
