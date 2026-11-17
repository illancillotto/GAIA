"""Domain, URL and address precedence for firewall peer hints."""

import json
from types import SimpleNamespace

import pytest

from app.modules.network.router.helpers import tracking, traffic


@pytest.fixture
def peer_hint(monkeypatch):
    calls = []

    def resolve(address):
        calls.append(address)
        return "Resolved"

    monkeypatch.setattr(traffic, "_resolve_peer_label", resolve)
    return calls


@pytest.mark.parametrize(
    "raw_payload",
    [
        None,
        "",
        "bad",
        "null",
        "[]",
        "1",
        "{}",
        '{"parsed":null}',
        '{"parsed":[]}',
        '{"parsed":"bad"}',
        '{"parsed":{}}',
    ],
)
def test_invalid_or_empty_payloads_fall_back_to_address(peer_hint, raw_payload):
    assert (
        traffic._extract_peer_hint(SimpleNamespace(raw_payload=raw_payload), peer_ip="8.8.8.8")
        == "Resolved"
    )
    assert peer_hint == ["8.8.8.8"]


@pytest.mark.parametrize(
    "parsed, expected, calls",
    [
        ({"domain": " Domain.Example. ", "url": "https://url.example"}, "Domain.Example.", []),
        ({"domain": "arbitrary/path", "url": "https://[bad"}, "arbitrary/path", []),
        ({"domain": 3, "url": "https://URL.example/path"}, "url.example", []),
        ({"domain": " ", "url": " https://url.example/path "}, "url.example", []),
        ({"domain": None, "url": "//url.example/path"}, "url.example", []),
        ({"url": "https://user:pass@URL.example:bad/path"}, "url.example", []),
        ({"url": "https://[2001:4860::1]/path"}, "2001:4860::1", []),
        ({"url": "relative/path"}, "Resolved", ["8.8.8.8"]),
        ({"url": "https:///path"}, "Resolved", ["8.8.8.8"]),
        ({"url": " "}, "Resolved", ["8.8.8.8"]),
        ({"url": []}, "Resolved", ["8.8.8.8"]),
        ({"url": 3}, "Resolved", ["8.8.8.8"]),
    ],
)
def test_domain_then_url_then_address_precedence(peer_hint, parsed, expected, calls):
    event = SimpleNamespace(raw_payload=json.dumps({"parsed": parsed}))
    assert traffic._extract_peer_hint(event, peer_ip="8.8.8.8") == expected
    assert peer_hint == calls


@pytest.mark.parametrize("address", [None, "", 0, False])
def test_falsy_peer_address_does_not_invoke_the_resolver(peer_hint, address):
    assert traffic._extract_peer_hint(SimpleNamespace(raw_payload="{}"), peer_ip=address) is None
    assert peer_hint == []


@pytest.mark.parametrize(
    "url", ["https://[bad", "https://[not-an-ip]/", "https://example\uff0f.test"]
)
def test_invalid_url_errors_propagate_without_address_fallback(peer_hint, url):
    event = SimpleNamespace(raw_payload=json.dumps({"parsed": {"url": url}}))
    with pytest.raises(ValueError):
        traffic._extract_peer_hint(event, peer_ip="8.8.8.8")
    assert peer_hint == []


def install_payload(monkeypatch, payload):
    # Both callers use the same production metadata parser; substitute it at
    # either binding so these contracts also run against the frozen original.
    monkeypatch.setattr(traffic, "metadata_sources_to_dict", lambda _raw: payload)
    monkeypatch.setattr(tracking, "metadata_sources_to_dict", lambda _raw: payload)


@pytest.mark.parametrize("second", ["", None, 0])
def test_second_domain_strip_result_returns_immediately_even_if_falsy(
    monkeypatch, peer_hint, second
):
    trace = []

    class Domain(str):
        def strip(self):
            trace.append("strip")
            return "first" if len(trace) == 1 else second

    install_payload(
        monkeypatch, {"parsed": {"domain": Domain("Domain"), "url": "https://url.example"}}
    )
    assert (
        traffic._extract_peer_hint(SimpleNamespace(raw_payload="raw"), peer_ip="8.8.8.8") is second
    )
    assert trace == ["strip", "strip"]
    assert peer_hint == []


def test_payload_gets_and_strip_calls_stay_lazy_and_in_order(monkeypatch, peer_hint):
    trace = []

    class Payload(dict):
        def get(self, key, default=None):
            trace.append(("get", key))
            return super().get(key, default)

    class Domain(str):
        def strip(self):
            trace.append(("strip",))
            return "Domain"

    install_payload(monkeypatch, Payload(parsed=Payload(domain=Domain("Domain"))))
    assert (
        traffic._extract_peer_hint(SimpleNamespace(raw_payload="raw"), peer_ip="8.8.8.8")
        == "Domain"
    )
    assert trace == [("get", "parsed"), ("get", "domain"), ("strip",), ("strip",)]
    assert peer_hint == []


def test_url_is_stripped_twice_and_hostname_is_read_once(monkeypatch, peer_hint):
    trace = []

    class Url(str):
        def strip(self):
            trace.append("strip")
            return (
                "https://first.example" if trace.count("strip") == 1 else "https://second.example"
            )

    class ParsedUrl:
        @property
        def hostname(self):
            trace.append("hostname")
            return "second.example"

    def parse(value):
        trace.append(("parse", value))
        return ParsedUrl()

    install_payload(monkeypatch, {"parsed": {"url": Url("URL")}})
    monkeypatch.setattr(traffic, "urlparse", parse)
    assert (
        traffic._extract_peer_hint(SimpleNamespace(raw_payload="raw"), peer_ip="8.8.8.8")
        == "second.example"
    )
    assert trace == ["strip", "strip", ("parse", "https://second.example"), "hostname"]
    assert peer_hint == []


def test_hostname_access_error_is_not_hidden_by_ip_fallback(monkeypatch, peer_hint):
    class ParsedUrl:
        @property
        def hostname(self):
            raise RuntimeError("hostname unavailable")

    monkeypatch.setattr(traffic, "urlparse", lambda _url: ParsedUrl())
    event = SimpleNamespace(raw_payload='{"parsed":{"url":"https://url.example"}}')
    with pytest.raises(RuntimeError, match="hostname unavailable"):
        traffic._extract_peer_hint(event, peer_ip="8.8.8.8")
    assert peer_hint == []
