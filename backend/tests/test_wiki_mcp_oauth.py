import asyncio
import base64
import hashlib
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from fastapi import HTTPException
from mcp import types
from mcp.server.auth.provider import AuthorizationParams, AuthorizeError, TokenError
from mcp.shared.auth import OAuthClientInformationFull

from app.modules.wiki.mcps import oauth_gaia
from app.modules.wiki.mcps.context import CallContext
from app.modules.wiki.mcps.data.database import seed_database
from app.modules.wiki.mcps.data.server import create_server
from app.modules.wiki.mcps.data.service import DataService
from app.modules.wiki.mcps.oauth_http import create_oauth_app
from app.modules.wiki.mcps.oauth_provider import GAIAOAuthProvider, https_url
from app.modules.wiki.mcps.oauth_store import OAuthStore, token_hash

RESOURCE = "https://synthetic.example/mcp"
ISSUER = "https://synthetic.example/oauth"
REDIRECT = "https://client.example/callback"
VERIFIER = "synthetic-verifier-" + "x" * 48
CHALLENGE = (
    base64.urlsafe_b64encode(hashlib.sha256(VERIFIER.encode()).digest()).decode().rstrip("=")
)


def client(client_id="approved", **changes):
    return OAuthClientInformationFull.model_validate(
        {
            "client_id": client_id,
            "client_name": "Synthetic connector",
            "redirect_uris": [REDIRECT],
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code", "refresh_token"],
            "scope": "utenze.read catasto.read ruolo.read",
            **changes,
        }
    )


def params(**changes):
    return AuthorizationParams.model_validate(
        {
            "state": "synthetic-state",
            "scopes": ["utenze.read"],
            "code_challenge": CHALLENGE,
            "redirect_uri": REDIRECT,
            "redirect_uri_provided_explicitly": True,
            "resource": RESOURCE,
            **changes,
        }
    )


@pytest.fixture
def foundation(tmp_path):
    store = OAuthStore(tmp_path / "gaia-mcp-oauth.sqlite")
    permissions = {"1": {"utenze.read", "catasto.read", "docs.read", "mcp.audit.read"}}
    approved = client()
    provider = GAIAOAuthProvider(
        store,
        {approved.client_id: approved},
        lambda subject: permissions.get(subject, set()),
        resource=RESOURCE,
        consent_url="https://synthetic.example/consent",
    )
    yield store, permissions, approved, provider
    store.close()


async def issue_code(provider, approved, **changes):
    target = await provider.authorize(approved, params(**changes))
    request_id = parse_qs(urlsplit(target).query)["request_id"][0]
    response = provider.consent(request_id, "1", True)
    assert parse_qs(urlsplit(response).query).get("state") == ["synthetic-state"]
    return parse_qs(urlsplit(response).query)["code"][0]


def test_store_security_transactions_and_expiry(tmp_path, monkeypatch):
    with pytest.raises(ValueError):
        OAuthStore(tmp_path / "real.sqlite")
    path = tmp_path / "gaia-mcp-oauth.sqlite"
    path.symlink_to(tmp_path / "other")
    with pytest.raises(ValueError):
        OAuthStore(path)
    path.unlink()
    store = OAuthStore(path)
    assert path.stat().st_mode & 0o777 == 0o600
    token = store.put("code", {"client_id": "approved"}, lifetime=60)
    assert token.encode() not in path.read_bytes()
    assert store.consume("code", token, client_id="other") is None
    assert store.get("code", token)
    with pytest.raises(RuntimeError), store.transaction():
        store.consume("code", token)
        raise RuntimeError("rollback")
    assert store.get("code", token)
    assert store.consume("code", token)["client_id"] == "approved"
    assert store.consume("code", token) is None
    store.revoke(token)
    assert store.get("used_code", token)
    expiring = store.put("access", {}, lifetime=-1)
    assert store.get("access", expiring) is None
    store.cleanup()
    assert store.connection.execute("SELECT COUNT(*) FROM grants").fetchone()[0] == 1
    assert len(token_hash(token)) == 64
    store.close()


