from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any

import httpx

from app.modules.presenze.services.whatsapp_config import WhatsAppRuntimeConfig


class WahaSessionError(Exception):
    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class WahaSessionManager:
    config: WhatsAppRuntimeConfig
    client: httpx.Client | None = None

    @property
    def session(self) -> str:
        return self.config.waha_session or "default"

    def status(self) -> dict[str, str | None]:
        response = self._request("GET", f"/api/sessions/{self.session}", allow_not_found=True)
        if response.status_code == 404:
            return _session_payload(self.session, "not_created", None)
        return _session_response(self.session, response)

    def start(self) -> dict[str, str | None]:
        current = self._request("GET", f"/api/sessions/{self.session}", allow_not_found=True)
        if current.status_code == 404:
            response = self._request(
                "POST", "/api/sessions", json={"name": self.session, "start": True}
            )
        else:
            status = _session_response(self.session, current)["status"]
            # WAHA considers FAILED sessions running, so /start cannot recover them.
            action = "restart" if status == "failed" else "start"
            response = self._request("POST", f"/api/sessions/{self.session}/{action}")
        return _session_response(self.session, response)

    def logout(self) -> dict[str, str | None]:
        response = self._request("POST", f"/api/sessions/{self.session}/logout", json={})
        return _session_response(self.session, response)

    def qr_code(self) -> dict[str, str]:
        response = self._request(
            "GET",
            f"/api/{self.session}/auth/qr",
            accept="image/png",
            params={"format": "image"},
        )
        content_type = response.headers.get("content-type", "").split(";", 1)[0]
        if content_type != "image/png" or not response.content:
            raise WahaSessionError("WAHA non ha restituito un QR valido", status_code=502)
        encoded = base64.b64encode(response.content).decode("ascii")
        return {"image_data_url": f"data:image/png;base64,{encoded}"}

    def _request(
        self,
        method: str,
        path: str,
        *,
        accept: str = "application/json",
        allow_not_found: bool = False,
        **kwargs: Any,
    ) -> httpx.Response:
        if not self.config.waha_url or not self.config.waha_api_key:
            raise WahaSessionError("Configurazione WAHA incompleta", status_code=409)
        request = self.client.request if self.client is not None else httpx.request
        try:
            response = request(
                method,
                self.config.waha_url.rstrip("/") + path,
                headers={"accept": accept, "x-api-key": self.config.waha_api_key},
                timeout=10.0,
                **kwargs,
            )
        except httpx.HTTPError as exc:
            raise WahaSessionError("WAHA non raggiungibile", status_code=503) from exc
        if response.is_success or (allow_not_found and response.status_code == 404):
            return response
        message = _error_message(response)
        status_code = 409 if response.status_code in {404, 409, 422} else 502
        raise WahaSessionError(message, status_code=status_code)


def _session_response(session: str, response: httpx.Response) -> dict[str, str | None]:
    try:
        body = response.json()
    except ValueError as exc:
        raise WahaSessionError("Risposta WAHA non valida", status_code=502) from exc
    if not isinstance(body, dict):
        raise WahaSessionError("Risposta WAHA non valida", status_code=502)
    status = body.get("status")
    if not isinstance(status, str) or not status.strip():
        raise WahaSessionError("Stato sessione WAHA assente", status_code=502)
    me = body.get("me") if isinstance(body.get("me"), dict) else None
    return _session_payload(session, status.strip().lower(), me)


def _session_payload(session: str, status: str, me: dict[str, Any] | None) -> dict[str, str | None]:
    raw_id = me.get("id") if me else None
    phone = raw_id.split("@", 1)[0] if isinstance(raw_id, str) and "@" in raw_id else None
    display_name = me.get("pushName") if me and isinstance(me.get("pushName"), str) else None
    return {"name": session, "status": status, "phone": phone, "display_name": display_name}


def _error_message(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        body = None
    message = body.get("message") if isinstance(body, dict) else None
    return message if isinstance(message, str) and message else f"WAHA HTTP {response.status_code}"
