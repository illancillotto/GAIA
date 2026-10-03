import base64
import json
import logging
import runpy
import sqlite3
import sys
from contextlib import asynccontextmanager, closing
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import anyio
import pytest
from mcp import ClientSession, types
from mcp.client.stdio import StdioServerParameters, stdio_client

from app.modules.wiki.mcps.context import CallContext
from app.modules.wiki.mcps.data import cli, database, server
from app.modules.wiki.mcps.data.database import (
    dataset_manifest,
    open_readonly,
    read_manifest,
    seed_database,
    validate_database_path,
)
from app.modules.wiki.mcps.data.generator import TABLES, generate_dataset, record_id
from app.modules.wiki.mcps.data.inputs import INPUTS
from app.modules.wiki.mcps.data.queries import QUERIES
from app.modules.wiki.mcps.data.service import (
    DataService,
    SourceError,
    decode_cursor,
    encode_cursor,
)

SEED = "pytest-gaia-synthetic"


@pytest.fixture(scope="module")
def dataset():
    return generate_dataset(SEED)


@pytest.fixture(scope="module")
def database_path(tmp_path_factory):
    path = tmp_path_factory.mktemp("mcp-data") / "gaia-mcp-synthetic-test.sqlite"
    seed_database(path, SEED)
    return path


@pytest.fixture
def service(database_path):
    service = DataService(database_path)
    yield service
    service.close()


def context(scopes=None, **kwargs):
    return CallContext(
        principal="pytest-user",
        scopes=frozenset(
            scopes if scopes is not None else {"utenze.read", "catasto.read", "ruolo.read"}
        ),
        **kwargs,
    )


def call(service, tool, arguments):
    return service.call(tool, arguments, context())


def test_seed_determinism_counts_relations_and_money(dataset, tmp_path):
    assert dataset == generate_dataset(SEED)
    assert dataset != generate_dataset("another-seed")
    expected_counts = dict(
        zip(TABLES, (300, 12, 1000, 450, 600, 1500, 500, 800, 1500, 500), strict=True)
    )
    assert {table: len(rows) for table, rows in dataset.items()} == expected_counts
    assert dataset["subjects"][0]["display_name"] == dataset["subjects"][1]["display_name"]
    assert dataset["subjects"][0]["id"] != dataset["subjects"][1]["id"]
    notices = {row["id"]: row for row in dataset["role_notices"]}
    for notice_id, notice in notices.items():
        assert (
            sum(
                row["maintenance_amount_cents"]
                for row in dataset["role_lines"]
                if row["notice_id"] == notice_id
            )
            == notice["total_amount_cents"]
        )
    path = tmp_path / "gaia-mcp-synthetic-seed.sqlite"
    first = seed_database(path, SEED)
    first_bytes = path.read_bytes()
    assert seed_database(path, SEED) == first
    assert path.read_bytes() == first_bytes
    assert seed_database(path, "other-seed")["dataset_version"] != first["dataset_version"]
    with closing(open_readonly(path)) as connection:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert read_manifest(connection)["seed"] == "other-seed"
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1


@pytest.mark.parametrize("seed", ["", "x" * 121, 42, None])
def test_invalid_seed(seed):
    with pytest.raises(ValueError):
        generate_dataset(seed)


@pytest.mark.parametrize(
    "path", ["gaia.db", "postgresql://real-db/gaia", "gaia-mcp-synthetic-secret.db", "real.sqlite"]
)
def test_cannot_open_or_reset_operational_database(tmp_path, path):
    candidate = tmp_path / path
    with pytest.raises(ValueError):
        validate_database_path(candidate)
    with pytest.raises(ValueError):
        seed_database(candidate, SEED)
    with pytest.raises(ValueError):
        open_readonly(candidate)


def test_symlink_database_rejected(tmp_path):
    path = tmp_path / "gaia-mcp-synthetic-link.sqlite"
    path.symlink_to(tmp_path / "secret")
    with pytest.raises(ValueError):
        open_readonly(path)


