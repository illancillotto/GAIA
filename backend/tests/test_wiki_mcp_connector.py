import asyncio
import base64
import hashlib
import json
import logging
import socket
import sqlite3
import threading
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
import uvicorn
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.models.application_user import ApplicationUser
from app.models.network import NetworkVpnDevice, NetworkVpnSession
from app.models.section_permission import RoleSectionPermission, Section, UserSectionPermission
from app.modules.accessi.routes.auth import login
from app.modules.wiki.mcps import connector, connector_budget, oauth_maintenance
from app.modules.wiki.mcps.audit import AuditStore
from app.modules.wiki.mcps.connector import ConnectorBearer, create_connector_app, read_body
from app.modules.wiki.mcps.connector_budget import PrincipalBudget
from app.modules.wiki.mcps.connector_config import (
    DATA_PATH,
    OAUTH_PATH,
    ConnectorConfig,
    configuration,
)
from app.modules.wiki.mcps.data.database import dataset_manifest, seed_database
from app.modules.wiki.mcps.data.generator import TABLES
from app.modules.wiki.mcps.http import REQUEST_CONTEXT
from app.modules.wiki.mcps.oauth_store import OAuthStore
from app.schemas.auth import LoginRequest

ORIGIN = "https://synthetic.example"
CALLBACK = "https://approved-client.example/callback"
VERIFIER = "synthetic-connector-verifier-" + "x" * 48
CHALLENGE = (
    base64.urlsafe_b64encode(hashlib.sha256(VERIFIER.encode()).digest()).decode().rstrip("=")
)


def test_maintenance_without_traffic_retries_and_stops(tmp_path, monkeypatch, caplog):
    store = OAuthStore(tmp_path / "gaia-mcp-oauth.sqlite")
    budget = PrincipalBudget(store, 60, 20)
    stale = store.put("pending", {"client_id": "first"}, lifetime=-1)
    store.connection.execute("INSERT INTO connector_budget VALUES ('stale', -1, 1, 1)")
    original_cleanup = store.cleanup

    async def exercise():
        tick = asyncio.Event()
        waiting = asyncio.Event()

        async def sleep(seconds):
            assert seconds == 60
            waiting.set()
            await tick.wait()
            tick.clear()

        monkeypatch.setattr(oauth_maintenance.asyncio, "sleep", sleep)
        async with oauth_maintenance.maintenance(store, budget):
            assert store.get("pending", stale) is None
            assert (
                store.connection.execute("SELECT COUNT(*) FROM connector_budget").fetchone()[0] == 0
            )
            await waiting.wait()
            waiting.clear()
            monkeypatch.setattr(
                store,
                "cleanup",
                lambda: (_ for _ in ()).throw(sqlite3.OperationalError("secret detail")),
            )
            tick.set()
            await waiting.wait()
            assert "gaia_mcp_oauth_cleanup_failed" in caplog.text
            assert "secret detail" not in caplog.text
            waiting.clear()
            monkeypatch.setattr(store, "cleanup", original_cleanup)
            store.put("pending", {"client_id": "first"}, lifetime=-1)
            tick.set()
            await waiting.wait()
            assert store.connection.execute("SELECT COUNT(*) FROM grants").fetchone()[0] == 0
        assert not any(task.get_name() == "gaia-mcp-oauth-cleanup" for task in asyncio.all_tasks())
        assert store.put("pending", {"client_id": "first"}, lifetime=60)

    try:
        asyncio.run(exercise())
    finally:
        store.close()


def test_maintenance_startup_failure_does_not_launch_task(tmp_path, monkeypatch):
    store = OAuthStore(tmp_path / "gaia-mcp-oauth.sqlite")
    budget = PrincipalBudget(store, 60, 20)
    monkeypatch.setattr(
        store, "cleanup", lambda: (_ for _ in ()).throw(sqlite3.OperationalError("startup"))
    )

    async def exercise():
        with pytest.raises(sqlite3.OperationalError):
            async with oauth_maintenance.maintenance(store, budget):
                pytest.fail("Failed maintenance must prevent startup")
        assert not any(task.get_name() == "gaia-mcp-oauth-cleanup" for task in asyncio.all_tasks())

    try:
        asyncio.run(exercise())
    finally:
        store.close()


