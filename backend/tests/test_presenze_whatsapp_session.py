from __future__ import annotations

from dataclasses import replace

import httpx
import pytest

from app.modules.presenze.services import whatsapp_session as service
from app.modules.presenze.services.whatsapp_config import environment_whatsapp_config
from app.modules.presenze.services.whatsapp_session import WahaSessionError, WahaSessionManager


def manager(handler, **overrides) -> WahaSessionManager:
    values = {
        "waha_url": "http://waha:3000",
        "waha_api_key": "secret",
        "waha_session": "default",
        **overrides,
    }
    config = replace(
        environment_whatsapp_config(),
        **values,
    )
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return WahaSessionManager(config, client)


def test_status_handles_missing_and_connected_sessions() -> None:
    missing = manager(lambda request: httpx.Response(404, json={}))
    assert missing.status() == {
        "name": "default",
        "status": "not_created",
        "phone": None,
        "display_name": None,
    }

    connected = manager(
        lambda request: httpx.Response(
            200,
            json={"status": " WORKING ", "me": {"id": "39333123@c.us", "pushName": "GAIA"}},
        ),
        waha_session="",
    )
    assert connected.status() == {
        "name": "default",
        "status": "working",
        "phone": "39333123",
        "display_name": "GAIA",
    }


def test_default_http_client_is_one_shot(monkeypatch: pytest.MonkeyPatch) -> None:
    config = replace(
        environment_whatsapp_config(),
        waha_url="http://waha:3000",
        waha_api_key="secret",
    )
    monkeypatch.setattr(
        service.httpx,
        "request",
        lambda *args, **kwargs: httpx.Response(200, json={"status": "WORKING"}),
    )
    assert WahaSessionManager(config).status()["status"] == "working"


def test_start_creates_or_starts_and_logout() -> None:
    requests: list[httpx.Request] = []

    def create_handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(404, json={})
        return httpx.Response(201, json={"status": "STARTING"})

    assert manager(create_handler).start()["status"] == "starting"
    assert requests[1].url.path == "/api/sessions"
    assert requests[1].read() == b'{"name":"default","start":true}'

    def existing_handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, json={"status": "STOPPED"})
        return httpx.Response(201, json={"status": "STARTING"})

    assert manager(existing_handler).start()["status"] == "starting"

    logout_requests: list[httpx.Request] = []

    def logout_handler(request: httpx.Request) -> httpx.Response:
        logout_requests.append(request)
        return httpx.Response(201, json={"status": "STOPPED"})

    assert manager(logout_handler).logout()["status"] == "stopped"
    assert logout_requests[0].read() == b"{}"


@pytest.mark.parametrize("status", ["FAILED", " failed ", "STOPPED", "STARTING", "SCAN_QR_CODE", "WORKING"])
def test_start_recovers_only_failed_sessions(status: str) -> None:
    requests: list[tuple[str, str]] = []
    action = "restart" if status.strip().upper() == "FAILED" else "start"

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, request.url.path))
        assert request.headers["x-api-key"] == "secret"
        if request.method == "GET":
            return httpx.Response(200, json={"status": status})
        return httpx.Response(201, json={"status": "SCAN_QR_CODE"})

    assert manager(handler, waha_session="office").start()["status"] == "scan_qr_code"
    assert requests == [
        ("GET", "/api/sessions/office"),
        ("POST", f"/api/sessions/office/{action}"),
    ]


def test_failed_session_recovery_propagates_gateway_failure_without_retry() -> None:
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        if request.method == "GET":
            return httpx.Response(200, json={"status": "FAILED"})
        return httpx.Response(500, json={"message": "Restart failed"})

    with pytest.raises(WahaSessionError, match="Restart failed") as failure:
        manager(handler).start()
    assert failure.value.status_code == 502
    assert requests == ["/api/sessions/default", "/api/sessions/default/restart"]


def test_qr_encodes_png_and_rejects_invalid_payloads() -> None:
    requests: list[httpx.Request] = []

    def valid_qr(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200, content=b"png", headers={"content-type": "image/png; charset=binary"}
        )

    valid = manager(valid_qr)
    assert valid.qr_code() == {"image_data_url": "data:image/png;base64,cG5n"}
    assert requests[0].headers["accept"] == "image/png"

    for response in (
        httpx.Response(200, content=b"json", headers={"content-type": "application/json"}),
        httpx.Response(200, content=b"", headers={"content-type": "image/png"}),
    ):
        with pytest.raises(WahaSessionError, match="QR valido"):
            manager(lambda request, response=response: response).qr_code()


def test_configuration_network_and_http_errors() -> None:
    base = environment_whatsapp_config()
    with pytest.raises(WahaSessionError, match="incompleta") as missing_url:
        WahaSessionManager(replace(base, waha_url="", waha_api_key="secret")).status()
    assert missing_url.value.status_code == 409
    with pytest.raises(WahaSessionError, match="incompleta"):
        WahaSessionManager(replace(base, waha_url="http://waha", waha_api_key="")).status()

    def offline(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline")

    with pytest.raises(WahaSessionError, match="non raggiungibile") as unavailable:
        manager(offline).status()
    assert unavailable.value.status_code == 503

    for response, expected_status, expected_message in (
        (httpx.Response(422, json={"message": "QR non pronto"}), 409, "QR non pronto"),
        (httpx.Response(401, json={"message": ""}), 502, "WAHA HTTP 401"),
        (httpx.Response(500, text="errore"), 502, "WAHA HTTP 500"),
    ):
        with pytest.raises(WahaSessionError, match=expected_message) as failure:
            manager(lambda request, response=response: response).qr_code()
        assert failure.value.status_code == expected_status


def test_invalid_session_responses_and_optional_identity() -> None:
    for response, message in (
        (httpx.Response(200, text="invalid"), "Risposta WAHA non valida"),
        (httpx.Response(200, json=[]), "Risposta WAHA non valida"),
        (httpx.Response(200, json={"status": None}), "Stato sessione WAHA assente"),
        (httpx.Response(200, json={"status": " "}), "Stato sessione WAHA assente"),
    ):
        with pytest.raises(WahaSessionError, match=message):
            manager(lambda request, response=response: response).status()

    no_identity = manager(
        lambda request: httpx.Response(
            200, json={"status": "WORKING", "me": {"id": 3, "pushName": 4}}
        )
    )
    assert no_identity.status()["phone"] is None
    assert no_identity.status()["display_name"] is None
