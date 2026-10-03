from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import anyio
import jwt
import pytest
from starlette.testclient import TestClient

from app.modules.wiki.mcps.auth import (
    AUDIENCE,
    ISSUER,
    effective_scopes,
    issue_token,
    validate_secret,
    verify_token,
)
from app.modules.wiki.mcps.context import CallContext
from app.modules.wiki.mcps.data.database import seed_database
from app.modules.wiki.mcps.data.service import DataService
from app.modules.wiki.mcps.docs.corpus import Manifest, ManifestEntry, build_corpus
from app.modules.wiki.mcps.docs.service import DocsService
from app.modules.wiki.mcps.http import REQUEST_CONTEXT, BearerMiddleware, create_http_app

SECRET = "pytest-mcp-separate-signing-secret-123456789"


@pytest.fixture
def sources(tmp_path):
    path = tmp_path / "domain-docs/catasto/docs/PRD.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        "# Catasto\n## Ricerca\nParticelle sintetiche.\n## Distretto\nDistretto irriguo."
    )
    entry = ManifestEntry(
        path=path.relative_to(tmp_path).as_posix(),
        domain="catasto",
        category="prd",
        status="current",
        included=True,
        reason="Reviewed synthetic fixture",
    )
    docs = DocsService(build_corpus(tmp_path, Manifest(entries=[entry])))
    database = tmp_path / "gaia-mcp-synthetic-http.sqlite"
    seed_database(database, "http-test")
    data = DataService(database)
    yield docs, data
    docs.close()
    data.close()


def headers(scopes, secret=SECRET):
    token = issue_token(
        secret,
        CallContext(
            principal="gaia:7",
            scopes=frozenset(scopes),
            conversation_id="conversation",
            experiment_run_id="experiment",
        ),
    )
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2025-11-25",
    }


def rpc(client, source, method, params=None, scopes=None):
    return client.post(
        f"/{source}/",
        headers=headers(scopes or []),
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}},
    )


def test_permission_mapping_checks_module_and_each_section():
    user = SimpleNamespace(is_active=True, enabled_modules=["catasto", "utenze", "ruolo"])
    checks = []

    def permission(db, current_user, section):
        checks.append((db, current_user, section))
        return section != "ruolo.tributi.view"

    scopes = effective_scopes("database", user, permission)
    assert scopes == frozenset({"docs.read", "catasto.read", "utenze.read"})
    assert checks[-1][-1] == "ruolo.tributi.view"
    user.enabled_modules = []
    assert effective_scopes("database", user, permission) == frozenset({"docs.read"})
    user.is_active = False
    assert effective_scopes("database", user, permission) == frozenset()


def test_tokens_validate_signature_audience_issuer_expiry_and_scope():
    original = CallContext(
        principal="gaia:7",
        scopes=frozenset({"docs.read", "catasto.read"}),
        conversation_id="conversation",
        experiment_run_id="experiment",
    )
    token = issue_token(SECRET, original)
    verified = verify_token(SECRET, token)
    assert verified.principal == original.principal and verified.scopes == original.scopes
    assert verified.conversation_id == "conversation" and verified.experiment_run_id == "experiment"
    claims = jwt.decode(token, SECRET, algorithms=["HS256"], issuer=ISSUER, audience=AUDIENCE)
    assert claims["exp"] - claims["iat"] == 60
    with pytest.raises(jwt.InvalidSignatureError):
        verify_token("other-secret-with-at-least-32-characters", token)
    for changes in [
        {"aud": "other"},
        {"iss": "other"},
        {"type": "access"},
        {"scopes": "admin"},
        {"scopes": [1]},
        {"scopes": ["admin"]},
        {"exp": datetime.now(UTC) - timedelta(seconds=1)},
    ]:
        with pytest.raises(jwt.InvalidTokenError):
            verify_token(SECRET, jwt.encode(dict(claims, **changes), SECRET, algorithm="HS256"))
    with pytest.raises(ValueError):
        validate_secret("short")


