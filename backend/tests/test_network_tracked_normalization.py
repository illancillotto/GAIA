"""Freeze tracked IP/domain/URL normalization and error boundaries."""

from ipaddress import IPv6Address

import pytest
from fastapi import HTTPException

from app.modules.network.router.helpers import tracking


@pytest.mark.parametrize(
    "kind, value, expected",
    [
        ("ip", " 192.168.1.1 ", "192.168.1.1"),
        ("ip", " 2001:4860:0000:0000:0000:0000:0000:8888 ", "2001:4860::8888"),
        # Python versions differ in how they render the mapped IPv4 suffix.
        ("ip", "::ffff:192.0.2.1", str(IPv6Address("::ffff:c000:201"))),
        ("ip", "::ffff:c000:201", str(IPv6Address("::ffff:192.0.2.1"))),
        ("ip", "fe80::1%eth0", "fe80::1%eth0"),
        ("domain", " Example.COM... ", "example.com"),
        ("domain", " HTTPS://User:pass@Example.COM:bad/path?q=1 ", "example.com"),
        ("domain", "https://[2001:4860::1]/path", "2001:4860::1"),
        ("domain", "https:///Some.Path", "https:///some.path"),
        ("domain", "https://", "https://"),
        ("domain", "//EXAMPLE.COM/path", "//example.com/path"),
        ("domain", "arbitrary/path", "arbitrary/path"),
        ("domain", "Foo:Bar", "foo:bar"),
        ("domain", " example.com. \t", "example.com"),
        ("domain", "ÄXAMPLE.COM", "äxample.com"),
        ("url", " HTTPS://Example.COM/path. ", "HTTPS://Example.COM/path."),
        ("url", "https://[malformed", "https://[malformed"),
        ("url", "arbitrary text", "arbitrary text"),
        ("other", " Value... ", "Value..."),
        ("IP", " Bad ", "Bad"),
        ("DOMAIN", " Example.COM. ", "Example.COM."),
        ("", " ", ""),
        (None, " Value ", "Value"),
    ],
)
def test_existing_normalization_rules(kind, value, expected):
    assert tracking._normalize_tracked_value(kind, value) == expected


@pytest.mark.parametrize(
    "kind, value, detail",
    [
        ("ip", "bad", "Invalid IP address: bad"),
        ("ip", " bad ", "Invalid IP address:  bad "),
        ("ip", "", "Invalid IP address: "),
        ("ip", "01.2.3.4", "Invalid IP address: 01.2.3.4"),
        ("domain", "", "Invalid domain value"),
        ("domain", " ", "Invalid domain value"),
        ("domain", "...", "Invalid domain value"),
        ("url", "", "Invalid URL value"),
        ("url", " \t", "Invalid URL value"),
    ],
)
def test_http_error_status_detail_and_ip_cause(kind, value, detail):
    with pytest.raises(HTTPException) as caught:
        tracking._normalize_tracked_value(kind, value)
    assert caught.value.status_code == 422
    assert caught.value.detail == detail
    assert isinstance(caught.value.__cause__, ValueError) is (kind == "ip")
    assert caught.value.headers is None


@pytest.mark.parametrize(
    "value", ["https://[bad", "https://[not-ip]/", "https://example\uff0f.test"]
)
def test_urlparse_value_errors_are_not_converted_to_http_errors(value):
    with pytest.raises(ValueError):
        tracking._normalize_tracked_value("domain", value)


@pytest.mark.parametrize("kind", ["ip", "domain", "url", "other"])
def test_initial_strip_error_propagates_before_type_dispatch(kind):
    class Value:
        def strip(self):
            raise RuntimeError("strip failed")

    with pytest.raises(RuntimeError, match="strip failed"):
        tracking._normalize_tracked_value(kind, Value())


@pytest.mark.parametrize("kind", ["ip", "domain", "url", "other"])
def test_none_input_keeps_attribute_error(kind):
    with pytest.raises(AttributeError, match="has no attribute 'strip'"):
        tracking._normalize_tracked_value(kind, None)


def test_domain_operations_and_hostname_read_order(monkeypatch):
    trace = []

    class Host(str):
        def strip(self):
            trace.append("host-strip")
            return self

        def rstrip(self, chars):
            trace.append(("rstrip", chars))
            return self

        def lower(self):
            trace.append("lower")
            return "normalized"

    class Parsed:
        @property
        def hostname(self):
            trace.append("hostname")
            return Host("Host")

    class Value(str):
        def strip(self):
            trace.append("initial-strip")
            return "https://Host/path"

    def parse(value):
        trace.append(("parse", value))
        return Parsed()

    monkeypatch.setattr(tracking, "urlparse", parse)
    assert tracking._normalize_tracked_value("domain", Value("URL")) == "normalized"
    assert trace == [
        "initial-strip",
        ("parse", "https://Host/path"),
        "hostname",
        "host-strip",
        ("rstrip", "."),
        "lower",
    ]


@pytest.mark.parametrize("hostname", [None, "", False])
def test_falsy_parsed_hostname_uses_original_normalized_text(monkeypatch, hostname):
    class Parsed:
        pass

    parsed = Parsed()
    parsed.hostname = hostname
    monkeypatch.setattr(tracking, "urlparse", lambda _value: parsed)
    assert (
        tracking._normalize_tracked_value("domain", " HTTPS://Original.Path... ")
        == "https://original.path"
    )


def test_hostname_property_error_propagates(monkeypatch):
    class Parsed:
        @property
        def hostname(self):
            raise RuntimeError("hostname failed")

    monkeypatch.setattr(tracking, "urlparse", lambda _value: Parsed())
    with pytest.raises(RuntimeError, match="hostname failed"):
        tracking._normalize_tracked_value("domain", "https://example.test")


def test_parser_is_not_called_without_scheme_separator(monkeypatch):
    def parse(_value):
        raise AssertionError("unexpected URL parsing")

    monkeypatch.setattr(tracking, "urlparse", parse)
    assert tracking._normalize_tracked_value("domain", " Example.COM. ") == "example.com"
    assert tracking._normalize_tracked_value("url", "https://[bad") == "https://[bad"


def test_non_value_error_from_ip_parser_propagates(monkeypatch):
    def parse(_value):
        raise TypeError("IP parser unavailable")

    monkeypatch.setattr(tracking.ipaddress, "ip_address", parse)
    with pytest.raises(TypeError, match="IP parser unavailable"):
        tracking._normalize_tracked_value("ip", "8.8.8.8")
