import json
import re
import runpy
import sqlite3
from pathlib import Path
from uuid import UUID

import anyio
import httpx
import pytest
from mcp import ClientSession, types
from mcp.shared.memory import create_client_server_memory_streams

from app.modules.wiki.mcps.audit import AuditStore
from app.modules.wiki.mcps.live import cli
from app.modules.wiki.mcps.live import service as service_module
from app.modules.wiki.mcps.live.api import GaiaAPI, SourceError
from app.modules.wiki.mcps.live.catalog import BLOCKED_INTEGRATIONS, TOOLS
from app.modules.wiki.mcps.live.server import create_server
from app.modules.wiki.mcps.live.service import LiveService, project

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def backend():
    return {
        "user": {
            "id": 7,
            "is_active": True,
            "enabled_modules": [
                "utenze",
                "catasto",
                "ruolo",
                "dotazioni",
                "presenze",
                "operazioni",
                "organigramma",
                "rete",
            ],
        },
        "permissions": {
            "granted_keys": sorted(
                {section for spec in TOOLS.values() for section in spec.sections}
            )
        },
        "data": {
            "items": [{"id": "public-id", "name": "Public asset", "password": "not-for-model"}],
            "total": 1,
        },
        "status": 200,
        "requests": [],
    }


@pytest.fixture
def live(tmp_path, backend):
    def handle(request):
        assert request.method == "GET"
        assert request.headers["authorization"] == "Bearer session-test"
        backend["requests"].append(request)
        if request.url.path == "/api/auth/me":
            return httpx.Response(200, json=backend["user"])
        if request.url.path == "/api/auth/my-permissions":
            return httpx.Response(200, json=backend["permissions"])
        return httpx.Response(
            backend["status"],
            content=json.dumps(backend["data"]),
            headers={"content-type": "application/json"},
        )

    api = GaiaAPI("https://gaia.lan", "session-test", transport=httpx.MockTransport(handle))
    audit = AuditStore(tmp_path / "gaia-mcp-audit.sqlite")
    yield LiveService(api, audit, TOOLS)
    audit.close()


@pytest.mark.parametrize("name", TOOLS)
async def test_catalog_routes_are_read_only_authorized_and_projected(live, backend, name):
    spec = TOOLS[name]
    arguments = {}
    if "record_id" in spec.inputs.model_fields:
        arguments["record_id"] = str(UUID(int=1))
    if "q" in spec.inputs.model_fields:
        arguments["q"] = "private query"
    result = await live.call(name, arguments)
    assert "error" not in result
    assert result["data"] == {"items": [{"id": "public-id", "name": "Public asset"}], "total": 1}
    assert result["source"] == "gaia_live_api"
    assert result["truncated"] is False
    assert result["path"] == "/api" + spec.path.format(record_id=str(UUID(int=1)))
    assert backend["requests"][-1].url.path == result["path"]
    rows = live.audit.connection.execute("SELECT payload FROM calls").fetchall()
    assert len(rows) == 1
    assert all(
        secret not in rows[0][0]
        for secret in ["session-test", "private query", "Public asset", "not-for-model"]
    )
    assert (
        Path(live.audit.connection.execute("PRAGMA database_list").fetchone()[2]).stat().st_mode
        & 0o777
    ) == 0o600
    await live.api.close()


@pytest.mark.parametrize(
    "name,arguments",
    [
        ("search_gaia", {"q": "a"}),
        ("search_gaia", {"q": "a" * 121}),
        ("search_gaia", {"q": "test", "limit": 31}),
        ("search_assets", {"page": 0}),
        ("search_assets", {"page": 1001}),
        ("get_my_presenze", {"page_size": 0}),
        ("get_portal_health", {"hours": 0}),
        ("get_portal_health", {"hours": 73}),
        ("search_parcels", {"foglio": "a" * 21}),
        ("get_asset_history", {"record_id": str(UUID(int=1)), "page_size": 51}),
        ("get_my_summary", None),
    ],
)
async def test_invalid_boundary_inputs_never_reach_the_data_source(live, backend, name, arguments):
    assert await live.call(name, arguments) == {"error": {"code": "INVALID_ARGUMENT"}}
    assert all(request.url.path.startswith("/api/auth/") for request in backend["requests"])
    await live.api.close()


