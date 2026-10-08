import json
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from app.modules.network.models import NetworkDevice
from app.modules.network.router.helpers import traffic


def test_device_traffic_summary_with_no_events(monkeypatch):
    database = MagicMock()
    database.scalars.return_value.all.return_value = []
    monkeypatch.setattr(traffic, "_get_active_tracked_subject_map", lambda _database: {})

    summary = traffic._build_device_traffic_summary(
        database, NetworkDevice(ip_address="10.0.0.1"), window_hours=12
    )

    assert summary.window_hours == 12
    assert summary.model_dump() == traffic.NetworkDeviceTrafficSummary(window_hours=12).model_dump()
    assert database.scalars.call_count == 1


@pytest.mark.parametrize("lifecycle", ["active", "retired", "missing"])
@pytest.mark.parametrize(
    ("sent", "received", "expected_out", "expected_in"),
    [
        (" 17 ", " 29 ", 17, 29),
        (-5, "-7", 0, 0),
        (None, [], 0, 0),
        ("1.5", "bad", 0, 0),
        (True, False, 0, 0),
        (0, 42, 0, 42),
        ("+13", "003", 13, 3),
        (17.0, {}, 0, 0),
    ],
)
def test_statistics_normalizes_bytes_in_all_source_states(
    monkeypatch, lifecycle, sent, received, expected_out, expected_in
):
    source = NetworkDevice(
        id=1,
        ip_address="10.0.0.1",
        lifecycle_state=lifecycle,
        status="online",
        display_name="Source",
    )
    database = MagicMock()
    database.scalars.return_value.all.return_value = [] if lifecycle == "missing" else [source]
    database.execute.return_value.mappings.return_value = [
        {
            "event_type": "allow.rule",
            "severity": "info",
            "protocol": "tcp",
            "src_ip": "10.0.0.1",
            "dst_ip": "8.8.8.8",
            "device_id": 1,
            "observed_at": datetime.now(UTC),
            "raw_payload": json.dumps(
                {
                    "parsed": {
                        "bytes_sent": sent,
                        "bytes_received": received,
                        "domain": "test.example",
                    }
                }
            ),
        }
    ]
    monkeypatch.setattr(traffic, "_get_active_tracked_subject_map", lambda _database: {})
    monkeypatch.setattr(traffic, "list_network_firewalls", lambda _database: [])
    monkeypatch.setattr(traffic, "list_network_alerts", lambda *_args, **_kwargs: [])

    result = traffic._build_network_statistics_summary(database)

    assert (result.bytes_out, result.bytes_in) == (expected_out, expected_in)
    assert result.total_events == result.allowed_events == 1
    assert result.blocked_events == 0
    assert result.devices_with_traffic == (1 if lifecycle == "active" else 0)
    assert len(result.top_source_devices) == (1 if lifecycle == "active" else 0)
    for item in [*result.top_domains, *result.top_destinations, *result.top_source_devices]:
        assert (item.bytes_out, item.bytes_in) == (expected_out, expected_in)
        assert item.bytes_total == expected_out + expected_in
    assert len(result.hourly_timeline) == 1
    assert result.hourly_timeline[0].bytes_in == expected_in
    assert result.hourly_timeline[0].bytes_out == expected_out


@pytest.mark.parametrize(
    ("device_ips", "expected_in", "expected_out"),
    [
        (["source-key", "destination", "destination"], 17, 29),
        (["source-key", "other", "another"], 0, 0),
    ],
)
def test_statistics_preserves_byte_direction_when_device_ip_changes(
    monkeypatch, device_ips, expected_in, expected_out
):
    observations = []

    class ChangingIpDevice:
        id = 1
        lifecycle_state = "active"
        status = "online"
        is_known_device = True
        is_monitored = False
        assigned_user_id = None
        assigned_user = None
        device_type = None
        vendor = None
        location_hint = None

        @property
        def ip_address(self):
            observations.append("ip")
            return device_ips.pop(0) if device_ips else "stable"

    class OrderedBytes(dict):
        def get(self, key, default=None):
            observations.append(key)
            return super().get(key, default)

    database = MagicMock()
    database.scalars.return_value.all.return_value = [ChangingIpDevice()]
    database.execute.return_value.mappings.return_value = [
        {
            "event_type": "other",
            "severity": "info",
            "protocol": "tcp",
            "src_ip": "source-key",
            "dst_ip": "destination",
            "device_id": 1,
            "observed_at": datetime.now(UTC),
            "raw_payload": "fixture",
        }
    ]
    monkeypatch.setattr(traffic, "_get_active_tracked_subject_map", lambda _database: {})
    monkeypatch.setattr(traffic, "list_network_firewalls", lambda _database: [])
    monkeypatch.setattr(traffic, "list_network_alerts", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(traffic, "_resolve_device_label", lambda _device: ("Changing", "device"))
    monkeypatch.setattr(
        traffic,
        "metadata_sources_to_dict",
        lambda _raw: {"parsed": OrderedBytes(bytes_sent=17, bytes_received=29)},
    )

    result = traffic._build_network_statistics_summary(database)

    assert (result.bytes_in, result.bytes_out) == (expected_in, expected_out)
    assert observations[:5] == ["ip", "bytes_sent", "bytes_received", "ip", "ip"]
    assert result.devices_with_traffic == 1
