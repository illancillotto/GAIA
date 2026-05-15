from __future__ import annotations

import asyncio
import base64
import hashlib
from datetime import datetime, timezone

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.modules.utenze.anpr.auth import PdndAuthManager, PdndConfigurationError


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
    monkeypatch.setattr("app.modules.utenze.anpr.auth.settings.pdnd_client_assertion_audience", "")
    monkeypatch.setattr(manager, "_load_private_key", lambda: private_key)

    token = manager._build_client_assertion("purpose-123", tracking_digest="deadbeef")
    headers = jwt.get_unverified_header(token)
    claims = jwt.decode(
        token,
        public_key_pem,
        algorithms=["RS256"],
        audience="auth.example.test/client-assertion",
    )

    assert headers["kid"] == "kid-xyz"
    assert claims["iss"] == "client-abc"
    assert claims["sub"] == "client-abc"
    assert claims["aud"] == "auth.example.test/client-assertion"
    assert claims["purposeId"] == "purpose-123"
    assert claims["digest"]["alg"] == "SHA256"
    assert claims["digest"]["value"] == "deadbeef"
    assert claims["jti"]
    assert claims["exp"] >= claims["iat"]


def test_build_client_assertion_uses_explicit_audience_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    private_key, public_key_pem = _generate_test_rsa_keypair()
    manager = PdndAuthManager()

    monkeypatch.setattr("app.modules.utenze.anpr.auth.settings.pdnd_client_id", "client-abc")
    monkeypatch.setattr("app.modules.utenze.anpr.auth.settings.pdnd_kid", "kid-xyz")
    monkeypatch.setattr("app.modules.utenze.anpr.auth.settings.pdnd_client_assertion_audience", "pdnd.example.test/client-assertion")
    monkeypatch.setattr(manager, "_load_private_key", lambda: private_key)

    token = manager._build_client_assertion()
    claims = jwt.decode(
        token,
        public_key_pem,
        algorithms=["RS256"],
        audience="pdnd.example.test/client-assertion",
    )

    assert claims["aud"] == "pdnd.example.test/client-assertion"


def test_build_agid_jwt_signature_contains_digest_claim(monkeypatch: pytest.MonkeyPatch) -> None:
    private_key, public_key_pem = _generate_test_rsa_keypair()
    manager = PdndAuthManager()
    payload = b'{"hello":"world"}'
    expected_digest = _base64url_encode(hashlib.sha256(payload).digest())

    monkeypatch.setattr("app.modules.utenze.anpr.auth.settings.pdnd_client_id", "client-abc")
    monkeypatch.setattr("app.modules.utenze.anpr.auth.settings.pdnd_kid", "kid-signature")
    monkeypatch.setattr(manager, "_load_private_key", lambda: private_key)

    token = manager.build_agid_jwt_signature(
        payload,
        endpoint_url="https://modipa-val.anpr.interno.it/govway/rest/in/MinInternoPortaANPR-PDND/C030-servizioAccertamentoIdUnicoNazionale/v1/anpr-service-e002",
        digest_header=f"SHA-256={expected_digest}",
    )
    headers = jwt.get_unverified_header(token)
    claims = jwt.decode(token, public_key_pem, algorithms=["RS256"], options={"verify_aud": False})

    assert headers["kid"] == "kid-signature"
    assert claims["aud"] == "https://modipa-val.anpr.interno.it/govway/rest/in/MinInternoPortaANPR/C030-servizioAccertamentoIdUnicoNazionale/v1"
    assert "iss" not in claims
    assert "sub" not in claims
    assert "digest" not in claims
    assert claims["signed_headers"][0]["digest"] == f"SHA-256={expected_digest}"
    assert claims["signed_headers"][1]["content-type"] == "application/json"