def test_internal_admin_revocation_uses_current_real_gaia_role(runtime, monkeypatch, caplog):
    from app.modules.wiki.mcps.oauth_store import token_hash

    config, sessions, _ = runtime
    session = gaia_login(sessions)
    app = create_connector_app(config, sessions)
    path = OAUTH_PATH + "/admin/revoke"

    async def exercise():
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=ORIGIN) as http,
        ):
            assert (await http.post(path, json={"subject": "1"})).status_code == 401
            headers = {"Authorization": "Bearer " + session}
            assert (
                await http.post(
                    path, headers={"Authorization": "Bearer invalid"}, json={"subject": "1"}
                )
            ).status_code == 401
            assert (
                await http.post(path, headers=headers, json={"subject": "1"})
            ).status_code == 403
            tokens = await delegate(http, config, session)
            with sessions() as database:
                user = database.query(ApplicationUser).filter_by(username="synthetic-one").one()
                user.role = "admin"
                database.commit()
            for invalid in [{}, {"subject": ""}, {"subject": 1}, {"subject": "1", "unknown": True}]:
                assert (await http.post(path, headers=headers, json=invalid)).status_code == 400
            assert (await http.post(path, headers=headers, content="not-json")).status_code == 400
            preflight = await http.options(path)
            assert preflight.status_code == 404
            assert "access-control-allow-origin" not in preflight.headers
            assert (await http.get(path)).status_code == 404
            handler = next(route.endpoint.__self__ for route in app.routes if route.path == path)
            revoke = handler.store.revoke_authorizations

            def unavailable(**selectors):
                raise sqlite3.OperationalError("secret storage failure")

            monkeypatch.setattr(handler.store, "revoke_authorizations", unavailable)
            response = await http.post(path, headers=headers, json={"subject": "1"})
            assert response.status_code == 503
            assert "secret" not in response.text
            monkeypatch.setattr(handler.store, "revoke_authorizations", revoke)
            caplog.set_level(logging.INFO)
            response = await http.post(path, headers=headers, json={"subject": "1"})
            assert response.status_code == 200
            assert response.json() == {"revoked_grants": 2}
            assert response.headers["cache-control"] == "no-store"
            assert handler.store.get("access", tokens["access_token"]) is None
            event = next(
                record.mcp_event
                for record in caplog.records
                if record.message == "gaia_mcp_oauth_admin_revocation"
            )
            assert event["principal"] == token_hash("1")
            assert event["selectors"] == {"subject": token_hash("1")}
            assert session not in caplog.text and tokens["access_token"] not in caplog.text
            with sessions() as database:
                user = database.query(ApplicationUser).filter_by(username="synthetic-one").one()
                user.is_active = False
                database.commit()
            assert (await http.post(path, headers=headers, json={"subject": "1"})).status_code in {
                401,
                403,
            }

    asyncio.run(exercise())


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    monkeypatch.setattr(
        settings, "jwt_secret_key", "synthetic-connector-session-signing-secret-12345"
    )
    clients = tmp_path / "approved-clients.json"
    client_data = {
        "client_id": "synthetic-approved",
        "redirect_uris": [CALLBACK],
        "client_name": "Synthetic connector",
        "token_endpoint_auth_method": "none",
        "scope": "utenze.read catasto.read ruolo.read",
        "grant_types": ["authorization_code", "refresh_token"],
    }
    clients.write_text(json.dumps([client_data]))
    config = ConnectorConfig(
        ORIGIN + OAUTH_PATH,
        ORIGIN + DATA_PATH,
        ORIGIN + "/mcp/consent",
        clients,
        tmp_path / "gaia-mcp-oauth.sqlite",
        tmp_path / "gaia-mcp-synthetic-connector.sqlite",
        tmp_path / "gaia-mcp-audit.sqlite",
    )
    seed_database(config.data_database, "connector-synthetic")
    engine = create_engine(f"sqlite:///{tmp_path / 'synthetic-users.sqlite'}")
    Base.metadata.create_all(
        engine,
        tables=[
            ApplicationUser.__table__,
            NetworkVpnDevice.__table__,
            NetworkVpnSession.__table__,
            Section.__table__,
            RoleSectionPermission.__table__,
            UserSectionPermission.__table__,
        ],
    )
    sessions = sessionmaker(bind=engine)
    with sessions() as database:
        for username in ["synthetic-one", "synthetic-two"]:
            database.add(
                ApplicationUser(
                    username=username,
                    email=username + "@example.invalid",
                    password_hash=hash_password("synthetic-password"),
                    role="viewer",
                    module_utenze=True,
                    module_catasto=True,
                    module_ruolo=True,
                )
            )
        for key in ["utenze.subjects", "catasto.dashboard", "ruolo.avvisi", "ruolo.tributi.view"]:
            database.add(Section(key=key, module=key.split(".")[0], label=key, min_role="viewer"))
        database.commit()
    yield config, sessions, client_data
    engine.dispose()


