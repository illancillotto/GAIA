import asyncio
import runpy
import socket
import threading
from contextlib import asynccontextmanager, contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import anyio
import pytest
import uvicorn
from fastapi import FastAPI
from fastapi.testclient import TestClient
from openai.types.chat import ChatCompletionMessage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.deps import require_active_user
from app.core.config import settings
from app.core.database import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.models.application_user import ApplicationUser
from app.models.network import NetworkVpnDevice, NetworkVpnSession
from app.models.section_permission import RoleSectionPermission, Section, UserSectionPermission
from app.modules.accessi.routes.auth import router as auth_router
from app.modules.wiki.mcps import cli, routes
from app.modules.wiki.mcps.agent import AgentRun, WikiMCPAgent, bounded_evidence
from app.modules.wiki.mcps.auth import verify_token
from app.modules.wiki.mcps.client import WikiMCPClient, tool_scope, validate_source_url
from app.modules.wiki.mcps.context import CallContext
from app.modules.wiki.mcps.data.database import seed_database
from app.modules.wiki.mcps.data.service import DataService, SourceError
from app.modules.wiki.mcps.docs.corpus import Manifest, ManifestEntry, build_corpus
from app.modules.wiki.mcps.docs.service import DocsService
from app.modules.wiki.mcps.http import create_http_app

SECRET = "pytest-mcp-signing-secret-for-integration-12345"


@contextmanager
def authenticated_application(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'synthetic-auth.sqlite'}", connect_args={"check_same_thread": False}
    )
    tables = [
        ApplicationUser.__table__,
        NetworkVpnDevice.__table__,
        NetworkVpnSession.__table__,
        Section.__table__,
        RoleSectionPermission.__table__,
        UserSectionPermission.__table__,
    ]
    Base.metadata.create_all(engine, tables=tables)
    sessions = sessionmaker(bind=engine)
    with sessions() as database:
        database.add(
            ApplicationUser(
                username="synthetic-mcp",
                email="synthetic-mcp@example.invalid",
                password_hash=hash_password("synthetic-login-password"),
                role="viewer",
                module_utenze=True,
                module_catasto=True,
                module_ruolo=True,
            )
        )
        for key in ("utenze.subjects", "catasto.dashboard", "ruolo.avvisi", "ruolo.tributi.view"):
            database.add(Section(key=key, module=key.split(".")[0], label=key, min_role="viewer"))
        database.commit()

    def isolated_database():
        with sessions() as database:
            yield database

    application = FastAPI()
    application.include_router(auth_router)
    application.include_router(routes.router, prefix="/wiki")
    application.dependency_overrides[get_db] = isolated_database
    try:
        with TestClient(application) as client:
            yield client, sessions
    finally:
        engine.dispose()


def test_gateway_real_login_permissions_revocation_and_inactive_user(tmp_path, monkeypatch):
    monkeypatch.setenv("GAIA_MCP_SIGNING_SECRET", SECRET)
    monkeypatch.setattr(settings, "jwt_secret_key", SECRET)
    with authenticated_application(tmp_path) as (client, sessions):
        assert client.get("/wiki/mcp/tools").status_code == 401
        assert client.post("/wiki/mcp/chat", json={"question": "Sintetico"}).status_code == 401
        assert (
            client.post(
                "/auth/login", json={"username": "synthetic-mcp", "password": "incorrect"}
            ).status_code
            == 401
        )
        login = client.post(
            "/auth/login",
            json={"username": "synthetic-mcp", "password": "synthetic-login-password"},
        )
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        with sessions() as database:
            persisted_user = database.get(ApplicationUser, 1)
            assert persisted_user.login_count == 1
            assert persisted_user.last_login_at is not None
            assert database.query(NetworkVpnDevice).filter_by(user_id=1).count() == 1
        token = client.post("/wiki/mcp/token", json={}, headers=headers)
        assert token.status_code == 200
        assert token.json()["scopes"] == ["catasto.read", "ruolo.read", "utenze.read"]
        verified = verify_token(SECRET, token.json()["access_token"])
        assert verified.principal == "gaia:1" and "docs.read" not in verified.scopes
        with sessions() as database:
            user = database.get(ApplicationUser, 1)
            user.module_catasto = False
            section = database.query(Section).filter_by(key="utenze.subjects").one()
            database.add(UserSectionPermission(user_id=1, section_id=section.id, is_granted=False))
            role_section = database.query(Section).filter_by(key="ruolo.tributi.view").one()
            database.add(
                RoleSectionPermission(section_id=role_section.id, role="viewer", is_granted=False)
            )
            database.commit()
        assert client.post("/wiki/mcp/token", json={}, headers=headers).json()["scopes"] == []
        with sessions() as database:
            database.get(ApplicationUser, 1).is_active = False
            database.commit()
        assert client.post("/wiki/mcp/token", json={}, headers=headers).status_code == 401
        assert (
            client.post(
                "/wiki/mcp/chat", json={"question": "Sintetico"}, headers=headers
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/auth/login",
                json={"username": "synthetic-mcp", "password": "synthetic-login-password"},
            ).status_code
            == 403
        )


