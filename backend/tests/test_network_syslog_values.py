"""Syslog field decoding and remaining full-file Sophos contracts."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.db.base import Base
from app.modules.network import sophos
from app.modules.network.models import NetworkFirewall


@pytest.mark.parametrize(
    "message,expected",
    [
        ("", {}),
        ("no fields", {}),
        ("a=plain b=second", {"a": "plain", "b": "second"}),
        ("a=\"two words\" b='single quotes'", {"a": "two words", "b": "single quotes"}),
        ("a=\"\" b=''", {"a": "", "b": ""}),
        ('a="  padded  "', {"a": "  padded  "}),
        ('a="first" b=keep a="last"', {"a": "last", "b": "keep"}),
        ('a="unterminated', {"a": '"unterminated'}),
        ('a="trailing' + "\\" + '"', {"a": "trailing\\"}),
        (
            "src_ip=10.0.0.1 url=https://example/?a=b",
            {"src_ip": "10.0.0.1", "url": "https://example/?a=b"},
        ),
    ],
)
def test_real_log_field_decoding(message, expected):
    actual = sophos.parse_sophos_syslog_message(message)
    assert actual == expected
    assert list(actual) == list(expected)


@pytest.mark.parametrize("raw", ["", "plain", "\"mismatch'", '"', "'"])
def test_quote_detection_uses_exact_slices(monkeypatch, raw):
    monkeypatch.setattr(
        sophos, "_KV_PATTERN", SimpleNamespace(findall=lambda message: [("key", raw)])
    )
    split = MagicMock(return_value=["decoded"])
    monkeypatch.setattr(sophos.shlex, "split", split)
    quoted = raw[:1] in {'"', "'"} and raw[-1:] == raw[:1]
    assert sophos.parse_sophos_syslog_message("ignored") == {"key": "decoded" if quoted else raw}
    assert split.call_count == int(quoted)


@pytest.mark.parametrize("error", [ValueError("bad"), IndexError("empty"), RuntimeError("other")])
def test_only_value_error_falls_back_and_other_errors_stop_later_fields(monkeypatch, error):
    monkeypatch.setattr(
        sophos,
        "_KV_PATTERN",
        SimpleNamespace(findall=lambda message: [("a", '"bad"'), ("b", '"later"')]),
    )
    split = MagicMock(side_effect=error)
    monkeypatch.setattr(sophos.shlex, "split", split)
    if isinstance(error, ValueError):
        assert sophos.parse_sophos_syslog_message("ignored") == {"a": "bad", "b": "later"}
        assert split.call_count == 2
    else:
        with pytest.raises(type(error), match=str(error)):
            sophos.parse_sophos_syslog_message("ignored")
        assert split.call_args_list == [(('"bad"',), {})]


def test_utility_empty_and_invalid_values():
    assert sophos._safe_text(None) is None
    assert sophos._coerce_utc(None) is None
    assert sophos._json_dumps(None) is None
    assert sophos._json_loads(None) == {}
    assert sophos._json_loads("broken") == {}
    assert sophos._json_loads("[]") == {}
    assert sophos.strip_syslog_prefix("  ") == ("", None)
    assert sophos.strip_syslog_prefix("host body") == ("body", "host")
    assert sophos.strip_syslog_prefix("single") == ("single", None)
    assert sophos._normalize_severity("Alert") == "critical"
    assert sophos._normalize_severity("Warn") == "warning"
    db = MagicMock()
    assert sophos._find_network_device(db, src_ip=None, dst_ip=None) is None
    db.scalar.assert_not_called()


def test_firewall_serial_matching_and_empty_metadata_retention():
    assert NetworkFirewall.metadata is Base.metadata
    db = MagicMock()
    db.scalar.return_value = None
    when = datetime.now(UTC)
    fw = sophos.upsert_network_firewall(
        db, vendor="Sophos", name="one", serial_number="serial", seen_at=when
    )
    assert fw.serial_number == "serial" and fw.last_seen_at == when
    db.scalar.return_value = fw
    fw.metadata_sources = None
    assert sophos.upsert_network_firewall(db, vendor="Sophos", name="", seen_at=when) is fw
    assert fw.name == "one" and fw.metadata_sources is None


def test_ingestion_keeps_existing_alert_and_ignores_unclassified_history(monkeypatch):
    db = MagicMock()
    fw = NetworkFirewall(id=4, vendor="Sophos", name="one")
    db.get.return_value = fw
    db.scalar.return_value = object()
    recent = SimpleNamespace(
        raw_payload='{"parsed": {}}', event_type="other", message="other", protocol=None
    )
    db.scalars.return_value.all.return_value = [recent]
    monkeypatch.setattr(sophos, "_active_watchlist_entries", lambda db: [])
    monkeypatch.setattr(sophos, "_find_network_device", lambda *args, **kwargs: None)
    tags = MagicMock(side_effect=[["vpn_suspected"], []])
    monkeypatch.setattr(sophos, "event_detection_tags", tags)
    event = sophos.ingest_sophos_syslog(
        db, message="log_type=Firewall priority=critical message=test", firewall_id=4
    )
    assert event.severity == "critical" and tags.call_count == 2
    assert [type(call.args[0]).__name__ for call in db.add.call_args_list] == [
        "NetworkFirewallEvent",
        "NetworkFirewall",
    ]
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(event)


def test_filtered_event_query_keeps_severity_and_limit():
    db = MagicMock()
    expected = [object()]
    db.scalars.return_value.all.return_value = expected
    assert (
        sophos.list_network_firewall_events(db, firewall_id=7, severity="critical", limit=3)
        is expected
    )
    sql = str(db.scalars.call_args.args[0].compile(compile_kwargs={"literal_binds": True}))
    assert "severity = 'critical'" in sql and "LIMIT 3" in sql
