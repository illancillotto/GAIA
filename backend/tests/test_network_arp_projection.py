"""ARP item projection preserves label and late observation reads."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.modules.network.router.helpers import tracking


def row(index=1, **changes):
    values = {
        "id": index,
        "scan_id": index,
        "device_id": 4,
        "ip_address": "10.0.0.4",
        "mac_address": "aa",
        "display_name": "Snapshot",
        "hostname": "snapshot-host",
        "status": "online",
        "observed_at": datetime(2026, 11, 17, tzinfo=UTC),
    }
    values.update(changes)
    return SimpleNamespace(**values)


def project(rows, devices=(), *, limit=10):
    calls = []

    def scalars(query):
        calls.append(query)
        return SimpleNamespace(all=lambda: rows if len(calls) == 1 else devices)

    result = tracking._build_arp_timeline(
        SimpleNamespace(scalars=scalars), window_hours=24, limit=limit
    )
    assert len(calls) == 2
    return result


@pytest.mark.parametrize(
    "display_name,hostname,expected",
    [("Display", "Host", "Display"), ("", "Host", "Host"), (None, "", "10.0.0.4")],
)
def test_latest_snapshot_label_fallback_is_shared_by_all_details(display_name, hostname, expected):
    result = project([row(1), row(2, display_name=display_name, hostname=hostname)])
    assert result[0].resolved_label == expected
    assert [item.resolved_label for item in result[0].observations] == [expected, expected]


def test_current_reference_label_is_resolved_before_presence_reads(monkeypatch):
    trace = []

    class Observation:
        def __init__(self):
            self.values = vars(row())

        def __getattr__(self, key):
            trace.append(key)
            return self.values[key]

    device = SimpleNamespace(id=4)

    def resolve(value):
        assert value is device
        trace.append("resolve")
        return "Current", "device"

    monkeypatch.setattr(tracking, "_resolve_device_label", resolve)
    result = project([Observation()], [device])
    assert result[0].resolved_label == "Current"
    resolve_index = trace.index("resolve")
    assert trace[:resolve_index].count("status") == 1
    assert trace[resolve_index:].count("status") == 3
    assert trace[resolve_index : resolve_index + 3] == ["resolve", "ip_address", "ip_address"]


def test_online_offline_and_detail_status_are_independent_late_reads():
    class Observation:
        def __init__(self):
            self.values = vars(row())
            self.status_reads = 0

        def __getattr__(self, key):
            if key == "status":
                self.status_reads += 1
                return ["offline", "online", "offline", "online"][self.status_reads - 1]
            return self.values[key]

    item = Observation()
    result = project([item])[0]
    assert (result.rapid_reappearances, result.online_appearances, result.offline_appearances) == (
        0,
        1,
        1,
    )
    assert result.observations[0].status == "online"
    assert item.status_reads == 4


def test_equal_ranked_groups_keep_first_encounter_order():
    rows = [row(1, device_id=9), row(2, device_id=3), row(3, device_id=7)]
    result = project(rows)
    assert [item.scope_key for item in result] == ["device:9", "device:3", "device:7"]


def test_none_device_uses_ip_scope_and_does_not_resolve_current_label(monkeypatch):
    def unexpected(_):
        raise AssertionError("IP-only scope has no device label")

    monkeypatch.setattr(tracking, "_resolve_device_label", unexpected)
    result = project([row(device_id=None, display_name=None, hostname=None)])
    assert (result[0].scope_key, result[0].scope_type, result[0].device_id) == (
        "ip:10.0.0.4",
        "ip",
        None,
    )
    assert result[0].resolved_label == "10.0.0.4"


def test_snapshot_sort_does_not_mutate_input_sequence():
    rows = [row(1), row(3), row(2)]
    original = list(rows)
    result = project(rows)
    assert rows == original
    assert [item.scan_id for item in result[0].observations] == [3, 2, 1]