def gaia_login(sessions, username="synthetic-one"):
    request = Request({"type": "http", "headers": [], "client": ("127.0.0.1", 1)})
    with sessions() as database:
        return login(
            LoginRequest(username=username, password="synthetic-password"), request, database
        ).access_token


async def delegate(http, config, session, client_id="synthetic-approved"):
    response = await http.get(
        OAUTH_PATH + "/authorize",
        params={
            "client_id": client_id,
            "redirect_uri": CALLBACK,
            "response_type": "code",
            "scope": "utenze.read",
            "state": "synthetic-state",
            "resource": config.resource,
            "code_challenge": CHALLENGE,
            "code_challenge_method": "S256",
        },
    )
    assert response.status_code == 302
    request_id = parse_qs(urlsplit(response.headers["location"]).query)["request_id"][0]
    headers = {"Authorization": "Bearer " + session}
    details = await http.get(
        OAUTH_PATH + "/consent", params={"request_id": request_id}, headers=headers
    )
    assert details.json()["redirect_uri"] == CALLBACK
    decision = await http.post(
        OAUTH_PATH + "/consent", json={"request_id": request_id, "allowed": True}, headers=headers
    )
    query = parse_qs(urlsplit(decision.json()["redirect_url"]).query)
    assert query["state"] == ["synthetic-state"]
    response = await http.post(
        OAUTH_PATH + "/token",
        data={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "code": query["code"][0],
            "redirect_uri": CALLBACK,
            "code_verifier": VERIFIER,
            "resource": config.resource,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


async def rpc(http, token, method="tools/list", params=None):
    return await http.post(
        DATA_PATH,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}},
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/json, text/event-stream",
        },
    )


