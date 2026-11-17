"""WHOIS response boundaries, CIDR derivation and RDAP field read order."""

import io
import json
import urllib.error
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.modules.network.router.helpers import devices


def _lookup(monkeypatch, payload, address="8.8.8.8"):
    trace = []

    class Response(io.StringIO):
        def __enter__(self):
            trace.append("enter")
            return super().__enter__()

        def __exit__(self, *args):
            trace.append("exit")
            return super().__exit__(*args)

    def open_url(url, *, timeout):
        trace.append((url, timeout))
        return Response(json.dumps(payload))

    monkeypatch.setattr(devices.urllib.request, "urlopen", open_url)
    response = devices._summarize_ip_whois(address)
    assert trace == [(f"https://rdap.org/ip/{response.ip_address}", 4), "enter", "exit"]
    return response.model_dump()


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        ("8.8.8.0", "8.8.8.255", ["8.8.8.0/24"]),
        ("8.8.8.1", "8.8.8.3", ["8.8.8.1/32", "8.8.8.2/31"]),
        ("8.8.8.8", "8.8.8.8", ["8.8.8.8/32"]),
        ("8.8.8.9", "8.8.8.1", []),
        ("bad", "8.8.8.8", []),
        ("8.8.8.8", "bad", []),
        ("", "", []),
        (None, "8.8.8.8", []),
        ("8.8.8.8", None, []),
        (123, "8.8.8.8", []),
        ("8.8.8.8", [], []),
        ("2001:4860::", "2001:4860::3", ["2001:4860::/126"]),
    ],
)
def test_range_is_summarized_in_order_or_kept_empty(monkeypatch, start, end, expected):
    payload = {"startAddress": start, "endAddress": end}
    result = _lookup(monkeypatch, payload)
    assert result["cidr"] == expected
    assert result["start_address"] == (start if isinstance(start, str) else None)
    assert result["end_address"] == (end if isinstance(end, str) else None)
    assert result["raw"] == payload
    assert result["rdap_status"] == "ok"


def test_mixed_ipv4_ipv6_range_error_is_not_caught_as_a_network_failure(monkeypatch):
    with pytest.raises(TypeError, match="same version"):
        _lookup(monkeypatch, {"startAddress": "8.8.8.8", "endAddress": "2001:4860::1"})


@pytest.mark.parametrize("value", [None, 0, False, [], {}, "", "  spaced  ", "Caffè"])
def test_optional_fields_accept_only_strings_without_new_trimming(monkeypatch, value):
    result = _lookup(monkeypatch, {"name": value, "handle": value, "country": value})
    expected = value if isinstance(value, str) else None
    assert result["network_name"] == result["handle"] == result["country"] == expected
    assert result["label"] is None
    assert result["entities"] == []


def test_ipv6_is_canonicalized_and_first_entity_names_are_stably_deduplicated(monkeypatch):
    payload = {
        "entities": [
            {"vcardArray": ["vcard", [["org", {}, "text", name]]]} for name in (" B ", "A", "B")
        ],
        "name": " Network ",
        "handle": "Handle",
        "country": "IT",
    }
    result = _lookup(monkeypatch, payload, "2001:4860:4860:0:0:0:0:8888")
    assert result["ip_address"] == "2001:4860:4860::8888"
    assert result["entities"] == ["B", "A"]
    assert result["label"] == "B"
    assert result["network_name"] == " Network "


@pytest.mark.parametrize("payload", [None, [], "text", 123])
def test_valid_json_of_the_wrong_shape_still_propagates_an_attribute_error(monkeypatch, payload):
    with pytest.raises(AttributeError):
        _lookup(monkeypatch, payload)


@pytest.mark.parametrize(
    "error",
    [urllib.error.URLError("offline"), TimeoutError("timeout"), ValueError("bad"), OSError("io")],
)
def test_transport_errors_keep_the_public_unavailable_response(monkeypatch, error):
    open_url = Mock(side_effect=error)
    monkeypatch.setattr(devices.urllib.request, "urlopen", open_url)
    result = devices._summarize_ip_whois("8.8.8.8")
    assert result.rdap_status == "unavailable"
    assert result.scope == "IP pubblico"
    assert result.external_url == "https://rdap.org/ip/8.8.8.8"
    assert result.raw is None
    open_url.assert_called_once_with("https://rdap.org/ip/8.8.8.8", timeout=4)


def test_invalid_json_closes_the_response_and_becomes_unavailable(monkeypatch):
    stream = io.StringIO("not json")
    monkeypatch.setattr(devices.urllib.request, "urlopen", lambda *_args, **_kwargs: stream)
    assert devices._summarize_ip_whois("8.8.8.8").rdap_status == "unavailable"
    assert stream.closed


@pytest.mark.parametrize(
    ("flags", "expected_scope"),
    [
        ((True, True, True), "IP privato"),
        ((False, True, True), "Loopback locale"),
        ((False, False, True), "Link-local"),
    ],
)
def test_local_scope_precedence_avoids_remote_lookup(monkeypatch, flags, expected_scope):
    parsed = SimpleNamespace(is_private=flags[0], is_loopback=flags[1], is_link_local=flags[2])
    monkeypatch.setattr(devices.ipaddress, "ip_address", lambda _address: parsed)
    remote = Mock(side_effect=AssertionError("unexpected remote lookup"))
    monkeypatch.setattr(devices.urllib.request, "urlopen", remote)
    assert devices._summarize_ip_whois("local").scope == expected_scope
    remote.assert_not_called()


def test_payload_read_order_and_repeated_gets_remain_observable(monkeypatch):
    reads = []
    values = {
        "name": iter(["check", "Network"]),
        "handle": iter([None]),
        "country": iter(["check", "IT"]),
    }

    class Payload(dict):
        def get(self, key, default=None):
            reads.append(key)
            return next(values[key]) if key in values else default

    payload = Payload()
    monkeypatch.setattr(devices.json, "load", lambda _response: payload)
    monkeypatch.setattr(devices.urllib.request, "urlopen", lambda *_args, **_kwargs: io.StringIO())
    result = devices._summarize_ip_whois("8.8.8.8")
    assert result.network_name == "Network"
    assert result.handle is None
    assert result.country == "IT"
    assert reads == [
        "startAddress",
        "endAddress",
        "entities",
        "name",
        "name",
        "handle",
        "country",
        "country",
    ]


def test_payload_field_error_after_json_load_is_not_swallowed(monkeypatch):
    class Payload(dict):
        def get(self, key, default=None):
            if key == "name":
                raise ValueError("invalid name access")
            return default

    monkeypatch.setattr(devices.json, "load", lambda _response: Payload())
    monkeypatch.setattr(devices.urllib.request, "urlopen", lambda *_args, **_kwargs: io.StringIO())
    with pytest.raises(ValueError, match="invalid name access"):
        devices._summarize_ip_whois("8.8.8.8")