@pytest.mark.parametrize("failure", [httpx.ReadTimeout, httpx.ConnectTimeout])
async def test_timeouts_are_sanitized_and_transport_has_no_implicit_proxy(failure):
    def unavailable(request):
        assert request.extensions["timeout"] == {"connect": 10, "read": 10, "write": 10, "pool": 10}
        raise failure("private origin or token", request=request)

    api = GaiaAPI("https://gaia.lan", "token", transport=httpx.MockTransport(unavailable))
    try:
        with pytest.raises(SourceError, match=r"^SOURCE_UNAVAILABLE$"):
            await api.get("/api/search")
        assert api.client.trust_env is False
    finally:
        await api.close()


@pytest.mark.parametrize("overflow", [False, True])
async def test_streaming_limit_counts_accumulated_chunks_and_closes_response(overflow):
    closed = []

    class ChunkedBody(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b'{"name":"'
            yield b"a" * 65525
            yield b'"}' + (b" " * 2 if overflow else b"")

        async def aclose(self):
            closed.append(True)

    api = GaiaAPI(
        "https://gaia.lan",
        "token",
        transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=ChunkedBody())),
    )
    try:
        if overflow:
            with pytest.raises(SourceError, match="SOURCE_RESPONSE_TOO_LARGE"):
                await api.get("/api/search")
        else:
            assert await api.get("/api/search") == {"name": "a" * 65525}
        assert closed == [True]
    finally:
        await api.close()


async def test_deeply_nested_source_json_fails_with_a_sanitized_error():
    api = GaiaAPI(
        "https://gaia.lan",
        "token",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=b"[" * 30000 + b"0" + b"]" * 30000)
        ),
    )
    try:
        with pytest.raises(SourceError, match=r"^SOURCE_UNAVAILABLE$"):
            await api.get("/api/search")
    finally:
        await api.close()


async def test_stdio_failure_closes_http_and_audit_resources(tmp_path, monkeypatch):
    instances = []

    class TrackedAPI:
        def __init__(self, *args, **kwargs):
            self.closed = False
            instances.append(self)

        async def close(self):
            self.closed = True

    captured = []

    def capture_server(service):
        captured.append(service.audit)
        return create_server(service)

    async def broken_stdio(server):
        raise RuntimeError("client disconnected")

    monkeypatch.setattr(cli, "GaiaAPI", TrackedAPI)
    monkeypatch.setattr(cli, "create_server", capture_server)
    monkeypatch.setattr(cli, "serve_stdio", broken_stdio)
    with pytest.raises(RuntimeError, match="client disconnected"):
        await cli.serve(
            {
                "GAIA_MCP_LIVE_ENABLED": "true",
                "GAIA_MCP_LIVE_ORIGIN": "https://gaia.lan",
                "GAIA_MCP_LIVE_TOKEN": "token",
                "GAIA_MCP_LIVE_TOOLS": "get_my_summary",
                "GAIA_MCP_LIVE_AUDIT": str(tmp_path / "gaia-mcp-audit.sqlite"),
            }
        )
    assert instances[0].closed
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        captured[0].connection.execute("SELECT 1")


@pytest.mark.parametrize("name", TOOLS)
async def test_each_tool_requires_explicit_allowlist_and_current_module_permissions(
    live, backend, name
):
    live.approved_tools = frozenset()
    assert await live.call(name, {}) == {"error": {"code": "PERMISSION_DENIED"}}
    live.approved_tools = frozenset(TOOLS)
    module = TOOLS[name].module
    if module:
        backend["user"]["enabled_modules"].remove(module)
    elif name == "search_gaia":
        backend["user"]["enabled_modules"].remove("utenze")
    else:
        backend["user"]["is_active"] = False
    result = await live.call(name, {})
    assert result["error"]["code"] in {"PERMISSION_DENIED", "AUTH_REQUIRED"}
    assert all(request.url.path.startswith("/api/auth/") for request in backend["requests"])
    await live.api.close()


