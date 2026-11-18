"""Scan delta classification relies on non-None map values and key union."""

from types import SimpleNamespace

import pytest

from app.modules.network import services


def snapshot(key, *, tag=None, **changes):
    return SimpleNamespace(
        **{
            "tag": tag or key,
            "ip_address": key,
            "mac_address": None,
            "hostname": "host",
            "hostname_source": "dns",
            "display_name": None,
            "asset_label": None,
            "vendor": None,
            "model_name": None,
            "device_type": None,
            "operating_system": None,
            "dns_name": None,
            "location_hint": None,
            "metadata_sources": None,
            "status": "online",
            "open_ports": [22],
            **changes,
        }
    )


@pytest.mark.parametrize(
    "before,after,expected",
    [
        ([], [], (0, 0, 0)),
        ([], [snapshot("a")], (1, 0, 0)),
        ([snapshot("a")], [], (0, 1, 0)),
        ([snapshot("a")], [snapshot("a")], (0, 0, 0)),
        ([snapshot("a")], [snapshot("a", vendor="changed")], (0, 0, 1)),
        (
            [snapshot("a"), snapshot("b")],
            [snapshot("b", status="offline"), snapshot("c")],
            (1, 1, 1),
        ),
    ],
)
def test_new_missing_changed_and_unchanged_partitions(before, after, expected):
    summary, changes = services._build_diff(before, after)
    assert summary == dict(
        zip(
            ["new_devices_count", "missing_devices_count", "changed_devices_count"],
            expected,
            strict=True,
        )
    )
    assert len(changes) == sum(expected)
    assert [item["change_type"] for item in changes] == ["new"] * expected[0] + [
        "missing"
    ] * expected[1] + ["changed"] * expected[2]
    for item in changes:
        assert list(item) == ["key", "before", "after", "change_type"]
        if item["change_type"] == "new":
            assert item["before"] is None and any(item["after"] is row for row in after)
        elif item["change_type"] == "missing":
            assert item["after"] is None and any(item["before"] is row for row in before)
        else:
            assert any(item["before"] is row for row in before) and any(
                item["after"] is row for row in after
            )


@pytest.mark.parametrize("side", ["before", "after", "both"])
def test_duplicate_keys_use_last_snapshot_without_duplicate_changes(side):
    old_first = snapshot("a", tag="old-first")
    old_last = snapshot("a", tag="old-last", vendor="old")
    new_first = snapshot("a", tag="new-first")
    new_last = snapshot("a", tag="new-last", vendor="new")
    before = [old_first, old_last] if side in {"before", "both"} else [old_last]
    after = [new_first, new_last] if side in {"after", "both"} else [new_last]
    summary, changes = services._build_diff(before, after)
    assert summary == {
        "new_devices_count": 0,
        "missing_devices_count": 0,
        "changed_devices_count": 1,
    }
    assert len(changes) == 1
    assert changes[0]["before"] is old_last and changes[0]["after"] is new_last


def test_sorted_comparisons_and_category_grouping_keep_original_order(monkeypatch):
    pairs = []
    original = services._snapshot_payload_changed

    def compare(before, after):
        assert before is not None and after is not None
        pairs.append((before.ip_address, after.ip_address))
        return original(before, after)

    monkeypatch.setattr(services, "_snapshot_payload_changed", compare)
    before = [snapshot(key) for key in ["z", "m", "a", "n"]]
    after = [
        snapshot(key, vendor="changed" if key in {"a", "z"} else None)
        for key in ["y", "z", "b", "a", "n"]
    ]
    summary, changes = services._build_diff(before, after)
    assert pairs == [("a", "a"), ("n", "n"), ("z", "z")]
    assert [(item["key"], item["change_type"]) for item in changes] == [
        ("b", "new"),
        ("y", "new"),
        ("m", "missing"),
        ("a", "changed"),
        ("z", "changed"),
    ]
    assert summary == {
        "new_devices_count": 2,
        "missing_devices_count": 1,
        "changed_devices_count": 2,
    }


@pytest.mark.parametrize("side", ["before", "after"])
def test_none_input_is_rejected_while_building_maps_before_comparisons(monkeypatch, side):
    compared = []
    monkeypatch.setattr(services, "_snapshot_payload_changed", lambda *rows: compared.append(rows))
    before = [snapshot("a"), None] if side == "before" else [snapshot("a")]
    after = [snapshot("a"), None] if side == "after" else [snapshot("a")]
    with pytest.raises(AttributeError):
        services._build_diff(before, after)
    assert compared == []


def test_comparison_error_stops_before_later_shared_keys(monkeypatch):
    calls = []

    def compare(before, after):
        calls.append(before.ip_address)
        if before.ip_address == "b":
            raise RuntimeError("comparison")
        return True

    monkeypatch.setattr(services, "_snapshot_payload_changed", compare)
    with pytest.raises(RuntimeError, match="comparison"):
        services._build_diff([snapshot(k) for k in "cba"], [snapshot(k) for k in "bac"])
    assert calls == ["a", "b"]


def test_falsey_snapshots_are_present_without_evaluating_their_truthiness():
    class Row(SimpleNamespace):
        def __bool__(self):
            pytest.fail("snapshot truthiness is not a presence test")

    before = Row(**vars(snapshot("a")))
    after = Row(**vars(snapshot("a", status="offline")))
    summary, changes = services._build_diff([before], [after])
    assert summary["changed_devices_count"] == 1
    assert changes[0]["before"] is before and changes[0]["after"] is after


def test_none_key_does_not_make_map_values_none():
    before = snapshot(None)
    after = snapshot(None, status="offline")
    summary, changes = services._build_diff([before], [after])
    assert summary["changed_devices_count"] == 1 and changes[0]["key"] is None
    assert changes[0]["before"] is before and changes[0]["after"] is after
