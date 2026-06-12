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
    tags: list[str] = []
    allowed_tags: set[str] = set()

    if watchlist_entries:
        for category, rule_mode, match_type, pattern in watchlist_entries:
            normalized_pattern = pattern.strip().lower()
            if not normalized_pattern:
                continue
            matched = False
            if match_type == "keyword":
                matched = normalized_pattern in haystack
            elif match_type == "domain":
                domain = str(parsed.get("domain") or "").lower()
                matched = domain == normalized_pattern or domain.endswith(f".{normalized_pattern}")
            elif match_type == "url":
                matched = normalized_pattern in str(parsed.get("url") or "").lower()
            elif match_type == "ip":
                matched = normalized_pattern in {str(parsed.get("src_ip") or "").lower(), str(parsed.get("dst_ip") or "").lower()}
            if matched:
                tag = {
                    "vpn": "vpn_suspected",
                    "proxy": "proxy_suspected",
                    "tor": "tor_suspected",
                    "encrypted_dns": "encrypted_dns",
                }.get(category)
                if tag:
                    if rule_mode == "allow":
                        allowed_tags.add(tag)
                    elif tag not in tags:
                        tags.append(tag)

    dst_port = parsed.get("dst_port") or parsed.get("destination_port") or parsed.get("server_port")
    if isinstance(dst_port, str):
        normalized_port = re.sub(r"[^0-9]", "", dst_port)
        port_tag = SUSPICIOUS_PORTS.get(normalized_port)
        if port_tag and port_tag not in tags:
            tags.append(port_tag)
            if port_tag in {"vpn_port", "wireguard_port"} and "vpn_suspected" not in tags:
                tags.append("vpn_suspected")
            if port_tag == "encrypted_dns" and "encrypted_dns" not in tags:
                tags.append("encrypted_dns")

    return [tag for tag in tags if tag not in allowed_tags]