def test_readonly_database_and_guarded_reset(database_path, tmp_path):
    with closing(open_readonly(database_path)) as connection:
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            connection.execute("DELETE FROM subjects")
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            connection.execute("DROP TABLE subjects")
    path = tmp_path / "gaia-mcp-synthetic-existing.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE real_data (secret TEXT)")
    initial = path.read_bytes()
    with pytest.raises(sqlite3.Error):
        seed_database(path, SEED)
    assert path.read_bytes() == initial


def test_seed_failure_cleans_temporary_file(tmp_path, monkeypatch):
    path = tmp_path / "gaia-mcp-synthetic-test.sqlite"

    def fail(*args):
        raise OSError("failed replace")

    monkeypatch.setattr(database.os, "replace", fail)
    with pytest.raises(OSError):
        seed_database(path, SEED)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "mutation", ["empty", "source", "schema", "content", "manifest", "relationships"]
)
def test_corrupt_database_fails_closed(tmp_path, mutation):
    path = tmp_path / "gaia-mcp-synthetic-corrupt.sqlite"
    seed_database(path, SEED)
    with sqlite3.connect(path) as connection:
        if mutation == "empty":
            connection.execute("DELETE FROM dataset_manifest")
        elif mutation == "source":
            connection.execute("PRAGMA ignore_check_constraints=ON")
            connection.execute("UPDATE dataset_manifest SET source='real_db'")
        elif mutation == "schema":
            connection.execute("PRAGMA ignore_check_constraints=ON")
            connection.execute("UPDATE dataset_manifest SET schema_version=999")
        elif mutation == "content":
            connection.execute("UPDATE subjects SET display_name='modified'")
        elif mutation == "manifest":
            connection.execute("UPDATE dataset_manifest SET dataset_version='modified'")
        else:
            connection.execute("UPDATE parcels SET district_id='missing'")
            data = {
                table: [
                    dict(zip([column[0] for column in cursor.description], row, strict=True))
                    for row in cursor.fetchall()
                ]
                for table in TABLES
                for cursor in [connection.execute(f"SELECT * FROM {table} ORDER BY id")]
            }
            manifest = dataset_manifest(SEED, data)
            connection.execute(
                "UPDATE dataset_manifest SET dataset_version=?, manifest_json=?",
                (manifest["dataset_version"], json.dumps(manifest)),
            )
    with pytest.raises(ValueError):
        DataService(path)


VALID_ARGUMENTS = {
    "search_subjects": {"query": "sintetico"},
    "get_subject": {"subject_id": record_id(SEED, "subjects", 0)},
    "search_irrigation_accounts": {},
    "get_irrigation_account": {"account_id": record_id(SEED, "irrigation_accounts", 0)},
    "search_parcels": {},
    "get_parcel": {"parcel_id": record_id(SEED, "parcels", 0)},
    "get_accounts_by_parcel": {"parcel_id": record_id(SEED, "parcels", 0), "year": 2024},
    "get_parcels_by_account": {
        "account_id": record_id(SEED, "irrigation_accounts", 0),
        "year": 2024,
    },
    "search_role_notices": {},
    "get_role_notice": {"notice_id": record_id(SEED, "role_notices", 0)},
    "get_payments_by_notice": {"notice_id": record_id(SEED, "role_notices", 1)},
    "get_role_lines_by_notice": {"notice_id": record_id(SEED, "role_notices", 0)},
}


