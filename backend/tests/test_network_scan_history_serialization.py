"""Scan history serialization preserves order, reads and caller-specific fallbacks."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.modules.network.router.helpers import devices, tracking


@pytest.fixture
def serialize_history(monkeypatch):
    device = SimpleNamespace(
        **dict.fromkeys(
            [
                "id",
                "last_scan_id",
                "assigned_user_id",
                "ip_address",
                "mac_address",
                "hostname",
                "hostname_source",
                "display_name",
                "lifecycle_state",
                "asset_label",
                "vendor",
                "model_name",
                "device_type",
                "operating_system",
                "dns_name",
                "location_hint",
                "notes",
                "is_known_device",
                "metadata_sources",
                "status",
                "is_monitored",
                "open_ports",
                "first_seen_at",
                "last_seen_at",
                "created_at",
                "updated_at",
                "assigned_user",
                "retired_at",
            ]
        )
    )
    subject = SimpleNamespace(
        id=9,
        entity_type="domain",
        normalized_value="example.test",
        value="example.test",
        label=None,
        notes=None,
        is_active=True,
        device_id=7,
        created_by_user_id=None,
        created_at=None,
        updated_at=None,
    )
    monkeypatch.setattr(devices, "_resolve_device_label", lambda _device: ("label", "device"))
    monkeypatch.setattr(devices, "metadata_sources_to_dict", lambda _value: {})
    monkeypatch.setattr(
        devices, "NetworkDeviceResponse", SimpleNamespace(model_validate=lambda payload: payload)
    )
    monkeypatch.setattr(tracking, "_resolve_device_label", lambda _device: ("label", "device"))
    monkeypatch.setattr(tracking, "_resolve_tracked_subject_label", lambda *_args: "label")
    monkeypatch.setattr(tracking, "NetworkTrackedSubjectResponse", lambda **payload: payload)

    def call(target, history):
        if target == "device":
            return devices._serialize_device(device, scan_history=history)["scan_history"]
        monkeypatch.setattr(tracking, "get_device_scan_history", lambda *_args, **_kwargs: history)
        return tracking._serialize_tracked_subject(
            SimpleNamespace(get=lambda *_args: device), subject, include_activity_summary=False
        )["scan_history"]

    return call


@pytest.mark.parametrize("target", ["device", "tracking"])
def test_history_keeps_order_duplicate_scans_and_field_references(serialize_history, target):
    observed = datetime(2026, 11, 17, 12, tzinfo=UTC)
    ports = [22, 443]
    rows = [
        SimpleNamespace(
            scan_id=scan_id,
            observed_at=observed,
            status=status,
            hostname=hostname,
            ip_address="192.0.2.7",
            mac_address=None,
            open_ports=ports,
        )
        for scan_id, status, hostname in [
            (7, "online", "a"),
            (3, "offline", None),
            (7, "online", "b"),
        ]
    ]
    result = serialize_history(target, rows)
    assert [row["scan_id"] for row in result] == [7, 3, 7]
    assert [row["hostname"] for row in result] == ["a", None, "b"]
    assert [row["status"] for row in result] == ["online", "offline", "online"]
    assert all(
        list(row)
        == [
            "scan_id",
            "observed_at",
            "status",
            "hostname",
            "ip_address",
            "mac_address",
            "open_ports",
        ]
        for row in result
    )
    assert all(row["observed_at"] is observed and row["open_ports"] is ports for row in result)
    assert all(row["ip_address"] == "192.0.2.7" and row["mac_address"] is None for row in result)
    assert result[0] is not result[2]


@pytest.mark.parametrize("target", ["device", "tracking"])
def test_history_is_consumed_once_with_fields_in_original_order(serialize_history, target):
    trace = []

    class Row:
        def __getattr__(self, key):
            trace.append(key)
            return key

    def rows():
        trace.append("start")
        yield Row()
        trace.append("finish")

    result = serialize_history(target, rows())
    assert trace == [
        "start",
        "scan_id",
        "observed_at",
        "status",
        "hostname",
        "ip_address",
        "mac_address",
        "open_ports",
        "finish",
    ]
    assert len(result) == 1


@pytest.mark.parametrize("target", ["device", "tracking"])
def test_falsey_iterable_keeps_each_callers_original_fallback(serialize_history, target):
    trace = []

    class FalseyHistory:
        def __bool__(self):
            trace.append("bool")
            return False

        def __iter__(self):
            trace.append("iter")
            return iter(())

    assert serialize_history(target, FalseyHistory()) == []
    assert trace == (["bool"] if target == "device" else ["iter"])


@pytest.mark.parametrize("target", ["device", "tracking"])
def test_none_keeps_each_callers_original_contract(serialize_history, target):
    if target == "device":
        assert serialize_history(target, None) == []
    else:
        with pytest.raises(TypeError):
            serialize_history(target, None)


@pytest.mark.parametrize("target", ["device", "tracking"])
@pytest.mark.parametrize(
    "field",
    ["scan_id", "observed_at", "status", "hostname", "ip_address", "mac_address", "open_ports"],
)
def test_field_error_stops_before_remaining_fields_and_rows(serialize_history, target, field):
    trace = []

    class Row:
        def __getattr__(self, key):
            trace.append(key)
            if key == field:
                raise RuntimeError(key)
            return key

    def rows():
        yield Row()
        pytest.fail("second row consumed after field error")

    with pytest.raises(RuntimeError, match=field):
        serialize_history(target, rows())
    fields = [
        "scan_id",
        "observed_at",
        "status",
        "hostname",
        "ip_address",
        "mac_address",
        "open_ports",
    ]
    assert trace == fields[: fields.index(field) + 1]


@pytest.mark.parametrize("target", ["device", "tracking"])
def test_iterator_error_is_preserved(serialize_history, target):
    def rows():
        raise RuntimeError("iteration")
        yield

    with pytest.raises(RuntimeError, match="iteration"):
        serialize_history(target, rows())
