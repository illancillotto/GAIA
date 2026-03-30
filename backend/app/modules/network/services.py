from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import ipaddress
import json
from urllib.parse import quote
import re
import shutil
import socket
import subprocess
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.network.models import (
    DevicePosition,
    FloorPlan,
    NetworkAlert,
    NetworkDevice,
    NetworkScan,
    NetworkScanDevice,
)

try:
    import nmap  # type: ignore
except ImportError:  # pragma: no cover
    nmap = None

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None

try:
    import paramiko
except ImportError:  # pragma: no cover
    paramiko = None

try:
    from pysnmp.hlapi.v3arch.asyncio import (  # type: ignore
        CommunityData,
        ContextData,
        ObjectIdentity,
        ObjectType,
        SnmpEngine,
        UdpTransportTarget,
        get_cmd,
    )
except ImportError:  # pragma: no cover
    CommunityData = ContextData = ObjectIdentity = ObjectType = SnmpEngine = UdpTransportTarget = get_cmd = None


@dataclass
class DiscoveredHost:
    ip_address: str
    mac_address: str | None = None
    hostname: str | None = None
    vendor: str | None = None
    device_type: str | None = None
    operating_system: str | None = None
    open_ports: list[int] | None = None


@dataclass
class NetworkScanResult:
    scan: NetworkScan
    devices_upserted: int
    alerts_created: int
    delta: dict[str, int]


@dataclass
class EnrichmentMetadata:
    dns_name: str | None = None
    mdns_name: str | None = None
    netbios_name: str | None = None
    snmp_name: str | None = None
    vendor: str | None = None
    model_name: str | None = None
    operating_system: str | None = None
    hostname_source: str | None = None
    metadata_sources: dict[str, str] | None = None
    http_title: str | None = None
    http_server: str | None = None


