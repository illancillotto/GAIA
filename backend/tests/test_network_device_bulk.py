"""Bulk updates preserve field intent, observable reads and transaction order."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.modules.network.router.routes import devices as routes
from app.modules.network.schemas import NetworkDeviceResponse


def device(index, *, notes="existing"):
    return SimpleNamespace(
        id=index,
        ip_address=f"10.0.0.{index}",
        notes=notes,
        location_hint="original location",
        is_known_device=True,
    )


def bulk(monkeypatch, payload, rows, *, trace=None, fail=None):
    trace = [] if trace is None else trace

    def record(name, *args):
        trace.append((name, *args))
        if name == fail:
            raise RuntimeError(f"failed {name}")

    def scalars(query):
        record("query", str(query.compile(compile_kwargs={"literal_binds": True})))
        return SimpleNamespace(all=lambda: rows)

    def serialize(row):
        record("serialize", row.id)
        now = datetime.now(UTC)
        return NetworkDeviceResponse(
            id=row.id,
            last_scan_id=None,
            ip_address=row.ip_address,
            mac_address=None,
            hostname=None,
            resolved_label=row.ip_address,
            label_source="ip",
            notes=row.notes,
            location_hint=row.location_hint,
            is_known_device=row.is_known_device,
            status="online",
            is_monitored=True,
            open_ports=None,
            first_seen_at=now,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )

    monkeypatch.setattr(routes, "_require_network_module", lambda _user: record("auth"))
    monkeypatch.setattr(
        routes,
        "sync_network_device_alert_state",
        lambda _db, row: record("sync", row.id, row.is_known_device, row.location_hint, row.notes),
    )
    monkeypatch.setattr(routes, "_serialize_device", serialize)
    db = SimpleNamespace(
        scalars=scalars,
        add=lambda row: record("add", row.id),
        commit=lambda: record("commit"),
        refresh=lambda row: record("refresh", row.id),
    )
    result = routes.bulk_update_devices(payload, SimpleNamespace(), db)
    return result, trace


def payload(**changes):
    return SimpleNamespace(
        **{
            "device_ids": [1, 2],
            "is_known_device": None,
            "location_hint": None,
            "notes_append": None,
            **changes,
        }
    )


@pytest.mark.parametrize(
    "changes,expected",
    [
        ({}, (True, "original location", "existing")),
        ({"is_known_device": False}, (False, "original location", "existing")),
        ({"is_known_device": True}, (True, "original location", "existing")),
        ({"location_hint": ""}, (True, None, "existing")),
        ({"location_hint": " "}, (True, " ", "existing")),
        ({"location_hint": "Rack"}, (True, "Rack", "existing")),
        ({"notes_append": ""}, (True, "original location", "existing")),
        ({"notes_append": " \n "}, (True, "original location", "existing")),
        ({"notes_append": " new "}, (True, "original location", "existing\nnew")),
    ],
)
def test_optional_fields_keep_none_false_empty_and_whitespace_distinct(
    monkeypatch, changes, expected
):
    row = device(1)
    result, trace = bulk(monkeypatch, payload(**changes), [row])
    assert (row.is_known_device, row.location_hint, row.notes) == expected
    assert result.updated_count == 1
    assert (
        result.items[0].is_known_device,
        result.items[0].location_hint,
        result.items[0].notes,
    ) == expected
    assert next(entry for entry in trace if entry[0] == "sync")[2:] == expected


@pytest.mark.parametrize(
    "existing,expected",
    [
        (None, "new"),
        ("", "new"),
        (" ", "new"),
        (" old ", "old \nnew"),
        ("first\nsecond", "first\nsecond\nnew"),
    ],
)
def test_note_append_strips_boundaries_and_preserves_internal_content(
    monkeypatch, existing, expected
):
    row = device(1, notes=existing)
    bulk(monkeypatch, payload(notes_append=" new "), [row])
    assert row.notes == expected


def test_all_updates_and_alert_sync_precede_one_commit_then_refresh_then_serialization(monkeypatch):
    rows = [device(2), device(1)]
    result, trace = bulk(monkeypatch, payload(is_known_device=False), rows)
    assert [entry[0] for entry in trace] == [
        "auth",
        "query",
        "sync",
        "add",
        "sync",
        "add",
        "commit",
        "refresh",
        "refresh",
        "serialize",
        "serialize",
    ]
    assert "ORDER BY network_devices.ip_address ASC" in trace[1][1]
    assert [entry[1] for entry in trace if entry[0] == "refresh"] == [2, 1]
    assert [row.id for row in result.items] == [2, 1]


def test_payload_fields_remain_repeated_reads(monkeypatch):
    class Payload:
        device_ids = [1]

        def __init__(self):
            self.reads = []

        def __getattr__(self, key):
            self.reads.append(key)
            count = self.reads.count(key)
            return {
                "notes_append": ["guard", " append "],
                "is_known_device": [True, False],
                "location_hint": ["guard", ""],
            }[key][count - 1]

    request = Payload()
    row = device(1)
    bulk(monkeypatch, request, [row])
    assert (row.is_known_device, row.location_hint, row.notes) == (False, None, "existing\nappend")
    assert request.reads == [
        "notes_append",
        "notes_append",
        "is_known_device",
        "is_known_device",
        "location_hint",
        "location_hint",
    ]


@pytest.mark.parametrize("fail", ["auth", "query", "sync", "add", "commit", "refresh", "serialize"])
def test_failures_stop_at_original_stage_without_implicit_rollback_or_retry(monkeypatch, fail):
    trace = []
    with pytest.raises(RuntimeError, match=f"failed {fail}"):
        bulk(monkeypatch, payload(is_known_device=False), [device(1)], trace=trace, fail=fail)
    order = ["auth", "query", "sync", "add", "commit", "refresh", "serialize"]
    assert [entry[0] for entry in trace] == order[: order.index(fail) + 1]


def test_no_matching_devices_raises_before_reading_update_fields(monkeypatch):
    class Payload:
        device_ids = [99]

        def __getattr__(self, key):
            raise AssertionError(f"unexpected payload read {key}")

    trace = []
    with pytest.raises(HTTPException) as caught:
        bulk(monkeypatch, Payload(), [], trace=trace)
    assert caught.value.status_code == 404
    assert caught.value.detail == "No devices found for bulk update"
    assert [entry[0] for entry in trace] == ["auth", "query"]