def context():
    return CallContext(
        principal="gaia:7",
        scopes=frozenset({"docs.read", "utenze.read", "catasto.read", "ruolo.read"}),
    )


def corpus_files(tmp_path):
    path = tmp_path / "domain-docs/catasto/docs/PRD.md"
    path.parent.mkdir(parents=True)
    path.write_text("# Catasto\nParticelle e utenze irrigue sintetiche.")
    entry = ManifestEntry(
        path=path.relative_to(tmp_path).as_posix(),
        domain="catasto",
        category="prd",
        included=True,
        status="current",
        reason="Synthetic integration fixture",
    )
    corpus = build_corpus(tmp_path, Manifest(entries=[entry]))
    frozen = tmp_path / "corpus.json"
    frozen.write_text(corpus.model_dump_json())
    database = tmp_path / "gaia-mcp-synthetic-integration.sqlite"
    seed_database(database, "integration")
    return frozen, database


@pytest.mark.parametrize(
    "url",
    [
        "https://cloud.example/mcp",
        "file:///etc/passwd",
        "http://localhost@cloud.example/mcp",
        "http://user:password@localhost/mcp",
        "http://localhost/mcp?token=secret",
        "http://localhost/mcp#fragment",
    ],
)
def test_source_urls_cannot_escape_internal_hosts(url):
    with pytest.raises(ValueError):
        validate_source_url(url)
    with pytest.raises(ValueError):
        WikiMCPClient(url, "http://localhost:8768/data/", SECRET)


def test_client_validation_and_scopes():
    assert tool_scope("docs", "search_docs") == "docs.read"
    assert tool_scope("data", "search_subjects") == "utenze.read"
    for source, name in [
        ("nas", "read_file"),
        ("docs", "search_subjects"),
        ("data", "search_docs"),
    ]:
        with pytest.raises(SourceError):
            tool_scope(source, name)


