from __future__ import annotations

import hashlib
import hmac

import httpx
import pytest

from app.core.config import settings
from app.modules.presenze.services.whatsapp_waha import (
    DryRunWhatsAppSender,
    WahaWhatsAppSender,
    WhatsAppAck,
    WhatsAppOptOut,
    WhatsAppSendError,
    build_whatsapp_sender_from_settings,
    parse_waha_webhook,
    verify_waha_signature,
    waha_chat_id,
)


def _sender(handler) -> WahaWhatsAppSender:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return WahaWhatsAppSender(
        base_url="http://waha:3000/", api_key="key", session="gaia", client=client
    )


def test_send_text_posts_to_waha_chat_id() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(201, json={"id": {"_serialized": "true_393331234567@c.us_ABC"}})

    result = _sender(handler).send_text("+393331234567", "Ciao")
    assert (result.status, result.provider, result.provider_message_id) == (
        "SENT",
        "waha",
        "true_393331234567@c.us_ABC",
    )
    assert str(requests[0].url) == "http://waha:3000/api/sendText"
    assert requests[0].headers["x-api-key"] == "key"
    assert requests[0].read() == b'{"session":"gaia","chatId":"393331234567@c.us","text":"Ciao"}'
    for response in [
        httpx.Response(200, text="not json"),
        httpx.Response(200, json=["x"]),
        httpx.Response(200, json={"id": ""}),
    ]:
        with pytest.raises(WhatsAppSendError) as exc:
            _sender(lambda request, response=response: response).send_text("+393331234567", "Ciao")
        assert exc.value.uncertain is True
        assert exc.value.code == "invalid_response"
    assert waha_chat_id("+441234567890") == "441234567890@c.us"


def test_check_number_queries_contacts_endpoint() -> None:
    urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        urls.append(str(request.url))
        return httpx.Response(200, json={"numberExists": True})

    assert _sender(handler).check_number("+393331234567") is True
    assert urls == ["http://waha:3000/api/contacts/check-exists?phone=393331234567&session=gaia"]
    assert (
        _sender(lambda request: httpx.Response(200, json={"numberExists": False})).check_number(
            "+39333"
        )
        is False
    )
    for payload in [{}, {"numberExists": "false"}, {"numberExists": 1}, []]:
        with pytest.raises(WhatsAppSendError) as exc:
            _sender(
                lambda request, payload=payload: httpx.Response(200, json=payload)
            ).check_number("+39333")
        assert (exc.value.code, exc.value.uncertain) == ("invalid_response", False)


def test_waha_errors_are_classified() -> None:
    def failure(handler) -> WhatsAppSendError:
        with pytest.raises(WhatsAppSendError) as exc_info:
            _sender(handler).send_text("+393331234567", "Ciao")
        return exc_info.value

    def offline(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline")

    network = failure(offline)
    assert (network.code, network.retryable) == ("network_error", True)
    session = failure(
        lambda request: httpx.Response(422, json={"message": "Session status is not as expected"})
    )
    assert (session.code, session.retryable, str(session)) == (
        "http_422",
        False,
        "Session status is not as expected",
    )
    throttled = failure(lambda request: httpx.Response(429, json={}))
    assert (throttled.retryable, str(throttled)) == (True, "WAHA HTTP 429")
    assert failure(lambda request: httpx.Response(502)).retryable is True


def test_dry_run_sender_records_messages() -> None:
    sender = DryRunWhatsAppSender()
    assert sender.check_number("+393331234567") is True
    result = sender.send_text("+393331234567", "Ciao")
    assert (result.status, result.provider, result.provider_message_id) == (
        "DRY_RUN",
        "dry_run",
        None,
    )
    assert sender.sent == [("+393331234567", "Ciao")]


def test_build_sender_from_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "presenze_whatsapp_provider", "")
    assert build_whatsapp_sender_from_settings() is None
    monkeypatch.setattr(settings, "presenze_whatsapp_provider", " DRY_RUN ")
    assert isinstance(build_whatsapp_sender_from_settings(), DryRunWhatsAppSender)
    monkeypatch.setattr(settings, "presenze_whatsapp_provider", "waha")
    monkeypatch.setattr(settings, "presenze_whatsapp_waha_api_key", "")
    with pytest.raises(ValueError, match="PRESENZE_WHATSAPP_WAHA_API_KEY"):
        build_whatsapp_sender_from_settings()
    monkeypatch.setattr(settings, "presenze_whatsapp_waha_api_key", "key")
    monkeypatch.setattr(settings, "presenze_whatsapp_waha_session", "")
    assert isinstance(build_whatsapp_sender_from_settings(), WahaWhatsAppSender)


def test_verify_waha_signature() -> None:
    signature = hmac.new(b"secret", b"{}", hashlib.sha512).hexdigest()
    assert verify_waha_signature(b"{}", signature.upper(), "secret") is True
    assert verify_waha_signature(b"{}", "0" * 128, "secret") is False
    assert verify_waha_signature(b"{}", None, "secret") is False


def test_parse_waha_webhook_extracts_acks_and_opt_outs() -> None:
    assert parse_waha_webhook(None) == []
    assert parse_waha_webhook({"event": "message.ack", "payload": {"id": "wamid", "ack": 3}}) == [
        WhatsAppAck("wamid", "READ")
    ]
    assert parse_waha_webhook(
        {"event": "message.ack", "payload": {"id": {"_serialized": "x"}, "ack": -1}}
    ) == [WhatsAppAck("x", "FAILED")]
    assert parse_waha_webhook({"event": "message.ack", "payload": {"id": "wamid", "ack": 0}}) == []
    assert (
        parse_waha_webhook(
            {"event": "message.ack", "payload": {"id": {"_serialized": ""}, "ack": 2}}
        )
        == []
    )
    assert parse_waha_webhook(
        {"event": "message", "payload": {"from": "393331234567@c.us", "body": " Stop "}}
    ) == [WhatsAppOptOut("+393331234567", "Stop")]
    assert (
        parse_waha_webhook(
            {"event": "message", "payload": {"from": "393331234567@c.us", "body": "ok"}}
        )
        == []
    )
    assert (
        parse_waha_webhook({"event": "message", "payload": {"from": "123@g.us", "body": "stop"}})
        == []
    )
    assert (
        parse_waha_webhook(
            {
                "event": "message",
                "payload": {"from": "393331234567@c.us", "body": "stop", "fromMe": True},
            }
        )
        == []
    )
    assert parse_waha_webhook({"event": "message", "payload": "bad"}) == []
    assert parse_waha_webhook({"event": "session.status", "payload": {}}) == []
