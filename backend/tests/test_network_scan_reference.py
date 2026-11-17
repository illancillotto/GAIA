"""Scan snapshots preserve reference lookup priority and serialized labels."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy.dialects import postgresql

from app.modules.network.models import NetworkDevice
from app.modules.network.router.helpers import scans


def snapshot(**changes):
    fields = {
        "id": 2,
        "scan_id": 1,
        "device_id": 7,
        "ip_address": "10.0.0.7",
        "mac_address": "aa:bb:cc:dd:ee:ff",
        "hostname": "snapshot-host",
        "hostname_source": "dns",
        "display_name": "Snapshot",
        "asset_label": "asset",
        "vendor": "vendor",
        "model_name": "model",
        "device_type": "host",
        "operating_system": "system",
        "dns_name": "snapshot.example",
        "location_hint": "room",
        "metadata_sources": '{"origin":"scan"}',
        "status": "online",
        "open_ports": "80,443",
        "observed_at": datetime(2026, 11, 17, tzinfo=UTC),
    }
    fields.update(changes)
    return SimpleNamespace(**fields)


class LookupSession:
    def __init__(self, by_id=None, by_ip=None, *, fail=None):
        self.by_id = by_id
        self.by_ip = by_ip
        self.fail = fail
        self.trace = []
        self.query = None

    def get(self, model, key):
        self.trace.append(("get", model, key))
        if self.fail == "get":
            raise RuntimeError("get unavailable")
        return self.by_id

    def scalar(self, query):
        self.query = query.compile(dialect=postgresql.dialect())
        self.trace.append(("scalar",))
        if self.fail == "scalar":
            raise RuntimeError("scalar unavailable")
        return self.by_ip


@pytest.mark.parametrize("device_id", [None, 0, 7])
@pytest.mark.parametrize("has_id_reference", [False, True])
@pytest.mark.parametrize("has_ip_reference", [False, True])
def test_reference_lookup_uses_truthy_id_then_ip_and_preserves_all_snapshot_fields(
    monkeypatch, device_id, has_id_reference, has_ip_reference
):
    by_id = SimpleNamespace(assigned_user_id=4)
    by_ip = SimpleNamespace(assigned_user_id=None)
    db = LookupSession(by_id if has_id_reference else None, by_ip if has_ip_reference else None)
    item = snapshot(device_id=device_id)
    original = vars(item).copy()
    labels = []

    def resolve(reference):
        labels.append(reference)
        return ("From ID", "application_user") if reference is by_id else ("From IP", "device")

    monkeypatch.setattr(scans, "_resolve_device_label", resolve)
    result = scans._serialize_scan_device(item, db)

    expected_reference = (
        by_id if device_id and has_id_reference else by_ip if has_ip_reference else None
    )
    assert labels == ([] if expected_reference is None else [expected_reference])
    expected_trace = [("get", NetworkDevice, device_id)] if device_id else []
    if not (device_id and has_id_reference):
        expected_trace.append(("scalar",))
        assert db.query.params == {"ip_address_1": "10.0.0.7"}
        assert "network_devices.ip_address =" in str(db.query)
    assert db.trace == expected_trace
    label = (
        "From ID"
        if expected_reference is by_id
        else "From IP"
        if expected_reference is by_ip
        else "Snapshot"
    )
    expected = original | {
        "metadata_sources": {"origin": "scan"},
        "resolved_label": label,
        "label_source": "application_user"
        if expected_reference is by_id
        else "device"
        if expected_reference is by_ip
        else None,
        "assigned_user_label": label if expected_reference is by_id else None,
    }
    assert result.model_dump() == expected
    assert vars(item) == original


@pytest.mark.parametrize(
    "display_name,hostname,ip_address,expected_label,queries",
    [
        ("Display", "Host", "10.0.0.7", "Display", 1),
        ("", "Host", "10.0.0.7", "Host", 1),
        (None, "", "10.0.0.7", "10.0.0.7", 1),
        (None, None, "", "", 0),
    ],
)
def test_missing_reference_uses_snapshot_display_then_hostname_then_ip(
    display_name, hostname, ip_address, expected_label, queries
):
    db = LookupSession()
    result = scans._serialize_scan_device(
        snapshot(
            device_id=None, display_name=display_name, hostname=hostname, ip_address=ip_address
        ),
        db,
    )
    assert (result.resolved_label, result.label_source, result.assigned_user_label) == (
        expected_label,
        None,
        None,
    )
    assert db.trace == [("scalar",)] * queries


@pytest.mark.parametrize("failure", ["get", "scalar"])
def test_lookup_errors_propagate_before_label_resolution(monkeypatch, failure):
    def unexpected_label(_):
        raise AssertionError("lookup failed before label resolution")

    monkeypatch.setattr(scans, "_resolve_device_label", unexpected_label)
    db = LookupSession(fail=failure)
    with pytest.raises(RuntimeError, match=f"{failure} unavailable"):
        scans._serialize_scan_device(snapshot(), db)
    assert [event[0] for event in db.trace] == (["get"] if failure == "get" else ["get", "scalar"])


def test_falsey_reference_is_still_resolved_but_has_no_assigned_user_label(monkeypatch):
    class Reference:
        def __bool__(self):
            return False

        @property
        def assigned_user_id(self):
            raise AssertionError("falsey reference must skip assigned_user_id")

    reference = Reference()
    db = LookupSession(by_id=reference)
    monkeypatch.setattr(scans, "_resolve_device_label", lambda value: ("Resolved", "device"))
    result = scans._serialize_scan_device(snapshot(), db)
    assert (result.resolved_label, result.label_source, result.assigned_user_label) == (
        "Resolved",
        "device",
        None,
    )
    assert db.trace == [("get", NetworkDevice, 7)]


def test_id_is_read_again_for_lookup_and_then_for_payload(monkeypatch):
    reads = []

    class Snapshot:
        def __init__(self):
            self.fields = vars(snapshot())

        def __getattr__(self, key):
            reads.append(key)
            if key == "device_id":
                return [7, 8, 9][reads.count(key) - 1]
            return self.fields[key]

    db = LookupSession(by_id=SimpleNamespace(assigned_user_id=None))
    monkeypatch.setattr(scans, "_resolve_device_label", lambda _: ("Resolved", "device"))
    result = scans._serialize_scan_device(Snapshot(), db)
    assert db.trace == [("get", NetworkDevice, 8)]
    assert result.device_id == 9
    assert reads[:4] == ["device_id", "device_id", "id", "scan_id"]
    assert reads.count("device_id") == 3


def test_ip_is_read_again_for_query_then_fallback_and_payload():
    class Snapshot:
        def __init__(self):
            self.fields = vars(snapshot(device_id=None, display_name=None, hostname=None))
            self.ip_reads = 0

        def __getattr__(self, key):
            if key == "ip_address":
                self.ip_reads += 1
                return f"10.0.0.{self.ip_reads}"
            return self.fields[key]

    db = LookupSession()
    item = Snapshot()
    result = scans._serialize_scan_device(item, db)
    assert db.query.params == {"ip_address_1": "10.0.0.2"}
    assert result.resolved_label == "10.0.0.3"
    assert result.ip_address == "10.0.0.4"
    assert item.ip_reads == 4