def test_client_calls_and_remote_contract_validation(monkeypatch):
    instance = WikiMCPClient("http://localhost:8768/docs/", "http://localhost:8768/data/", SECRET)
    response = {"source": "gaia_docs", "tool": "search_docs", "results": []}
    fake = SimpleNamespace(
        call_tool=AsyncMock(
            return_value=SimpleNamespace(structured_content=response, is_error=False)
        ),
        list_tools=AsyncMock(
            return_value=SimpleNamespace(
                tools=[SimpleNamespace(name="search_docs", description="Search", input_schema={})]
            )
        ),
    )

    @asynccontextmanager
    async def session(source, current_context):
        yield fake

    monkeypatch.setattr(instance, "session", session)

    async def exercise():
        assert await instance.call_tool("docs__search_docs", {"query": "x"}, context()) == response
        for name in ["bad", "docs__bad__name", "nas__get_file"]:
            with pytest.raises(SourceError, match="INVALID_ARGUMENT"):
                await instance.call_tool(name, {}, context())
        with pytest.raises(SourceError, match="PERMISSION_DENIED"):
            await instance.call_tool(
                "docs__search_docs", {}, CallContext(principal="denied", scopes=frozenset())
            )
        fake.call_tool.return_value = SimpleNamespace(structured_content=None, is_error=True)
        with pytest.raises(SourceError, match="INVALID_ARGUMENT"):
            await instance.call_tool("docs__search_docs", {}, context())
        fake.call_tool.return_value = SimpleNamespace(structured_content=None, is_error=False)
        with pytest.raises(SourceError, match="INTERNAL_ERROR"):
            await instance.call_tool("docs__search_docs", {}, context())
        fake.call_tool.return_value = SimpleNamespace(
            structured_content={"source": "nas", "tool": "search_docs"}, is_error=False
        )
        with pytest.raises(SourceError, match="INTERNAL_ERROR"):
            await instance.call_tool("docs__search_docs", {}, context())
        fake.call_tool.return_value = SimpleNamespace(
            structured_content={"source": "gaia_docs", "tool": "other"}, is_error=False
        )
        with pytest.raises(SourceError, match="INTERNAL_ERROR"):
            await instance.call_tool("docs__search_docs", {}, context())
        fake.list_tools.side_effect = [
            SimpleNamespace(
                tools=[SimpleNamespace(name="search_docs", description="Search", input_schema={})]
            ),
            SimpleNamespace(
                tools=[
                    SimpleNamespace(name="search_subjects", description="Search", input_schema={})
                ]
            ),
        ]
        tools = await instance.list_tools(
            CallContext(principal="docs", scopes=frozenset({"docs.read"}))
        )
        assert [tool["name"] for tool in tools] == ["docs__search_docs"]

    anyio.run(exercise)


def message(content=None, calls=None):
    return ChatCompletionMessage(role="assistant", content=content, tool_calls=calls)


def tool_call(name, arguments, identifier="call-1"):
    return {
        "id": identifier,
        "type": "function",
        "function": {"name": name, "arguments": arguments},
    }


def model_client(messages):
    responses = [SimpleNamespace(choices=[SimpleNamespace(message=value)]) for value in messages]
    return SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(side_effect=responses)))
    )


def sources():
    return SimpleNamespace(
        list_tools=AsyncMock(
            return_value=[
                {"name": "docs__search_docs", "description": "Search", "input_schema": {}}
            ]
        ),
        call_tool=AsyncMock(
            return_value={
                "source": "gaia_docs",
                "results": [{"content": "Evidence"}],
                "provenance": [{"source_path": "docs/PRD.md"}],
                "result_count": 1,
            }
        ),
    )


def test_agent_selects_sources_and_returns_provenance():
    source = sources()
    model = model_client(
        [
            message(calls=[tool_call("docs__search_docs", '{"query":"particelle"}')]),
            message(content="Risposta dalle evidenze."),
        ]
    )
    agent = WikiMCPAgent(source, model, "local-model")
    result = anyio.run(agent.answer, "Come cercare particelle?", context())
    assert result["found"] is True and result["tool_calls"] == 1
    assert result["provenance"] == [{"source_path": "docs/PRD.md"}]
    assert source.call_tool.call_args.args[0] == "docs__search_docs"
    assert source.call_tool.call_args.args[2].principal == context().principal
    assert model.chat.completions.create.call_args_list[0].kwargs["tool_choice"] == "auto"


@pytest.mark.parametrize("arguments", ["invalid json", "[]"])
def test_agent_invalid_model_arguments_are_source_errors(arguments):
    source = sources()
    model = model_client([message(calls=[tool_call("docs__search_docs", arguments)]), message()])
    result = anyio.run(WikiMCPAgent(source, model, "local").answer, "Question", context())
    assert result["found"] is False
    assert "non bastano" in result["answer"]
    source.call_tool.assert_not_awaited()


