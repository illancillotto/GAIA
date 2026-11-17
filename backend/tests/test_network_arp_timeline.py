"""ARP temporal boundaries, anomaly priority and observation ordering."""

from datetime import UTC, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy.dialects import postgresql

from app.modules.network.router.helpers import tracking

ANCHOR = datetime(2026, 11, 17, 12, tzinfo=UTC)


def observation(index, *, minutes=0, **changes):
    fields = {
        "id": index,
        "scan_id": index,
        "device_id": 4,
        "ip_address": "10.0.0.4",
        "mac_address": "aa",
        "display_name": None,
        "hostname": "snapshot-host",
        "status": "online",
        "observed_at": ANCHOR + timedelta(minutes=minutes),
    }
    fields.update(changes)
    return SimpleNamespace(**fields)


def run_timeline(monkeypatch, rows, *, devices=(), limit=10, window_hours=24):
    queries = []
    trace = []

    class Clock:
        @staticmethod
        def now(zone):
            assert zone is UTC
            trace.append("clock")
            return ANCHOR

    def scalars(query):
        queries.append(query)
        result = rows if len(queries) == 1 else devices

        def all_rows():
            trace.append(("all", len(queries)))
            return result

        return SimpleNamespace(all=all_rows)

    monkeypatch.setattr(tracking, "datetime", Clock)
    result = tracking._build_arp_timeline(
        SimpleNamespace(scalars=scalars), window_hours=window_hours, limit=limit
    )
    return result, queries, trace


@pytest.mark.parametrize(
    "gap,expected",
    [
        (timedelta(0), 1),
        (timedelta(hours=2), 1),
        (timedelta(hours=2, microseconds=1), 0),
        (timedelta(days=1), 0),
    ],
)
def test_rapid_reappearance_window_is_inclusive(monkeypatch, gap, expected):
    rows = [observation(1), observation(2, observed_at=ANCHOR + gap)]
    result, _, _ = run_timeline(monkeypatch, rows)
    assert result[0].rapid_reappearances == expected
    assert result[0].suspicious_reasons == []


@pytest.mark.parametrize("middle_status", ["offline", "unknown", "ONLINE"])
def test_nononline_observations_do_not_reset_previous_online_timestamp(monkeypatch, middle_status):
    rows = [
        observation(1),
        observation(2, minutes=90, status=middle_status),
        observation(3, minutes=150),
    ]
    result, _, _ = run_timeline(monkeypatch, rows)
    assert result[0].rapid_reappearances == 0
    assert (result[0].online_appearances, result[0].offline_appearances) == (2, 1)


@pytest.mark.parametrize("naive", [False, True])
def test_three_online_appearances_trigger_anomaly_and_keep_original_timestamps(monkeypatch, naive):
    stamps = [ANCHOR + timedelta(minutes=index * 60) for index in range(3)]
    if naive:
        stamps = [stamp.replace(tzinfo=None) for stamp in stamps]
    rows = [observation(index + 1, observed_at=stamp) for index, stamp in enumerate(stamps)]
    result, _, _ = run_timeline(monkeypatch, rows)
    item = result[0]
    assert item.rapid_reappearances == 2
    assert item.suspicious_reasons == ["rapid_reappearances"]
    assert item.first_observed_at == stamps[0]
    assert item.last_observed_at == stamps[-1]
    assert [entry.observed_at for entry in item.observations] == list(reversed(stamps))


def test_aware_timestamps_use_absolute_elapsed_time(monkeypatch):
    east = timezone(timedelta(hours=2))
    rows = [
        observation(1, observed_at=ANCHOR.astimezone(east)),
        observation(2, observed_at=ANCHOR + timedelta(hours=2)),
    ]
    result, _, _ = run_timeline(monkeypatch, rows)
    assert result[0].rapid_reappearances == 1
    assert result[0].first_observed_at == ANCHOR.astimezone(east)


