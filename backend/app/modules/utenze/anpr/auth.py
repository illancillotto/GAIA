from __future__ import annotations

import base64
import hashlib
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import httpx
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.config import settings

logger = logging.getLogger(__name__)

UTC = timezone.utc
CLIENT_ASSERTION_TYPE = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _normalize_anpr_audience(endpoint_url: str) -> str:
    normalized = endpoint_url.rstrip("/")
    if normalized.endswith("/anpr-service-e002"):
        normalized = normalized[: -len("/anpr-service-e002")]
    return normalized.replace("/MinInternoPortaANPR-PDND/", "/MinInternoPortaANPR/")


class PdndConfigurationError(ValueError):
    """Raised when PDND credentials are missing or invalid."""


class PdndAuthManager:
    _voucher_cache: dict[str, dict[str, str | float]] = {}

    def _validate_settings(self) -> None:
        if not (settings.pdnd_client_id or "").strip():
            raise PdndConfigurationError("PDND client id not configured: set PDND_CLIENT_ID")
        if not (settings.pdnd_kid or "").strip():
            raise PdndConfigurationError("PDND key id not configured: set PDND_KID")

    def _load_private_key(self) -> rsa.RSAPrivateKey:
        private_key_pem = (settings.pdnd_private_key_pem or "").strip()
        private_key_path = (settings.pdnd_private_key_path or "").strip()

        if private_key_path:
            try:
                private_key_pem = Path(private_key_path).read_text(encoding="utf-8")
            except FileNotFoundError as exc:
                raise PdndConfigurationError(
                    f"PDND private key file not found: {private_key_path}"
                ) from exc
        elif not private_key_pem:
            raise PdndConfigurationError(
                "PDND private key not configured: set PDND_PRIVATE_KEY_PATH or PDND_PRIVATE_KEY_PEM"
            )

        try:
            key = serialization.load_pem_private_key(private_key_pem.encode("utf-8"), password=None)
        except (TypeError, ValueError) as exc:
            raise PdndConfigurationError("PDND private key is not a valid PEM RSA private key") from exc
        if not isinstance(key, rsa.RSAPrivateKey):
            raise PdndConfigurationError("PDND private key must be an RSA private key")
        return key

    @staticmethod
    def _build_client_assertion_audience() -> str:
        configured = (settings.pdnd_client_assertion_audience or "").strip()
        if configured:
            return configured

        parsed = urlparse(settings.pdnd_auth_url)
        if parsed.netloc:
            return f"{parsed.netloc}/client-assertion"
        if parsed.path:
            return f"{parsed.path.rstrip('/')}/client-assertion"
        raise PdndConfigurationError("Unable to derive PDND client assertion audience from PDND_AUTH_URL")

    def _build_client_assertion(self, purpose_id: str | None = None, tracking_digest: str | None = None) -> str:
        self._validate_settings()
        now = datetime.now(UTC)
        payload = {
            "iss": settings.pdnd_client_id,
            "sub": settings.pdnd_client_id,
            "aud": self._build_client_assertion_audience(),
            "jti": str(uuid4()),
            "iat": now,
            "exp": now + timedelta(seconds=60),
        }
        if purpose_id:
            payload["purposeId"] = purpose_id
        if tracking_digest:
            payload["digest"] = {
                "alg": "SHA256",
                "value": tracking_digest,
            }
        headers = {"kid": settings.pdnd_kid}
        return jwt.encode(payload, self._load_private_key(), algorithm="RS256", headers=headers)

    async def get_voucher(self, purpose_id: str | None = None, tracking_digest: str | None = None) -> str:
        now_ts = time.time()
        digest_key = (tracking_digest or "").strip() or "__default__"
        cache_key = f"{(purpose_id or '__default__').strip() or '__default__'}::{digest_key}"
        cached_entry = self._voucher_cache.get(cache_key) or {}
        cached_token = cached_entry.get("token")
        cached_expiry = cached_entry.get("expires_at")
        if isinstance(cached_token, str) and isinstance(cached_expiry, (int, float)) and cached_expiry > now_ts + 300:
            return cached_token

        payload = {
            "grant_type": "client_credentials",
            "client_id": settings.pdnd_client_id,
            "client_assertion_type": CLIENT_ASSERTION_TYPE,
            "client_assertion": self._build_client_assertion(purpose_id, tracking_digest=tracking_digest),
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(settings.pdnd_auth_url, data=payload)
            response.raise_for_status()

        token_payload = response.json()
        access_token = token_payload["access_token"]
        expires_in = int(token_payload.get("expires_in", 0))
        self._voucher_cache[cache_key] = {
            "token": access_token,
            "expires_at": now_ts + expires_in,
        }
        logger.info("PDND voucher refreshed; purpose=%s expires_in=%s", purpose_id or "<default>", expires_in)
        return access_token

    def build_agid_jwt_signature(
        self,
        payload_bytes: bytes,
        *,
        endpoint_url: str,
        digest_header: str,
    ) -> str:
        self._validate_settings()
        now = datetime.now(UTC)
        del payload_bytes
        claims = {
            "aud": _normalize_anpr_audience(endpoint_url),
            "nbf": now,
            "iat": now,
            "exp": now + timedelta(seconds=300),
            "jti": str(uuid4()),
            "signed_headers": [
                {"digest": digest_header},
                {"content-type": "application/json"},
            ],
        }
        headers = {
            "alg": "RS256",
            "kid": settings.pdnd_kid,
            "typ": "JWT",
        }
        return jwt.encode(claims, self._load_private_key(), algorithm="RS256", headers=headers)

    def build_agid_jwt_tracking_evidence(
        self,
        *,
        endpoint_url: str,
        purpose_id: str | None = None,
    ) -> str:
        self._validate_settings()
        now = datetime.now(UTC)
        claims = {
            "iss": settings.pdnd_client_id,
            "sub": settings.pdnd_client_id,
            "aud": _normalize_anpr_audience(endpoint_url),
            "nbf": now,
            "iat": now,
            "exp": now + timedelta(seconds=300),
            "jti": str(uuid4()),
            "userID": settings.pdnd_fruitore_user_id,
            "userLocation": settings.pdnd_fruitore_user_location,
            "LoA": settings.pdnd_loa,
        }
        if purpose_id:
            claims["purposeId"] = purpose_id
        headers = {
            "alg": "RS256",
            "kid": settings.pdnd_kid,
            "typ": "JWT",
        }
        return jwt.encode(claims, self._load_private_key(), algorithm="RS256", headers=headers)
