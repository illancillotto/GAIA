"""Custom OID contracts and isolated full-file SNMP boundary coverage."""

import asyncio
import json
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.dialects import postgresql

from app.core import database
from app.modules.network import sophos_snmp as snmp


@pytest.mark.parametrize("raw", ["", "bad", "null", "{}", "1", '"text"', "[]"])
def test_custom_oids_reject_invalid_json_and_nonlists(monkeypatch, raw):
    monkeypatch.setattr(snmp.settings, "network_sophos_snmp_custom_oids", raw)
    assert snmp._load_custom_oids() == []


@pytest.mark.parametrize(
    "item",
    [
        None,
        [],
        3,
        {},
        {"key": None, "oid": "1"},
        {"key": " ", "oid": "1"},
        {"key": "key", "oid": None},
        {"key": "key", "oid": " "},
    ],
)
def test_custom_oids_skip_invalid_entries(monkeypatch, item):
    monkeypatch.setattr(snmp.settings, "network_sophos_snmp_custom_oids", json.dumps([item]))
    assert snmp._load_custom_oids() == []


def test_custom_oid_order_duplicates_whitespace_and_optional_defaults(monkeypatch):
    rows = [
        {"key": " cpu ", "oid": " 1.2.3 ", "mode": "int", "unit": "%"},
        {"key": "cpu", "oid": "1.2.4", "mode": 3, "unit": {}},
        {"key": "uptime", "oid": "1.2.5", "mode": "", "unit": ""},
    ]
    monkeypatch.setattr(snmp.settings, "network_sophos_snmp_custom_oids", json.dumps(rows))
    assert snmp._load_custom_oids() == [
        {"key": "cpu", "oid": "1.2.3", "mode": "int", "unit": "%"},
        {"key": "cpu", "oid": "1.2.4", "mode": "text", "unit": None},
        {"key": "uptime", "oid": "1.2.5", "mode": "", "unit": ""},
    ]


def test_optional_fields_keep_repeated_gets_and_second_result(monkeypatch):
    trace = []

    class Entry(dict):
        def get(self, key, default=None):
            trace.append(("get", key))
            if key in ("mode", "unit"):
                return "first" if trace.count(("get", key)) == 1 else None
            return super().get(key, default)

    monkeypatch.setattr(snmp.json, "loads", lambda _raw: [Entry(key="cpu", oid="1")])
    assert snmp._load_custom_oids() == [{"key": "cpu", "oid": "1", "mode": None, "unit": None}]
    assert trace == [
        ("get", "key"),
        ("get", "oid"),
        ("get", "mode"),
        ("get", "mode"),
        ("get", "unit"),
        ("get", "unit"),
    ]


@pytest.mark.parametrize("field", ["key", "oid"])
@pytest.mark.parametrize("second", ["", None, 0])
def test_second_strip_result_is_preserved_even_when_falsy(monkeypatch, field, second):
    reads = []

    class Text(str):
        def strip(self):
            reads.append("strip")
            return "first" if len(reads) == 1 else second

    row = {"key": "key", "oid": "oid", field: Text("value")}
    monkeypatch.setattr(snmp.json, "loads", lambda _raw: [row])
    result = snmp._load_custom_oids()
    assert result[0][field] is second
    assert reads == ["strip", "strip"]


def test_entry_read_error_is_not_swallowed_as_a_json_error(monkeypatch):
    class Entry(dict):
        def get(self, key, default=None):
            raise ValueError("entry unavailable")

    monkeypatch.setattr(snmp.json, "loads", lambda _raw: [Entry()])
    with pytest.raises(ValueError, match="entry unavailable"):
        snmp._load_custom_oids()


@pytest.mark.parametrize(
    "key, value, expected",
    [
        ("cpu", None, "info"),
        ("cpu", 69, "info"),
        ("cpu", 70, "warning"),
        ("CPU", 80, "danger"),
        ("cpu", 90, "critical"),
        ("memory", 95, "critical"),
        ("disk", 75, "warning"),
        ("other", 100, "info"),
    ],
)
def test_metric_severity_boundaries(key, value, expected):
    assert snmp._normalize_severity(key, value) == expected


