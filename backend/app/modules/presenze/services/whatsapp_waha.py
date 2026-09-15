"""Canale WhatsApp NON ufficiale tramite WAHA (WhatsApp HTTP API) self-hosted.

Un numero aziendale dedicato e collegato via QR a una sessione WhatsApp Web nel
container WAHA. Il numero puo essere bloccato da WhatsApp: l'invio va dosato con
``punch_reminder_dispatch`` e il canale resta un avviso di cortesia.
"""

from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.modules.presenze.services.whatsapp_config import (
    WhatsAppRuntimeConfig,
    environment_whatsapp_config,
)

PROVIDER_WAHA = "waha"
PROVIDER_DRY_RUN = "dry_run"
_OPT_OUT_RE = re.compile(r"^(stop|basta|disiscrivi)$", re.IGNORECASE)
_CHAT_ID_RE = re.compile(r"^(\d{8,15})@c\.us$")
_ACK_STATUS = {"-1": "FAILED", "1": "SENT", "2": "DELIVERED", "3": "READ", "4": "READ"}


class WhatsAppSendError(Exception):
    def __init__(
        self, message: str, *, retryable: bool, code: str, uncertain: bool = False
    ) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.code = code
        self.uncertain = uncertain


@dataclass(frozen=True)
class WhatsAppSendResult:
    status: str
    provider: str
    provider_message_id: str | None


class WhatsAppSender(Protocol):
    provider: str

    def check_number(self, phone_e164: str) -> bool: ...

    def send_text(self, phone_e164: str, text: str) -> WhatsAppSendResult: ...


@dataclass(frozen=True)
class WhatsAppAck:
    provider_message_id: str
    status: str


@dataclass(frozen=True)
class WhatsAppOptOut:
    phone_e164: str
    text: str


class WahaWhatsAppSender:
    provider = PROVIDER_WAHA

    def __init__(
        self, *, base_url: str, api_key: str, session: str, client: httpx.Client | None = None
    ) -> None:
        self._session = session
        self._client = client or httpx.Client(timeout=20.0)
        self._base_url = base_url.rstrip("/")
        self._headers = {"accept": "application/json", "x-api-key": api_key}

    def check_number(self, phone_e164: str) -> bool:
        params = {"phone": phone_e164.lstrip("+"), "session": self._session}
        body = self._request("GET", "/api/contacts/check-exists", params=params)
        exists = body.get("numberExists")
        if not isinstance(exists, bool):
            raise WhatsAppSendError(
                "Risposta WAHA check-exists non valida", retryable=True, code="invalid_response"
            )
        return exists

    def send_text(self, phone_e164: str, text: str) -> WhatsAppSendResult:
        payload = {"session": self._session, "chatId": waha_chat_id(phone_e164), "text": text}
        try:
            body = self._request("POST", "/api/sendText", json=payload)
        except WhatsAppSendError as exc:
            # Una risposta persa o un errore server non prova che il messaggio non sia partito.
            exc.uncertain = exc.retryable and exc.code != "http_429"
            raise
        message_id = waha_message_id(body.get("id"))
        if message_id is None:
            raise WhatsAppSendError(
                "Risposta WAHA sendText senza ID",
                retryable=False,
                code="invalid_response",
                uncertain=True,
            )
        return WhatsAppSendResult("SENT", PROVIDER_WAHA, message_id)

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = self._client.request(
                method, self._base_url + path, headers=self._headers, **kwargs
            )
        except httpx.HTTPError as exc:
            raise WhatsAppSendError(
                f"WAHA non raggiungibile: {exc}", retryable=True, code="network_error"
            ) from exc
        body = _json_object(response)
        if response.is_success:
            return body
        message = (
            body.get("message")
            if isinstance(body.get("message"), str)
            else f"WAHA HTTP {response.status_code}"
        )
        retryable = response.status_code == 429 or response.status_code >= 500
        raise WhatsAppSendError(message, retryable=retryable, code=f"http_{response.status_code}")


class DryRunWhatsAppSender:
    provider = PROVIDER_DRY_RUN

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def check_number(self, phone_e164: str) -> bool:
        return True

    def send_text(self, phone_e164: str, text: str) -> WhatsAppSendResult:
        self.sent.append((phone_e164, text))
        return WhatsAppSendResult("DRY_RUN", PROVIDER_DRY_RUN, None)


def build_whatsapp_sender(config: WhatsAppRuntimeConfig) -> WhatsAppSender | None:
    provider = config.provider.strip().lower()
    if provider == PROVIDER_DRY_RUN:
        return DryRunWhatsAppSender()
    if provider != PROVIDER_WAHA:
        return None
    if not config.waha_url or not config.waha_api_key:
        raise ValueError(
            "PRESENZE_WHATSAPP_PROVIDER=waha richiede PRESENZE_WHATSAPP_WAHA_URL e PRESENZE_WHATSAPP_WAHA_API_KEY"
        )
    return WahaWhatsAppSender(
        base_url=config.waha_url,
        api_key=config.waha_api_key,
        session=config.waha_session or "default",
    )


def build_whatsapp_sender_from_settings() -> WhatsAppSender | None:
    """Compatibility helper for environment-only callers and isolated tests."""
    return build_whatsapp_sender(environment_whatsapp_config())


def waha_chat_id(phone_e164: str) -> str:
    return phone_e164.lstrip("+") + "@c.us"


def waha_message_id(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    serialized = value.get("_serialized") if isinstance(value, dict) else None
    return serialized if isinstance(serialized, str) and serialized else None


def verify_waha_signature(raw_body: bytes, signature: str | None, hmac_key: str) -> bool:
    expected = hmac.new(hmac_key.encode(), raw_body, hashlib.sha512).hexdigest()
    return hmac.compare_digest((signature or "").strip().lower(), expected)


def parse_waha_webhook(body: Any) -> list[WhatsAppAck | WhatsAppOptOut]:
    event = body if isinstance(body, dict) else {}
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    if event.get("event") == "message.ack":
        return _ack_events(payload)
    if event.get("event") == "message":
        return _opt_out_events(payload)
    return []


def _ack_events(payload: dict[str, Any]) -> list[WhatsAppAck | WhatsAppOptOut]:
    message_id = waha_message_id(payload.get("id"))
    status = _ACK_STATUS.get(str(payload.get("ack")))
    return [WhatsAppAck(message_id, status)] if message_id and status else []


def _opt_out_events(payload: dict[str, Any]) -> list[WhatsAppAck | WhatsAppOptOut]:
    if payload.get("fromMe") is True:
        return []
    match = _CHAT_ID_RE.match(str(payload.get("from") or ""))
    text = str(payload.get("body") or "").strip()
    if match is None or not _OPT_OUT_RE.match(text):
        return []
    return [WhatsAppOptOut("+" + match.group(1), text)]


def _json_object(response: httpx.Response) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}
