"""Peer DNS/RDAP precedence, lazy payload reads, failures and LRU contracts."""

from types import SimpleNamespace
from urllib.error import URLError

import pytest

from app.modules.network.router.helpers import traffic


@pytest.fixture(autouse=True)
def clear_peer_cache():
    traffic._resolve_peer_label.cache_clear()
    yield
    traffic._resolve_peer_label.cache_clear()


@pytest.fixture
def peer(monkeypatch):
    state = SimpleNamespace(
        payload={},
        hostname=None,
        dns_error=OSError("no DNS"),
        open_error=None,
        json_error=None,
        trace=[],
    )

    def dns(address):
        state.trace.append(("dns", address))
        if state.dns_error is not None:
            raise state.dns_error
        return state.hostname, [], []

    class Response:
        def __enter__(self):
            state.trace.append(("enter",))
            return self

        def __exit__(self, *args):
            state.trace.append(("exit", args[0]))

    def open_url(url, *, timeout):
        state.trace.append(("urlopen", url, timeout))
        if state.open_error is not None:
            raise state.open_error
        return Response()

    def read_json(response):
        assert isinstance(response, Response)
        state.trace.append(("json",))
        if state.json_error is not None:
            raise state.json_error
        return state.payload

    monkeypatch.setattr(traffic.socket, "gethostbyaddr", dns)
    monkeypatch.setattr(traffic.urllib.request, "urlopen", open_url)
    monkeypatch.setattr(traffic.json, "load", read_json)
    return state


def entity(*items):
    return {"vcardArray": ["vcard", list(items)]}


@pytest.mark.parametrize("address", [None, "", "bad", " 8.8.8.8 "])
def test_empty_or_invalid_address_avoids_dns_and_rdap(peer, address):
    assert traffic._resolve_peer_label(address) is None
    assert peer.trace == []


@pytest.mark.parametrize("address", ["10.0.0.1", "127.0.0.1", "169.254.1.1", "224.0.0.1"])
def test_dns_has_precedence_even_for_addresses_excluded_from_rdap(peer, address):
    peer.dns_error = None
    peer.hostname = " resolved.example. "
    assert traffic._resolve_peer_label(address) == "resolved.example"
    assert peer.trace == [("dns", address)]


@pytest.mark.parametrize("hostname", ["", " ", ".", " . "])
def test_empty_dns_result_falls_back_to_rdap_for_public_addresses(peer, hostname):
    peer.dns_error = None
    peer.hostname = hostname
    peer.payload = {"name": " Network "}
    assert traffic._resolve_peer_label("8.8.8.8") == "Network"
    assert peer.trace == [
        ("dns", "8.8.8.8"),
        ("urlopen", "https://rdap.org/ip/8.8.8.8", 4),
        ("enter",),
        ("json",),
        ("exit", None),
    ]


@pytest.mark.parametrize("address", ["10.0.0.1", "127.0.0.1", "169.254.1.1", "224.0.0.1"])
def test_dns_failure_on_nonpublic_addresses_does_not_request_rdap(peer, address):
    assert traffic._resolve_peer_label(address) is None
    assert peer.trace == [("dns", address)]


@pytest.mark.parametrize(
    "payload, expected",
    [
        ({"entities": None}, None),
        ({"entities": {}}, None),
        ({"entities": [None, {}, {"vcardArray": []}]}, None),
        ({"entities": [{"vcardArray": ["vcard", {}]}]}, None),
        ({"entities": [{"vcardArray": ("vcard", [])}]}, None),
        ({"entities": [entity(None, [], ["fn"], ["fn", {}, "text", 3])]}, None),
        ({"entities": [entity(["fn", {}, "text", " "])]}, None),
        ({"entities": [entity(["org", {}, "text", "Org"])], "name": "Name"}, "Name"),
        ({"name": " Name ", "handle": "Handle"}, "Name"),
        ({"name": " ", "handle": " Handle "}, "Handle"),
        ({"name": 3, "handle": " Handle "}, "Handle"),
        ({"name": [], "handle": {}}, None),
        (
            {
                "entities": [entity(["fn", {}, "text", "First"], ["fn", {}, "text", "Second"])],
                "name": "Name",
            },
            "First",
        ),
        (
            {
                "entities": [
                    entity(["fn", {}, "text", "First"]),
                    entity(["fn", {}, "text", "Second"]),
                ]
            },
            "First",
        ),
        ({"entities": [entity(["org", {}, "text", "Org"], ["fn", {}, "text", " Fn "])]}, "Fn"),
    ],
)
def test_first_fn_then_name_then_handle_with_malformed_vcards(peer, payload, expected):
    peer.payload = payload
    assert traffic._resolve_peer_label("8.8.8.8") == expected