def test_agent_permission_denial_no_tools_and_budgets():
    source = sources()
    source.call_tool.side_effect = SourceError("PERMISSION_DENIED")
    model = model_client(
        [message(calls=[tool_call("docs__search_docs", "{}")]), message(content="Accesso negato.")]
    )
    result = anyio.run(WikiMCPAgent(source, model, "local").answer, "Question", context())
    assert result["found"] is False
    source.list_tools.return_value = []
    model = model_client([message()])
    assert (
        anyio.run(WikiMCPAgent(source, model, "local").answer, "Question", context())["tool_calls"]
        == 0
    )
    assert model.chat.completions.create.call_args.kwargs["tool_choice"] == "none"
    for kwargs in [{"max_calls": 0}, {"max_evidence_tokens": 99}, {"max_evidence_tokens": 12001}]:
        with pytest.raises(ValueError):
            WikiMCPAgent(source, model, "local", **kwargs)


def test_agent_batch_call_cap_and_model_ignoring_budget():
    source = sources()
    model = model_client(
        [
            message(
                calls=[
                    tool_call("docs__search_docs", "{}", "first"),
                    tool_call("docs__search_docs", "{}", "second"),
                ]
            ),
            message(content="Limited evidence."),
        ]
    )
    result = anyio.run(
        WikiMCPAgent(source, model, "local", max_calls=1).answer, "Question", context()
    )
    assert result["tool_calls"] == 1
    assert source.call_tool.await_count == 1
    assert model.chat.completions.create.call_args.kwargs["tool_choice"] == "none"
    model = model_client(
        [message(calls=[tool_call("docs__search_docs", "{}")]) for _index in range(2)]
    )
    with pytest.raises(RuntimeError, match="ignored"):
        anyio.run(WikiMCPAgent(source, model, "local", max_calls=1).answer, "Question", context())


def test_evidence_hard_budget_truncates_without_mutating_source():
    response = {
        "results": [{"content": "x" * 1000}, {"content": "y" * 1000}],
        "provenance": [{"id": 1}, {"id": 2}],
        "result_count": 2,
    }
    bounded = bounded_evidence(response, 300)
    assert len(bounded["results"]) == 1 and bounded["truncated"]
    assert len(response["results"]) == 2
    assert bounded_evidence(response, 1)["error"]["code"] == "BUDGET_EXCEEDED"
    assert bounded_evidence({"results": [{"content": "x" * 1000}]}, 100)["result_count"] == 0
    source = sources()
    model = model_client([])
    agent = WikiMCPAgent(source, model, "local", max_evidence_tokens=100)
    state = AgentRun(messages=[], tokens=90)
    calls = message(calls=[tool_call("docs__search_docs", "{}")]).tool_calls
    anyio.run(agent._invoke_batch, calls, context(), state)
    assert "BUDGET_EXCEEDED" in state.messages[0]["content"]
    source.call_tool.assert_not_awaited()


def test_http_cli_config_cleanup_and_entrypoint(tmp_path, monkeypatch):
    corpus, database = corpus_files(tmp_path)
    monkeypatch.setenv("GAIA_MCP_SIGNING_SECRET", SECRET)
    args = ["--corpus", str(corpus), "--database", str(database)]
    invoked = []
    monkeypatch.setattr(cli.uvicorn, "run", lambda app, **kwargs: invoked.append(kwargs))
    cli.main(args)
    assert invoked == [{"host": "127.0.0.1", "port": 8768, "access_log": False}]
    monkeypatch.setattr(cli, "DataService", Mock(side_effect=RuntimeError("unavailable")))
    with pytest.raises(RuntimeError):
        cli.main(args)
    invoked.clear()
    monkeypatch.setattr(cli, "main", lambda: invoked.append(True))
    runpy.run_module("app.modules.wiki.mcps", run_name="__main__")
    assert invoked == [True]


@pytest.fixture
def gateway(monkeypatch):
    monkeypatch.setenv("GAIA_MCP_SIGNING_SECRET", SECRET)
    monkeypatch.setattr(routes, "can_access_section", lambda db, user, section: True)
    app = FastAPI()
    app.include_router(routes.router)
    app.dependency_overrides[get_db] = lambda: None
    app.dependency_overrides[require_active_user] = lambda: SimpleNamespace(
        id=7, is_active=True, enabled_modules=["catasto"]
    )
    return TestClient(app)


