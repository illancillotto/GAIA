import asyncio
from unittest.mock import AsyncMock

import httpx
import pytest
from mcp import types

from app.modules.wiki.mcps.agent import WikiMCPAgent
from app.modules.wiki.mcps.auth import issue_token
from app.modules.wiki.mcps.context import CallContext
from app.modules.wiki.mcps.data.catalog import SERVER_INSTRUCTIONS, TOOL_DESCRIPTIONS
from app.modules.wiki.mcps.data.database import seed_database
from app.modules.wiki.mcps.data.queries import QUERIES
from app.modules.wiki.mcps.data.server import create_server, run_stdio, serve_stdio
from app.modules.wiki.mcps.data.service import DataService
from app.modules.wiki.mcps.http import create_http_app

SECRET = "synthetic-discovery-test-signing-secret-12345"
ALL_SCOPES = frozenset({"utenze.read", "catasto.read", "ruolo.read"})


@pytest.fixture
def service(tmp_path):
    database = tmp_path / "gaia-mcp-synthetic-discovery.sqlite"
    seed_database(database, "discovery-synthetic")
    instance = DataService(database)
    yield instance
    instance.close()


def expected_tools(scopes):
    return sorted(name for name, query in QUERIES.items() if query.scope in scopes)


@pytest.mark.parametrize(
    "scopes", [set(), {"docs.read"}, {"utenze.read"}, {"catasto.read"}, {"ruolo.read"}, ALL_SCOPES]
)
def test_discovery_filters_at_server_for_every_scope(service, scopes):
    context = CallContext("synthetic-discovery", frozenset(scopes))
    server = create_server(service, lambda: context)

    async def exercise():
        result = await server._request_handlers["tools/list"].handler(None, None)
        assert [tool.name for tool in result.tools] == expected_tools(scopes)
        assert all(tool.annotations.read_only_hint for tool in result.tools)
        assert all(tool.name in QUERIES for tool in result.tools)
        for tool in result.tools:
            assert tool.description == (
                TOOL_DESCRIPTIONS[tool.name] + f" Requires {QUERIES[tool.name].scope}."
            )

    asyncio.run(exercise())


def test_context_is_resolved_per_discovery_and_missing_context_fails_closed(service):
    contexts = iter([CallContext("first", ALL_SCOPES), CallContext("second", frozenset())])
    server = create_server(service, lambda: next(contexts))

    async def exercise():
        handler = server._request_handlers["tools/list"].handler
        assert len((await handler(None, None)).tools) == len(QUERIES)
        assert (await handler(None, None)).tools == []

    asyncio.run(exercise())

    def missing_context():
        raise LookupError("No authenticated context")

    missing = create_server(service, missing_context)
    with pytest.raises(LookupError):
        asyncio.run(missing._request_handlers["tools/list"].handler(None, None))


def test_hidden_tools_remain_denied_and_docs_never_execute(service):
    context = CallContext("synthetic-restricted", frozenset({"utenze.read"}))
    server = create_server(service, lambda: context)

    async def exercise():
        handler = server._request_handlers["tools/call"].handler
        allowed = await handler(
            None,
            types.CallToolRequestParams(name="search_subjects", arguments={"query": "omonimo"}),
        )
        assert not allowed.is_error
        assert allowed.structured_content["source"] == "gaia_synthetic_db"
        denied = await handler(
            None,
            types.CallToolRequestParams(
                name="search_role_notices", arguments={"notice_code": "SYN-N0001"}
            ),
        )
        assert denied.is_error
        assert denied.structured_content["error"]["code"] == "PERMISSION_DENIED"
        docs = await handler(
            None, types.CallToolRequestParams(name="search_docs", arguments={"query": "synthetic"})
        )
        assert docs.is_error
        assert docs.structured_content["error"]["code"] == "INVALID_ARGUMENT"

    asyncio.run(exercise())


def test_data_only_http_scope_isolation_and_docs_absence_without_network(service):
    application = create_http_app(None, service, SECRET)

    async def exercise():
        async with application.app.router.lifespan_context(application.app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=application), base_url="http://localhost"
            ) as client:

                async def discover(principal, scopes):
                    context = CallContext(principal, frozenset(scopes))
                    headers = {
                        "Authorization": "Bearer " + issue_token(SECRET, context),
                        "Accept": "application/json, text/event-stream",
                        "MCP-Protocol-Version": "2025-11-25",
                    }
                    payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
                    response = await client.post("/data/", headers=headers, json=payload)
                    assert response.status_code == 200
                    assert [
                        tool["name"] for tool in response.json()["result"]["tools"]
                    ] == expected_tools(scopes)
                    assert (
                        await client.post("/docs/", headers=headers, json=payload)
                    ).status_code == 404
                    return headers

                await asyncio.gather(
                    discover("all", ALL_SCOPES),
                    discover("restricted", {"utenze.read"}),
                    discover("docs-only", {"docs.read"}),
                )
                headers = await discover("restricted-again", {"utenze.read"})
                denied = await client.post(
                    "/data/",
                    headers=headers,
                    json={
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {
                            "name": "get_role_notice",
                            "arguments": {"notice_id": "00000000-0000-0000-0000-000000000000"},
                        },
                    },
                )
                assert (
                    denied.json()["result"]["structuredContent"]["error"]["code"]
                    == "PERMISSION_DENIED"
                )
                assert (
                    await client.post(
                        "/data/", json={"jsonrpc": "2.0", "id": 3, "method": "tools/list"}
                    )
                ).status_code == 401

    asyncio.run(exercise())


