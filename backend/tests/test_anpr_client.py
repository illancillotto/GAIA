from __future__ import annotations

import json
from datetime import date, timedelta

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


def test_resolve_verify_returns_system_cas_when_bundle_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.modules.utenze.anpr.client.settings.anpr_ssl_verify", True)
    monkeypatch.setattr("app.modules.utenze.anpr.client.settings.anpr_ca_bundle_path", "/tmp/does-not-exist.pem")

    verify = AnprClient._resolve_verify()

    assert verify is True


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
    assert payload["verifica"]["datiDecesso"]["dataEvento"] == (date.today() - timedelta(days=1)).isoformat()