def test_real_gaia_login_oauth_data_tools_audit_permissions_and_revocation(runtime):
    config, sessions, _ = runtime
    session = gaia_login(sessions)
    app = create_connector_app(config, sessions)

    async def exercise():
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=ORIGIN) as http,
        ):
            metadata = await http.get("/.well-known/oauth-protected-resource" + DATA_PATH)
            assert metadata.json()["resource"] == config.resource
            assert metadata.json()["authorization_servers"] == [config.issuer]
            auth = (await http.get("/.well-known/oauth-authorization-server" + OAUTH_PATH)).json()
            assert auth["issuer"] == config.issuer
            denied = await http.post(DATA_PATH, json={})
            assert denied.status_code == 401
            assert config.resource.removesuffix(DATA_PATH) in denied.headers["www-authenticate"]
            for path in ["/docs", "/inspection", "/data/", OAUTH_PATH + "/register"]:
                assert (await http.get(path)).status_code == 404
            tokens = await delegate(http, config, session)
            access = tokens["access_token"]
            init = await rpc(
                http,
                access,
                "initialize",
                {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "synthetic", "version": "1"},
                },
            )
            assert init.status_code == 200, init.text
            tools = (await rpc(http, access)).json()["result"]["tools"]
            assert {item["name"] for item in tools} == {"search_subjects", "get_subject"}
            result = (
                await rpc(
                    http,
                    access,
                    "tools/call",
                    {"name": "search_subjects", "arguments": {"query": "omonimo"}},
                )
            ).json()["result"]["structuredContent"]
            assert result["source"] == "gaia_synthetic_db" and result["provenance"]
            for tool, error in [
                ("search_docs", "INVALID_ARGUMENT"),
                ("search_role_notices", "PERMISSION_DENIED"),
            ]:
                result = (
                    await rpc(http, access, "tools/call", {"name": tool, "arguments": {}})
                ).json()["result"]["structuredContent"]
                assert result["error"]["code"] == error
            audit = AuditStore(config.audit_database)
            try:
                rows = audit.connection.execute("SELECT payload FROM calls").fetchall()
                assert len(rows) == 3
                assert "gaia_synthetic_db" in rows[0][0]
                assert access not in "".join(row[0] for row in rows)
            finally:
                audit.close()
            with sessions() as database:
                user = database.query(ApplicationUser).filter_by(username="synthetic-one").one()
                user.module_utenze = False
                database.commit()
            assert (await rpc(http, access)).status_code == 401
            with sessions() as database:
                user = database.query(ApplicationUser).filter_by(username="synthetic-one").one()
                user.module_utenze = True
                database.commit()
            assert (await rpc(http, access)).status_code == 200
            revoke = await http.post(
                OAUTH_PATH + "/revoke",
                data={"client_id": "synthetic-approved", "token": tokens["refresh_token"]},
            )
            assert revoke.status_code == 200
            assert (await rpc(http, access)).status_code == 401
            new = await delegate(http, config, session)
            with sessions() as database:
                user = database.query(ApplicationUser).filter_by(username="synthetic-one").one()
                user.is_active = False
                database.commit()
            assert (await rpc(http, new["access_token"])).status_code == 401
        assert app.router.routes == []
        with pytest.raises(LookupError):
            REQUEST_CONTEXT.get()

    asyncio.run(exercise())


def test_real_tcp_oauth_connector_tool_call_and_revocation(runtime):
    config, sessions, _ = runtime
    session = gaia_login(sessions)
    application = create_connector_app(config, sessions)
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(application, log_level="error", access_log=False, ws="none")
    )
    thread = threading.Thread(
        target=lambda: asyncio.run(server.serve(sockets=[listener])), daemon=True
    )
    thread.start()

    async def exercise():
        for _attempt in range(200):
            if server.started:
                break
            await asyncio.sleep(0.01)
        assert server.started
        async with httpx.AsyncClient(
            base_url=f"http://127.0.0.1:{port}", headers={"Host": "synthetic.example"}
        ) as http:
            tokens = await delegate(http, config, session)
            access = tokens["access_token"]
            tools = (await rpc(http, access)).json()["result"]["tools"]
            assert {tool["name"] for tool in tools} == {"search_subjects", "get_subject"}
            result = (
                await rpc(
                    http,
                    access,
                    "tools/call",
                    {"name": "search_subjects", "arguments": {"query": "omonimo"}},
                )
            ).json()["result"]["structuredContent"]
            assert result["source"] == "gaia_synthetic_db" and result["provenance"]
            assert (await http.get("/docs")).status_code == 404
            denied = (
                await rpc(http, access, "tools/call", {"name": "search_docs", "arguments": {}})
            ).json()["result"]["structuredContent"]
            assert denied["error"]["code"] == "INVALID_ARGUMENT"
            response = await http.post(
                OAUTH_PATH + "/revoke",
                data={"client_id": "synthetic-approved", "token": tokens["refresh_token"]},
            )
            assert response.status_code == 200
            assert (await rpc(http, access)).status_code == 401

    try:
        asyncio.run(exercise())
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        listener.close()
    assert not thread.is_alive()
    assert application.router.routes == []