async def test_audit_metadata_persists_without_source_records_or_query(live, tmp_path):
    result = await live.call("search_gaia", {"q": "private test query"})
    assert "error" not in result
    persisted = AuditStore(tmp_path / "gaia-mcp-audit.sqlite")
    try:
        payload = json.loads(
            persisted.connection.execute("SELECT payload FROM calls").fetchone()[0]
        )
        assert payload["event"]["tool_name"] == "search_gaia"
        assert payload["event"]["status"] == "ok"
        assert payload["filters"] == {}
        assert payload["response"] == {"status": "ok"}
        assert "private test query" not in str(payload)
        assert "Public asset" not in str(payload)
    finally:
        persisted.close()
        await live.api.close()


def test_every_source_contract_matches_a_registered_backend_get_route():
    from app.api.router import api_router

    routes = {route.path for route in api_router.routes if "GET" in getattr(route, "methods", ())}
    for spec in TOOLS.values():
        normalized = re.sub(r"\{[^}]+\}", "{}", spec.path)
        matching = [path for path in routes if re.sub(r"\{[^}]+\}", "{}", path) == normalized]
        assert matching, spec.path
    assert set(BLOCKED_INTEGRATIONS) == {"nas_documents", "trasparenza", "processing_batches"}


async def test_discovery_and_invocation_recheck_revoked_module_and_sections(live, backend):
    assert set(await live.tools()) == TOOLS.keys()
    backend["permissions"]["granted_keys"].remove("dotazioni.view")
    assert "search_assets" not in await live.tools()
    result = await live.call("search_assets", {})
    assert result == {"error": {"code": "PERMISSION_DENIED"}}
    assert all(request.url.path.startswith("/api/auth/") for request in backend["requests"])
    backend["user"]["enabled_modules"].remove("rete")
    assert "list_network_devices" not in await live.tools()
    live.approved_tools = frozenset({"get_my_summary"})
    assert await live.tools() == ["get_my_summary"]
    await live.api.close()


@pytest.mark.parametrize(
    "user,permissions",
    [
        ([], {}),
        ({"id": 7, "is_active": False}, {}),
        ({"id": True, "is_active": True}, {}),
        ({"id": 0, "is_active": True}, {}),
        ({"id": 7, "is_active": True, "enabled_modules": None}, {}),
        ({"id": 7, "is_active": True, "enabled_modules": []}, []),
        ({"id": 7, "is_active": True, "enabled_modules": []}, {"granted_keys": None}),
        ({"id": 7, "is_active": True, "enabled_modules": [7]}, {"granted_keys": []}),
        ({"id": 7, "is_active": True, "enabled_modules": []}, {"granted_keys": [{}]}),
    ],
)
async def test_invalid_or_inactive_identity_is_fail_closed(live, backend, user, permissions):
    backend["user"], backend["permissions"] = user, permissions
    assert await live.call("get_my_summary", {}) == {"error": {"code": "AUTH_REQUIRED"}}
    await live.api.close()


async def test_unknown_tool_invalid_arguments_and_unconfigured_sources_are_not_called(
    live, backend
):
    assert await live.call("secret-as-tool-name", {}) == {"error": {"code": "UNKNOWN_TOOL"}}
    assert await live.call("get_asset", {"record_id": "../../secret"}) == {
        "error": {"code": "INVALID_ARGUMENT"}
    }
    assert await live.call("get_my_summary", {"user_id": 99}) == {
        "error": {"code": "INVALID_ARGUMENT"}
    }
    assert await live.call("search_assets", {"page_size": 1000}) == {
        "error": {"code": "INVALID_ARGUMENT"}
    }
    assert not any(
        "secret-as-tool-name" in row[0]
        for row in live.audit.connection.execute("SELECT payload FROM calls")
    )
    assert all(request.url.path.startswith("/api/auth/") for request in backend["requests"])
    await live.api.close()


def test_allowlist_is_required(live):
    for names in [[], ["arbitrary_sql"]]:
        with pytest.raises(ValueError, match="allowlist"):
            LiveService(live.api, live.audit, names)