def test_authenticated_discovery_source_separation_and_error_handling(sources):
    docs, data = sources
    app = create_http_app(docs, data, SECRET)
    with TestClient(app, base_url="http://localhost") as client:
        for authorization in [None, "Basic fake", "Bearer invalid"]:
            response = client.post(
                "/data/", headers={"Authorization": authorization} if authorization else {}
            )
            assert response.status_code == 401
            assert response.json() == {"error": "UNAUTHORIZED"}
        for source, expected in [("docs", 4), ("data", 2)]:
            response = rpc(client, source, "tools/list", scopes=["docs.read", "utenze.read"])
            assert response.status_code == 200
            assert len(response.json()["result"]["tools"]) == expected
        data_result = rpc(
            client,
            "data",
            "tools/call",
            {"name": "search_subjects", "arguments": {"query": "omonimo"}},
            ["utenze.read"],
        )
        assert data_result.json()["result"]["structuredContent"]["result_count"] == 2
        denied = rpc(client, "data", "tools/call", {"name": "search_parcels"}, ["utenze.read"])
        assert denied.json()["result"]["structuredContent"]["error"]["code"] == "PERMISSION_DENIED"
        response = rpc(
            client,
            "docs",
            "tools/call",
            {"name": "search_docs", "arguments": {"query": "particelle"}},
            ["docs.read"],
        )
        assert response.status_code == 200
        found = response.json()["result"]["structuredContent"]
        assert found["result_count"] > 0
        evidence = found["results"][0]
        for name, arguments in [
            ("get_doc_section", {"chunk_id": evidence["chunk_id"]}),
            ("get_document_metadata", {"source_path": evidence["source_path"]}),
            ("list_doc_domains", {}),
        ]:
            result = rpc(
                client, "docs", "tools/call", {"name": name, "arguments": arguments}, ["docs.read"]
            )
            assert result.json()["result"]["isError"] is False
        denied = rpc(client, "docs", "tools/call", {"name": "list_doc_domains"})
        assert denied.json()["result"]["isError"] is True
        assert "PERMISSION_DENIED" in denied.text
        assert rpc(client, "data", "tools/call", {"name": "search_docs"}, ["utenze.read"]).json()[
            "result"
        ]["isError"]
        oversized = client.post("/data/", headers=headers(["catasto.read"]), content=b"x" * 65537)
        assert oversized.status_code == 413
    with pytest.raises(LookupError):
        REQUEST_CONTEXT.get()


def test_http_concurrent_principals_do_not_leak_context(sources):
    app = create_http_app(*sources, SECRET)
    with TestClient(app, base_url="http://localhost") as client:
        with ThreadPoolExecutor(max_workers=2) as executor:
            allowed_request = executor.submit(
                rpc, client, "data", "tools/call", {"name": "search_parcels"}, ["catasto.read"]
            )
            denied_request = executor.submit(
                rpc, client, "data", "tools/call", {"name": "search_parcels"}, []
            )
            allowed = allowed_request.result(timeout=10)
            denied = denied_request.result(timeout=10)
        assert allowed.json()["result"]["isError"] is False
        assert denied.json()["result"]["isError"] is True


def test_bearer_context_isolated_during_overlapping_requests():
    async def exercise():
        ready = anyio.Event()
        arrivals = []
        observed = []

        async def app(scope, receive, send):
            original = REQUEST_CONTEXT.get()
            arrivals.append(original.principal)
            if len(arrivals) == 2:
                ready.set()
            await ready.wait()
            await anyio.sleep(0)
            observed.append(REQUEST_CONTEXT.get())
            assert REQUEST_CONTEXT.get() == original

        middleware = BearerMiddleware(app, SECRET)
        async with anyio.create_task_group() as tasks:
            for principal, scopes in [("gaia:7", {"catasto.read"}), ("gaia:8", set())]:
                token = issue_token(SECRET, CallContext(principal, frozenset(scopes)))
                scope = {
                    "type": "http",
                    "headers": [(b"authorization", f"Bearer {token}".encode())],
                }
                tasks.start_soon(middleware, scope, None, None)
        assert {context.principal: context.scopes for context in observed} == {
            "gaia:7": frozenset({"catasto.read"}),
            "gaia:8": frozenset(),
        }
        with pytest.raises(LookupError):
            REQUEST_CONTEXT.get()

    anyio.run(exercise)


def test_non_http_passthrough():
    received = []

    async def app(scope, receive, send):
        received.append(scope["type"])

    middleware = BearerMiddleware(app, SECRET)
    anyio.run(middleware, {"type": "lifespan"}, None, None)
    assert received == ["lifespan"]
