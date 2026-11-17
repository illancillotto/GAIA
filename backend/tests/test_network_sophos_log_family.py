"""Sophos family priority, normalization and ordered string operations."""

import pytest

from app.modules.network.router.helpers import firewalls


@pytest.mark.parametrize(
    "event_type,parsed,expected",
    [
        ("FIREWALL.rule", None, "firewall"),
        ("plain", {"log_type": " Firewall "}, "firewall"),
        ("firewall", {"log_component": "vpn"}, "vpn"),
        ("remote.VPN", None, "vpn"),
        ("plain", {"log_type": "vpn"}, "vpn"),
        ("plain", {"log_component": " VPN "}, "vpn"),
        ("network.IPS", None, "ips"),
        ("xxipsxx", None, "ips"),
        ("plain", {"log_type": "Intrusion Prevention"}, "ips"),
        ("plain", {"log_type": "IPS"}, "ips"),
        ("plain", {"log_component": "IPS"}, "ips"),
        ("user.AUTH", None, "authentication"),
        ("unauthorized", None, "authentication"),
        ("plain", {"log_type": "Authentication"}, "authentication"),
        ("plain", {"log_component": "Authentication"}, "authentication"),
        ("system_health.cpu", None, "system"),
        ("event.gui.login", None, "system"),
        ("plain", {"log_type": "System"}, "system"),
        ("plain", {"log_component": "System"}, "system"),
        ("content_filtering.web", None, "content_filtering"),
        ("before.content_filtering.web", None, "before"),
        ("anti-virus.scan", None, "anti-virus"),
        ("before.anti-virus.scan", None, "anti-virus"),
        ("plain", {"log_type": "anti-virus", "log_component": "content_filtering"}, "plain"),
        ("custom.event", None, "custom"),
        ("custom", None, "custom"),
        ("", None, "other"),
        (".suffix", None, ""),
        (".", None, ""),
        (" Space ", None, " space "),
        ("plain", {"log_type": 0, "log_component": False}, "plain"),
    ],
)
def test_family_sources_substrings_prefixes_and_literal_fallback(event_type, parsed, expected):
    assert (
        firewalls._classify_sophos_log_family_from_values(event_type=event_type, parsed=parsed)
        == expected
    )


@pytest.mark.parametrize(
    "event_type,log_type,expected",
    [
        ("remote.vpn", "firewall", "firewall"),
        ("network.ips", "firewall vpn", "firewall"),
        ("user.auth", "vpn intrusion", "vpn"),
        ("system_health.cpu", "vpn", "vpn"),
        ("user.auth", "intrusion authentication", "ips"),
        ("content_filtering.web", "ips", "ips"),
        ("system_health.cpu", "authentication", "authentication"),
        ("anti-virus.scan", "authentication system", "authentication"),
        ("content_filtering.web", "system", "system"),
        ("anti-virus.scan", "system", "system"),
        ("content_filtering.anti-virus", "", "content_filtering"),
    ],
)
def test_earlier_family_precedes_overlapping_later_family(event_type, log_type, expected):
    assert (
        firewalls._classify_sophos_log_family_from_values(
            event_type=event_type, parsed={"log_type": log_type}
        )
        == expected
    )


@pytest.mark.parametrize("parsed", [None, [], "vpn", 1, False])
def test_nonmapping_metadata_is_ignored(parsed):
    assert (
        firewalls._classify_sophos_log_family_from_values(event_type="custom.event", parsed=parsed)
        == "custom"
    )


def test_both_metadata_fields_are_normalized_before_event_type():
    trace = []

    class Value:
        def __init__(self, name):
            self.name = name

        def __bool__(self):
            trace.append(("bool", self.name))
            return True

        def __str__(self):
            trace.append(("str", self.name))
            return " Firewall "

    class Parsed(dict):
        def get(self, key, default=None):
            trace.append(("get", key))
            return Value(key)

    class EventType(str):
        def lower(self):
            trace.append("lower")
            return super().lower()

    assert (
        firewalls._classify_sophos_log_family_from_values(
            event_type=EventType("firewall.rule"), parsed=Parsed()
        )
        == "firewall"
    )
    assert trace == [
        ("get", "log_type"),
        ("bool", "log_type"),
        ("str", "log_type"),
        ("get", "log_component"),
        ("bool", "log_component"),
        ("str", "log_component"),
        "lower",
    ]


def test_string_operations_remain_ordered_and_fallback_keeps_truthiness():
    trace = []

    class EventType(str):
        def lower(self):
            trace.append("lower")
            return self

        def startswith(self, prefix):
            trace.append(("startswith", prefix))
            return super().startswith(prefix)

        def __contains__(self, term):
            trace.append(("contains", term))
            return super().__contains__(term)

        def __bool__(self):
            trace.append("bool")
            return len(self) != 0

    event_type = EventType("plain")
    assert (
        firewalls._classify_sophos_log_family_from_values(event_type=event_type, parsed=None)
        is event_type
    )
    assert trace == [
        "lower",
        ("startswith", "firewall."),
        ("contains", "vpn"),
        ("contains", "ips"),
        ("contains", "auth"),
        ("startswith", ("system_health.", "event.gui.")),
        ("startswith", "content_filtering."),
        ("startswith", "anti-virus."),
        ("contains", "anti-virus"),
        ("contains", "."),
        "bool",
    ]


def test_successful_family_skips_later_string_operations():
    class EventType(str):
        def lower(self):
            return self

        def __contains__(self, term):
            assert term == "vpn", "later family must not be inspected"
            return True

    assert (
        firewalls._classify_sophos_log_family_from_values(event_type=EventType("plain"), parsed={})
        == "vpn"
    )


@pytest.mark.parametrize("field", ["log_type", "log_component"])
def test_metadata_conversion_errors_propagate_before_classification(field):
    class Invalid:
        def __str__(self):
            raise RuntimeError("metadata unavailable")

    with pytest.raises(RuntimeError, match="metadata unavailable"):
        firewalls._classify_sophos_log_family_from_values(
            event_type="firewall.rule", parsed={field: Invalid()}
        )
