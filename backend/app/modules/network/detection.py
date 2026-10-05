from __future__ import annotations

import re
from typing import Any

VPN_PROVIDER_KEYWORDS = (
    "nordvpn",
    "surfshark",
    "expressvpn",
    "protonvpn",
    "mullvad",
    "privateinternetaccess",
    "pia vpn",
    "ipvanish",
    "cyberghost",
    "tunnelbear",
    "windscribe",
    "hotspotshield",
    "urbanvpn",
    "browsec",
    "hola",
    "psiphon",
    "ultrasurf",
    "warp",
    "1.1.1.1 warp",
    "opera vpn",
)

PROXY_KEYWORDS = (
    "proxy",
    "proxysite",
    "croxyproxy",
    "kproxy",
    "webproxy",
    "anonymizer",
    "whoer",
    "hidemyass",
    "hide.me",
)

TOR_KEYWORDS = (
    "torproject",
    "tor exit",
    "tor relay",
    "obfs4",
    "snowflake",
    "onion",
)

ENCRYPTED_DNS_KEYWORDS = (
    "dns.google",
    "cloudflare-dns.com",
    "mozilla.cloudflare-dns.com",
    "quad9.net",
    "dns.quad9.net",
    "nextdns.io",
    "doh.opendns.com",
    "dns-family.adguard.com",
)

SUSPICIOUS_PORTS = {
    "1194": "vpn_port",
    "1701": "vpn_port",
    "1723": "vpn_port",
    "500": "vpn_port",
    "4500": "vpn_port",
    "51820": "wireguard_port",
    "853": "encrypted_dns",
}

CATEGORY_TAGS = {
    "vpn": "vpn_suspected",
    "proxy": "proxy_suspected",
    "tor": "tor_suspected",
    "encrypted_dns": "encrypted_dns",
}


def default_watchlist_items() -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for keyword in VPN_PROVIDER_KEYWORDS:
        items.append({"category": "vpn", "rule_mode": "detect", "match_type": "keyword", "pattern": keyword, "label": keyword})
    for keyword in PROXY_KEYWORDS:
        items.append({"category": "proxy", "rule_mode": "detect", "match_type": "keyword", "pattern": keyword, "label": keyword})
    for keyword in TOR_KEYWORDS:
        items.append({"category": "tor", "rule_mode": "detect", "match_type": "keyword", "pattern": keyword, "label": keyword})
    for keyword in ENCRYPTED_DNS_KEYWORDS:
        items.append({"category": "encrypted_dns", "rule_mode": "detect", "match_type": "keyword", "pattern": keyword, "label": keyword})
    return items


def _normalized_event_field(parsed: dict[str, Any], field: str) -> str:
    return str(parsed.get(field) or "").lower()


def _domain_matches(pattern: str, haystack: str, parsed: dict[str, Any]) -> bool:
    domain = _normalized_event_field(parsed, "domain")
    return domain == pattern or domain.endswith(f".{pattern}")


WATCHLIST_MATCHERS = {
    "keyword": lambda pattern, haystack, parsed: pattern in haystack,
    "domain": _domain_matches,
    "url": lambda pattern, haystack, parsed: pattern in _normalized_event_field(parsed, "url"),
    "ip": lambda pattern, haystack, parsed: pattern in {
        _normalized_event_field(parsed, "src_ip"),
        _normalized_event_field(parsed, "dst_ip"),
    },
}


def _watchlist_matches(
    match_type: str,
    pattern: str,
    haystack: str,
    parsed: dict[str, Any],
) -> bool:
    matcher = WATCHLIST_MATCHERS.get(match_type)
    return matcher(pattern, haystack, parsed) if matcher else False


def _watchlist_detection(
    haystack: str,
    parsed: dict[str, Any],
    entries: list[tuple[str, str, str, str]],
) -> tuple[list[str], set[str]]:
    tags: list[str] = []
    allowed_tags: set[str] = set()
    for category, rule_mode, match_type, pattern in entries:
        normalized_pattern = pattern.strip().lower()
        if not normalized_pattern:
            continue
        if not _watchlist_matches(match_type, normalized_pattern, haystack, parsed):
            continue
        tag = CATEGORY_TAGS.get(category)
        if not tag:
            continue
        if rule_mode == "allow":
            allowed_tags.add(tag)
        elif tag not in tags:
            tags.append(tag)
    return tags, allowed_tags


def _port_detection_tag(parsed: dict[str, Any]) -> str | None:
    dst_port = parsed.get("dst_port") or parsed.get("destination_port") or parsed.get("server_port")
    if not isinstance(dst_port, str):
        return None
    normalized_port = re.sub(r"[^0-9]", "", dst_port)
    return SUSPICIOUS_PORTS.get(normalized_port)


def _append_port_detection(tags: list[str], parsed: dict[str, Any]) -> None:
    port_tag = _port_detection_tag(parsed)
    if not port_tag or port_tag in tags:
        return
    tags.append(port_tag)
    if port_tag in {"vpn_port", "wireguard_port"} and "vpn_suspected" not in tags:
        tags.append("vpn_suspected")


def event_detection_tags(
    event_type: str,
    message: str | None,
    protocol: str | None,
    parsed: dict[str, Any],
    *,
    watchlist_entries: list[tuple[str, str, str, str]] | None = None,
) -> list[str]:
    text_parts = [
        event_type,
        message,
        protocol,
        parsed.get("domain"),
        parsed.get("url"),
        parsed.get("app_name"),
        parsed.get("application"),
        parsed.get("category"),
        parsed.get("message"),
        parsed.get("dst_domain"),
        parsed.get("hostname"),
    ]
    haystack = " ".join(str(part).lower() for part in text_parts if isinstance(part, str) and part.strip())
    tags, allowed_tags = _watchlist_detection(haystack, parsed, watchlist_entries or [])
    _append_port_detection(tags, parsed)
    return [tag for tag in tags if tag not in allowed_tags]
