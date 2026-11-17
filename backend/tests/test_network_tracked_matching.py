"""Tracked subject matching precedence, short circuits and observable reads."""

from types import SimpleNamespace

import pytest

from app.modules.network.router.helpers import tracking


def match(
    kind,
    *,
    device_id=4,
    value="peer",
    normalized="peer",
    event_id=4,
    src="source",
    dst="destination",
    parsed=None,
):
    subject = SimpleNamespace(
        entity_type=kind, device_id=device_id, value=value, normalized_value=normalized
    )
    event = SimpleNamespace(device_id=event_id, src_ip=src, dst_ip=dst)
    return tracking._match_tracked_subject_against_event(
        subject, event, parsed={} if parsed is None else parsed
    )


@pytest.mark.parametrize(
    "device_id, event_id, value, src, dst, expected",
    [
        (4, 4, "peer", "source", "destination", ("device", "peer")),
        (4, 5, "peer", "peer", "destination", ("device", "peer")),
        (4, 5, "peer", "source", "peer", ("device", "peer")),
        (4, 5, "peer", "source", "destination", None),
        (None, 4, "peer", "peer", "peer", None),
        (0, 0, "peer", "peer", "peer", None),
        (4, 4, "", "source", "destination", ("device", "")),
    ],
)
def test_device_requires_truthy_subject_id_then_matches_id_or_either_ip(
    device_id, event_id, value, src, dst, expected
):
    assert (
        match("device", device_id=device_id, event_id=event_id, value=value, src=src, dst=dst)
        == expected
    )


@pytest.mark.parametrize(
    "normalized, src, dst, expected",
    [
        ("peer", "peer", "peer", ("src_ip", "peer")),
        ("peer", "other", "peer", ("dst_ip", "peer")),
        ("peer", "other", "different", None),
        (None, None, None, ("src_ip", None)),
        ("", "", "", ("src_ip", "")),
        ("8.8.8.8", " 8.8.8.8 ", "other", None),
    ],
)
def test_ip_source_precedes_destination_and_comparison_is_literal(normalized, src, dst, expected):
    assert match("ip", normalized=normalized, src=src, dst=dst) == expected


@pytest.mark.parametrize(
    "parsed, normalized, expected",
    [
        (
            {"domain": " DOMAIN.Example ", "url": "https://other.example"},
            "domain.example",
            ("domain", "domain.example"),
        ),
        ({"domain": "different", "url": "https://match.example"}, "match.example", None),
        ({"domain": "Example.COM."}, "example.com", None),
        ({"domain": "Example.COM."}, "example.com.", ("domain", "example.com.")),
        (
            {"domain": " ", "url": " HTTPS://EXAMPLE.COM/path "},
            "example.com",
            ("domain", "example.com"),
        ),
        ({"domain": 3, "url": "//EXAMPLE.COM/path"}, "example.com", ("domain", "example.com")),
        ({"url": "https:///path"}, "path", None),
        ({"url": "relative/path"}, "relative/path", None),
        ({"url": []}, "peer", None),
        ({}, "peer", None),
        ({"domain": ""}, "", None),
        ({"domain": " Example.COM "}, "EXAMPLE.COM", None),
    ],
)
def test_domain_field_has_precedence_and_keeps_trailing_dot_and_literal_target(
    parsed, normalized, expected
):
    assert match("domain", parsed=parsed, normalized=normalized) == expected


@pytest.mark.parametrize(
    "url, normalized, expected",
    [
        (
            " https://Example.COM/path ",
            "https://Example.COM/path",
            ("url", "https://Example.COM/path"),
        ),
        ("https://Example.COM/path", "https://example.com/path", None),
        ("https://[bad", "https://[bad", ("url", "https://[bad")),
        (" ", "", ("url", "")),
        ("", "", ("url", "")),
        (None, None, None),
        (3, "3", None),
    ],
)
def test_url_compares_stripped_text_without_parsing(url, normalized, expected):
    assert match("url", parsed={"url": url}, normalized=normalized) == expected


@pytest.mark.parametrize("kind", ["unknown", "DEVICE", "", None])
def test_unknown_type_does_not_read_event_or_payload(kind):
    class Unreadable:
        def __getattr__(self, name):
            raise AssertionError("unexpected read " + name)

        def get(self, key):
            raise AssertionError("unexpected get " + key)

    assert (
        tracking._match_tracked_subject_against_event(
            SimpleNamespace(entity_type=kind), Unreadable(), parsed=Unreadable()
        )
        is None
    )


@pytest.mark.parametrize("url", ["https://[bad", "https://[not-ip]/"])
def test_domain_url_errors_propagate_but_valid_domain_skips_bad_url(url):
    with pytest.raises(ValueError):
        match("domain", parsed={"url": url})
    assert match("domain", parsed={"domain": "peer", "url": url}) == ("domain", "peer")


def test_device_id_match_skips_ip_fields_and_reads_subject_id_twice():
    trace = []

    class Subject:
        entity_type = "device"

        @property
        def device_id(self):
            trace.append("subject-id")
            return 4

        @property
        def value(self):
            trace.append("value")
            return "peer"

    class Event:
        @property
        def device_id(self):
            trace.append("event-id")
            return 4

        def __getattr__(self, name):
            raise AssertionError("unexpected read " + name)

    assert tracking._match_tracked_subject_against_event(Subject(), Event(), parsed={}) == (
        "device",
        "peer",
    )
    assert trace == ["subject-id", "event-id", "subject-id", "value"]


def test_ip_match_reloads_normalized_value_for_comparison_and_return():
    trace = []
    values = iter(["source", "returned"])

    class Subject:
        entity_type = "ip"

        @property
        def normalized_value(self):
            value = next(values)
            trace.append(value)
            return value

    class Event:
        src_ip = "source"

        @property
        def dst_ip(self):
            raise AssertionError("destination read after source matched")

    assert tracking._match_tracked_subject_against_event(Subject(), Event(), parsed={}) == (
        "src_ip",
        "returned",
    )
    assert trace == ["source", "returned"]


def test_url_second_strip_result_is_returned_even_if_falsy():
    trace = []

    class Url(str):
        def strip(self):
            trace.append("strip")
            return "target" if len(trace) == 1 else None

    assert match("url", normalized="target", parsed={"url": Url("URL")}) == ("url", None)
    assert trace == ["strip", "strip"]


def test_domain_double_strip_and_lazy_payload_get_order():
    trace = []

    class Domain(str):
        def strip(self):
            trace.append("strip")
            return "PEER"

    class Payload(dict):
        def get(self, key, default=None):
            trace.append(("get", key))
            return super().get(key, default)

    assert match("domain", parsed=Payload(domain=Domain("Domain"))) == ("domain", "peer")
    assert trace == [("get", "domain"), "strip", "strip"]


def test_hostname_property_failure_is_not_hidden(monkeypatch):
    class Parsed:
        @property
        def hostname(self):
            raise RuntimeError("hostname unavailable")

    monkeypatch.setattr(tracking, "urlparse", lambda _url: Parsed())
    with pytest.raises(RuntimeError, match="hostname unavailable"):
        match("domain", parsed={"url": "https://example.com"})
