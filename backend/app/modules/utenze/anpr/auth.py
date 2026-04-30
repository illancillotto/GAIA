from __future__ import annotations

import base64
import hashlib
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
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


class PdndAuthManager:
    _voucher_cache: dict[str, str | float] = {}

    def _load_private_key(self) -> rsa.RSAPrivateKey:
        private_key_pem = (settings.pdnd_private_key_pem or "").strip()
        private_key_path = (settings.pdnd_private_key_path or "").strip()

        if private_key_path:
            private_key_pem = Path(private_key_path).read_text(encoding="utf-8")
        elif not private_key_pem:
            raise ValueError("PDND private key not configured: set PDND_PRIVATE_KEY_PATH or PDND_PRIVATE_KEY_PEM")

        key = serialization.load_pem_private_key(private_key_pem.encode("utf-8"), password=None)
        if not isinstance(key, rsa.RSAPrivateKey):
            raise TypeError("PDND private key must be an RSA private key")
        return key

    def _build_client_assertion(self) -> str:
        now = datetime.now(UTC)
        payload = {
            "iss": settings.pdnd_client_id,
            "sub": settings.pdnd_client_id,
            "aud": settings.pdnd_auth_url,
            "jti": str(uuid4()),
            "iat": now,
            "exp": now + timedelta(seconds=60),
        }
        headers = {"kid": settings.pdnd_kid}
        return jwt.encode(payload, self._load_private_key(), algorithm="RS256", headers=headers)

    async def get_voucher(self) -> str:
        now_ts = time.time()
        cached_token = self._voucher_cache.get("token")
        cached_expiry = self._voucher_cache.get("expires_at")
        if isinstance(cached_token, str) and isinstance(cached_expiry, (int, float)) and cached_expiry > now_ts + 300:
            return cached_token

        payload = {
            "grant_type": "client_credentials",
            "client_assertion_type": CLIENT_ASSERTION_TYPE,
            "client_assertion": self._build_client_assertion(),
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(settings.pdnd_auth_url, data=payload)
            response.raise_for_status()

        token_payload = response.json()
        access_token = token_payload["access_token"]
        expires_in = int(token_payload.get("expires_in", 0))
        self._voucher_cache = {
            "token": access_token,
            "expires_at": now_ts + expires_in,
        }
        logger.info("PDND voucher refreshed; expires_in=%s", expires_in)
        return access_token

    def build_agid_jwt_signature(self, payload_bytes: bytes) -> str:
        now = datetime.now(UTC)
        digest = _base64url_encode(hashlib.sha256(payload_bytes).digest())
        claims = {
            "iat": now,
            "exp": now + timedelta(seconds=300),
            "jti": str(uuid4()),
            "digest": {
                "alg": "SHA-256",
                "value": digest,
            },
            "signed_headers": [
                {"digest": f"SHA-256={digest}"},
                {"content-type": "application/json"},
            ],
        }
        headers = {
            "alg": "RS256",
            "kid": settings.pdnd_kid,
            "typ": "JWT",
        }
        return jwt.encode(claims, self._load_private_key(), algorithm="RS256", headers=headers)

    def build_agid_jwt_tracking_evidence(self, motivo_richiesta: str) -> str:
        now = datetime.now(UTC)
        claims = {
            "iat": now,
            "exp": now + timedelta(seconds=300),
            "jti": str(uuid4()),
            "userID": settings.pdnd_fruitore_user_id,
            "userLocation": settings.pdnd_fruitore_user_location,
            "LoA": settings.pdnd_loa,
            "purpose": motivo_richiesta,
        }
        headers = {
            "alg": "RS256",
            "kid": settings.pdnd_kid,
            "typ": "JWT",
        }
        return jwt.encode(claims, self._load_private_key(), algorithm="RS256", headers=headers)
