"""Traffic counters retain conversion, precedence and lazy endpoint reads."""

import json
from types import SimpleNamespace

import pytest

from app.modules.network.router.helpers import endpoints


def extract(raw, *, source="device", destination="peer", device="device"):
    return endpoints._extract_event_traffic(
        SimpleNamespace(raw_payload=raw, src_ip=source, dst_ip=destination), device_ip=device
    )


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, 0),
        ("", 0),
        (" \t12\n", 12),
        ("+12", 12),
        ("00012", 12),
        ("\uff11\uff12", 12),
        ("1_000", 1000),
        ("1.5", 0),
        (1.5, 0),
        (12, 12),
        (-12, 0),
        ("-12", 0),
        (True, 0),
        (False, 0),
        ([], 0),
        ({}, 0),
        (10**80, 10**80),
    ],
)
def test_counter_conversion_uses_trimmed_integer_text_and_clamps_negatives(value, expected):
    raw = json.dumps({"parsed": {"bytes_sent": value, "bytes_received": "7"}})
    assert extract(raw) == (7, expected, "peer")
    assert extract(raw, source="peer", destination="device") == (expected, 7, "peer")


@pytest.mark.parametrize(
    "raw",
    [
        None,
        "",
        "bad json",
        "null",
        "[]",
        "0",
        "true",
        '"text"',
        "{}",
        '{"parsed": null}',
        '{"parsed": []}',
        '{"parsed": "invalid"}',
        '{"parsed": {}}',
    ],
)
def test_empty_invalid_and_nonmapping_payloads_produce_zero_counts(raw):
    assert extract(raw) == (0, 0, "peer")


@pytest.mark.parametrize(
    "source,destination,device,expected",
    [
        ("device", "device", "device", (7, 12, "device")),
        (None, None, None, (7, 12, None)),
        ("source", "destination", "other", (0, 0, "destination")),
        ("source", "", "other", (0, 0, "source")),
        ("source", None, "other", (0, 0, "source")),
        (None, "", "other", (0, 0, None)),
        ("", "", "other", (0, 0, "")),
    ],
)
def test_source_precedes_destination_and_unknown_direction_keeps_peer_fallback(
    source, destination, device, expected
):
    raw = '{"parsed":{"bytes_sent":12,"bytes_received":7}}'
    assert extract(raw, source=source, destination=destination, device=device) == expected


def test_counter_reads_and_conversions_finish_before_endpoint_reads(monkeypatch):
    trace = []

    class Counter:
        def __init__(self, name, value):
            self.name, self.value = name, value

        def __str__(self):
            trace.append(("str", self.name))
            return self.value

    class Parsed(dict):
        def get(self, key, default=None):
            trace.append(("get", key))
            return super().get(key, default)

    parsed = Parsed(bytes_sent=Counter("sent", "12"), bytes_received=Counter("received", "7"))

    def metadata(raw):
        trace.append(("metadata", raw))
        return {"parsed": parsed}

    class Event:
        @property
        def raw_payload(self):
            trace.append("raw_payload")
            return "raw"

        @property
        def src_ip(self):
            trace.append("src_ip")
            return "device"

        @property
        def dst_ip(self):
            trace.append("dst_ip")
            return "peer"

    monkeypatch.setattr(endpoints, "metadata_sources_to_dict", metadata)
    assert endpoints._extract_event_traffic(Event(), device_ip="device") == (7, 12, "peer")
    assert trace == [
        "raw_payload",
        ("metadata", "raw"),
        ("get", "bytes_sent"),
        ("str", "sent"),
        ("get", "bytes_received"),
        ("str", "received"),
        "src_ip",
        "dst_ip",
    ]


@pytest.mark.parametrize("error", [TypeError, ValueError, OverflowError, RuntimeError])
def test_only_type_and_value_conversion_errors_are_swallowed(monkeypatch, error):
    trace = []

    class InvalidCounter:
        def __str__(self):
            trace.append("str")
            raise error("counter unavailable")

    monkeypatch.setattr(
        endpoints,
        "metadata_sources_to_dict",
        lambda _: {"parsed": {"bytes_sent": InvalidCounter(), "bytes_received": 7}},
    )

    class Event:
        raw_payload = "raw"

        @property
        def src_ip(self):
            trace.append("src_ip")
            return "device"

        dst_ip = "peer"

    if error in (TypeError, ValueError):
        assert endpoints._extract_event_traffic(Event(), device_ip="device") == (7, 0, "peer")
        assert trace == ["str", "src_ip"]
    else:
        with pytest.raises(error, match="counter unavailable"):
            endpoints._extract_event_traffic(Event(), device_ip="device")
        assert trace == ["str"]


def test_source_is_read_again_when_returning_destination_match():
    class Event:
        raw_payload = '{"parsed":{"bytes_sent":12,"bytes_received":7}}'
        dst_ip = "device"
        reads = 0

        @property
        def src_ip(self):
            self.reads += 1
            return "first source" if self.reads == 1 else "second source"

    event = Event()
    assert endpoints._extract_event_traffic(event, device_ip="device") == (12, 7, "second source")
    assert event.reads == 2