async def test_budget_enforces_tool_and_discovery_limits_and_recovers(live, monkeypatch):
    monkeypatch.setattr(service_module, "monotonic", lambda: 0)
    for _count in range(20):
        assert "error" not in await live.call("get_my_summary", {})
    assert await live.call("get_my_summary", {}) == {"error": {"code": "RATE_LIMITED"}}
    for _count in range(40):
        await live.tools()
    with pytest.raises(SourceError, match="RATE_LIMITED"):
        await live.tools()
    monkeypatch.setattr(service_module, "monotonic", lambda: 60)
    assert "error" not in await live.call("get_my_summary", {})
    await live.api.close()


async def test_audit_failure_does_not_return_real_records(live, monkeypatch):
    def failure(*args):
        raise OSError("disk unavailable")

    monkeypatch.setattr(live.audit, "record", failure)
    assert await live.call("get_my_summary", {}) == {"error": {"code": "AUDIT_UNAVAILABLE"}}
    await live.api.close()


def test_projection_drops_unapproved_fields_and_marks_every_truncation():
    assert project({"password": "secret", "name": None}, {"name"}) == ({"name": None}, False)
    assert project("a" * 501, set()) == ("a" * 500, True)
    assert project(list(range(51)), set()) == (list(range(50)), True)
    assert project(["a" * 501], set()) == (["a" * 500], True)
    nested = {"items": {"items": {"items": {"items": {"items": {"items": {"items": 5}}}}}}}
    assert project(nested, {"items"})[1] is True


@pytest.mark.parametrize(
    "origin,token",
    [
        ("http://gaia.lan", "token"),
        ("https://", "token"),
        ("https://gaia.lan/path", "token"),
        ("https://user:password@gaia.lan", "token"),
        ("https://gaia.lan?query", "token"),
        ("https://gaia.lan#fragment", "token"),
        ("https://gaia.lan", ""),
        ("https://gaia.lan", "token\nheader"),
    ],
)
def test_transport_rejects_insecure_origins_or_credentials(origin, token):
    with pytest.raises(ValueError):
        GaiaAPI(origin, token)


@pytest.mark.parametrize(
    "status,code",
    [
        (401, "AUTH_REQUIRED"),
        (403, "PERMISSION_DENIED"),
        (404, "NOT_FOUND"),
        (429, "RATE_LIMITED"),
        (302, "SOURCE_UNAVAILABLE"),
        (500, "SOURCE_UNAVAILABLE"),
    ],
)
async def test_transport_sanitizes_errors_and_never_follows_redirects(status, code):
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(
            status, headers={"location": "https://untrusted.example"}, text="private server error"
        )

    api = GaiaAPI("https://gaia.lan/", "token", transport=httpx.MockTransport(handle))
    with pytest.raises(SourceError, match=code):
        await api.get("/api/search")
    assert len(requests) == 1
    await api.close()


@pytest.mark.parametrize(
    "content,code",
    [
        (b"not json", "SOURCE_UNAVAILABLE"),
        (b"true", "INVALID_SOURCE_RESPONSE"),
        (b"a" * 65537, "SOURCE_RESPONSE_TOO_LARGE"),
    ],
)
async def test_transport_bounds_and_validates_source_response(content, code):
    api = GaiaAPI(
        "https://gaia.lan",
        "token",
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=content)),
    )
    with pytest.raises(SourceError, match=code):
        await api.get("/api/search")
    await api.close()


async def test_transport_network_failure_and_invalid_path():
    def failure(request):
        raise httpx.ConnectError("private endpoint", request=request)

    api = GaiaAPI("https://gaia.lan", "token", transport=httpx.MockTransport(failure))
    for path in ["https://untrusted.example", "/api/../secret", "/api/search?token=value"]:
        with pytest.raises(SourceError, match="INVALID_SOURCE_PATH"):
            await api.get(path)
    with pytest.raises(SourceError, match="SOURCE_UNAVAILABLE"):
        await api.get("/api/search")
    await api.close()