def _normalize_mac(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower().replace("-", ":")
    return normalized or None


def _resolve_mac_from_arp_cache(ip_address: str) -> str | None:
    commands = (
        ["ip", "neigh", "show", ip_address],
        ["arp", "-n", ip_address],
    )
    patterns = (
        r"\blladdr\s+([0-9a-fA-F:-]{17})\b",
        r"\bat\s+([0-9a-fA-F:-]{17})\b",
    )

    for command in commands:
        if shutil.which(command[0]) is None:
            continue
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=settings.network_enrichment_timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue

        if result.returncode != 0:
            continue

        for pattern in patterns:
            match = re.search(pattern, result.stdout)
            if match:
                return _normalize_mac(match.group(1))
    return None


def _extract_mac_from_text(raw_value: str) -> str | None:
    match = re.search(r"\b([0-9a-fA-F]{2}(?::|-)[0-9a-fA-F]{2}(?::|-)[0-9a-fA-F]{2}(?::|-)[0-9a-fA-F]{2}(?::|-)[0-9a-fA-F]{2}(?::|-)[0-9a-fA-F]{2})\b", raw_value)
    if not match:
        return None
    return _normalize_mac(match.group(1))


def _resolve_mac_via_arp_helper(ip_address: str) -> str | None:
    if httpx is None or not settings.network_arp_helper_base_url:
        return None

    base_url = settings.network_arp_helper_base_url.rstrip("/")
    lookup_url = f"{base_url}/lookup?ip={quote(ip_address, safe='')}"

    try:
        with httpx.Client(timeout=settings.network_enrichment_timeout_seconds) as client:
            response = client.get(lookup_url, headers={"User-Agent": "GAIA-Network-Monitor/1.0"})
        if response.status_code != 200:
            return None
        payload = response.json()
    except Exception:
        return None

    if not isinstance(payload, dict):
        return None
    mac_address = payload.get("mac_address")
    return _normalize_mac(mac_address) if isinstance(mac_address, str) else None


def _resolve_mac_via_gateway_arp(ip_address: str) -> str | None:
    if paramiko is None:
        return None
    if not settings.network_gateway_arp_host or not settings.network_gateway_arp_username:
        return None

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    connect_kwargs: dict[str, Any] = {
        "hostname": settings.network_gateway_arp_host,
        "port": settings.network_gateway_arp_port,
        "username": settings.network_gateway_arp_username,
        "timeout": settings.network_enrichment_timeout_seconds,
        "banner_timeout": settings.network_enrichment_timeout_seconds,
        "auth_timeout": settings.network_enrichment_timeout_seconds,
    }
    if settings.network_gateway_arp_private_key_path:
        connect_kwargs["key_filename"] = settings.network_gateway_arp_private_key_path
    elif settings.network_gateway_arp_password:
        connect_kwargs["password"] = settings.network_gateway_arp_password
    else:
        return None

    try:
        client.connect(**connect_kwargs)
        command = settings.network_gateway_arp_command.format(ip=ip_address)
        _, stdout, _ = client.exec_command(command, timeout=settings.network_enrichment_timeout_seconds)
        output = stdout.read().decode("utf-8", errors="ignore")
        return _extract_mac_from_text(output)
    except Exception:
        return None
    finally:
        client.close()


def _resolve_mac_address(ip_address: str, discovered_mac: str | None) -> str | None:
    return (
        _normalize_mac(discovered_mac)
        or _resolve_mac_from_arp_cache(ip_address)
        or _resolve_mac_via_arp_helper(ip_address)
        or _resolve_mac_via_gateway_arp(ip_address)
    )


def _guess_device_type(open_ports: Iterable[int]) -> str | None:
    port_set = set(open_ports)
    if 3389 in port_set:
        return "workstation"
    if 22 in port_set and 445 in port_set:
        return "server"
    if 80 in port_set or 443 in port_set:
        return "network-service"
    return None


def _guess_operating_system(open_ports: Iterable[int]) -> str | None:
    port_set = set(open_ports)
    if 3389 in port_set:
        return "Windows"
    if 445 in port_set and 22 in port_set:
        return "Linux/Unix server"
    if 445 in port_set:
        return "Windows or SMB appliance"
    if 22 in port_set:
        return "Linux/Unix"
    if 80 in port_set or 443 in port_set:
        return "Embedded/Web appliance"
    return None


def _safe_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().rstrip(".")
    return normalized or None


def _coerce_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _json_dumps(value: dict[str, Any] | None) -> str | None:
    if not value:
        return None
    return json.dumps(value, ensure_ascii=True)


def metadata_sources_to_dict(raw_value: str | None) -> dict[str, Any] | None:
    if not raw_value:
        return None
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _resolve_dns_name(ip_address: str) -> str | None:
    try:
        hostname, _, _ = socket.gethostbyaddr(ip_address)
    except OSError:
        return None
    return _safe_text(hostname)


def _resolve_mdns_name(ip_address: str) -> str | None:
    if shutil.which("avahi-resolve-address") is None:
        return None

    try:
        result = subprocess.run(
            ["avahi-resolve-address", ip_address],
            capture_output=True,
            text=True,
            timeout=settings.network_enrichment_timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    if result.returncode != 0:
        return None

    parts = result.stdout.strip().split(maxsplit=1)
    if len(parts) != 2:
        return None
    return _safe_text(parts[1])


def _parse_netbios_name(output: str) -> str | None:
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if "<00>" not in line or "GROUP" in line.upper():
            continue
        if "<ACTIVE>" not in line.upper():
            continue
        candidate = line.split("<", 1)[0].strip()
        if candidate:
            return candidate
    return None


def _resolve_netbios_name(ip_address: str) -> str | None:
    if shutil.which("nmblookup") is None:
        return None

    try:
        result = subprocess.run(
            ["nmblookup", "-A", ip_address],
            capture_output=True,
            text=True,
            timeout=settings.network_enrichment_timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    if result.returncode != 0:
        return None
    return _safe_text(_parse_netbios_name(result.stdout))


def _snmp_communities() -> list[str]:
    return [item.strip() for item in settings.network_snmp_communities.split(",") if item.strip()]


def _snmp_profile_communities(ip_address: str) -> list[str]:
    communities: list[str] = []
    try:
        profiles = json.loads(settings.network_snmp_community_profiles)
    except json.JSONDecodeError:
        profiles = []

    for profile in profiles if isinstance(profiles, list) else []:
        if not isinstance(profile, dict):
            continue
        cidr = profile.get("cidr")
        profile_communities = profile.get("communities")
        if not isinstance(cidr, str) or not isinstance(profile_communities, list):
            continue
        try:
            network = ipaddress.ip_network(cidr, strict=False)
            address = ipaddress.ip_address(ip_address)
        except ValueError:
            continue
        if address not in network:
            continue
        for item in profile_communities:
            if isinstance(item, str) and item.strip():
                communities.append(item.strip())

    for item in _snmp_communities():
        if item not in communities:
            communities.append(item)
    return communities


def _classify_snmp_descr(sys_descr: str | None) -> tuple[str | None, str | None, str | None]:
    if not sys_descr:
        return None, None, None

    value = sys_descr.strip()
    lowered = value.lower()

    vendor_map = {
        "cisco": "Cisco",
        "mikrotik": "MikroTik",
        "routeros": "MikroTik",
        "synology": "Synology",
        "qnap": "QNAP",
        "ubiquiti": "Ubiquiti",
        "unifi": "Ubiquiti",
        "hewlett packard": "HPE",
        "aruba": "Aruba",
        "fortinet": "Fortinet",
        "tp-link": "TP-Link",
    }
    operating_system_map = {
        "windows": "Windows",
        "linux": "Linux",
        "routeros": "RouterOS",
        "ios xe": "Cisco IOS XE",
        "ios": "Cisco IOS",
        "dsm": "Synology DSM",
    }

    vendor = next((mapped for key, mapped in vendor_map.items() if key in lowered), None)
    operating_system = next((mapped for key, mapped in operating_system_map.items() if key in lowered), None)
    return vendor, value[:255], operating_system


def _extract_html_title(body: str) -> str | None:
    match = re.search(r"<title[^>]*>(.*?)</title>", body, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    title = re.sub(r"\s+", " ", match.group(1)).strip()
    return _safe_text(title)


def _extract_meta_refresh_target(body: str) -> str | None:
    match = re.search(r'<meta[^>]+http-equiv=["\']?refresh["\']?[^>]+content=["\'][^"\']*url=([^"\'>]+)', body, flags=re.IGNORECASE)
    if not match:
        return None
    return _safe_text(match.group(1))


def _extract_device_name(body: str) -> str | None:
    patterns = (
        r'<span[^>]+id=["\']deviceName["\'][^>]*>(.*?)</span>',
        r'<meta[^>]+name=["\']device-name["\'][^>]+content=["\'](.*?)["\']',
    )
    for pattern in patterns:
        match = re.search(pattern, body, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            continue
        value = re.sub(r"<[^>]+>", " ", match.group(1))
        value = re.sub(r"\s+", " ", value).strip()
        if value:
            return _safe_text(value)
    return None


def _normalize_http_model_name(title: str | None, device_name: str | None, server: str | None) -> str | None:
    candidates = [device_name, title, server]
    for candidate in candidates:
        if not candidate:
            continue
        normalized = candidate.replace("User Authentication :", "").replace("Accesso", "").strip(" -:/")
        normalized = re.sub(r"\s{2,}", " ", normalized)
        if normalized:
            return normalized[:255]
    return None


def _classify_http_identity(title: str | None, server: str | None, device_name: str | None = None) -> tuple[str | None, str | None, str | None]:
    values = [item for item in [device_name, title, server] if item]
    if not values:
        return None, None, None

    combined = " | ".join(values)
    lowered = combined.lower()

    vendor_map = {
        "canon": "Canon",
        "hp ": "HP",
        "hewlett-packard": "HP",
        "konica minolta": "Konica Minolta",
        "ricoh": "Ricoh",
        "xerox": "Xerox",
        "brother": "Brother",
        "epson": "Epson",
        "kyocera": "Kyocera",
        "lexmark": "Lexmark",
        "mikrotik": "MikroTik",
        "synology": "Synology",
        "qnap": "QNAP",
        "tp-link": "TP-Link",
        "cisco": "Cisco",
        "ubiquiti": "Ubiquiti",
        "unifi": "Ubiquiti",
    }
    operating_system_map = {
        "canon": "Embedded/Web appliance",
        "jetdirect": "Embedded/Web appliance",
        "airprint": "Embedded/Web appliance",
        "printer": "Embedded/Web appliance",
        "apache": "Embedded/Web appliance",
        "nginx": "Embedded/Web appliance",
    }

    vendor = next((mapped for key, mapped in vendor_map.items() if key in lowered), None)
    operating_system = next((mapped for key, mapped in operating_system_map.items() if key in lowered), None)
    model_name = _normalize_http_model_name(title, device_name, server)
    return vendor, model_name, operating_system


def _resolve_http_metadata(ip_address: str, open_ports: Iterable[int]) -> EnrichmentMetadata:
    if httpx is None:
        return EnrichmentMetadata()

    ports = set(open_ports)
    candidates: list[tuple[str, int]] = []
    if 80 in ports:
        candidates.append(("http", 80))
    if 443 in ports:
        candidates.append(("https", 443))
    if not candidates:
        return EnrichmentMetadata()

    for scheme, port in candidates:
        base_url = f"{scheme}://{ip_address}:{port}/"
        try:
            with httpx.Client(
                follow_redirects=True,
                verify=False,
                timeout=settings.network_enrichment_timeout_seconds,
            ) as client:
                response = client.get(base_url, headers={"User-Agent": "GAIA-Network-Monitor/1.0"})

                body = response.text
                refresh_target = _extract_meta_refresh_target(body)
                if refresh_target:
                    follow_url = refresh_target if refresh_target.startswith("http") else f"{scheme}://{ip_address}:{port}{refresh_target}"
                    try:
                        refresh_response = client.get(follow_url, headers={"User-Agent": "GAIA-Network-Monitor/1.0"})
                        if refresh_response.status_code < 500:
                            response = refresh_response
                            body = refresh_response.text
                    except Exception:
                        pass
        except Exception:
            continue

        title = _extract_html_title(body)
        device_name = _extract_device_name(body)
        server = _safe_text(response.headers.get("server"))
        vendor, model_name, operating_system = _classify_http_identity(title, server, device_name)

        metadata_sources: dict[str, str] = {}
        if title:
            metadata_sources["http_title"] = title
        if device_name:
            metadata_sources["http_device_name"] = device_name
        if server:
            metadata_sources["http_server"] = server
        if refresh_target:
            metadata_sources["http_refresh_target"] = refresh_target
        if metadata_sources:
            metadata_sources["http"] = f"{scheme}:{port}"

        return EnrichmentMetadata(
            vendor=vendor,
            model_name=model_name,
            operating_system=operating_system,
            metadata_sources=metadata_sources or None,
            http_title=title,
            http_server=server,
        )

    return EnrichmentMetadata()


async def _resolve_snmp_metadata_async(ip_address: str) -> EnrichmentMetadata:
    communities = _snmp_profile_communities(ip_address)
    if get_cmd is None or UdpTransportTarget is None or not communities:
        return EnrichmentMetadata()

    oid_map = {
        "1.3.6.1.2.1.1.5.0": "snmp_name",
        "1.3.6.1.2.1.1.1.0": "sys_descr",
    }

    for community in communities:
        try:
            transport = await UdpTransportTarget.create(
                (ip_address, 161),
                timeout=settings.network_enrichment_timeout_seconds,
                retries=0,
            )
            error_indication, error_status, _, var_binds = await get_cmd(
                SnmpEngine(),
                CommunityData(community, mpModel=1),
                transport,
                ContextData(),
                *[ObjectType(ObjectIdentity(oid)) for oid in oid_map],
            )
        except Exception:
            continue

        if error_indication or error_status:
            continue

        values: dict[str, str] = {}
        for name, value in var_binds:
            key = oid_map.get(str(name))
            if key:
                values[key] = _safe_text(str(value)) or ""

        vendor, model_name, operating_system = _classify_snmp_descr(values.get("sys_descr"))
        return EnrichmentMetadata(
            snmp_name=_safe_text(values.get("snmp_name")),
            vendor=vendor,
            model_name=model_name,
            operating_system=operating_system,
            metadata_sources={"snmp": community},
        )

    return EnrichmentMetadata()


def _resolve_snmp_metadata(ip_address: str) -> EnrichmentMetadata:
    if get_cmd is None:
        return EnrichmentMetadata()

    try:
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            return EnrichmentMetadata()
        return asyncio.run(_resolve_snmp_metadata_async(ip_address))
    except Exception:
        return EnrichmentMetadata()


def _collect_enrichment(ip_address: str, open_ports: Iterable[int]) -> EnrichmentMetadata:
    metadata = EnrichmentMetadata(
        dns_name=_resolve_dns_name(ip_address),
        mdns_name=_resolve_mdns_name(ip_address),
        netbios_name=_resolve_netbios_name(ip_address),
        metadata_sources={},
    )
    if metadata.dns_name:
        metadata.metadata_sources["dns"] = metadata.dns_name
    if metadata.mdns_name:
        metadata.metadata_sources["mdns"] = metadata.mdns_name
    if metadata.netbios_name:
        metadata.metadata_sources["netbios"] = metadata.netbios_name

    if 161 in set(open_ports):
        snmp_data = _resolve_snmp_metadata(ip_address)
        metadata.snmp_name = snmp_data.snmp_name or metadata.snmp_name
        metadata.vendor = snmp_data.vendor or metadata.vendor
        metadata.model_name = snmp_data.model_name or metadata.model_name
        metadata.operating_system = snmp_data.operating_system or metadata.operating_system
        if snmp_data.metadata_sources:
            metadata.metadata_sources.update(snmp_data.metadata_sources)

    if 80 in set(open_ports) or 443 in set(open_ports):
        http_data = _resolve_http_metadata(ip_address, open_ports)
        metadata.http_title = http_data.http_title or metadata.http_title
        metadata.http_server = http_data.http_server or metadata.http_server
        metadata.vendor = metadata.vendor or http_data.vendor
        metadata.model_name = metadata.model_name or http_data.model_name
        metadata.operating_system = metadata.operating_system or http_data.operating_system
        if http_data.metadata_sources:
            metadata.metadata_sources.update(http_data.metadata_sources)

    metadata.hostname_source = (
        "snmp"
        if metadata.snmp_name
        else "netbios"
        if metadata.netbios_name
        else "mdns"
        if metadata.mdns_name
        else "dns"
        if metadata.dns_name
        else None
    )

    return metadata


def _preferred_hostname(observed_hostname: str | None, metadata: EnrichmentMetadata) -> str | None:
    return (
        _safe_text(observed_hostname)
        or metadata.snmp_name
        or metadata.netbios_name
        or metadata.mdns_name
        or metadata.dns_name
    )


def _preferred_hostname_source(observed_hostname: str | None, metadata: EnrichmentMetadata) -> str | None:
    if _safe_text(observed_hostname):
        return "nmap"
    return metadata.hostname_source


def _fallback_hosts() -> list[DiscoveredHost]:
    hosts: list[DiscoveredHost] = []
    try:
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        hosts.append(
            DiscoveredHost(
                ip_address=ip_address,
                hostname=hostname,
                device_type="scanner",
                open_ports=[],
            )
        )
    except OSError:
        pass
    return hosts


def _run_nmap_scan(network_range: str, ports: str) -> list[DiscoveredHost]:
    if nmap is None or shutil.which("nmap") is None:
        return _fallback_hosts()

    ping_scanner = nmap.PortScanner()
    ping_scanner.scan(hosts=network_range, arguments=f"-sn -PE -n --host-timeout {settings.network_scan_ping_timeout_ms}ms")
    active_hosts = [host for host in ping_scanner.all_hosts() if ping_scanner[host].state() == "up"]
    if not active_hosts:
        return []

    port_hosts = " ".join(active_hosts)
    port_scanner = nmap.PortScanner()
    port_scanner.scan(hosts=port_hosts, arguments=f"-Pn -n -p {ports} --open")

    discovered: list[DiscoveredHost] = []
    for host in active_hosts:
        ping_state = ping_scanner[host]
        port_state = port_scanner._scan_result.get("scan", {}).get(host, {})

        addresses = port_state.get("addresses") or ping_state.get("addresses", {})
        vendor_map = port_state.get("vendor") or ping_state.get("vendor", {})
        hostname_entries = port_state.get("hostnames") or ping_state.get("hostnames", []) or []
        tcp_ports = sorted((port_state.get("tcp") or {}).keys())
        enrichment = _collect_enrichment(host, tcp_ports)

        discovered.append(
            DiscoveredHost(
                ip_address=host,
                mac_address=_normalize_mac(addresses.get("mac")),
                hostname=_preferred_hostname(next(iter(hostname_entries), {}).get("name"), enrichment),
                vendor=(next(iter(vendor_map.values()), None) if isinstance(vendor_map, dict) else None) or enrichment.vendor,
                device_type=_guess_device_type(tcp_ports),
                operating_system=enrichment.operating_system or _guess_operating_system(tcp_ports),
                open_ports=tcp_ports,
            )
        )
    return discovered


def _run_scapy_scan(network_range: str) -> list[DiscoveredHost]:
    try:
        from scapy.all import ARP, Ether, srp  # type: ignore
    except ImportError:  # pragma: no cover
        return _fallback_hosts()

    packet = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=network_range)
    answered, _ = srp(packet, timeout=max(settings.network_scan_ping_timeout_ms / 1000, 1), verbose=False)
    return [
        DiscoveredHost(ip_address=item[1].psrc, mac_address=_normalize_mac(item[1].hwsrc), open_ports=[])
        for item in answered
    ]


def discover_hosts(network_range: str | None = None, ports: str | None = None) -> list[DiscoveredHost]:
    resolved_range = network_range or settings.network_range
    resolved_ports = ports or settings.network_scan_ports

    try:
        ipaddress.ip_network(resolved_range, strict=False)
    except ValueError:
        raise ValueError(f"Invalid network range: {resolved_range}") from None

    discovered = _run_nmap_scan(resolved_range, resolved_ports)
    if discovered:
        return discovered

    discovered = _run_scapy_scan(resolved_range)
    if discovered:
        return discovered

    return _fallback_hosts()


def _snapshot_key(item: NetworkScanDevice) -> str:
    return item.mac_address or item.ip_address


def _snapshot_payload_changed(previous: NetworkScanDevice, current: NetworkScanDevice) -> bool:
    compared_fields = [
        "ip_address",
        "mac_address",
        "hostname",
        "hostname_source",
        "display_name",
        "asset_label",
        "vendor",
        "model_name",
        "device_type",
        "operating_system",
        "dns_name",
        "location_hint",
        "metadata_sources",
        "status",
        "open_ports",
    ]
    return any(getattr(previous, field_name) != getattr(current, field_name) for field_name in compared_fields)


def _build_diff(previous_items: list[NetworkScanDevice], current_items: list[NetworkScanDevice]) -> tuple[dict[str, int], list[dict[str, Any]]]:
    previous_map = {_snapshot_key(item): item for item in previous_items}
    current_map = {_snapshot_key(item): item for item in current_items}

    new_items: list[dict[str, Any]] = []
    missing_items: list[dict[str, Any]] = []
    changed_items: list[dict[str, Any]] = []

    keys = sorted(set(previous_map) | set(current_map))
    for key in keys:
        before = previous_map.get(key)
        after = current_map.get(key)
        if before is None and after is not None:
            new_items.append({"key": key, "before": None, "after": after, "change_type": "new"})
            continue
        if before is not None and after is None:
            missing_items.append({"key": key, "before": before, "after": None, "change_type": "missing"})
            continue
        if before is not None and after is not None and _snapshot_payload_changed(before, after):
            changed_items.append({"key": key, "before": before, "after": after, "change_type": "changed"})

    summary = {
        "new_devices_count": len(new_items),
        "missing_devices_count": len(missing_items),
        "changed_devices_count": len(changed_items),
    }
    return summary, [*new_items, *missing_items, *changed_items]


def get_scan_delta(db: Session, scan_id: int) -> dict[str, int]:
    current_items = db.scalars(
        select(NetworkScanDevice).where(NetworkScanDevice.scan_id == scan_id).order_by(NetworkScanDevice.ip_address.asc())
    ).all()
    previous_scan_id = db.scalar(
        select(NetworkScan.id).where(NetworkScan.id < scan_id).order_by(NetworkScan.id.desc()).limit(1)
    )
    if previous_scan_id is None:
        return {
            "new_devices_count": len(current_items),
            "missing_devices_count": 0,
            "changed_devices_count": 0,
        }
    previous_items = db.scalars(
        select(NetworkScanDevice).where(NetworkScanDevice.scan_id == previous_scan_id).order_by(NetworkScanDevice.ip_address.asc())
    ).all()
    summary, _ = _build_diff(previous_items, current_items)
    return summary


def get_scan_diff(db: Session, from_scan_id: int, to_scan_id: int) -> tuple[dict[str, int], list[dict[str, Any]]]:
    from_items = db.scalars(
        select(NetworkScanDevice).where(NetworkScanDevice.scan_id == from_scan_id).order_by(NetworkScanDevice.ip_address.asc())
    ).all()
    to_items = db.scalars(
        select(NetworkScanDevice).where(NetworkScanDevice.scan_id == to_scan_id).order_by(NetworkScanDevice.ip_address.asc())
    ).all()
    return _build_diff(from_items, to_items)


def _create_or_refresh_snapshot_rows(db: Session, scan: NetworkScan) -> list[NetworkScanDevice]:
    db.query(NetworkScanDevice).filter(NetworkScanDevice.scan_id == scan.id).delete()
    db.flush()

    current_devices = db.scalars(select(NetworkDevice).order_by(NetworkDevice.ip_address.asc())).all()
    snapshot_rows: list[NetworkScanDevice] = []
    for device in current_devices:
        snapshot = NetworkScanDevice(
            scan_id=scan.id,
            device_id=device.id,
            ip_address=device.ip_address,
            mac_address=device.mac_address,
            hostname=device.hostname,
            hostname_source=device.hostname_source,
            display_name=device.display_name,
            asset_label=device.asset_label,
            vendor=device.vendor,
            model_name=device.model_name,
            device_type=device.device_type,
            operating_system=device.operating_system,
            dns_name=device.dns_name,
            location_hint=device.location_hint,
            metadata_sources=device.metadata_sources,
            status=device.status,
            open_ports=device.open_ports,
            observed_at=scan.completed_at,
        )
        db.add(snapshot)
        snapshot_rows.append(snapshot)
    db.flush()
    return snapshot_rows


def _latest_scan_before(db: Session, scan_id: int) -> int | None:
    return db.scalar(select(NetworkScan.id).where(NetworkScan.id < scan_id).order_by(NetworkScan.id.desc()).limit(1))


def _create_alert(
    db: Session,
    *,
    device_id: int | None,
    scan_id: int | None,
    alert_type: str,
    severity: str,
    title: str,
    message: str | None,
) -> bool:
    existing_open = db.scalar(
        select(NetworkAlert.id).where(
            NetworkAlert.device_id == device_id,
            NetworkAlert.alert_type == alert_type,
            NetworkAlert.status == "open",
        )
    )
    if existing_open:
        return False

    db.add(
        NetworkAlert(
            device_id=device_id,
            scan_id=scan_id,
            alert_type=alert_type,
            severity=severity,
            status="open",
            title=title,
            message=message,
        )
    )
    return True


def _resolve_alerts_for_device(db: Session, *, device_id: int | None, alert_types: Iterable[str]) -> None:
    if device_id is None:
        return
    alerts = db.scalars(
        select(NetworkAlert).where(
            NetworkAlert.device_id == device_id,
            NetworkAlert.alert_type.in_(list(alert_types)),
            NetworkAlert.status == "open",
        )
    ).all()
    now = datetime.now(UTC)
    for alert in alerts:
        alert.status = "resolved"
        alert.acknowledged_at = now


def sync_network_device_alert_state(db: Session, device: NetworkDevice) -> None:
    if device.is_known_device:
        _resolve_alerts_for_device(db, device_id=device.id, alert_types=["UNKNOWN_DEVICE", "NEW_DEVICE", "new_device"])
        return

    _resolve_alerts_for_device(db, device_id=device.id, alert_types=["MISSING_DEVICE", "device_offline"])
    if device.status != "online":
        return

    _create_alert(
        db,
        device_id=device.id,
        scan_id=device.last_scan_id,
        alert_type="UNKNOWN_DEVICE",
        severity="warning",
        title=f"Dispositivo non registrato: {device.ip_address}",
        message=f"Hostname: {device.hostname or 'n/d'} | MAC: {device.mac_address or 'n/d'}",
    )


def run_network_scan(
    db: Session,
    initiated_by: str | None = None,
    network_range: str | None = None,
    discovered_hosts: list[DiscoveredHost] | None = None,
) -> NetworkScanResult:
    resolved_range = network_range or settings.network_range
    started_at = datetime.now(UTC)
    previous_scan_id = db.scalar(select(NetworkScan.id).order_by(NetworkScan.id.desc()).limit(1))
    discovered = discovered_hosts if discovered_hosts is not None else discover_hosts(resolved_range)

    scan = NetworkScan(
        network_range=resolved_range,
        scan_type="incremental",
        status="completed",
        hosts_scanned=max(len(discovered), 1),
        active_hosts=len(discovered),
        discovered_devices=len(discovered),
        initiated_by=initiated_by,
        started_at=started_at,
        completed_at=datetime.now(UTC),
    )
    db.add(scan)
    db.flush()

    devices_by_ip = {item.ip_address: item for item in db.scalars(select(NetworkDevice)).all()}
    seen_ips = {host.ip_address for host in discovered}
    alerts_created = 0

    for host in discovered:
        device = devices_by_ip.get(host.ip_address)
        is_new = device is None
        now = datetime.now(UTC)
        enrichment = _collect_enrichment(host.ip_address, host.open_ports or [])

        if device is None:
            device = NetworkDevice(
                ip_address=host.ip_address,
                mac_address=_resolve_mac_address(host.ip_address, host.mac_address),
                hostname=_preferred_hostname(host.hostname, enrichment),
                hostname_source=_preferred_hostname_source(host.hostname, enrichment),
                dns_name=enrichment.dns_name or enrichment.mdns_name,
                vendor=host.vendor or enrichment.vendor,
                model_name=enrichment.model_name,
                metadata_sources=_json_dumps(enrichment.metadata_sources),
                device_type=host.device_type or _guess_device_type(host.open_ports or []),
                operating_system=host.operating_system
                or enrichment.operating_system
                or _guess_operating_system(host.open_ports or []),
                status="online",
                is_known_device=False,
                is_monitored=True,
                open_ports=",".join(str(port) for port in (host.open_ports or [])) or None,
                first_seen_at=now,
                last_seen_at=now,
                last_scan_id=scan.id,
            )
            db.add(device)
            db.flush()
            devices_by_ip[device.ip_address] = device
        else:
            device.mac_address = _resolve_mac_address(host.ip_address, host.mac_address) or device.mac_address
            device.hostname = _preferred_hostname(host.hostname, enrichment) or device.hostname
            device.hostname_source = _preferred_hostname_source(host.hostname, enrichment) or device.hostname_source
            device.dns_name = enrichment.dns_name or enrichment.mdns_name or device.dns_name
            device.vendor = host.vendor or enrichment.vendor or device.vendor
            device.model_name = enrichment.model_name or device.model_name
            device.metadata_sources = _json_dumps(enrichment.metadata_sources) or device.metadata_sources
            device.device_type = host.device_type or device.device_type or _guess_device_type(host.open_ports or [])
            device.operating_system = (
                host.operating_system
                or enrichment.operating_system
                or device.operating_system
                or _guess_operating_system(host.open_ports or [])
            )
            device.status = "online"
            device.open_ports = ",".join(str(port) for port in (host.open_ports or [])) or device.open_ports
            device.last_seen_at = now
            device.last_scan_id = scan.id

        _resolve_alerts_for_device(db, device_id=device.id, alert_types=["MISSING_DEVICE", "device_offline"])
        if not device.is_known_device:
            _resolve_alerts_for_device(db, device_id=device.id, alert_types=["NEW_DEVICE", "new_device"])
            created_unknown_alert = _create_alert(
                db,
                device_id=device.id,
                scan_id=scan.id,
                alert_type="UNKNOWN_DEVICE",
                severity="warning",
                title=f"Dispositivo non registrato: {device.ip_address}",
                message=f"Hostname: {device.hostname or 'n/d'} | MAC: {device.mac_address or 'n/d'}",
            )
            if created_unknown_alert:
                alerts_created += 1
        else:
            _resolve_alerts_for_device(db, device_id=device.id, alert_types=["UNKNOWN_DEVICE", "NEW_DEVICE", "new_device"])

    now = datetime.now(UTC)
    alert_threshold = timedelta(days=max(settings.network_missing_device_alert_days, 1))
    monitored_devices = db.scalars(select(NetworkDevice).where(NetworkDevice.is_monitored.is_(True))).all()
    for device in monitored_devices:
        if device.ip_address in seen_ips:
            continue
        if device.status != "offline":
            device.status = "offline"
        device.last_scan_id = scan.id
        if not device.is_known_device:
            _resolve_alerts_for_device(db, device_id=device.id, alert_types=["MISSING_DEVICE", "device_offline"])
            continue
        if now - _coerce_utc(device.last_seen_at) < alert_threshold:
            _resolve_alerts_for_device(db, device_id=device.id, alert_types=["MISSING_DEVICE", "device_offline"])
            continue
        if _create_alert(
            db,
            device_id=device.id,
            scan_id=scan.id,
            alert_type="MISSING_DEVICE",
            severity="danger",
            title=f"Dispositivo conosciuto assente dalla rete: {device.ip_address}",
            message=f"Ultimo avvistamento: {device.last_seen_at.isoformat()}",
        ):
            alerts_created += 1

    db.flush()
    _create_or_refresh_snapshot_rows(db, scan)
    db.commit()
    db.refresh(scan)
    delta = get_scan_delta(db, scan.id) if previous_scan_id else {
        "new_devices_count": scan.discovered_devices,
        "missing_devices_count": 0,
        "changed_devices_count": 0,
    }
    return NetworkScanResult(scan=scan, devices_upserted=len(discovered), alerts_created=alerts_created, delta=delta)


def list_network_devices(
    db: Session,
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
    status: str | None = None,
    vendor: str | None = None,
    device_type: str | None = None,
    floor_plan_id: int | None = None,
) -> tuple[list[NetworkDevice], int]:
    query = select(NetworkDevice)
    count_query = select(func.count(NetworkDevice.id))

    if search:
        like_value = f"%{search.strip()}%"
        predicate = or_(
            NetworkDevice.ip_address.ilike(like_value),
            NetworkDevice.hostname.ilike(like_value),
            NetworkDevice.display_name.ilike(like_value),
            NetworkDevice.asset_label.ilike(like_value),
            NetworkDevice.dns_name.ilike(like_value),
            NetworkDevice.mac_address.ilike(like_value),
            NetworkDevice.notes.ilike(like_value),
        )
        query = query.where(predicate)
        count_query = count_query.where(predicate)

    if status:
        query = query.where(NetworkDevice.status == status)
        count_query = count_query.where(NetworkDevice.status == status)

    if vendor:
        query = query.where(NetworkDevice.vendor == vendor)
        count_query = count_query.where(NetworkDevice.vendor == vendor)

    if device_type:
        query = query.where(NetworkDevice.device_type == device_type)
        count_query = count_query.where(NetworkDevice.device_type == device_type)

    if floor_plan_id is not None:
        query = query.join(DevicePosition, DevicePosition.device_id == NetworkDevice.id).where(
            DevicePosition.floor_plan_id == floor_plan_id
        )
        count_query = count_query.join(DevicePosition, DevicePosition.device_id == NetworkDevice.id).where(
            DevicePosition.floor_plan_id == floor_plan_id
        )

    total = db.scalar(count_query) or 0
    items = db.scalars(
        query.order_by(NetworkDevice.status.asc(), NetworkDevice.ip_address.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return items, total


def list_network_scans(db: Session) -> list[NetworkScan]:
    return db.scalars(select(NetworkScan).order_by(NetworkScan.started_at.desc(), NetworkScan.id.desc())).all()


def get_network_dashboard_summary(db: Session) -> dict[str, object]:
    now = datetime.now(UTC)
    latest_scan_at = db.scalar(select(func.max(NetworkScan.completed_at)))

    return {
        "total_devices": db.scalar(select(func.count(NetworkDevice.id))) or 0,
        "online_devices": db.scalar(select(func.count(NetworkDevice.id)).where(NetworkDevice.status == "online")) or 0,
        "offline_devices": db.scalar(select(func.count(NetworkDevice.id)).where(NetworkDevice.status == "offline")) or 0,
        "open_alerts": db.scalar(select(func.count(NetworkAlert.id)).where(NetworkAlert.status == "open")) or 0,
        "scans_last_24h": db.scalar(
            select(func.count(NetworkScan.id)).where(NetworkScan.started_at >= now - timedelta(hours=24))
        )
        or 0,
        "floor_plans": db.scalar(select(func.count(FloorPlan.id))) or 0,
        "latest_scan_at": latest_scan_at,
    }


def get_device_positions(db: Session, device_id: int) -> list[DevicePosition]:
    return db.scalars(
        select(DevicePosition).where(DevicePosition.device_id == device_id).order_by(DevicePosition.updated_at.desc())
    ).all()


def get_device_scan_history(db: Session, device_id: int, limit: int = 10) -> list[NetworkScanDevice]:
    return db.scalars(
        select(NetworkScanDevice)
        .where(NetworkScanDevice.device_id == device_id)
        .order_by(NetworkScanDevice.observed_at.desc(), NetworkScanDevice.id.desc())
        .limit(limit)
    ).all()


def list_network_alerts(db: Session, status: str | None = None, severity: str | None = None) -> list[NetworkAlert]:
    query = select(NetworkAlert).order_by(NetworkAlert.created_at.desc(), NetworkAlert.id.desc())
    if status:
        query = query.where(NetworkAlert.status == status)
    if severity:
        query = query.where(NetworkAlert.severity == severity)
    return db.scalars(query).all()


def update_network_alert(db: Session, alert_id: int, status: str) -> NetworkAlert | None:
    alert = db.get(NetworkAlert, alert_id)
    if alert is None:
        return None
    alert.status = status
    alert.acknowledged_at = datetime.now(UTC) if status in {"resolved", "ignored"} else None
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def create_floor_plan(
    db: Session,
    *,
    name: str,
    floor_label: str,
    building: str | None = None,
    svg_content: str | None = None,
    image_url: str | None = None,
    width: float | None = None,
    height: float | None = None,
) -> FloorPlan:
    floor_plan = FloorPlan(
        name=name.strip(),
        floor_label=floor_label.strip(),
        building=building.strip() if building else None,
        svg_content=svg_content,
        image_url=image_url,
        width=width,
        height=height,
    )
    db.add(floor_plan)
    db.commit()
    db.refresh(floor_plan)
    return floor_plan


def upsert_device_position(
    db: Session,
    *,
    device_id: int,
    floor_plan_id: int,
    x: float,
    y: float,
    label: str | None = None,
) -> DevicePosition:
    position = db.scalar(
        select(DevicePosition).where(
            DevicePosition.device_id == device_id,
            DevicePosition.floor_plan_id == floor_plan_id,
        )
    )
    if position is None:
        position = DevicePosition(
            device_id=device_id,
            floor_plan_id=floor_plan_id,
            x=x,
            y=y,
            label=label,
        )
    else:
        position.x = x
        position.y = y
        position.label = label

    db.add(position)
    db.commit()
    db.refresh(position)
    return position


def get_floor_plan_devices(db: Session, floor_plan_id: int) -> list[tuple[DevicePosition, NetworkDevice]]:
    rows = db.execute(
        select(DevicePosition, NetworkDevice)
        .join(NetworkDevice, NetworkDevice.id == DevicePosition.device_id)
        .where(DevicePosition.floor_plan_id == floor_plan_id)
        .order_by(DevicePosition.id.asc())
    ).all()
    return [(position, device) for position, device in rows]


def get_network_scan_detail(db: Session, scan_id: int) -> tuple[NetworkScan | None, list[NetworkScanDevice], dict[str, int]]:
    scan = db.get(NetworkScan, scan_id)
    if scan is None:
        return None, [], {"new_devices_count": 0, "missing_devices_count": 0, "changed_devices_count": 0}
    devices = db.scalars(
        select(NetworkScanDevice)
        .where(NetworkScanDevice.scan_id == scan_id)
        .order_by(NetworkScanDevice.status.asc(), NetworkScanDevice.ip_address.asc())
    ).all()
    return scan, devices, get_scan_delta(db, scan_id)


def run_network_scan_subprocess() -> int:
    return subprocess.call(["python", "-m", "app.scripts.network_scanner"])
