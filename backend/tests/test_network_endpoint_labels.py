"""Precedence and lazy linked-device reads in firewall endpoint labels."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import Session

from app.modules.network.models import NetworkDevice
from app.modules.network.router.helpers import endpoints


@pytest.mark.parametrize(
    ("labels", "addresses", "device_id", "exists", "linked_label", "expected", "get_called"),
    [
        ((None, None), ("match", "match"), None, True, "Linked", (None, None), False),
        (("Known", "Known"), ("match", "match"), 4, True, "Linked", ("Known", "Known"), False),
        ((None, None), ("match", "match"), 0, True, "Linked", ("Linked", "Linked"), True),
        (("Known", None), ("match", "match"), 4, True, "Linked", ("Known", "Linked"), True),
        ((None, "Known"), ("match", "match"), 4, True, "Linked", ("Linked", "Known"), True),
        (("", ""), ("match", "other"), 4, True, "Linked", ("Linked", ""), True),
        (("", "Known"), (None, "match"), 4, True, "Linked", ("", "Known"), True),
        ((None, ""), ("other", ""), 4, True, "Linked", (None, ""), True),
        ((None, None), ("match", "match"), 4, False, "Linked", (None, None), True),
        ((None, None), ("match", "other"), 4, True, "", ("", None), True),
        (("", ""), ("match", "other"), 4, True, None, (None, ""), True),
    ],
)
def test_fallback_keeps_existing_labels_and_only_uses_matching_nonempty_addresses(
    monkeypatch, labels, addresses, device_id, exists, linked_label, expected, get_called
):
    trace = []
    linked_device = SimpleNamespace(ip_address="match")
    pending = iter(labels)

    def resolve_ip(session, ip):
        assert session is db
        trace.append(("ip", ip))
        return next(pending)

    def get_device(model, identifier):
        trace.append(("get", model, identifier))
        return linked_device if exists else None

    db = SimpleNamespace(get=get_device)

    def resolve_device(device):
        assert device is linked_device
        trace.append(("label",))
        return linked_label, "device"

    monkeypatch.setattr(endpoints, "_resolve_label_for_ip", resolve_ip)
    monkeypatch.setattr(endpoints, "_resolve_device_label", resolve_device)
    assert (
        endpoints._resolve_firewall_event_endpoint_labels(
            db, device_id=device_id, src_ip=addresses[0], dst_ip=addresses[1]
        )
        == expected
    )
    expected_trace = [("ip", addresses[0]), ("ip", addresses[1])]
    if get_called:
        expected_trace.append(("get", NetworkDevice, device_id))
        if exists:
            expected_trace.append(("label",))
    assert trace == expected_trace


def test_linked_ip_is_read_for_each_eligible_endpoint_in_source_destination_order(monkeypatch):
    trace = []
    pending_addresses = iter(["source", "destination"])

    class Device:
        @property
        def ip_address(self):
            address = next(pending_addresses)
            trace.append(("address", address))
            return address

    device = Device()

    def resolve_device(actual):
        assert actual is device
        trace.append(("label",))
        return "Linked", "device"

    monkeypatch.setattr(endpoints, "_resolve_label_for_ip", lambda *_args: None)
    monkeypatch.setattr(endpoints, "_resolve_device_label", resolve_device)
    db = SimpleNamespace(get=lambda *_args: device)
    assert endpoints._resolve_firewall_event_endpoint_labels(
        db, device_id=4, src_ip="source", dst_ip="destination"
    ) == ("Linked", "Linked")
    assert trace == [("label",), ("address", "source"), ("address", "destination")]


def test_linked_ip_is_not_read_for_an_existing_label_or_an_empty_address(monkeypatch):
    class Device:
        @property
        def ip_address(self):
            raise AssertionError("unnecessary linked-device address read")

    monkeypatch.setattr(endpoints, "_resolve_label_for_ip", Mock(side_effect=["Known", None]))
    monkeypatch.setattr(endpoints, "_resolve_device_label", lambda _device: ("Linked", "device"))
    db = SimpleNamespace(get=lambda *_args: Device())
    assert endpoints._resolve_firewall_event_endpoint_labels(
        db, device_id=4, src_ip="match", dst_ip=""
    ) == ("Known", None)


def test_second_linked_ip_read_failure_still_propagates_after_the_first_read(monkeypatch):
    reads = []

    class Device:
        @property
        def ip_address(self):
            reads.append("ip")
            if len(reads) == 2:
                raise RuntimeError("expired address unavailable")
            return "source"

    monkeypatch.setattr(endpoints, "_resolve_label_for_ip", lambda *_args: None)
    monkeypatch.setattr(endpoints, "_resolve_device_label", lambda _device: ("Linked", "device"))
    db = SimpleNamespace(get=lambda *_args: Device())
    with pytest.raises(RuntimeError, match="expired address unavailable"):
        endpoints._resolve_firewall_event_endpoint_labels(
            db, device_id=4, src_ip="source", dst_ip="destination"
        )
    assert reads == ["ip", "ip"]


@pytest.mark.parametrize(
    ("addresses", "expected", "refreshes"),
    [
        (("match", "match"), ("Linked", "Linked"), 1),
        (("match", "other"), ("Linked", None), 1),
        ((None, ""), (None, None), 0),
        (("other", "other"), (None, None), 1),
    ],
)
def test_expired_orm_address_refreshes_lazily_without_writes(
    monkeypatch, addresses, expected, refreshes
):
    monkeypatch.setattr(endpoints, "_resolve_label_for_ip", lambda *_args: None)
    engine = create_engine("sqlite://")
    NetworkDevice.__table__.create(engine)
    statements = []

    def record_statement(_connection, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement)

    try:
        with Session(engine, expire_on_commit=False) as db:
            device = NetworkDevice(id=4, ip_address="match", display_name="Linked")
            db.add(device)
            db.commit()
            db.expire(device, ["ip_address"])
            event.listen(engine, "before_cursor_execute", record_statement)
            assert (
                endpoints._resolve_firewall_event_endpoint_labels(
                    db, device_id=4, src_ip=addresses[0], dst_ip=addresses[1]
                )
                == expected
            )
            assert len(statements) == refreshes
            assert all(sql.startswith("SELECT network_devices.ip_address") for sql in statements)
            assert ("ip_address" in inspect(device).expired_attributes) == (refreshes == 0)
            assert not db.new and not db.dirty and not db.deleted
    finally:
        engine.dispose()