async def test_mcp_protocol_handlers_preserve_schema_and_permission_errors(live, backend):
    server = create_server(live)
    tools = await server._request_handlers["tools/list"].handler(None, None)
    assert len(tools.tools) == len(TOOLS)
    assert all(tool.annotations.read_only_hint for tool in tools.tools)
    response = await server._request_handlers["tools/call"].handler(
        None,
        types.CallToolRequestParams(name="get_my_summary", arguments={}),
    )
    assert not response.is_error
    backend["user"]["is_active"] = False
    denied = await server._request_handlers["tools/call"].handler(
        None, types.CallToolRequestParams(name="get_my_summary")
    )
    assert denied.is_error
    await live.api.close()


async def test_cli_is_disabled_by_default_and_closes_resources(tmp_path, monkeypatch):
    with pytest.raises(ValueError, match="opt-in"):
        await cli.serve({})
    closed = []

    class FakeAPI:
        def __init__(self, *args, **kwargs):
            pass

        async def close(self):
            closed.append(True)

    async def run_stdio(server):
        assert server.name == "GAIA Live MCP"

    monkeypatch.setattr(cli, "GaiaAPI", FakeAPI)
    monkeypatch.setattr(cli, "serve_stdio", run_stdio)
    environ = {
        "GAIA_MCP_LIVE_ENABLED": "true",
        "GAIA_MCP_LIVE_AUDIT": str(tmp_path / "gaia-mcp-audit.sqlite"),
        "GAIA_MCP_LIVE_ORIGIN": "https://gaia.lan",
        "GAIA_MCP_LIVE_TOKEN": "token",
        "GAIA_MCP_LIVE_TOOLS": "get_my_summary",
    }
    await cli.serve(environ)
    environ["GAIA_MCP_LIVE_TOOLS"] = "unknown"
    with pytest.raises(ValueError):
        await cli.serve(environ)
    assert len(closed) == 2


def test_module_entrypoint_uses_the_explicit_environment(monkeypatch):
    invoked = []
    monkeypatch.setattr("anyio.run", lambda handler, environ: invoked.append(handler))
    runpy.run_module("app.modules.wiki.mcps.live", run_name="__main__")
    assert invoked == [cli.serve]