@pytest.mark.parametrize(
    "raw, mode, expected",
    [
        ("12", "text", (None, "12")),
        (" 12.5 ", "int", (12.5, None)),
        ("-2", "custom", (-2.0, None)),
        ("bad", "int", (None, "bad")),
        (None, "int", (None, None)),
    ],
)
def test_metric_coercion_preserves_text_and_invalid_numeric_values(raw, mode, expected):
    assert snmp._coerce_metric_value(raw, mode) == expected


@pytest.mark.parametrize("missing", ["get_cmd", "UdpTransportTarget"])
def test_async_snmp_skips_missing_dependencies(monkeypatch, missing):
    monkeypatch.setattr(snmp, missing, None)
    assert asyncio.run(snmp._snmp_get_values_async("host", 161, "public", [])) == {}


@pytest.mark.parametrize("indication, status", [("offline", 0), (None, 1), (None, 0)])
def test_async_snmp_transport_parameters_errors_and_oid_mapping(monkeypatch, indication, status):
    create = AsyncMock(return_value="transport")
    command = AsyncMock(
        return_value=(
            indication,
            status,
            0,
            [
                ("1", "old"),
                ("other", "ignored"),
                ("1", "new"),
            ],
        )
    )
    monkeypatch.setattr(snmp, "UdpTransportTarget", SimpleNamespace(create=create))
    monkeypatch.setattr(snmp, "get_cmd", command)
    monkeypatch.setattr(snmp, "SnmpEngine", lambda: "engine")
    monkeypatch.setattr(snmp, "CommunityData", lambda value, **kwargs: (value, kwargs))
    monkeypatch.setattr(snmp, "ContextData", lambda: "context")
    monkeypatch.setattr(snmp, "ObjectIdentity", lambda value: ("oid", value))
    monkeypatch.setattr(snmp, "ObjectType", lambda value: ("object", value))
    result = asyncio.run(
        snmp._snmp_get_values_async(
            "host", 162, "community", [{"oid": "1", "key": "first"}, {"oid": "1", "key": "last"}]
        )
    )
    assert result == ({} if indication or status else {"last": "new"})
    create.assert_awaited_once_with(("host", 162), timeout=3.0, retries=0)
    command.assert_awaited_once_with(
        "engine",
        ("community", {"mpModel": 1}),
        "transport",
        "context",
        ("object", ("oid", "1")),
        ("object", ("oid", "1")),
    )


@pytest.mark.parametrize("mode", ["missing", "error", "ok"])
def test_sync_snmp_dependency_error_and_success(monkeypatch, mode):
    monkeypatch.setattr(snmp, "get_cmd", None if mode == "missing" else object())

    async def read(*args):
        if mode == "error":
            raise RuntimeError("transport unavailable")
        return {"key": "value"}

    monkeypatch.setattr(snmp, "_snmp_get_values_async", read)
    assert snmp._snmp_get_values("host", 161, "public", []) == (
        {"key": "value"} if mode == "ok" else {}
    )


@pytest.mark.parametrize("observed", [None, "naive", "aware"])
def test_record_metric_keeps_utc_timestamp_and_add_flush_order(monkeypatch, observed):
    now = datetime.now(UTC)
    value = None if observed is None else now.replace(tzinfo=None) if observed == "naive" else now
    monkeypatch.setattr(snmp, "datetime", SimpleNamespace(now=lambda zone: now))
    calls = []
    db = SimpleNamespace(
        add=lambda metric: calls.append(("add", metric)), flush=lambda: calls.append(("flush",))
    )
    metric = snmp.record_firewall_metric(
        db,
        firewall_id=4,
        metric_key="cpu",
        metric_value=92,
        severity="critical",
        observed_at=value,
        raw_payload={"source": "test"},
    )
    assert calls == [("add", metric), ("flush",)]
    assert metric.observed_at == now
    assert metric.raw_payload == '{"source": "test"}'
    assert metric.firewall_id == 4 and metric.metric_value == 92


@pytest.mark.parametrize("missing", ["host", "community", "values"])
def test_poll_returns_without_writes_when_configuration_or_values_are_missing(monkeypatch, missing):
    monkeypatch.setattr(
        snmp.settings, "network_sophos_snmp_host", None if missing == "host" else "host"
    )
    monkeypatch.setattr(snmp.settings, "network_sophos_firewall_management_ip", None)
    monkeypatch.setattr(
        snmp.settings, "network_sophos_snmp_community", "" if missing == "community" else "public"
    )
    monkeypatch.setattr(snmp.settings, "network_sophos_snmp_custom_oids", "[]")
    monkeypatch.setattr(snmp, "_snmp_get_values", lambda *args: {})
    assert snmp.poll_sophos_firewall_metrics(SimpleNamespace()) == []