def test_anomalies_and_distinct_addresses_keep_original_priority(monkeypatch):
    rows = [
        observation(1, minutes=0, ip_address="10.0.0.1", mac_address="aa"),
        observation(2, minutes=60, ip_address="10.0.0.2", mac_address="bb"),
        observation(3, minutes=120, ip_address="10.0.0.1", mac_address="aa"),
    ]
    result, queries, trace = run_timeline(monkeypatch, rows, window_hours=7)
    item = result[0]
    assert item.suspicious_reasons == [
        "same_ip_multiple_macs",
        "same_mac_multiple_ips",
        "rapid_reappearances",
    ]
    assert item.distinct_ip_addresses == ["10.0.0.1", "10.0.0.2"]
    assert item.distinct_mac_addresses == ["aa", "bb"]
    assert (item.primary_ip_address, item.primary_mac_address) == ("10.0.0.1", "aa")
    assert item.scope_key == "device:4"
    assert trace == ["clock", ("all", 1), ("all", 2)]
    compiled = queries[0].compile(dialect=postgresql.dialect())
    assert compiled.params == {"scan_type_1": "arp", "completed_at_1": ANCHOR - timedelta(hours=7)}
    assert "ORDER BY network_scan_devices.observed_at DESC, network_scan_devices.id DESC" in str(
        compiled
    )
    assert queries[1].compile(dialect=postgresql.dialect()).params == {"id_1": [4]}


def test_latest_missing_mac_suppresses_multiple_ip_reason(monkeypatch):
    rows = [
        observation(1, ip_address="10.0.0.1", mac_address="aa"),
        observation(2, minutes=1, ip_address="10.0.0.2", mac_address=None),
    ]
    result, _, _ = run_timeline(monkeypatch, rows)
    assert result[0].suspicious_reasons == []
    assert result[0].distinct_mac_addresses == ["aa"]


def test_timestamp_ties_use_id_descending_and_only_six_observation_details(monkeypatch):
    rows = [observation(index, mac_address="bb" if index % 2 else "aa") for index in range(1, 9)]
    result, _, _ = run_timeline(monkeypatch, list(reversed(rows)))
    item = result[0]
    assert item.observations_count == 8
    assert [entry.scan_id for entry in item.observations] == [8, 7, 6, 5, 4, 3]
    assert item.primary_mac_address == "aa"
    assert item.rapid_reappearances == 7


@pytest.mark.parametrize("limit,expected", [(0, []), (1, ["device:2"]), (-1, ["device:2"])])
def test_ranking_precedes_literal_python_limit_slice(monkeypatch, limit, expected):
    rows = [
        observation(1, device_id=1, status="offline"),
        observation(2, device_id=2, mac_address="aa"),
        observation(3, device_id=2, minutes=1, mac_address="bb"),
    ]
    result, _, _ = run_timeline(monkeypatch, rows, limit=limit)
    assert [item.scope_key for item in result] == expected


def test_id_zero_keeps_device_scope_and_current_device_label(monkeypatch):
    labels = []

    def resolve(device):
        labels.append(device)
        return "Current", "device"

    monkeypatch.setattr(tracking, "_resolve_device_label", resolve)
    device = SimpleNamespace(id=0)
    result, _, _ = run_timeline(monkeypatch, [observation(1, device_id=0)], devices=[device])
    assert result[0].scope_key == "device:0"
    assert result[0].scope_type == "device"
    assert result[0].resolved_label == "Current"
    assert labels == [device]


def test_empty_rows_skip_device_query(monkeypatch):
    result, queries, trace = run_timeline(monkeypatch, [])
    assert result == []
    assert len(queries) == 1
    assert trace == ["clock", ("all", 1)]


def test_offline_timestamp_errors_are_not_skipped(monkeypatch):
    rows = [observation(1, status="offline", observed_at="invalid")]
    with pytest.raises(AttributeError, match="tzinfo"):
        run_timeline(monkeypatch, rows)