@pytest.mark.parametrize(
    "name,payload,expected",
    [
        (
            "search_gaia",
            {"items": [{"module": "utenze", "title": "Test", "metadata": {"tax_code": "private"}}]},
            {"items": [{"module": "utenze", "title": "Test"}]},
        ),
        (
            "get_subject",
            {
                "person": {"nome": "Test", "cognome": "Person", "codice_fiscale": "private"},
                "nas_folder_path": "private",
            },
            {"person": {"nome": "Test", "cognome": "Person"}},
        ),
        (
            "get_role_notice",
            {"anno_tributario": 2026, "importo_totale_euro": 100, "codice_fiscale_raw": "private"},
            {"anno_tributario": 2026, "importo_totale_euro": 100},
        ),
        (
            "search_assets",
            {"items": [{"asset_code": "TEST", "serial_number": "private"}]},
            {"items": [{"asset_code": "TEST"}]},
        ),
        ("get_asset", {"name": "Test", "notes": "private"}, {"name": "Test"}),
        ("get_asset_custody", {"holder_user_id": 7, "notes": "private"}, {"holder_user_id": 7}),
        (
            "get_asset_history",
            {"items": [{"action": "created", "details": {"notes": "private"}}]},
            {"items": [{"action": "created"}]},
        ),
        (
            "get_my_summary",
            {"ordinary_minutes": 480, "presenze": {"ordinary_hours": 8, "absence_hours": 1}},
            {"ordinary_minutes": 480, "presenze": {"ordinary_hours": 8}},
        ),
        (
            "get_my_presenze",
            {
                "items": [
                    {
                        "ordinary_minutes": 480,
                        "request_description": "private",
                        "resolved_absence_cause": "private",
                    }
                ]
            },
            {"items": [{"ordinary_minutes": 480}]},
        ),
        (
            "get_my_reports",
            {"items": [{"report_number": "TEST-1", "description": "private", "title": "private"}]},
            {"items": [{"report_number": "TEST-1"}]},
        ),
        (
            "get_operations_summary",
            {"vehicles": {"total": 2, "available": 1}, "storage": {"percentage_used": 5}},
            {"vehicles": {"total": 2, "available": 1}, "storage": {"percentage_used": 5}},
        ),
        (
            "list_org_units",
            [{"nome": "Test", "tipo": "area", "wc_area_id": "private"}],
            [{"nome": "Test", "tipo": "area"}],
        ),
        (
            "list_network_devices",
            {
                "items": [
                    {"hostname": "test.lan", "ip_address": "192.0.2.1", "mac_address": "private"}
                ]
            },
            {"items": [{"hostname": "test.lan", "ip_address": "192.0.2.1"}]},
        ),
        (
            "list_network_scans",
            [{"hosts_scanned": 2, "discovered_devices": 1, "notes": "private"}],
            [{"hosts_scanned": 2, "discovered_devices": 1}],
        ),
        (
            "get_portal_health",
            {
                "totals": {"executions": 2, "errors": 1},
                "credentials": [{"label": "private"}],
                "recent_events": [{"message": "private"}],
            },
            {"totals": {"executions": 2, "errors": 1}},
        ),
        (
            "get_processing_request",
            {
                "status": "running",
                "attempts": 2,
                "error_message": "private",
                "captcha_image_path": "private",
            },
            {"status": "running", "attempts": 2},
        ),
        (
            "search_parcels",
            [{"comune_nome": "Test", "foglio": "1", "particella": "2", "source": "private"}],
            [{"comune_nome": "Test", "foglio": "1", "particella": "2"}],
        ),
    ],
)
async def test_source_specific_projection_retains_useful_data_without_sensitive_fields(
    live, backend, name, payload, expected
):
    backend["data"] = payload
    arguments = (
        {"record_id": str(UUID(int=1))} if "record_id" in TOOLS[name].inputs.model_fields else {}
    )
    if name == "search_gaia":
        arguments["q"] = "test"
    result = await live.call(name, arguments)
    assert result["data"] == expected
    await live.api.close()


async def test_sdk_session_initialization_discovery_call_and_revocation(live, backend):
    server = create_server(live)
    async with create_client_server_memory_streams() as (client_streams, server_streams):
        async with anyio.create_task_group() as tasks:
            tasks.start_soon(server.run, *server_streams, server.create_initialization_options())
            async with ClientSession(*client_streams) as session:
                initialized = await session.initialize()
                assert initialized.server_info.name == "GAIA Live MCP"
                discovered = await session.list_tools()
                assert {tool.name for tool in discovered.tools} == set(TOOLS)
                response = await session.call_tool("get_my_summary", {})
                assert response.structured_content["source"] == "gaia_live_api"
                backend["permissions"]["granted_keys"].remove("dotazioni.view")
                assert "search_assets" not in {
                    tool.name for tool in (await session.list_tools()).tools
                }
                denied = await session.call_tool("search_assets", {})
                assert denied.is_error
                assert denied.structured_content == {"error": {"code": "PERMISSION_DENIED"}}
            tasks.cancel_scope.cancel()
    await live.api.close()


@pytest.mark.parametrize(
    "name",
    [
        "search_assets",
        "get_asset_history",
        "get_my_presenze",
        "get_my_reports",
        "list_network_devices",
        "search_parcels",
    ],
)
async def test_paged_tools_forward_bounded_pagination_to_the_source(live, backend, name):
    arguments = {"page": 2, "page_size": 3}
    if name == "get_asset_history":
        arguments["record_id"] = str(UUID(int=1))
    assert "error" not in await live.call(name, arguments)
    assert dict(backend["requests"][-1].url.params) == {"page": "2", "page_size": "3"}
    await live.api.close()


async def test_unassigned_asset_custody_returns_null_instead_of_a_source_error(live, backend):
    backend["data"] = None
    result = await live.call("get_asset_custody", {"record_id": str(UUID(int=1))})
    assert result["data"] is None
    assert result["truncated"] is False
    await live.api.close()