def test_transport_security_and_persisted_grants_survive_gateway_restart(runtime):
    config, sessions, _ = runtime
    session = gaia_login(sessions)

    async def exercise():
        application = create_connector_app(config, sessions)
        async with (
            application.router.lifespan_context(application),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=application), base_url=ORIGIN
            ) as http,
        ):
            access = (await delegate(http, config, session))["access_token"]
            headers = {
                "Authorization": "Bearer " + access,
                "Accept": "application/json, text/event-stream",
            }
            payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
            for changes, status in [
                ({"Host": "unapproved.example"}, 421),
                ({"Origin": "https://unapproved.example"}, 403),
                ({"Content-Type": "text/plain"}, 400),
            ]:
                response = await http.post(DATA_PATH, json=payload, headers={**headers, **changes})
                assert response.status_code == status
                assert "gaia_synthetic_db" not in response.text
            response = await http.post(
                DATA_PATH, json=payload, headers={**headers, "Origin": ORIGIN}
            )
            assert response.status_code == 200
            metadata = await http.options(
                "/.well-known/oauth-protected-resource" + DATA_PATH,
                headers={"Origin": ORIGIN, "Access-Control-Request-Method": "GET"},
            )
            assert metadata.status_code == 200
            assert metadata.headers["access-control-allow-origin"] == "*"
        restarted = create_connector_app(config, sessions)
        async with (
            restarted.router.lifespan_context(restarted),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=restarted), base_url=ORIGIN
            ) as http,
        ):
            tools = (await rpc(http, access)).json()["result"]["tools"]
            assert {tool["name"] for tool in tools} == {"search_subjects", "get_subject"}
        with pytest.raises(LookupError):
            REQUEST_CONTEXT.get()

    asyncio.run(exercise())


def test_principal_budget_shared_by_tokens_and_isolated_by_user(runtime, caplog):
    caplog.set_level(logging.INFO)
    config, sessions, client_data = runtime
    config.clients_file.write_text(
        json.dumps([client_data, {**client_data, "client_id": "synthetic-second"}])
    )
    config = replace(config, requests_per_minute=3, tools_per_minute=1)
    first_session = gaia_login(sessions)
    second_session = gaia_login(sessions, "synthetic-two")
    app = create_connector_app(config, sessions)

    async def exercise():
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=ORIGIN) as http,
        ):
            first = (await delegate(http, config, first_session))["access_token"]
            another = (await delegate(http, config, first_session, "synthetic-second"))[
                "access_token"
            ]
            second = (await delegate(http, config, second_session))["access_token"]
            call = {"name": "search_subjects", "arguments": {"query": "omonimo"}}
            assert (await rpc(http, first, "tools/call", call)).status_code == 200
            exceeded = await rpc(http, another, "tools/call", call)
            assert exceeded.status_code == 429
            assert exceeded.headers["retry-after"] == "60"
            assert (await rpc(http, second, "tools/call", call)).status_code == 200
            assert (await rpc(http, first)).status_code == 200
            assert (await rpc(http, another)).status_code == 200
            assert (await rpc(http, first)).status_code == 429

    asyncio.run(exercise())
    events = [
        record.mcp_event
        for record in caplog.records
        if record.message == "gaia_mcp_connector_budget_denied"
    ]
    assert len(events) == 2
    assert "gaia:" not in json.dumps(events)
    assert "Bearer" not in json.dumps(events)


