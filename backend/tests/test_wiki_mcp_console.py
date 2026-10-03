import sqlite3
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import FastAPI, HTTPException
from starlette.testclient import TestClient

from app.api.deps import require_active_user
from app.core.database import get_db
from app.modules.wiki.mcps import cli, console_routes
from app.modules.wiki.mcps.audit import AUDIT_SCOPE, AuditStore, audit_filter
from app.modules.wiki.mcps.auth import issue_token, verify_token
from app.modules.wiki.mcps.context import CallContext
from app.modules.wiki.mcps.data import cli as data_cli
from app.modules.wiki.mcps.data.database import seed_database
from app.modules.wiki.mcps.data.service import DataService
from app.modules.wiki.mcps.http import create_http_app
from app.modules.wiki.mcps.inspection import ENTITY_SCOPES

SECRET = "synthetic-console-test-signing-secret-12345"
ALL_SCOPES = frozenset({"utenze.read", "catasto.read", "ruolo.read"})


@pytest.mark.parametrize(
    "key,value,expected",
    [
        ("query", "SYN-SUBJECT-0001", "[omesso]"),
        ("cursor", "private", "[omesso]"),
        ("notice_code", "private-credential", "[omesso]"),
        ("notice_code", "SYN-NOTICE-0001", "SYN-NOTICE-0001"),
        (
            "subject_id",
            "4a00bb81-2eb8-5fbc-81fe-98e6858033af",
            "4a00bb81-2eb8-5fbc-81fe-98e6858033af",
        ),
        ("limit", 1, 1),
        ("cursor", None, "[omesso]"),
    ],
)
def test_audit_filters_never_persist_arbitrary_text(key, value, expected):
    assert audit_filter(key, value) == expected


@pytest.fixture
def inspected(tmp_path):
    path = tmp_path / "gaia-mcp-synthetic-console.sqlite"
    seed_database(path, "gaia-v1")
    audit = AuditStore(tmp_path / "gaia-mcp-audit.sqlite")
    service = DataService(path, audit=audit)
    with TestClient(create_http_app(None, service, SECRET)) as client:
        yield service, audit, client, path
    service.close()
    audit.close()


def bearer(principal="gaia:7", scopes=ALL_SCOPES):
    return {"Authorization": "Bearer " + issue_token(SECRET, CallContext(principal, scopes))}


def test_inspection_catalog_pagination_and_no_docs_or_model(inspected):
    service, _, client, _ = inspected
    assert client.get("/inspect/catalog").status_code == 401
    assert (
        client.get("/docs/", headers=bearer(scopes=ALL_SCOPES | {"docs.read"})).status_code == 404
    )
    catalog = client.get("/inspect/catalog", headers=bearer()).json()
    assert catalog["audit_enabled"] and catalog["source"] == "gaia_synthetic_db"
    assert {item["name"] for item in catalog["entities"]} == set(ENTITY_SCOPES)
    for entity in ENTITY_SCOPES:
        response = client.get(f"/inspect/{entity}", headers=bearer()).json()
        assert response["total"] == service.manifest["row_counts"][entity]
        assert response["results"] and response["dataset_version"] == catalog["dataset_version"]
    first = client.get("/inspect/subjects?limit=1", headers=bearer()).json()
    second = client.get("/inspect/subjects?limit=1&offset=1", headers=bearer()).json()
    assert first["next_offset"] == 1 and first["results"] != second["results"]
    final = client.get("/inspect/subjects?offset=300", headers=bearer()).json()
    assert final["results"] == [] and final["next_offset"] is None
    limited = bearer(scopes=frozenset({"utenze.read"}))
    assert client.get("/inspect/catalog", headers=limited).json()["entities"] == [
        {"name": "subjects", "count": 300}
    ]
    assert client.get("/inspect/subject_accounts", headers=limited).status_code == 403
    assert client.get("/inspect/docs", headers=bearer()).status_code == 404
    for query in ["limit=0", "limit=101", "offset=-1", "offset=100001", "before=-1", "limit=x"]:
        assert client.get(f"/inspect/catalog?{query}", headers=bearer()).status_code == 400
    service.audit = None
    assert not client.get("/inspect/catalog", headers=bearer()).json()["audit_enabled"]
    assert client.get("/inspect/calls", headers=bearer()).status_code == 503


def test_history_principal_scopes_admin_pagination_and_redaction(inspected):
    service, audit, client, _ = inspected
    own = CallContext("gaia:7", ALL_SCOPES)
    other = CallContext("local-stdio", ALL_SCOPES)
    version = service.manifest["dataset_version"]
    response = service.call("search_subjects", {"query": "omonimo"}, own)
    service.call("search_parcels", {"limit": 1}, own)
    service.call("search_subjects", {"query": "private-free-text"}, other)
    service.call("search_subjects", {"query": "secret-invalid", "extra": "password"}, own)
    service.call("unknown", {}, own)
    history = audit.history(own, version, limit=1)
    assert history["visibility"] == "own" and history["next_before"] is not None
    assert history["results"][0]["filters"] == {}
    next_page = audit.history(own, version, before=history["next_before"], limit=100)
    assert len(next_page["results"]) == 2 and next_page["next_before"] is None
    assert next_page["results"][-1]["response"] == response
    assert next_page["results"][-1]["filters"] == {"query": "[omesso]"}
    narrowed = CallContext(own.principal, frozenset({"utenze.read"}))
    assert len(audit.history(narrowed, version)["results"]) == 2
    assert audit.history(CallContext(own.principal, frozenset()), version)["results"] == []
    assert audit.history(own, "different-dataset")["results"] == []
    admin = bearer(scopes=ALL_SCOPES | {AUDIT_SCOPE})
    combined = client.get("/inspect/calls", headers=admin).json()
    assert combined["visibility"] == "all_authorized" and len(combined["results"]) == 4
    assert "private-free-text" not in str(combined) and "secret-invalid" not in str(combined)
    assert "password" not in str(combined)
    assert len(client.get("/inspect/calls", headers=bearer()).json()["results"]) == 3


