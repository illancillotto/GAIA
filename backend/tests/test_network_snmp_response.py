"""SNMP decoding preserves response timing, duplicates and lazy conversions."""

import asyncio
from types import SimpleNamespace

import pytest

from app.modules.network import sophos_snmp as snmp


def read(monkeypatch, oids, bindings, *, trace=None, indication=None, status=0, on_get=None):
    trace = [] if trace is None else trace

    async def create(address, **kwargs):
        trace.append(("create", address, kwargs))
        return "transport"

    async def get(*args):
        trace.append(("get", args))
        await asyncio.sleep(0)
        if on_get is not None:
            on_get()
        trace.append(("response",))
        return indication, status, 0, bindings

    def identity(oid):
        trace.append(("identity", oid))
        return oid

    monkeypatch.setattr(snmp, "UdpTransportTarget", SimpleNamespace(create=create))
    monkeypatch.setattr(snmp, "get_cmd", get)
    monkeypatch.setattr(snmp, "SnmpEngine", lambda: "engine")
    monkeypatch.setattr(snmp, "CommunityData", lambda value, **kwargs: (value, kwargs))
    monkeypatch.setattr(snmp, "ContextData", lambda: "context")
    monkeypatch.setattr(snmp, "ObjectIdentity", identity)
    monkeypatch.setattr(snmp, "ObjectType", lambda value: ("object", value))
    result = asyncio.run(snmp._snmp_get_values_async("host", 162, "community", oids))
    return result, trace


def test_duplicate_oids_and_bindings_keep_last_value_and_first_key_position(monkeypatch):
    result, _ = read(
        monkeypatch,
        [{"oid": "1", "key": "first"}, {"oid": "2", "key": "other"}, {"oid": "1", "key": "last"}],
        [("1", "old"), ("2", "second"), ("1", "new")],
    )
    assert list(result.items()) == [("last", "new"), ("other", "second")]


@pytest.mark.parametrize("key", [None, "", 0, False])
def test_unknown_and_falsey_keys_do_not_stringify_values(monkeypatch, key):
    class Unreadable:
        def __str__(self):
            raise AssertionError("unused value must remain unread")

    result, _ = read(
        monkeypatch,
        [{"oid": "1", "key": key}],
        [("unknown", Unreadable()), ("1", Unreadable())],
    )
    assert result == {}


def test_name_and_value_are_stringified_in_order_without_stripping(monkeypatch):
    trace = []

    class Text:
        def __init__(self, role, value):
            self.role, self.value = role, value

        def __str__(self):
            trace.append(self.role)
            return self.value

    result, _ = read(
        monkeypatch,
        [{"oid": "1", "key": "metric"}],
        [
            (Text("unknown-name", " 1"), Text("unread", "unused")),
            (Text("name", "1"), Text("value", " 42 ")),
        ],
    )
    assert result == {"metric": " 42 "}
    assert trace == ["unknown-name", "name", "value"]


def test_oid_map_reads_current_definitions_after_awaiting_response(monkeypatch):
    oids = [{"oid": "1", "key": "before"}]

    def mutate():
        oids[0]["key"] = "after"
        oids.append({"oid": "2", "key": "new"})

    result, trace = read(monkeypatch, oids, [("1", "one"), ("2", "two")], on_get=mutate)
    assert result == {"after": "one", "new": "two"}
    assert [entry for entry in trace if entry[0] == "identity"] == [("identity", "1")]
    request = next(entry[1] for entry in trace if entry[0] == "get")
    assert request[4:] == (("object", "1"),)


@pytest.mark.parametrize("indication,status", [("offline", 0), (None, 1)])
def test_error_response_does_not_read_oid_keys_or_bindings(monkeypatch, indication, status):
    class Definition(dict):
        def __getitem__(self, key):
            assert key != "key"
            return super().__getitem__(key)

    class Bindings:
        def __iter__(self):
            raise AssertionError("error response must not be decoded")

    result, _ = read(
        monkeypatch,
        [Definition(oid="1")],
        Bindings(),
        indication=indication,
        status=status,
    )
    assert result == {}


def test_truthy_error_indication_does_not_test_error_status(monkeypatch):
    class UnreadableStatus:
        def __bool__(self):
            raise AssertionError("indication short-circuits status")

    result, _ = read(monkeypatch, [], [], indication="offline", status=UnreadableStatus())
    assert result == {}


def test_empty_oid_list_still_executes_transport_and_get(monkeypatch):
    result, trace = read(monkeypatch, [], [("unknown", "unused")])
    assert result == {}
    assert trace[0] == ("create", ("host", 162), {"timeout": 3.0, "retries": 0})
    assert [entry[0] for entry in trace] == ["create", "get", "response"]


@pytest.mark.parametrize("where", ["name", "value", "oid_key", "binding"])
def test_decode_failures_propagate_after_response(monkeypatch, where):
    trace = []

    class BadText:
        def __str__(self):
            raise RuntimeError("decode failure")

    class Definition(dict):
        def __getitem__(self, key):
            if key == "key":
                raise RuntimeError("decode failure")
            return super().__getitem__(key)

    oids = [Definition(oid="1")] if where == "oid_key" else [{"oid": "1", "key": "metric"}]
    bindings = {
        "name": [(BadText(), "value")],
        "value": [("1", BadText())],
        "oid_key": [],
        "binding": [("1", "value", "extra")],
    }[where]
    error = ValueError if where == "binding" else RuntimeError
    with pytest.raises(error):
        read(monkeypatch, oids, bindings, trace=trace)
    assert trace[-1] == ("response",)