def test_stdio_lifecycle_uses_sdk_streams_without_real_io(monkeypatch):
    from contextlib import asynccontextmanager
    from types import SimpleNamespace

    @asynccontextmanager
    async def streams():
        yield "read", "write"

    server = SimpleNamespace(run=AsyncMock(), create_initialization_options=lambda: "options")
    monkeypatch.setattr("app.modules.wiki.mcps.data.server.stdio_server", streams)
    asyncio.run(serve_stdio(server))
    server.run.assert_awaited_once_with("read", "write", "options")
    called = []
    monkeypatch.setattr(
        "app.modules.wiki.mcps.data.server.anyio.run",
        lambda function, instance: called.append((function, instance)),
    )
    run_stdio(server)
    assert called == [(serve_stdio, server)]


def test_catalog_describes_every_input_and_coverage_boundary(service):
    from app.modules.wiki.mcps.data.inputs import INPUTS

    assert set(TOOL_DESCRIPTIONS) == set(INPUTS) == set(QUERIES)
    for name, model in INPUTS.items():
        description = TOOL_DESCRIPTIONS[name]
        assert "synthetic" in description
        for field in model.model_fields:
            assert field in description, (name, field)
        if "limit" in model.model_fields:
            field = model.model_json_schema()["properties"]["limit"]
            assert f"default {field['default']}" in description or (
                f"defaults to {field['default']}" in description
            )
            assert f"maximum {field['maximum']}" in description
    options = create_server(
        service, lambda: CallContext("synthetic", ALL_SCOPES)
    ).create_initialization_options()
    assert options.instructions == SERVER_INSTRUCTIONS
    for contract in (
        "not live GAIA",
        "No real documents",
        "no dedicated tools",
        "not returned",
        "next_cursor",
        "identical filters and principal",
        "NOT_FOUND",
        "permission denial",
        "Currency is not encoded",
        "do not divide them by 100 again",
        "entity and record_id",
        "dataset_version",
        "untrusted data",
    ):
        assert contract in options.instructions


def test_http_initialize_delivers_server_instructions(service):
    application = create_http_app(None, service, SECRET)

    async def exercise():
        async with application.app.router.lifespan_context(application.app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=application), base_url="http://localhost"
            ) as client:
                context = CallContext("synthetic-initialize", ALL_SCOPES)
                response = await client.post(
                    "/data/",
                    headers={
                        "Authorization": "Bearer " + issue_token(SECRET, context),
                        "Accept": "application/json, text/event-stream",
                    },
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2025-11-25",
                            "capabilities": {},
                            "clientInfo": {"name": "synthetic-test", "version": "1"},
                        },
                    },
                )
                assert response.status_code == 200
                assert response.json()["result"]["instructions"] == SERVER_INSTRUCTIONS

    asyncio.run(exercise())


def test_model_receives_full_tool_descriptions_with_authorized_schema(service):
    from types import SimpleNamespace

    context = CallContext("synthetic-model-catalog", frozenset({"utenze.read"}))
    server = create_server(service, lambda: context)
    create = AsyncMock(
        return_value=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="Synthetic data only.", tool_calls=[])
                )
            ]
        )
    )

    async def list_tools(current_context):
        assert current_context == context
        catalog = await server._request_handlers["tools/list"].handler(None, None)
        return [
            {
                "name": f"data__{tool.name}",
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in catalog.tools
        ]

    agent = WikiMCPAgent(
        SimpleNamespace(list_tools=list_tools),
        SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))),
        "gpt-reserve",
    )
    asyncio.run(agent.answer("Describe synthetic subjects.", context))
    tools = create.call_args.kwargs["tools"]
    assert {tool["function"]["name"] for tool in tools} == {
        "data__search_subjects",
        "data__get_subject",
    }
    for tool in tools:
        function = tool["function"]
        name = function["name"].removeprefix("data__")
        assert function["description"] == TOOL_DESCRIPTIONS[name] + " Requires utenze.read."
        assert function["parameters"]["additionalProperties"] is False
    assert "Docs" not in str(tools)


def test_experiment_manifest_binds_model_visible_catalog(service):
    from pathlib import Path

    from app.modules.wiki.mcps.docs.corpus import digest
    from app.modules.wiki.mcps.experiment_cases import synthetic_cases
    from app.modules.wiki.mcps.experiment_runner import ExperimentConfig, experiment_manifest

    manifest = experiment_manifest(
        synthetic_cases(service), "synthetic-version", ExperimentConfig()
    )
    catalog = Path(__file__).parents[1] / "app/modules/wiki/mcps/data/catalog.py"
    assert manifest["code_hashes"]["data/catalog.py"] == digest(catalog.read_bytes())