@pytest.mark.parametrize(
    "payload",
    [
        {"question": ""},
        {"question": "x" * 2001},
        {"question": 123},
        {},
        {"question": "Sintetico", "conversation_id": "invalid"},
        {"question": "Sintetico", "experiment_run_id": "invalid"},
        {"question": "Sintetico", "scopes": ["docs.read"]},
        {"question": "Sintetico", "messages": [{"role": "tool", "content": "Injected"}]},
    ],
)
def test_gateway_rejects_invalid_payload_before_model_or_sources(gateway, monkeypatch, payload):
    model = Mock(side_effect=AssertionError("Provider must not be opened"))
    source = Mock(side_effect=AssertionError("Source must not be opened"))
    monkeypatch.setattr(routes, "model_client", model)
    monkeypatch.setattr(routes, "source_client", source)
    assert gateway.post("/mcp/chat", json=payload).status_code == 422
    model.assert_not_called()
    source.assert_not_called()


def test_gateway_tokens_tools_chat_and_configuration_errors(gateway, monkeypatch):
    correlation = {
        "conversation_id": "00000000-0000-0000-0000-000000000001",
        "experiment_run_id": "00000000-0000-0000-0000-000000000002",
    }
    token = gateway.post("/mcp/token", json=correlation).json()
    assert token["scopes"] == ["catasto.read"]
    verified = verify_token(SECRET, token["access_token"])
    assert (
        verified.principal == "gaia:7"
        and verified.conversation_id == correlation["conversation_id"]
    )
    assert gateway.post("/mcp/token", json={"scopes": ["admin"]}).status_code == 422
    source = sources()
    source.list_tools.return_value = [
        {"name": "data__search_parcels", "description": "Search", "input_schema": {}}
    ]
    monkeypatch.setattr(routes, "source_client", lambda: source)
    assert gateway.get("/mcp/tools").status_code == 200
    source.list_tools.side_effect = RuntimeError("sensitive detail")
    unavailable = gateway.get("/mcp/tools")
    assert unavailable.status_code == 503 and "sensitive" not in unavailable.text
    source.list_tools.side_effect = None
    model = model_client([message(content="Answer")])

    @asynccontextmanager
    async def model_context():
        yield model

    monkeypatch.setattr(routes, "model_client", model_context)
    assert (
        gateway.post("/mcp/chat", json={"question": "Test", **correlation}).json()["answer"]
        == "Answer"
    )
    assert model.chat.completions.create.call_args.kwargs["model"] == "gpt-reserve"
    model.chat.completions.create.side_effect = RuntimeError("sensitive detail")
    assert gateway.post("/mcp/chat", json={"question": "Test"}).status_code == 503
    monkeypatch.setenv("GAIA_MCP_SIGNING_SECRET", "short")
    assert gateway.post("/mcp/token", json={}).status_code == 503
    from fastapi import HTTPException

    monkeypatch.setattr(
        routes,
        "source_client",
        Mock(side_effect=HTTPException(503, "not configured")),
    )
    assert gateway.get("/mcp/tools").status_code == 503
    monkeypatch.setattr(
        routes,
        "model_client",
        Mock(side_effect=HTTPException(503, "not configured")),
    )
    assert gateway.post("/mcp/chat", json={"question": "Test"}).status_code == 503


def test_model_provider_uses_configured_codex_lb_and_routes_mounted(monkeypatch):
    monkeypatch.setenv("GAIA_MCP_MODEL_API_KEY", "synthetic-provider-key")
    monkeypatch.setenv("GAIA_MCP_MODEL", "gpt-reserve")
    for url in [
        "file:///tmp/provider",
        "http:///v1",
        "http://user@localhost/v1",
        "http://localhost/v1?key=secret",
        "http://localhost/v1#fragment",
    ]:
        monkeypatch.setenv("GAIA_MCP_MODEL_BASE_URL", url)
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            routes.model_client()
    monkeypatch.setenv("GAIA_MCP_MODEL_BASE_URL", "https://codex-lb.example/v1")
    client = routes.model_client()
    assert str(client.base_url) == "https://codex-lb.example/v1/"
    assert client.api_key == "synthetic-provider-key"
    anyio.run(client.close)
    monkeypatch.setenv("GAIA_MCP_SIGNING_SECRET", SECRET)
    monkeypatch.setenv("GAIA_MCP_DOCS_URL", "https://forbidden.example/docs/")
    assert set(routes.source_client().urls) == {"data"}
    from app.modules.wiki.router import router

    assert "/mcp/chat" in {route.path for route in router.routes}