def test_audit_persistence_retention_and_path_guards(tmp_path):
    with pytest.raises(ValueError):
        AuditStore(tmp_path / "wrong.sqlite")
    target = tmp_path / "target"
    target.write_text("untouched")
    link = tmp_path / "gaia-mcp-audit.sqlite"
    link.symlink_to(target)
    with pytest.raises(ValueError):
        AuditStore(link)
    link.unlink()
    audit = AuditStore(link)
    assert link.stat().st_mode & 0o777 == 0o600
    event = {
        "principal": "hash",
        "permission_scope": "utenze.read",
        "dataset_or_corpus_version": "v1",
    }
    for _ in range(1002):
        audit.record(event, {"cursor": "secret-cursor"}, {"source": "gaia_synthetic_db"})
    assert audit.connection.execute("SELECT COUNT(*) FROM calls").fetchone()[0] == 1000
    assert (
        "secret-cursor"
        not in audit.connection.execute("SELECT payload FROM calls LIMIT 1").fetchone()[0]
    )
    audit.close()
    reopened = AuditStore(link)
    assert reopened.connection.execute("SELECT COUNT(*) FROM calls").fetchone()[0] == 1000
    reopened.close()


@pytest.fixture
def gateway(monkeypatch):
    monkeypatch.setattr(
        console_routes, "user_context", lambda *args: CallContext("gaia:7", ALL_SCOPES)
    )
    app = FastAPI()
    app.include_router(console_routes.router, prefix="/wiki/mcp")
    app.dependency_overrides[get_db] = lambda: None
    user = SimpleNamespace(id=7, role="viewer")
    app.dependency_overrides[require_active_user] = lambda: user
    return TestClient(app), user


def test_console_gateway_real_bearer_and_errors(gateway, monkeypatch):
    client, user = gateway
    monkeypatch.setattr(
        console_routes,
        "source_client",
        lambda: SimpleNamespace(secret=SECRET, urls={"data": "http://localhost:8768/data/"}),
    )
    observed = []
    status = [200]

    class Transport:
        def __init__(self, **kwargs):
            observed.append(kwargs)

        async def get(self, url, params):
            assert url == "http://localhost:8768/inspect/catalog"
            assert params == {"limit": 25, "offset": 0, "before": 0}
            return SimpleNamespace(
                status_code=status[0], json=lambda: {"source": "gaia_synthetic_db"}
            )

    @asynccontextmanager
    async def transport(**kwargs):
        yield Transport(**kwargs)

    monkeypatch.setattr(console_routes.httpx2, "AsyncClient", transport)
    assert client.get("/wiki/mcp/console/catalog").json() == {"source": "gaia_synthetic_db"}
    context = verify_token(SECRET, observed[-1]["headers"]["Authorization"][7:])
    assert context.scopes == ALL_SCOPES and not observed[-1]["follow_redirects"]
    user.role = "admin"
    assert client.get("/wiki/mcp/console/catalog").status_code == 200
    context = verify_token(SECRET, observed[-1]["headers"]["Authorization"][7:])
    assert AUDIT_SCOPE in context.scopes and "docs.read" not in context.scopes
    for code in [403, 404, 401, 500]:
        status[0] = code
        assert client.get("/wiki/mcp/console/catalog").status_code == (
            code if code in {403, 404} else 503
        )
    assert client.get("/wiki/mcp/console/docs").status_code == 404
    assert client.get("/wiki/mcp/console/catalog?limit=101").status_code == 422
    monkeypatch.setattr(
        console_routes, "source_client", Mock(side_effect=RuntimeError("private detail"))
    )
    result = client.get("/wiki/mcp/console/catalog")
    assert result.status_code == 503 and "private detail" not in result.text
    monkeypatch.setattr(
        console_routes, "source_client", Mock(side_effect=HTTPException(503, "configuration"))
    )
    assert client.get("/wiki/mcp/console/catalog").json()["detail"] == "configuration"
    client.app.dependency_overrides.pop(require_active_user)
    assert client.get("/wiki/mcp/console/catalog").status_code == 401


def test_http_and_stdio_audit_cli_cleanup_and_data_only(inspected, monkeypatch, tmp_path):
    _, _, _, path = inspected
    monkeypatch.setenv("GAIA_MCP_SIGNING_SECRET", SECRET)
    audit_path = tmp_path / "stdio" / "gaia-mcp-audit.sqlite"
    captured = []
    monkeypatch.setattr(cli.uvicorn, "run", lambda *args, **kwargs: captured.append(args[0]))
    cli.main(["--data-only", "--database", str(path), "--audit-database", str(audit_path)])
    assert captured and audit_path.exists()
    for args in [
        ["--database", str(path)],
        ["--data-only", "--corpus", "forbidden", "--database", str(path)],
    ]:
        with pytest.raises(SystemExit):
            cli.main(args)
    instances = []

    def create(service, context_factory):
        instances.append(service)
        assert context_factory().principal == "local-stdio"
        service.call("search_subjects", {"query": "omonimo"}, context_factory())
        return "server"

    monkeypatch.setattr(data_cli, "create_server", create)
    monkeypatch.setattr(data_cli, "run_stdio", lambda server: None)
    data_cli.main(["serve", "--database", str(path), "--audit-database", str(audit_path)])
    with pytest.raises(sqlite3.ProgrammingError):
        instances[0].audit.connection.execute("SELECT 1")