@pytest.mark.parametrize(
    "url",
    [
        "http://example.test",
        "https:///",
        "https://u:p@a.test",
        "https://a.test?q=1",
        "https://a.test/#frag",
    ],
)
def test_https_required(url):
    with pytest.raises(ValueError):
        https_url(url)


def test_configuration_requires_preapproved_public_clients(foundation):
    store, _, _, provider = foundation
    for clients in [
        {},
        {"bad": client(token_endpoint_auth_method="client_secret_post")},
        {"bad": client(redirect_uris=[])},
        {"bad": client(redirect_uris=["http://bad.test"])},
    ]:
        with pytest.raises(ValueError):
            GAIAOAuthProvider(
                store, clients, lambda _: set(), resource=RESOURCE, consent_url=RESOURCE
            )
    assert asyncio.run(provider.get_client("unknown")) is None
    with pytest.raises(NotImplementedError):
        asyncio.run(provider.register_client(client()))


@pytest.mark.parametrize(
    "changes,error",
    [
        ({"resource": "https://other.example/mcp"}, "invalid_target"),
        ({"scopes": ["docs.read"]}, "invalid_scope"),
        ({"scopes": ["mcp.audit.read"]}, "invalid_scope"),
        ({"scopes": None}, "invalid_scope"),
        ({"redirect_uri": "https://attacker.example/"}, "invalid_request"),
    ],
)
def test_authorization_is_data_only_and_bound(foundation, changes, error):
    _, _, approved, provider = foundation
    with pytest.raises(AuthorizeError) as caught:
        asyncio.run(provider.authorize(approved, params(**changes)))
    assert caught.value.error == error
    with pytest.raises(AuthorizeError):
        asyncio.run(provider.authorize(client("other"), params()))


def test_consent_expiration_denial_and_configuration_change(foundation):
    store, permissions, approved, provider = foundation
    with pytest.raises(ValueError):
        provider.consent_details("missing")
    with pytest.raises(ValueError):
        provider.consent("missing", "1", True)
    for allowed, subject, state in [(False, "1", "state"), (True, "2", None)]:
        target = asyncio.run(provider.authorize(approved, params(state=state)))
        request_id = parse_qs(urlsplit(target).query)["request_id"][0]
        approved.client_name = None
        assert provider.consent_details(request_id)["client_name"] == approved.client_id
        assert "access_denied" in provider.consent(request_id, subject, allowed)
        with pytest.raises(ValueError):
            provider.consent(request_id, subject, True)
    target = asyncio.run(provider.authorize(approved, params()))
    request_id = parse_qs(urlsplit(target).query)["request_id"][0]
    approved.redirect_uris = []
    with pytest.raises(ValueError):
        provider.consent_details(request_id)
    approved.redirect_uris = client().redirect_uris
    provider.resource = "https://changed.example/mcp"
    with pytest.raises(ValueError):
        provider.consent_details(request_id)
    provider.clients.clear()
    with pytest.raises(ValueError):
        provider.consent_details(request_id)
    assert store.get("pending", request_id)
    assert permissions