@pytest.mark.parametrize(
    "error", [URLError("offline"), TimeoutError("timeout"), ValueError("bad"), OSError("offline")]
)
@pytest.mark.parametrize("stage", ["open_error", "json_error"])
def test_network_and_json_failures_return_none_and_are_cached(peer, stage, error):
    setattr(peer, stage, error)
    assert traffic._resolve_peer_label("8.8.8.8") is None
    calls = list(peer.trace)
    assert traffic._resolve_peer_label("8.8.8.8") is None
    assert peer.trace == calls
    assert traffic._resolve_peer_label.cache_info().hits == 1


@pytest.mark.parametrize("payload", [None, [], 3, "unexpected"])
def test_unexpected_json_shape_raises_after_context_exit_and_is_not_cached(peer, payload):
    peer.payload = payload
    for _ in range(2):
        with pytest.raises(AttributeError, match="has no attribute 'get'"):
            traffic._resolve_peer_label("8.8.8.8")
        assert peer.trace[-1] == ("exit", None)
    assert traffic._resolve_peer_label.cache_info().currsize == 0


def test_payload_access_error_is_outside_the_network_error_handler(peer):
    class Payload(dict):
        def get(self, key, default=None):
            raise OSError("payload access failed")

    peer.payload = Payload()
    with pytest.raises(OSError, match="payload access failed"):
        traffic._resolve_peer_label("8.8.8.8")
    assert peer.trace[-1] == ("exit", None)


@pytest.mark.parametrize("second_result", ["", None, 0])
def test_second_fn_strip_result_is_returned_even_if_falsy(peer, second_result):
    reads = []

    class Name(str):
        def strip(self):
            reads.append("strip")
            return "first" if len(reads) == 1 else second_result

    peer.payload = {
        "entities": [entity(["fn", {}, "text", Name("Name")]), entity(["fn", {}, "text", "Later"])],
        "name": "Fallback",
    }
    assert traffic._resolve_peer_label("8.8.8.8") is second_result
    assert reads == ["strip", "strip"]


def test_lazy_payload_and_vcard_reads_stop_at_the_first_name(peer):
    trace = []

    class Payload(dict):
        def get(self, key, default=None):
            trace.append(("get", key))
            return super().get(key, default)

    class Item(list):
        def __getitem__(self, key):
            trace.append(("item", key))
            return super().__getitem__(key)

    class Name(str):
        def strip(self):
            trace.append(("strip",))
            return "Name"

    peer.payload = Payload(
        entities=[
            Payload(
                vcardArray=[
                    "vcard",
                    [
                        Item(["fn", {}, "text", Name("Name")]),
                    ],
                ]
            ),
            Payload(),
        ]
    )
    assert traffic._resolve_peer_label("8.8.8.8") == "Name"
    assert trace == [
        ("get", "entities"),
        ("get", "vcardArray"),
        ("item", 0),
        ("item", 3),
        ("item", 3),
        ("strip",),
        ("item", 3),
        ("strip",),
    ]


def test_cache_preserves_result_without_repeating_io(peer):
    peer.payload = {"name": "First"}
    assert traffic._resolve_peer_label("8.8.8.8") == "First"
    calls = list(peer.trace)
    peer.payload = {"name": "Changed"}
    assert traffic._resolve_peer_label("8.8.8.8") == "First"
    assert peer.trace == calls


def test_cache_keeps_512_entries_and_evicts_the_oldest(peer):
    peer.dns_error = None
    peer.hostname = "resolved.example"
    addresses = [f"8.8.{index // 256}.{index % 256}" for index in range(513)]
    for address in addresses:
        assert traffic._resolve_peer_label(address) == "resolved.example"
    assert len(peer.trace) == 513
    assert traffic._resolve_peer_label.cache_info().maxsize == 512
    assert traffic._resolve_peer_label.cache_info().currsize == 512
    assert traffic._resolve_peer_label(addresses[-1]) == "resolved.example"
    assert len(peer.trace) == 513
    assert traffic._resolve_peer_label(addresses[0]) == "resolved.example"
    assert len(peer.trace) == 514
