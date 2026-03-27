from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import ipaddress
import json
import shutil
import socket
import subprocess

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.network.models import FloorPlan, NetworkAlert, NetworkDevice, NetworkScan

try:
    import nmap  # type: ignore
except ImportError:  # pragma: no cover
    nmap = None

try:
    from pysnmp.hlapi.v3arch.asyncio import CommunityData, ContextData, ObjectIdentity, ObjectType, SnmpEngine, UdpTransportTarget, get_cmd  # type: ignore
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


def _normalize_mac(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower().replace("-", ":")
    return normalized or None


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

    metadata.hostname_source = (
        "snmp" if metadata.snmp_name
        else "netbios" if metadata.netbios_name
        else "mdns" if metadata.mdns_name
        else "dns" if metadata.dns_name
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


def run_network_scan(
    db: Session,
    initiated_by: str | None = None,
    network_range: str | None = None,
    discovered_hosts: list[DiscoveredHost] | None = None,
) -> NetworkScanResult:
    resolved_range = network_range or settings.network_range
    started_at = datetime.now(UTC)
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

        if device is None:
            enrichment = _collect_enrichment(host.ip_address, host.open_ports or [])
            device = NetworkDevice(
                ip_address=host.ip_address,
                mac_address=_normalize_mac(host.mac_address),
                hostname=_preferred_hostname(host.hostname, enrichment),
                hostname_source=_preferred_hostname_source(host.hostname, enrichment),
                dns_name=enrichment.dns_name or enrichment.mdns_name,
                vendor=host.vendor or enrichment.vendor,
                model_name=enrichment.model_name,
                metadata_sources=json.dumps(enrichment.metadata_sources or {}, ensure_ascii=True) or None,
                device_type=host.device_type or _guess_device_type(host.open_ports or []),
                operating_system=host.operating_system or enrichment.operating_system or _guess_operating_system(host.open_ports or []),
                status="online",
                is_monitored=True,
                open_ports=",".join(str(port) for port in (host.open_ports or [])) or None,
                first_seen_at=now,
                last_seen_at=now,
                last_scan_id=scan.id,
            )
            db.add(device)
            db.flush()
        else:
            enrichment = _collect_enrichment(host.ip_address, host.open_ports or [])
            device.mac_address = _normalize_mac(host.mac_address) or device.mac_address
            device.hostname = _preferred_hostname(host.hostname, enrichment) or device.hostname
            device.hostname_source = _preferred_hostname_source(host.hostname, enrichment) or device.hostname_source
            device.dns_name = enrichment.dns_name or enrichment.mdns_name or device.dns_name
            device.vendor = host.vendor or enrichment.vendor or device.vendor
            device.model_name = enrichment.model_name or device.model_name
            device.metadata_sources = json.dumps(enrichment.metadata_sources or {}, ensure_ascii=True) or device.metadata_sources
            device.device_type = host.device_type or device.device_type or _guess_device_type(host.open_ports or [])
            device.operating_system = host.operating_system or enrichment.operating_system or device.operating_system or _guess_operating_system(host.open_ports or [])
            device.status = "online"
            device.open_ports = ",".join(str(port) for port in (host.open_ports or [])) or device.open_ports
            device.last_seen_at = now
            device.last_scan_id = scan.id

        if is_new:
            db.add(
                NetworkAlert(
                    device_id=device.id,
                    scan_id=scan.id,
                    alert_type="new_device",
                    severity="warning",
                    status="open",
                    title=f"Nuovo dispositivo rilevato: {device.ip_address}",
                    message=f"Hostname: {device.hostname or 'n/d'} | MAC: {device.mac_address or 'n/d'}",
                )
            )
            alerts_created += 1

    previously_online = db.scalars(select(NetworkDevice).where(NetworkDevice.status == "online")).all()
    for device in previously_online:
        if device.ip_address in seen_ips:
            continue
        device.status = "offline"
        db.add(
            NetworkAlert(
                device_id=device.id,
                scan_id=scan.id,
                alert_type="device_offline",
                severity="danger",
                status="open",
                title=f"Dispositivo non raggiungibile: {device.ip_address}",
                message=f"Ultimo avvistamento: {device.last_seen_at.isoformat()}",
            )
        )
        alerts_created += 1

    db.commit()
    db.refresh(scan)
    return NetworkScanResult(scan=scan, devices_upserted=len(discovered), alerts_created=alerts_created)


def list_network_devices(
    db: Session,
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
    status: str | None = None,
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
        )
        query = query.where(predicate)
        count_query = count_query.where(predicate)

    if status:
        query = query.where(NetworkDevice.status == status)
        count_query = count_query.where(NetworkDevice.status == status)

    total = db.scalar(count_query) or 0
    items = db.scalars(
        query.order_by(NetworkDevice.status.asc(), NetworkDevice.ip_address.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return items, total


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
        ) or 0,
        "floor_plans": db.scalar(select(func.count(FloorPlan.id))) or 0,
        "latest_scan_at": latest_scan_at,
    }


def run_network_scan_subprocess() -> int:
    return subprocess.call(["python", "-m", "app.scripts.network_scanner"])