def test_token_lifecycle_rotation_reuse_and_permissions(foundation):
    store, permissions, approved, provider = foundation

    async def exercise():
        code = await issue_code(provider, approved, scopes=["utenze.read", "catasto.read"])
        assert await provider.load_authorization_code(client("other"), code) is None
        loaded = await provider.load_authorization_code(approved, code)
        with pytest.raises(TokenError):
            await provider.exchange_authorization_code(client("other"), loaded)
        tokens = await provider.exchange_authorization_code(approved, loaded)
        assert await provider.load_authorization_code(approved, code) is None
        with pytest.raises(TokenError):
            await provider.exchange_authorization_code(approved, loaded)
        access = await provider.load_access_token(tokens.access_token)
        assert access.subject == "1" and access.resource == RESOURCE
        assert set(access.scopes) == {"utenze.read", "catasto.read"}
        permissions["1"] = {"utenze.read"}
        assert (await provider.load_access_token(tokens.access_token)).scopes == ["utenze.read"]
        assert await provider.load_refresh_token(client("other"), tokens.refresh_token) is None
        refresh = await provider.load_refresh_token(approved, tokens.refresh_token)
        with pytest.raises(TokenError):
            await provider.exchange_refresh_token(client("other"), refresh, refresh.scopes)
        for scopes in [[], ["docs.read"]]:
            with pytest.raises(TokenError):
                await provider.exchange_refresh_token(approved, refresh, scopes)
        rotated = await provider.exchange_refresh_token(approved, refresh, ["utenze.read"])
        assert rotated.scope == "utenze.read"
        assert await provider.load_access_token(tokens.access_token) is None
        assert await provider.load_refresh_token(client("other"), tokens.refresh_token) is None
        assert await provider.load_access_token(rotated.access_token)
        assert await provider.load_refresh_token(approved, tokens.refresh_token) is None
        assert await provider.load_access_token(rotated.access_token) is None
        assert await provider.load_refresh_token(approved, rotated.refresh_token) is None
        with pytest.raises(TokenError):
            await provider.exchange_refresh_token(approved, refresh, ["utenze.read"])
        fresh_code = await issue_code(provider, approved)
        loaded = await provider.load_authorization_code(approved, fresh_code)
        permissions.clear()
        with pytest.raises(TokenError):
            await provider.exchange_authorization_code(approved, loaded)
        permissions["1"] = {"utenze.read"}
        fresh = await provider.exchange_authorization_code(approved, loaded)
        fresh_refresh = await provider.load_refresh_token(approved, fresh.refresh_token)
        permissions.clear()
        assert await provider.load_access_token(fresh.access_token) is None
        with pytest.raises(TokenError):
            await provider.exchange_refresh_token(approved, fresh_refresh, ["utenze.read"])
        permissions["1"] = {"utenze.read"}
        provider.resource = "https://wrong.example/mcp"
        assert await provider.load_access_token(fresh.access_token) is None
        provider.resource = RESOURCE
        await provider.revoke_token(fresh_refresh)
        assert await provider.load_access_token(fresh.access_token) is None
        store.revoke("missing")

    asyncio.run(exercise())


