from __future__ import annotations

import pytest

from app.modules.network.detection import (
    ENCRYPTED_DNS_KEYWORDS,
    PROXY_KEYWORDS,
    TOR_KEYWORDS,
    VPN_PROVIDER_KEYWORDS,
    default_watchlist_items,
    event_detection_tags,
)


def test_default_watchlist_order_and_independent_results():
    expected = [
        {
            "category": category,
            "rule_mode": "detect",
            "match_type": "keyword",
            "pattern": keyword,
            "label": keyword,
        }
        for category, keywords in (
            ("vpn", VPN_PROVIDER_KEYWORDS),
            ("proxy", PROXY_KEYWORDS),
            ("tor", TOR_KEYWORDS),
            ("encrypted_dns", ENCRYPTED_DNS_KEYWORDS),
        )
        for keyword in keywords
    ]
    first = default_watchlist_items()
    assert first == expected
    first[0]["pattern"] = "modified"
    first.clear()
    assert default_watchlist_items() == expected


@pytest.mark.parametrize("watchlist", [None, []])
def test_no_implicit_keyword_detection(watchlist):
    assert (
        event_detection_tags(
            "nordvpn proxy onion dns.google", None, None, {}, watchlist_entries=watchlist
        )
        == []
    )


@pytest.mark.parametrize(
    "field",
    ["domain", "url", "app_name", "application", "category", "message", "dst_domain", "hostname"],
)
def test_keyword_detection_from_each_parsed_text_field(field):
    assert event_detection_tags(
        "",
        None,
        None,
        {field: "  NoRdVpN  "},
        watchlist_entries=[("vpn", "detect", "keyword", "NORDVPN")],
    ) == ["vpn_suspected"]


@pytest.mark.parametrize("position", range(3))
def test_keyword_detection_from_each_top_level_text(position):
    text = ["", None, None]
    text[position] = "  NoRdVpN  "
    assert event_detection_tags(
        *text, {}, watchlist_entries=[("vpn", "detect", "keyword", " nordvpn ")]
    ) == ["vpn_suspected"]


@pytest.mark.parametrize("value", [None, 0, False, [], {}, "", "   "])
def test_keyword_detection_ignores_non_text_or_blank_fields(value):
    assert (
        event_detection_tags(
            "",
            None,
            None,
            {"domain": value},
            watchlist_entries=[("vpn", "detect", "keyword", "vpn")],
        )
        == []
    )


@pytest.mark.parametrize(
    ("match_type", "pattern", "parsed", "matched"),
    [
        ("keyword", "", {"domain": "vpn"}, False),
        ("keyword", "   ", {"domain": "vpn"}, False),
        ("keyword", " vpn ", {"domain": "superVPNsite"}, True),
        ("keyword", "vpn", {"domain": "other"}, False),
        ("domain", "EXAMPLE.com", {"domain": "example.COM"}, True),
        ("domain", "example.com", {"domain": "sub.example.com"}, True),
        ("domain", "example.com", {"domain": "evilexample.com"}, False),
        ("domain", "example.com", {"domain": None}, False),
        ("domain", "12", {"domain": 12}, True),
        ("domain", "false", {"domain": False}, False),
        ("url", "VPN", {"url": "https://site/VPN?q=1"}, True),
        ("url", "vpn", {}, False),
        ("url", "0", {"url": 0}, False),
        ("ip", "1.2.3.4", {"src_ip": "1.2.3.4", "dst_ip": "5.6.7.8"}, True),
        ("ip", "ABCD::1", {"dst_ip": "abcd::1"}, True),
        ("ip", "1.2.3", {"src_ip": "1.2.3.4"}, False),
        ("ip", "0", {"src_ip": 0, "dst_ip": False}, False),
        ("unsupported", "vpn", {"domain": "vpn"}, False),
    ],
)
def test_watchlist_matching_contract(match_type, pattern, parsed, matched):
    initial = dict(parsed)
    result = event_detection_tags(
        "", None, None, parsed, watchlist_entries=[("vpn", "detect", match_type, pattern)]
    )
    assert result == (["vpn_suspected"] if matched else [])
    assert parsed == initial


@pytest.mark.parametrize(
    ("category", "expected"),
    [
        ("vpn", ["vpn_suspected"]),
        ("proxy", ["proxy_suspected"]),
        ("tor", ["tor_suspected"]),
        ("encrypted_dns", ["encrypted_dns"]),
        ("unknown", []),
    ],
)
def test_category_mapping(category, expected):
    assert (
        event_detection_tags(
            "match", None, None, {}, watchlist_entries=[(category, "detect", "keyword", "match")]
        )
        == expected
    )


@pytest.mark.parametrize("rule_mode", ["detect", "custom", ""])
def test_every_non_allow_mode_detects(rule_mode):
    assert event_detection_tags(
        "match", None, None, {}, watchlist_entries=[("vpn", rule_mode, "keyword", "match")]
    ) == ["vpn_suspected"]


@pytest.mark.parametrize("allow_first", [True, False])
def test_allow_filters_after_detection_and_port_tagging(allow_first):
    entries = [("vpn", "allow", "keyword", "match"), ("vpn", "detect", "keyword", "match")]
    if not allow_first:
        entries.reverse()
    assert event_detection_tags(
        "match", None, None, {"dst_port": "1194"}, watchlist_entries=entries
    ) == ["vpn_port"]


@pytest.mark.parametrize(
    ("port", "expected"),
    [
        ("1194", ["vpn_port", "vpn_suspected"]),
        ("1701", ["vpn_port", "vpn_suspected"]),
        ("1723", ["vpn_port", "vpn_suspected"]),
        ("500", ["vpn_port", "vpn_suspected"]),
        ("4500", ["vpn_port", "vpn_suspected"]),
        ("51820/udp", ["wireguard_port", "vpn_suspected"]),
        ("tcp/853", ["encrypted_dns"]),
        ("443", []),
        (1194, []),
        (None, []),
    ],
)
def test_port_detection_and_normalization(port, expected):
    assert event_detection_tags("", None, None, {"dst_port": port}) == expected


@pytest.mark.parametrize(
    ("parsed", "expected"),
    [
        ({"dst_port": "unknown", "destination_port": "1194"}, []),
        ({"dst_port": 0, "destination_port": "1194"}, ["vpn_port", "vpn_suspected"]),
        ({"destination_port": "", "server_port": "tcp/853"}, ["encrypted_dns"]),
        ({"dst_port": "853", "destination_port": "1194"}, ["encrypted_dns"]),
    ],
)
def test_port_source_precedence(parsed, expected):
    assert event_detection_tags("", None, None, parsed) == expected


def test_tag_order_deduplication_and_encrypted_dns_port():
    entries = [
        (category, "detect", "keyword", "match")
        for category in ("proxy", "vpn", "proxy", "encrypted_dns", "tor")
    ]
    assert event_detection_tags(
        "match", None, None, {"dst_port": "853"}, watchlist_entries=entries
    ) == ["proxy_suspected", "vpn_suspected", "encrypted_dns", "tor_suspected"]
    assert event_detection_tags(
        "match", None, None, {"dst_port": "51820"}, watchlist_entries=entries
    ) == ["proxy_suspected", "vpn_suspected", "encrypted_dns", "tor_suspected", "wireguard_port"]
