from __future__ import annotations

import asyncio
import base64
import hashlib
from datetime import datetime, timezone

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.modules.utenze.anpr.auth import PdndAuthManager


UTC = timezone.utc


def _generate_test_rsa_keypair() -> tuple[rsa.RSAPrivateKey, bytes]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_key, public_key_pem


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def test_build_client_assertion_contains_expected_claims(monkeypatch: pytest.MonkeyPatch) -> None:
    private_key, public_key_pem = _generate_test_rsa_keypair()
    manager = PdndAuthManager()

    monkeypatch.setattr("app.modules.utenze.anpr.auth.settings.pdnd_client_id", "client-abc")
    monkeypatch.setattr("app.modules.utenze.anpr.auth.settings.pdnd_kid", "kid-xyz")
    monkeypatch.setattr("app.modules.utenze.anpr.auth.settings.pdnd_auth_url", "https://auth.example.test/token")
    monkeypatch.setattr(manager, "_load_private_key", lambda: private_key)

    token = manager._build_client_assertion()
    headers = jwt.get_unverified_header(token)
    claims = jwt.decode(
        token,
        public_key_pem,
        algorithms=["RS256"],
        audience="https://auth.example.test/token",
    )

    assert headers["kid"] == "kid-xyz"
    assert claims["iss"] == "client-abc"
    assert claims["sub"] == "client-abc"
    assert claims["aud"] == "https://auth.example.test/token"
    assert claims["jti"]
    assert claims["exp"] >= claims["iat"]


def test_build_agid_jwt_signature_contains_digest_claim(monkeypatch: pytest.MonkeyPatch) -> None:
    private_key, public_key_pem = _generate_test_rsa_keypair()
    manager = PdndAuthManager()
    payload = b'{"hello":"world"}'
    expected_digest = _base64url_encode(hashlib.sha256(payload).digest())

    monkeypatch.setattr("app.modules.utenze.anpr.auth.settings.pdnd_kid", "kid-signature")
    monkeypatch.setattr(manager, "_load_private_key", lambda: private_key)

    token = manager.build_agid_jwt_signature(payload)
    headers = jwt.get_unverified_header(token)
    claims = jwt.decode(token, public_key_pem, algorithms=["RS256"], options={"verify_aud": False})

    assert headers["kid"] == "kid-signature"
    assert claims["digest"]["alg"] == "SHA-256"
    assert claims["digest"]["value"] == expected_digest
    assert claims["signed_headers"][1]["content-type"] == "application/json"


def test_build_agid_jwt_tracking_evidence_contains_expected_claims(monkeypatch: pytest.MonkeyPatch) -> None:
    private_key, public_key_pem = _generate_test_rsa_keypair()
    manager = PdndAuthManager()

    monkeypatch.setattr("app.modules.utenze.anpr.auth.settings.pdnd_kid", "kid-track")
    monkeypatch.setattr("app.modules.utenze.anpr.auth.settings.pdnd_fruitore_user_id", "GAIA-CBO")
    monkeypatch.setattr("app.modules.utenze.anpr.auth.settings.pdnd_fruitore_user_location", "GAIA-SRV")
    monkeypatch.setattr("app.modules.utenze.anpr.auth.settings.pdnd_loa", "LOW")
    monkeypatch.setattr(manager, "_load_private_key", lambda: private_key)

    token = manager.build_agid_jwt_tracking_evidence("GAIA-CHECK-123")
    headers = jwt.get_unverified_header(token)
    claims = jwt.decode(token, public_key_pem, algorithms=["RS256"], options={"verify_aud": False})

    assert headers["kid"] == "kid-track"
    assert claims["userID"] == "GAIA-CBO"
    assert claims["userLocation"] == "GAIA-SRV"
    assert claims["LoA"] == "LOW"
    assert claims["purpose"] == "GAIA-CHECK-123"


def test_get_voucher_uses_cache_until_near_expiry(monkeypatch: pytest.MonkeyPatch) -> None:
    manager = PdndAuthManager()
    manager._voucher_cache = {}

    monkeypatch.setattr(manager, "_build_client_assertion", lambda: "assertion-token")
    monkeypatch.setattr("app.modules.utenze.anpr.auth.settings.pdnd_auth_url", "https://auth.example.test/token")

    calls: list[dict] = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"access_token": "voucher-1", "expires_in": 3600}

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, data: dict[str, str]) -> FakeResponse:
            calls.append({"url": url, "data": data})
            return FakeResponse()

    monkeypatch.setattr("app.modules.utenze.anpr.auth.httpx.AsyncClient", FakeAsyncClient)

    first = asyncio.run(manager.get_voucher())
    second = asyncio.run(manager.get_voucher())

    assert first == "voucher-1"
    assert second == "voucher-1"
    assert len(calls) == 1
    assert calls[0]["url"] == "https://auth.example.test/token"
    assert calls[0]["data"]["grant_type"] == "client_credentials"
    assert calls[0]["data"]["client_assertion"] == "assertion-token"