def test_budget_window_persistence_and_rollback(tmp_path, monkeypatch):
    monkeypatch.setattr(connector_budget, "time", lambda: 120)
    store = OAuthStore(tmp_path / "gaia-mcp-oauth.sqlite")
    budget = PrincipalBudget(store, 2, 1)
    assert budget.admit("gaia:1", True)
    assert not budget.admit("gaia:1", True)
    assert budget.admit("gaia:1", False)
    assert not budget.admit("gaia:1", False)
    store.close()
    store = OAuthStore(tmp_path / "gaia-mcp-oauth.sqlite")
    try:
        budget = PrincipalBudget(store, 2, 1)
        assert not budget.admit("gaia:1", False)
        monkeypatch.setattr(connector_budget, "time", lambda: 180)
        assert budget.admit("gaia:1", True)
    finally:
        store.close()


def test_configuration_fail_closed_and_preapproved_clients(runtime, monkeypatch):
    config, _, client_data = runtime
    assert configuration({}) is None
    with pytest.raises(ValueError):
        configuration({"GAIA_MCP_OAUTH_ENABLED": "yes"})
    with pytest.raises(KeyError):
        configuration({"GAIA_MCP_OAUTH_ENABLED": "true"})
    for changes in [
        {"issuer": ORIGIN + "/wrong"},
        {"resource": "https://other.example" + DATA_PATH},
        {"consent_url": ORIGIN + "/wrong"},
        {"tools_per_minute": 0},
        {"requests_per_minute": 601},
    ]:
        with pytest.raises(ValueError):
            replace(config, **changes)
    for data in [
        [],
        [client_data, client_data],
        [{**client_data, "client_id": ""}],
        [{**client_data, "client_secret": "synthetic-secret"}],
        [{**client_data, "scope": ""}],
        [{**client_data, "scope": "docs.read"}],
        [{**client_data, "grant_types": ["password"]}],
        [{**client_data, "response_types": ["token"]}],
    ]:
        config.clients_file.write_text(json.dumps(data))
        with pytest.raises(ValueError):
            config.clients()
    for payload in ["invalid-json", "null", '[{"client_secret":"synthetic-secret"}]']:
        config.clients_file.write_text(payload)
        with pytest.raises(ValueError, match="Invalid approved clients configuration"):
            config.clients()
    config.clients_file.write_text(" " * 65537)
    with pytest.raises(ValueError):
        config.clients()
    config.clients_file.write_text(json.dumps([client_data]))
    environment = {
        "GAIA_MCP_OAUTH_ENABLED": "true",
        "GAIA_MCP_OAUTH_ISSUER": config.issuer,
        "GAIA_MCP_OAUTH_RESOURCE": config.resource,
        "GAIA_MCP_OAUTH_CONSENT_URL": config.consent_url,
        "GAIA_MCP_OAUTH_CLIENTS_FILE": str(config.clients_file),
        "GAIA_MCP_OAUTH_DATABASE": str(config.oauth_database),
        "GAIA_MCP_CONNECTOR_DATA_DATABASE": str(config.data_database),
        "GAIA_MCP_CONNECTOR_AUDIT_DATABASE": str(config.audit_database),
    }
    assert configuration(environment) == config
    monkeypatch.setattr(connector.os, "environ", {})
    assert connector.create_configured_app().router.routes == []
    monkeypatch.setattr(connector.os, "environ", environment)
    event_logger = logging.getLogger("app.modules.wiki.mcps")
    previous = (event_logger.handlers, event_logger.level, event_logger.propagate)
    try:
        assert connector.create_configured_app().router.routes == []
        assert event_logger.level == logging.INFO and not event_logger.propagate
        assert type(event_logger.handlers[0].formatter).__name__ == "EventFormatter"
    finally:
        event_logger.handlers, level, event_logger.propagate = previous
        event_logger.setLevel(level)


def test_disabled_and_failed_startup_do_not_expose_routes(runtime):
    config, sessions, _ = runtime
    disabled = create_connector_app(None, None)
    invalid = create_connector_app(
        replace(config, data_database=config.data_database.parent / "real.sqlite"), sessions
    )

    async def exercise():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=disabled), base_url=ORIGIN
        ) as http:
            assert (await http.get(DATA_PATH)).status_code == 404
        with pytest.raises(ValueError):
            async with invalid.router.lifespan_context(invalid):
                pytest.fail("Should reject a non-synthetic database")
        assert invalid.router.routes == []

    asyncio.run(exercise())


