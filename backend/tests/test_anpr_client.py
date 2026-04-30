from __future__ import annotations

import json
from datetime import date

import httpx
import pytest

from app.modules.utenze.anpr.client import AnprClient


class AuthStub:
    async def get_voucher(self) -> str:
        return "voucher-token"

    def build_agid_jwt_signature(self, payload_bytes: bytes) -> str:
        return "signature-token"

    def build_agid_jwt_tracking_evidence(self, motivo_richiesta: str) -> str:
        return f"tracking-{motivo_richiesta}"


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
    assert requests[0].headers["Agid-JWT-Signature"] == "signature-token"
    assert requests[0].headers["Agid-JWT-TrackingEvidence"] == "tracking-GAIA-CHECK-SUBJ123"
    assert json.loads(requests[0].content.decode("utf-8"))["datiRichiesta"]["casoUso"] == "C030"


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