def test_http_sdk_pkce_resource_consent_and_revocation(foundation):
    _, permissions, approved, provider = foundation
    authenticate = AsyncMock(side_effect=lambda token: "1" if token == "gaia-session" else None)
    app = create_oauth_app(provider, ISSUER, authenticate)

    async def exercise():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://synthetic.example"
        ) as http:
            metadata = (await http.get("/.well-known/oauth-authorization-server")).json()
            assert metadata["issuer"] == ISSUER
            assert metadata["token_endpoint_auth_methods_supported"] == ["none"]
            assert metadata["scopes_supported"] == ["catasto.read", "ruolo.read", "utenze.read"]
            assert "registration_endpoint" not in metadata
            assert (await http.post("/register", json={})).status_code == 404
            query = {
                "client_id": approved.client_id,
                "response_type": "code",
                "redirect_uri": REDIRECT,
                "scope": "utenze.read",
                "state": "synthetic-state",
                "resource": RESOURCE,
                "code_challenge": CHALLENGE,
                "code_challenge_method": "S256",
            }
            response = await http.get("/authorize", params=query)
            assert response.status_code == 302
            request_id = parse_qs(urlsplit(response.headers["location"]).query)["request_id"][0]
            for headers in [{}, {"Authorization": "Bearer invalid"}]:
                assert (
                    await http.get("/consent", params={"request_id": request_id}, headers=headers)
                ).status_code == 401
            headers = {"Authorization": "Bearer gaia-session"}
            details = await http.get("/consent", params={"request_id": request_id}, headers=headers)
            assert details.json()["scopes"] == ["utenze.read"]
            assert details.headers["cache-control"] == "no-store"
            assert (
                await http.get("/consent", params={"request_id": "missing"}, headers=headers)
            ).status_code == 400
            for payload in [{}, {"request_id": request_id, "allowed": "yes"}]:
                assert (
                    await http.post("/consent", json=payload, headers=headers)
                ).status_code == 400
            consent = await http.post(
                "/consent", json={"request_id": request_id, "allowed": True}, headers=headers
            )
            code = parse_qs(urlsplit(consent.json()["redirect_url"]).query)["code"][0]
            body = {
                "grant_type": "authorization_code",
                "client_id": approved.client_id,
                "code": code,
                "redirect_uri": REDIRECT,
                "code_verifier": VERIFIER,
                "resource": RESOURCE,
            }
            for changes in [
                {"resource": "https://attacker.example/mcp"},
                {"resource": ""},
                {"code_verifier": "bad"},
                {"redirect_uri": "https://attacker.example/"},
            ]:
                assert (await http.post("/token", data={**body, **changes})).status_code == 400
            duplicated = [*body.items(), ("resource", RESOURCE)]
            encoded = "&".join(f"{key}={value}" for key, value in duplicated)
            assert (
                await http.post(
                    "/token",
                    content=encoded,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
            ).status_code == 400
            response = await http.post("/token", data=body)
            assert response.status_code == 200, response.text
            tokens = response.json()
            assert response.headers["cache-control"] == "no-store"
            assert (await http.post("/token", data=body)).status_code == 400
            refresh_body = {
                "grant_type": "refresh_token",
                "client_id": approved.client_id,
                "refresh_token": tokens["refresh_token"],
                "resource": RESOURCE,
            }
            assert (
                await http.post("/token", data={**refresh_body, "scope": "docs.read"})
            ).status_code == 400
            assert (
                await http.post(
                    "/token", data={**refresh_body, "resource": "https://other.example/mcp"}
                )
            ).status_code == 400
            rotated = (await http.post("/token", data=refresh_body)).json()
            provider.clients["other"] = client("other")
            assert (
                await http.post(
                    "/revoke", data={"client_id": "other", "token": rotated["access_token"]}
                )
            ).status_code == 200
            assert await provider.load_access_token(rotated["access_token"])
            fresh_code = await issue_code(provider, approved)
            fresh = await provider.exchange_authorization_code(
                approved, await provider.load_authorization_code(approved, fresh_code)
            )
            assert (
                await http.post(
                    "/revoke", data={"client_id": approved.client_id, "token": fresh.refresh_token}
                )
            ).status_code == 200
            assert await provider.load_access_token(fresh.access_token) is None
            revoke = await http.post(
                "/revoke", data={"client_id": approved.client_id, "token": rotated["access_token"]}
            )
            assert revoke.status_code == 200
            assert await provider.load_access_token(rotated["access_token"]) is None
            assert await provider.load_refresh_token(approved, rotated["refresh_token"]) is None
            assert (
                await http.post("/revoke", data={"client_id": "unknown", "token": "x"})
            ).status_code == 401
            assert (
                await http.post("/revoke", data={"client_id": approved.client_id})
            ).status_code == 400
            assert (
                await http.post(
                    "/revoke", data={"client_id": approved.client_id, "token": "missing"}
                )
            ).status_code == 200
            assert (
                await http.post(
                    "/revoke",
                    data={"client_id": approved.client_id, "token": tokens["refresh_token"]},
                )
            ).status_code == 200
            assert (
                await http.post(
                    "/token",
                    data={
                        "grant_type": "password",
                        "resource": RESOURCE,
                        "client_id": approved.client_id,
                    },
                )
            ).status_code == 400
            assert permissions

    asyncio.run(exercise())


def test_gaia_sessions_reuse_login_and_canonical_permissions(monkeypatch):
    database = object()
    user = SimpleNamespace(id=1, is_active=True)
    monkeypatch.setattr(
        oauth_gaia, "get_application_user_by_id", lambda db, subject: user if subject == 1 else None
    )
    monkeypatch.setattr(
        oauth_gaia,
        "effective_scopes",
        lambda *args: {"utenze.read", "docs.read", "mcp.audit.read"} if user.is_active else set(),
    )

    def session_user(db, token):
        assert db is database
        if token == "bad":
            raise HTTPException(status_code=401)
        return user

    monkeypatch.setattr(oauth_gaia, "get_current_user_from_token", session_user)
    scopes, authenticate = oauth_gaia.gaia_oauth_callbacks(lambda: nullcontext(database))
    assert scopes("1") == {"utenze.read"}
    assert scopes("2") == set()
    assert asyncio.run(authenticate("gaia-session")) == "1"
    assert asyncio.run(authenticate("bad")) is None
    user.is_active = False
    assert scopes("1") == set()
    assert asyncio.run(authenticate("gaia-session")) is None


def test_consumption_races_and_atomic_pair_rollback(foundation, monkeypatch):
    store, _, approved, provider = foundation

    async def exercise():
        code = await issue_code(provider, approved)
        loaded = await provider.load_authorization_code(approved, code)
        consume = store.consume
        monkeypatch.setattr(store, "consume", lambda *args, **kwargs: None)
        with pytest.raises(TokenError):
            await provider.exchange_authorization_code(approved, loaded)
        target = await provider.authorize(approved, params())
        request_id = parse_qs(urlsplit(target).query)["request_id"][0]
        with pytest.raises(ValueError):
            provider.consent(request_id, "1", True)
        monkeypatch.setattr(store, "consume", consume)
        put = store.put

        def fail_refresh(kind, *args, **kwargs):
            if kind == "refresh":
                raise RuntimeError("synthetic storage failure")
            return put(kind, *args, **kwargs)

        monkeypatch.setattr(store, "put", fail_refresh)
        with pytest.raises(RuntimeError):
            await provider.exchange_authorization_code(approved, loaded)
        assert store.get("code", code)
        assert (
            store.connection.execute("SELECT COUNT(*) FROM grants WHERE kind='access'").fetchone()[
                0
            ]
            == 0
        )
        monkeypatch.setattr(store, "put", put)
        tokens = await provider.exchange_authorization_code(approved, loaded)
        refresh = await provider.load_refresh_token(approved, tokens.refresh_token)
        monkeypatch.setattr(store, "consume", lambda *args, **kwargs: None)
        with pytest.raises(TokenError):
            await provider.exchange_refresh_token(approved, refresh, refresh.scopes)

    asyncio.run(exercise())


def test_delegated_scopes_keep_discovery_calls_and_provenance_data_only(foundation, tmp_path):
    _, _, approved, provider = foundation
    database = tmp_path / "gaia-mcp-synthetic-oauth.sqlite"
    seed_database(database, "oauth-synthetic")
    service = DataService(database)

    async def exercise():
        code = await issue_code(provider, approved)
        credential = await provider.exchange_authorization_code(
            approved, await provider.load_authorization_code(approved, code)
        )
        access = await provider.load_access_token(credential.access_token)
        context = CallContext(f"gaia:{access.subject}", frozenset(access.scopes))
        server = create_server(service, lambda: context)
        listed = await server._request_handlers["tools/list"].handler(None, None)
        assert {tool.name for tool in listed.tools} == {"search_subjects", "get_subject"}
        handler = server._request_handlers["tools/call"].handler
        result = await handler(
            None,
            types.CallToolRequestParams(
                name="search_subjects",
                arguments={"query": "omonimo"},
            ),
        )
        assert not result.is_error
        assert result.structured_content["source"] == "gaia_synthetic_db"
        for name, expected in [
            ("search_docs", "INVALID_ARGUMENT"),
            ("search_role_notices", "PERMISSION_DENIED"),
        ]:
            denied = await handler(None, types.CallToolRequestParams(name=name, arguments={}))
            assert denied.structured_content["error"]["code"] == expected

    try:
        asyncio.run(exercise())
    finally:
        service.close()