def test_build_agid_jwt_tracking_evidence_contains_expected_claims(monkeypatch: pytest.MonkeyPatch) -> None:
    private_key, public_key_pem = _generate_test_rsa_keypair()
    manager = PdndAuthManager()

    monkeypatch.setattr("app.modules.utenze.anpr.auth.settings.pdnd_client_id", "client-abc")
    monkeypatch.setattr("app.modules.utenze.anpr.auth.settings.pdnd_kid", "kid-track")
    monkeypatch.setattr("app.modules.utenze.anpr.auth.settings.pdnd_fruitore_user_id", "GAIA-CBO")
    monkeypatch.setattr("app.modules.utenze.anpr.auth.settings.pdnd_fruitore_user_location", "GAIA-SRV")
    monkeypatch.setattr("app.modules.utenze.anpr.auth.settings.pdnd_loa", "LOW")
    monkeypatch.setattr(manager, "_load_private_key", lambda: private_key)

    token = manager.build_agid_jwt_tracking_evidence(
        endpoint_url="https://modipa-val.anpr.interno.it/govway/rest/in/MinInternoPortaANPR-PDND/C004-servizioVerificaDichDecesso/v1/anpr-service-e002",
        purpose_id="purpose-c004",
    )
    headers = jwt.get_unverified_header(token)
    claims = jwt.decode(token, public_key_pem, algorithms=["RS256"], options={"verify_aud": False})

    assert headers["kid"] == "kid-track"
    assert claims["iss"] == "client-abc"
    assert claims["sub"] == "client-abc"
    assert claims["aud"] == "https://modipa-val.anpr.interno.it/govway/rest/in/MinInternoPortaANPR/C004-servizioVerificaDichDecesso/v1"
    assert claims["userID"] == "GAIA-CBO"
    assert claims["userLocation"] == "GAIA-SRV"
    assert claims["LoA"] == "LOW"
    assert claims["purposeId"] == "purpose-c004"


def test_get_voucher_uses_cache_until_near_expiry(monkeypatch: pytest.MonkeyPatch) -> None:
    manager = PdndAuthManager()
    manager._voucher_cache = {}

    monkeypatch.setattr(
        manager,
        "_build_client_assertion",
        lambda purpose_id=None, tracking_digest=None: f"assertion-token-{purpose_id or 'default'}-{tracking_digest or 'nodigest'}",
    )
    monkeypatch.setattr("app.modules.utenze.anpr.auth.settings.pdnd_client_id", "client-abc")
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

    first = asyncio.run(manager.get_voucher("purpose-c030", "digest-a"))
    second = asyncio.run(manager.get_voucher("purpose-c030", "digest-a"))
    third = asyncio.run(manager.get_voucher("purpose-c004", "digest-b"))

    assert first == "voucher-1"
    assert second == "voucher-1"
    assert third == "voucher-1"
    assert len(calls) == 2
    assert calls[0]["url"] == "https://auth.example.test/token"
    assert calls[0]["data"]["grant_type"] == "client_credentials"
    assert calls[0]["data"]["client_id"] == "client-abc"
    assert calls[0]["data"]["client_assertion"] == "assertion-token-purpose-c030-digest-a"
    assert calls[1]["data"]["client_assertion"] == "assertion-token-purpose-c004-digest-b"


def test_build_client_assertion_requires_client_id(monkeypatch: pytest.MonkeyPatch) -> None:
    manager = PdndAuthManager()

    monkeypatch.setattr("app.modules.utenze.anpr.auth.settings.pdnd_client_id", "")
    monkeypatch.setattr("app.modules.utenze.anpr.auth.settings.pdnd_kid", "kid-xyz")

    with pytest.raises(PdndConfigurationError, match="PDND client id not configured"):
        manager._build_client_assertion()


def test_load_private_key_requires_existing_file(monkeypatch: pytest.MonkeyPatch) -> None:
    manager = PdndAuthManager()

    monkeypatch.setattr("app.modules.utenze.anpr.auth.settings.pdnd_private_key_path", "/tmp/missing-pdnd-key.pem")
    monkeypatch.setattr("app.modules.utenze.anpr.auth.settings.pdnd_private_key_pem", "")

    with pytest.raises(PdndConfigurationError, match="PDND private key file not found"):
        manager._load_private_key()