@pytest.mark.parametrize(
    "url,key,model",
    [
        ("", "key", "gpt-reserve"),
        ("https://codex-lb.example/v1", "", "gpt-reserve"),
        ("https://codex-lb.example/v1", "key", "another-model"),
    ],
)
def test_model_provider_fails_closed_without_configuration(monkeypatch, url, key, model):
    from fastapi import HTTPException

    for name in (
        "CODEX_LB_URL",
        "CODEX_LB_API_KEY",
        "GAIA_MCP_MODEL_BASE_URL",
        "GAIA_MCP_MODEL_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GAIA_MCP_MODEL_BASE_URL", url)
    monkeypatch.setenv("GAIA_MCP_MODEL_API_KEY", key)
    monkeypatch.setenv("GAIA_MCP_MODEL", model)
    with pytest.raises(HTTPException, match="503"):
        routes.model_client()


def test_model_provider_reuses_existing_codex_lb_credentials(monkeypatch):
    monkeypatch.delenv("GAIA_MCP_MODEL", raising=False)
    monkeypatch.setenv("GAIA_MCP_MODEL_BASE_URL", "")
    monkeypatch.setenv("GAIA_MCP_MODEL_API_KEY", "")
    monkeypatch.setenv("CODEX_LB_URL", "http://codex-lb.example/v1")
    monkeypatch.setenv("CODEX_LB_API_KEY", "synthetic-existing-key")
    client = routes.model_client()
    assert str(client.base_url) == "http://codex-lb.example/v1/"
    assert client.api_key == "synthetic-existing-key"
    assert client.max_retries == 0
    anyio.run(client.close)


def test_data_only_client_blocks_docs_sessions_and_all_tools():
    source = WikiMCPClient(None, "http://localhost:8768/data/", SECRET)
    from app.modules.wiki.mcps.docs.service import INPUTS

    async def exercise():
        async with source.session("docs", context()):
            pytest.fail("A disabled Docs session was opened")

    with pytest.raises(SourceError, match="PERMISSION_DENIED"):
        anyio.run(exercise)
    for name in INPUTS:
        with pytest.raises(SourceError, match="PERMISSION_DENIED"):
            anyio.run(source.call_tool, f"docs__{name}", {}, context())


def test_data_only_agent_rejects_docs_evidence_from_data_transport(monkeypatch):
    source = WikiMCPClient(None, "http://localhost:8768/data/", SECRET)
    remote = SimpleNamespace(
        list_tools=AsyncMock(
            return_value=SimpleNamespace(
                tools=[
                    SimpleNamespace(
                        name="search_subjects", description="Synthetic subjects", input_schema={}
                    )
                ]
            )
        ),
        call_tool=AsyncMock(
            return_value=SimpleNamespace(
                is_error=False,
                structured_content={
                    "source": "gaia_docs",
                    "tool": "search_subjects",
                    "results": [{"content": "DOCUMENT_CONTENT_MUST_NOT_REACH_MODEL"}],
                    "provenance": [{"source_path": "docs/real.md"}],
                    "result_count": 1,
                },
            )
        ),
    )

    @asynccontextmanager
    async def session(source_name, current_context):
        assert source_name == "data"
        yield remote

    monkeypatch.setattr(source, "session", session)
    model = model_client(
        [
            message(calls=[tool_call("data__search_subjects", '{"query":"synthetic"}')]),
            message(content="Evidenze non disponibili."),
        ]
    )
    result = anyio.run(
        WikiMCPAgent(source, model, "gpt-reserve").answer, "Cerca soggetti sintetici", context()
    )
    assert not result["found"] and result["provenance"] == []
    final_messages = model.chat.completions.create.call_args.kwargs["messages"]
    assert "INTERNAL_ERROR" in final_messages[-1]["content"]
    assert "DOCUMENT_CONTENT_MUST_NOT_REACH_MODEL" not in str(final_messages)
    assert "docs/real.md" not in str(final_messages)