@pytest.mark.parametrize("tool", list(INPUTS))
def test_every_tool_valid_input_provenance_telemetry_and_permissions(service, tool, caplog):
    caplog.set_level(logging.INFO)
    request = context(conversation_id="conversation", experiment_run_id="experiment")
    response = service.call(tool, VALID_ARGUMENTS[tool], request)
    assert "error" not in response
    assert response["result_count"] > 0
    assert response["estimated_tokens"] > 0
    assert response["request_id"] == request.request_id
    assert response["dataset_version"] == service.manifest["dataset_version"]
    for evidence, provenance in zip(response["results"], response["provenance"], strict=True):
        assert evidence["id"] == provenance["record_id"]
        assert provenance["entity"] == QUERIES[tool].entity
    event = caplog.records[-1].mcp_event
    assert event["conversation_id"] == "conversation" and event["experiment_run_id"] == "experiment"
    assert event["principal"] != "pytest-user"
    assert event["permission_scope"] == QUERIES[tool].scope
    assert event["result_count"] == response["result_count"]
    assert "arguments" not in event and "results" not in event
    denied = service.call(tool, VALID_ARGUMENTS[tool], context([]))
    assert denied["error"]["code"] == "PERMISSION_DENIED"
    assert denied["results"] == []
    wrong = service.call(tool, VALID_ARGUMENTS[tool], context(["unrelated.read"]))
    assert wrong["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.parametrize("tool", list(INPUTS))
def test_all_tools_reject_extra_fields_and_wrong_types(service, tool):
    assert (
        call(service, tool, dict(VALID_ARGUMENTS[tool], scopes=["admin"]))["error"]["code"]
        == "INVALID_ARGUMENT"
    )
    first_parameter = next(iter(INPUTS[tool].model_fields))
    assert (
        call(service, tool, dict(VALID_ARGUMENTS[tool], **{first_parameter: []}))["error"]["code"]
        == "INVALID_ARGUMENT"
    )
    for parameter, field in INPUTS[tool].model_fields.items():
        if field.is_required():
            arguments = dict(VALID_ARGUMENTS[tool])
            arguments.pop(parameter)
            assert call(service, tool, arguments)["error"]["code"] == "INVALID_ARGUMENT"


@pytest.mark.parametrize(
    "tool", [name for name, query in QUERIES.items() if query.singleton or query.parent]
)
def test_unknown_record_is_not_found(service, tool):
    arguments = dict(VALID_ARGUMENTS[tool])
    parameter = next(key for key in arguments if key.endswith("_id"))
    arguments[parameter] = "00000000-0000-0000-0000-000000000000"
    assert call(service, tool, arguments)["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize(
    "tool", [name for name, model in INPUTS.items() if "limit" in model.model_fields]
)
def test_caps_and_pagination_for_every_collection(service, tool):
    limit = INPUTS[tool].model_fields["limit"].metadata[1].le
    assert (
        call(service, tool, dict(VALID_ARGUMENTS[tool], limit=limit + 1))["error"]["code"]
        == "RESULT_LIMIT_EXCEEDED"
    )
    assert (
        call(service, tool, dict(VALID_ARGUMENTS[tool], limit=0))["error"]["code"]
        == "INVALID_ARGUMENT"
    )
    expected = call(service, tool, dict(VALID_ARGUMENTS[tool], limit=limit))["results"]
    rows = []
    arguments = dict(VALID_ARGUMENTS[tool], limit=1)
    for _page in range(len(expected) + 1):
        response = call(service, tool, arguments)
        assert "error" not in response
        rows.extend(response["results"])
        if len(rows) >= len(expected) or response["next_cursor"] is None:
            break
        assert response["truncated"]
        arguments["cursor"] = response["next_cursor"]
    assert rows[: len(expected)] == expected
    assert len({row["id"] for row in rows}) == len(rows)


def test_single_hop_and_multi_hop_ground_truth(service, dataset):
    subject = dataset["subjects"][0]
    accounts = call(
        service, "search_irrigation_accounts", {"subject_id": subject["id"], "limit": 25}
    )["results"]
    expected = {
        link["account_id"]
        for link in dataset["subject_accounts"]
        if link["subject_id"] == subject["id"]
    }
    assert {account["id"] for account in accounts} == expected
    for account in accounts:
        parcels = call(
            service,
            "get_parcels_by_account",
            {"account_id": account["id"], "year": account["campaign_year"]},
        )["results"]
        for parcel in parcels:
            linked = call(
                service,
                "get_accounts_by_parcel",
                {"parcel_id": parcel["id"], "year": account["campaign_year"]},
            )["results"]
            assert account["id"] in {row["id"] for row in linked}
    notices = call(service, "search_role_notices", {"subject_id": subject["id"]})["results"]
    assert notices
    for notice in notices:
        assert notice["subject_id"] == subject["id"]
        lines = call(service, "get_role_lines_by_notice", {"notice_id": notice["id"]})["results"]
        assert lines
        parcel = call(service, "get_parcel", {"parcel_id": lines[0]["parcel_id"]})["results"][0]
        assert parcel["id"] == lines[0]["parcel_id"]
    for index, status in [(0, "unpaid"), (1, "partial"), (2, "paid")]:
        notice_id = dataset["role_notices"][index]["id"]
        notice = call(service, "get_role_notice", {"notice_id": notice_id})["results"][0]
        payments = call(service, "get_payments_by_notice", {"notice_id": notice_id})["results"]
        assert notice["status"] == status
        assert all(isinstance(payment["amount"], str) for payment in payments)
        if status == "unpaid":
            assert payments == []
    no_matches = call(
        service, "get_accounts_by_parcel", {"parcel_id": dataset["parcels"][0]["id"], "year": 2200}
    )
    assert no_matches["result_count"] == 0
    ambiguous = call(service, "search_subjects", {"query": "omonimo"})
    assert ambiguous["result_count"] == 2
    assert (
        call(service, "search_subjects", {"query": "omonimo", "subject_type": "company"})[
            "result_count"
        ]
        == 1
    )


def test_notice_code_lookup_payment_chain_and_filter_identity(service, dataset):
    payment = max(dataset["payments"], key=lambda row: row["notice_id"])
    notice = next(row for row in dataset["role_notices"] if row["id"] == payment["notice_id"])
    assert notice["id"] not in {
        row["id"] for row in call(service, "search_role_notices", {"limit": 25})["results"]
    }
    response = call(service, "search_role_notices", {"notice_code": notice["notice_code"]})
    assert [row["id"] for row in response["results"]] == [notice["id"]]
    assert response["provenance"][0]["record_id"] == notice["id"]
    payments = call(service, "get_payments_by_notice", {"notice_id": response["results"][0]["id"]})
    assert payment["id"] in {row["id"] for row in payments["results"]}
    assert all(row["notice_id"] == notice["id"] for row in payments["results"])
    combined = call(
        service,
        "search_role_notices",
        {"notice_code": notice["notice_code"], "account_code": notice["account_code"]},
    )
    assert combined["results"] == response["results"]
    for arguments in (
        {"notice_code": "SYN-N-NOT-EXISTENT"},
        {"account_code": notice["notice_code"]},
        {"notice_code": notice["account_code"]},
        {"notice_code": notice["notice_code"], "account_code": "SYN-A-NOT-EXISTENT"},
        {"notice_code": "' OR 1=1 --"},
    ):
        empty = call(service, "search_role_notices", arguments)
        assert empty["results"] == [] and "error" not in empty
    for invalid in ("", 42, "x" * 201, [notice["notice_code"]]):
        assert (
            call(service, "search_role_notices", {"notice_code": invalid})["error"]["code"]
            == "INVALID_ARGUMENT"
        )
    denied = service.call(
        "search_role_notices", {"notice_code": notice["notice_code"]}, context({"utenze.read"})
    )
    assert denied["error"]["code"] == "PERMISSION_DENIED" and denied["results"] == []
    schema = INPUTS["search_role_notices"].model_json_schema()["properties"]
    assert "not an account code" in schema["notice_code"]["description"]
    assert "not a notice code" in schema["account_code"]["description"]
    assert "notice_code" in server.TOOL_DESCRIPTIONS["search_role_notices"]
    assert "returned id" in server.TOOL_DESCRIPTIONS["get_payments_by_notice"]
    paid_notice_ids = {row["notice_id"] for row in dataset["payments"]}
    unpaid_notice = next(row for row in dataset["role_notices"] if row["id"] not in paid_notice_ids)
    existing = call(service, "search_role_notices", {"notice_code": unpaid_notice["notice_code"]})
    assert existing["result_count"] == 1
    empty_payments = call(
        service, "get_payments_by_notice", {"notice_id": existing["results"][0]["id"]}
    )
    assert empty_payments["result_count"] == 0 and "error" not in empty_payments


def test_every_filter_and_injection_is_parameterized(service, dataset):
    filters = {
        "search_irrigation_accounts": {
            "account_code": "SYN-A0000",
            "campaign_year": 2024,
            "district_code": "SYN-D01",
            "status": "closed",
        },
        "search_parcels": {
            "municipality_code": "SYN-M01",
            "sheet": "1",
            "parcel_number": "SYN-P0000",
            "district_code": "SYN-D01",
            "crop": "mais",
        },
        "search_role_notices": {
            "subject_id": dataset["subjects"][0]["id"],
            "tax_year": 2024,
            "status": "unpaid",
            "account_code": "SYN-A0000",
        },
    }
    for tool, arguments in filters.items():
        response = call(service, tool, arguments)
        assert response["result_count"] >= 1
    assert call(service, "search_subjects", {"query": "' OR 1=1 --"})["results"] == []
    assert (
        call(service, "search_irrigation_accounts", {"account_code": "' OR 1=1 --"})["results"]
        == []
    )
    assert (
        call(service, "execute_sql", {"sql": "SELECT * FROM subjects"})["error"]["code"]
        == "INVALID_ARGUMENT"
    )


@pytest.mark.parametrize(
    "payload",
    [
        "not base64",
        [],
        {},
        {"fingerprint": "other", "last_id": "x"},
        {"fingerprint": "test", "last_id": "invalid"},
        {"fingerprint": "test", "last_id": None},
    ],
)
def test_invalid_cursor_payloads(payload):
    cursor = (
        payload
        if isinstance(payload, str)
        else base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    )
    with pytest.raises(SourceError, match="INVALID_ARGUMENT"):
        decode_cursor(cursor, "test")


def test_cursor_bound_to_tool_filters_dataset_and_principal(service):
    response = call(service, "search_subjects", {"query": "sintetico", "limit": 1})
    cursor = response["next_cursor"]
    assert (
        call(service, "search_subjects", {"query": "other", "cursor": cursor})["error"]["code"]
        == "INVALID_ARGUMENT"
    )
    assert (
        call(service, "search_irrigation_accounts", {"cursor": cursor})["error"]["code"]
        == "INVALID_ARGUMENT"
    )
    result = service.call(
        "search_subjects",
        {"query": "sintetico", "cursor": cursor},
        CallContext(principal="other", scopes=context().scopes),
    )
    assert result["error"]["code"] == "INVALID_ARGUMENT"
    saved = service.manifest["dataset_version"]
    service.manifest["dataset_version"] = "changed"
    assert (
        call(service, "search_subjects", {"query": "sintetico", "cursor": cursor})["error"]["code"]
        == "INVALID_ARGUMENT"
    )
    service.manifest["dataset_version"] = saved
    assert (
        decode_cursor(encode_cursor("test", VALID_ARGUMENTS["get_subject"]["subject_id"]), "test")
        == VALID_ARGUMENTS["get_subject"]["subject_id"]
    )


def test_database_and_internal_errors_are_minimized(service, monkeypatch, caplog):
    caplog.set_level(logging.INFO)

    def fail(*args):
        raise RuntimeError("sensitive failure detail")

    monkeypatch.setattr(service, "_execute", fail)
    assert (
        call(service, "search_subjects", {"query": "secret"})["error"]["code"] == "INTERNAL_ERROR"
    )
    assert "secret" not in caplog.text and "sensitive failure detail" not in caplog.text
    monkeypatch.undo()
    service.connection.close()
    assert (
        call(service, "search_subjects", {"query": "x"})["error"]["code"] == "DATASET_UNAVAILABLE"
    )


def test_sdk_handlers_and_stdio_runner(service, monkeypatch):
    async def exercise():
        instance = server.create_server(service, context)
        discovered = await instance._request_handlers["tools/list"].handler(None, None)
        assert [tool.name for tool in discovered.tools] == sorted(INPUTS)
        assert all(tool.annotations.read_only_hint for tool in discovered.tools)
        handler = instance._request_handlers["tools/call"].handler
        response = await handler(
            None,
            types.CallToolRequestParams(name="search_subjects", arguments={"query": "omonimo"}),
        )
        assert response.structured_content["result_count"] == 2
        invalid = await handler(None, types.CallToolRequestParams(name="unknown"))
        assert invalid.is_error
        stub = SimpleNamespace(run=AsyncMock(), create_initialization_options=lambda: "options")

        @asynccontextmanager
        async def streams():
            yield "read", "write"

        monkeypatch.setattr(server, "stdio_server", streams)
        await server.serve_stdio(stub)
        stub.run.assert_awaited_once_with("read", "write", "options")

    anyio.run(exercise)
    captured = []
    monkeypatch.setattr(
        server.anyio, "run", lambda function, instance: captured.append((function, instance))
    )
    server.run_stdio("server")
    assert captured == [(server.serve_stdio, "server")]


def test_cli_seed_serve_cleanup_and_entrypoint(tmp_path, monkeypatch, capsys):
    path = tmp_path / "gaia-mcp-synthetic-cli.sqlite"
    cli.main(["seed", "--database", str(path), "--seed", SEED])
    assert json.loads(capsys.readouterr().out)["row_counts"]["subjects"] == 300
    assert json.loads(path.with_suffix(".manifest.json").read_text())["seed"] == SEED
    captured = {}

    def create(service, context_factory):
        captured["service"] = service
        captured["context"] = context_factory()
        return "server"

    def run(instance):
        assert instance == "server"
        raise RuntimeError("stopped")

    monkeypatch.setattr(cli, "create_server", create)
    monkeypatch.setattr(cli, "run_stdio", run)
    with pytest.raises(RuntimeError, match="stopped"):
        cli.main(["serve", "--database", str(path), "--scopes", "utenze.read,,"])
    assert captured["context"].scopes == frozenset({"utenze.read"})
    with pytest.raises(sqlite3.ProgrammingError):
        captured["service"].connection.execute("SELECT 1")
    called = []
    monkeypatch.setattr(cli, "main", lambda: called.append(True))
    runpy.run_module("app.modules.wiki.mcps.data", run_name="__main__")
    assert called == [True]


def test_real_stdio_handshake_discovery_multi_hop_and_denied_scope(database_path):
    async def exercise():
        params = StdioServerParameters(
            command=sys.executable,
            args=[
                "-m",
                "app.modules.wiki.mcps.data",
                "serve",
                "--database",
                str(database_path),
                "--scopes",
                "utenze.read",
            ],
            cwd=Path(__file__).resolve().parents[1],
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                initialized = await session.initialize()
                assert initialized.server_info.name == "GAIA Data MCP"
                tools = await session.list_tools()
                assert {tool.name for tool in tools.tools} == {
                    name for name, query in QUERIES.items() if query.scope == "utenze.read"
                }
                response = await session.call_tool("search_subjects", {"query": "omonimo"})
                assert response.structured_content["result_count"] == 2
                subject_id = response.structured_content["results"][0]["id"]
                detail = await session.call_tool("get_subject", {"subject_id": subject_id})
                assert detail.structured_content["results"][0]["id"] == subject_id
                denied = await session.call_tool("search_parcels", {})
                assert denied.is_error
                assert denied.structured_content["error"]["code"] == "PERMISSION_DENIED"

    anyio.run(exercise)
