"""SNMP polling preserves batch order, lazy reads and partial failure effects."""

import json
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.modules.network import sophos_snmp as snmp


@pytest.fixture
def poll_batch(monkeypatch):
    def prepare(oids, values, *, fail=None):
        trace = []
        added = []
        counts = {}
        now = datetime.now(UTC)

        def record(name, *args):
            trace.append((name, *args))
            counts[name] = counts.get(name, 0) + 1
            if fail == (name, counts[name]):
                raise RuntimeError(f"failed {name}")

        class Firewall:
            @property
            def id(self):
                record("firewall_id")
                return 10 + counts["firewall_id"]

            def __setattr__(self, name, value):
                record("write_firewall", name, value)
                super().__setattr__(name, value)

        firewall = Firewall()

        def add(item):
            if item is firewall:
                record("add_firewall")
            else:
                added.append(item)
                record("add_metric", item.metric_key)

        db = SimpleNamespace(
            add=add,
            flush=lambda: record("flush"),
            commit=lambda: record("commit"),
        )

        def read(*args):
            record("read", args)
            return values

        def upsert(_db, **kwargs):
            record("upsert", kwargs)
            return firewall

        monkeypatch.setattr(
            snmp,
            "settings",
            SimpleNamespace(
                network_sophos_snmp_host="snmp-host",
                network_sophos_firewall_management_ip="fallback-host",
                network_sophos_snmp_community="community",
                network_sophos_snmp_port=1161,
                network_sophos_firewall_default_name="Fallback firewall",
            ),
        )
        monkeypatch.setattr(snmp, "STANDARD_OIDS", oids)
        monkeypatch.setattr(snmp, "_load_custom_oids", lambda: [])
        monkeypatch.setattr(snmp, "_snmp_get_values", read)
        monkeypatch.setattr(snmp, "upsert_network_firewall", upsert)
        monkeypatch.setattr(snmp, "datetime", SimpleNamespace(now=lambda _zone: now))
        return SimpleNamespace(
            run=lambda: snmp.poll_sophos_firewall_metrics(db),
            trace=trace,
            added=added,
            firewall=firewall,
            now=now,
        )

    return prepare


def test_batch_uses_definition_order_and_keeps_duplicate_keys(poll_batch):
    oids = [
        {"key": "cpu", "oid": "1", "mode": "int", "unit": "%"},
        {"key": "absent", "oid": "unused"},
        {"key": "sys_name", "oid": "2"},
        {"key": "cpu", "oid": "3", "mode": "int"},
    ]
    case = poll_batch(oids, {"sys_name": "Firewall", "cpu": "92"})
    result = case.run()
    assert result == case.added
    assert [metric.metric_key for metric in result] == ["cpu", "sys_name", "cpu"]
    assert [metric.firewall_id for metric in result] == [11, 12, 13]
    assert [metric.metric_value for metric in result] == [92, None, 92]
    assert [metric.metric_text for metric in result] == [None, "Firewall", None]
    assert [metric.unit for metric in result] == ["%", None, None]
    assert [metric.severity for metric in result] == ["critical", "info", "critical"]
    assert [json.loads(metric.raw_payload)["oid"] for metric in result] == ["1", "2", "3"]
    assert all(metric.observed_at == case.now for metric in result)
    assert [entry[0] for entry in case.trace] == [
        "read",
        "upsert",
        "firewall_id",
        "add_metric",
        "flush",
        "firewall_id",
        "add_metric",
        "flush",
        "firewall_id",
        "add_metric",
        "flush",
        "write_firewall",
        "write_firewall",
        "add_firewall",
        "commit",
    ]
    assert case.firewall.last_seen_at == case.now
    assert case.firewall.status == "online"


def test_nonempty_unmatched_values_still_update_firewall_and_commit_without_id_reads(poll_batch):
    case = poll_batch([{"key": "missing", "oid": "1"}], {"unrelated": "value"})
    assert case.run() == []
    assert case.added == []
    assert [entry[0] for entry in case.trace] == [
        "read",
        "upsert",
        "write_firewall",
        "write_firewall",
        "add_firewall",
        "commit",
    ]
    assert case.firewall.status == "online"


def test_metric_conversion_and_raw_payload_keep_separate_mapping_reads(poll_batch):
    reads = []

    class Values(dict):
        def __getitem__(self, key):
            reads.append(key)
            return "92" if len(reads) == 1 else "second reading"

    case = poll_batch([{"key": "cpu", "oid": "1", "mode": "int"}], Values(cpu="present"))
    metric = case.run()[0]
    assert reads == ["cpu", "cpu"]
    assert metric.metric_value == 92
    assert json.loads(metric.raw_payload) == {
        "source": "snmp",
        "host": "snmp-host",
        "oid": "1",
        "raw_value": "second reading",
    }


def test_missing_values_skip_optional_definition_reads(poll_batch):
    class MissingDefinition(dict):
        def __getitem__(self, key):
            assert key == "key"
            return super().__getitem__(key)

        def get(self, key, default=None):
            raise AssertionError(f"unexpected definition read {key}")

    case = poll_batch([MissingDefinition(key="missing")], {"unrelated": "value"})
    assert case.run() == []


@pytest.mark.parametrize(
    "stage,occurrence,metrics",
    [
        ("read", 1, 0),
        ("upsert", 1, 0),
        ("firewall_id", 1, 0),
        ("add_metric", 1, 1),
        ("flush", 1, 1),
        ("firewall_id", 2, 1),
        ("add_metric", 2, 2),
        ("flush", 2, 2),
        ("write_firewall", 1, 2),
        ("write_firewall", 2, 2),
        ("add_firewall", 1, 2),
        ("commit", 1, 2),
    ],
)
def test_failure_preserves_partial_batch_and_stops_at_original_stage(
    poll_batch, stage, occurrence, metrics
):
    case = poll_batch(
        [{"key": "cpu", "oid": "1"}, {"key": "memory", "oid": "2"}],
        {"cpu": "92", "memory": "80"},
        fail=(stage, occurrence),
    )
    with pytest.raises(RuntimeError, match=f"failed {stage}"):
        case.run()
    assert len(case.added) == metrics
    assert case.trace[-1][0] == stage
    assert sum(entry[0] == stage for entry in case.trace) == occurrence
    assert not any(entry[0] in ("rollback", "retry") for entry in case.trace)
    if stage in ("read", "upsert", "firewall_id", "add_metric", "flush"):
        assert vars(case.firewall) == {}
    if stage != "commit":
        assert not any(entry[0] == "commit" for entry in case.trace)