def test_real_http_sdk_client_discovers_and_calls_both_sources(tmp_path):
    corpus, database = corpus_files(tmp_path)
    from app.modules.wiki.mcps.docs.corpus import load_corpus

    docs, data = DocsService(load_corpus(corpus)), DataService(database)
    app = create_http_app(docs, data, SECRET)
    requests = []

    async def record_requests(request, call_next):
        requests.append(request.url.path)
        return await call_next(request)

    app.app.add_middleware(BaseHTTPMiddleware, dispatch=record_requests)

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    instance = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error", access_log=False)
    )
    thread = threading.Thread(
        target=lambda: asyncio.run(instance.serve(sockets=[listener])), daemon=True
    )
    thread.start()

    async def exercise():
        for _attempt in range(200):
            if instance.started:
                break
            await anyio.sleep(0.01)
        assert instance.started
        source = WikiMCPClient(
            f"http://127.0.0.1:{port}/docs/", f"http://127.0.0.1:{port}/data/", SECRET
        )
        tools = await source.list_tools(context())
        assert len(tools) == 16
        document = await source.call_tool("docs__search_docs", {"query": "particelle"}, context())
        assert document["source"] == "gaia_docs" and document["result_count"] == 1
        subjects = await source.call_tool("data__search_subjects", {"query": "omonimo"}, context())
        subject_id = subjects["results"][0]["id"]
        accounts = await source.call_tool(
            "data__search_irrigation_accounts", {"subject_id": subject_id}, context()
        )
        assert accounts["source"] == "gaia_synthetic_db" and accounts["result_count"] >= 1
        model = model_client(
            [
                message(calls=[tool_call("docs__search_docs", '{"query":"particelle"}')]),
                message(calls=[tool_call("data__search_subjects", '{"query":"omonimo"}', "data")]),
                message(content="Evidenze documentali e dati sintetici verificati."),
            ]
        )
        result = await WikiMCPAgent(source, model, "local-test").answer(
            "Documenti e soggetti?", context()
        )
        assert result["found"] and result["tool_calls"] == 2
        assert len(result["provenance"]) == 3

        requests.clear()
        data_source = WikiMCPClient(None, f"http://127.0.0.1:{port}/data/", SECRET)
        data_tools = await data_source.list_tools(context())
        assert len(data_tools) == 12
        assert all(tool["source"] == "data" for tool in data_tools)
        data_model = model_client(
            [
                message(calls=[tool_call("docs__search_docs", '{"query":"particelle"}')]),
                message(calls=[tool_call("data__search_subjects", '{"query":"omonimo"}', "data")]),
                message(content="Soggetti sintetici verificati."),
            ]
        )
        data_result = await WikiMCPAgent(data_source, data_model, "gpt-reserve").answer(
            "Cerca soggetti sintetici omonimi", context()
        )
        assert data_result["found"] and data_result["tool_calls"] == 2
        assert data_result["provenance"] == subjects["provenance"]
        assert requests and all(path.startswith("/data/") for path in requests)
        for invocation in data_model.chat.completions.create.call_args_list:
            assert all(
                tool["function"]["name"].startswith("data__") for tool in invocation.kwargs["tools"]
            )
            tool_messages = [
                item for item in invocation.kwargs["messages"] if item["role"] == "tool"
            ]
            assert "PERMISSION_DENIED" in tool_messages[0]["content"]
            assert all(
                "gaia_docs" not in item["content"]
                and "source_path" not in item["content"]
                and "Particelle e utenze irrigue sintetiche." not in item["content"]
                for item in tool_messages
            )

    try:
        anyio.run(exercise)
    finally:
        instance.should_exit = True
        thread.join(timeout=5)
        listener.close()
        docs.close()
        data.close()
    assert not thread.is_alive()