@pytest.mark.parametrize("sys_name", [None, "Sophos"])
def test_poll_keeps_custom_order_duplicate_keys_and_commit_after_metrics(monkeypatch, sys_name):
    now = datetime.now(UTC)
    monkeypatch.setattr(snmp, "datetime", SimpleNamespace(now=lambda zone: now))
    monkeypatch.setattr(snmp.settings, "network_sophos_snmp_host", None)
    monkeypatch.setattr(snmp.settings, "network_sophos_firewall_management_ip", "fallback-host")
    monkeypatch.setattr(snmp.settings, "network_sophos_snmp_community", "public")
    monkeypatch.setattr(
        snmp.settings,
        "network_sophos_snmp_custom_oids",
        json.dumps(
            [
                {"key": "cpu", "oid": "1.2.3", "mode": "int", "unit": "%"},
                {"key": "cpu", "oid": "1.2.4", "mode": "int"},
            ]
        ),
    )
    values = {"cpu": "92"}
    if sys_name:
        values["sys_name"] = sys_name
    command = Mock(return_value=values)
    monkeypatch.setattr(snmp, "_snmp_get_values", command)
    firewall = SimpleNamespace(id=4)
    upsert = Mock(return_value=firewall)
    monkeypatch.setattr(snmp, "upsert_network_firewall", upsert)
    calls = []
    db = SimpleNamespace(
        add=lambda item: calls.append(("add", item)),
        flush=lambda: calls.append(("flush",)),
        commit=lambda: calls.append(("commit",)),
    )
    metrics = snmp.poll_sophos_firewall_metrics(db)
    assert [metric.metric_key for metric in metrics] == (["sys_name"] if sys_name else []) + [
        "cpu",
        "cpu",
    ]
    assert [metric.metric_value for metric in metrics if metric.metric_key == "cpu"] == [92, 92]
    assert all(metric.severity == "critical" for metric in metrics if metric.metric_key == "cpu")
    assert calls[-2:] == [("add", firewall), ("commit",)]
    assert firewall.status == "online" and firewall.last_seen_at == now
    assert command.call_args.args[:3] == (
        "fallback-host",
        snmp.settings.network_sophos_snmp_port,
        "public",
    )
    assert upsert.call_args.kwargs["name"] == (
        sys_name or snmp.settings.network_sophos_firewall_default_name
    )


@pytest.mark.parametrize("key", [None, "", "cpu"])
def test_list_metrics_keeps_optional_filter_and_descending_order(key):
    db = Mock()
    db.scalars.return_value.all.return_value = ["metric"]
    assert snmp.list_network_firewall_metrics(db, firewall_id=4, metric_key=key, limit=2) == [
        "metric"
    ]
    compiled = db.scalars.call_args.args[0].compile(dialect=postgresql.dialect())
    assert compiled.params["firewall_id_1"] == 4
    assert ("metric_key_1" in compiled.params) is bool(key)
    assert "observed_at DESC" in str(compiled) and "id DESC" in str(compiled)


@pytest.mark.parametrize("enabled, interval", [(False, 1), (True, 60)])
def test_poller_closes_session_before_sleep_and_respects_minimum_interval(
    monkeypatch, enabled, interval
):
    class EndPoll(Exception):
        pass

    calls = []
    db = SimpleNamespace(close=lambda: calls.append("close"))
    monkeypatch.setattr(database, "SessionLocal", lambda: db)
    monkeypatch.setattr(snmp.settings, "network_sophos_snmp_interval_seconds", interval)
    monkeypatch.setattr(
        snmp, "get_sophos_runtime_policy", lambda session: SimpleNamespace(snmp_should_poll=enabled)
    )
    monkeypatch.setattr(snmp, "poll_sophos_firewall_metrics", lambda session: calls.append("poll"))

    def sleep(seconds):
        calls.append(("sleep", seconds))
        raise EndPoll

    monkeypatch.setattr(snmp.time, "sleep", sleep)
    with pytest.raises(EndPoll):
        snmp.run_sophos_snmp_poller()
    assert calls == (["poll"] if enabled else []) + ["close", ("sleep", max(interval, 30))]