def test_body_limits_invalid_inputs_backend_failures_and_context_reset():
    provider = SimpleNamespace(
        load_access_token=AsyncMock(
            return_value=SimpleNamespace(subject="1", scopes=["utenze.read"])
        )
    )
    budget = SimpleNamespace(admit=lambda *args: True)

    async def application(scope, receive, send):
        assert (await receive())["body"] == b"{}"
        assert (await receive())["type"] == "http.disconnect"
        assert REQUEST_CONTEXT.get().principal == "gaia:1"
        raise RuntimeError("synthetic application failure")

    middleware = ConnectorBearer(application, provider, budget, ORIGIN)
    scope = {
        "type": "http",
        "method": "POST",
        "path": DATA_PATH,
        "headers": [(b"authorization", b"Bearer synthetic-token")],
    }

    async def exercise():
        send = AsyncMock()
        await middleware({**scope, "headers": []}, AsyncMock(), send)
        assert send.call_args_list[0].args[0]["status"] == 401
        for messages in [
            [{"type": "http.disconnect"}],
            [{"type": "http.request", "body": b"x" * 65537}],
            [{"type": "http.request", "body": b"invalid-json"}],
            [{"type": "http.request", "body": b"[]"}],
            [{"type": "http.request", "body": None}],
        ]:
            send = AsyncMock()
            await middleware(scope, AsyncMock(side_effect=messages), send)
            assert send.call_args_list[0].args[0]["status"] == 400
        assert (
            await read_body(
                AsyncMock(
                    side_effect=[
                        {"type": "http.request", "body": b"a", "more_body": True},
                        {"type": "http.request", "body": b"b"},
                    ]
                )
            )
            == b"ab"
        )
        send = AsyncMock()
        provider.load_access_token.return_value.subject = None
        await middleware(scope, AsyncMock(), send)
        assert send.call_args_list[0].args[0]["status"] == 401
        provider.load_access_token.return_value.subject = "1"
        budget.admit = lambda *args: (_ for _ in ()).throw(
            sqlite3.OperationalError("synthetic failure")
        )
        send = AsyncMock()
        await middleware(scope, AsyncMock(return_value={"type": "http.request", "body": b""}), send)
        assert send.call_args_list[0].args[0]["status"] == 503
        budget.admit = lambda *args: True
        with pytest.raises(RuntimeError):
            await middleware(
                scope,
                AsyncMock(
                    side_effect=[
                        {"type": "http.request", "body": b"{}"},
                        {"type": "http.disconnect"},
                    ]
                ),
                AsyncMock(),
            )
        with pytest.raises(LookupError):
            REQUEST_CONTEXT.get()

    asyncio.run(exercise())


def test_gateway_rejects_dataset_merely_labelled_synthetic(runtime):
    config, sessions, _ = runtime
    with sqlite3.connect(config.data_database) as database:
        database.row_factory = sqlite3.Row
        database.execute(
            "UPDATE subjects SET display_name='NOT-GENERATED-SYNTHETIC-SENTINEL' WHERE rowid=1"
        )
        data = {
            table: [dict(row) for row in database.execute(f"SELECT * FROM {table}")]
            for table in TABLES
        }
        manifest = dataset_manifest("connector-synthetic", data)
        database.execute(
            "UPDATE dataset_manifest SET dataset_version=?, manifest_json=? WHERE id=1",
            (manifest["dataset_version"], json.dumps(manifest)),
        )
    app = create_connector_app(config, sessions)

    async def exercise():
        with pytest.raises(ValueError, match="unmodified generated synthetic dataset"):
            async with app.router.lifespan_context(app):
                pytest.fail("A hand-labelled dataset must never be exposed")
        assert app.router.routes == []

    asyncio.run(exercise())
