from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import ipaddress
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

    scanner = nmap.PortScanner()
    scanner.scan(hosts=network_range, arguments=f"-sn -PE -n --host-timeout {settings.network_scan_ping_timeout_ms}ms")
    active_hosts = [host for host in scanner.all_hosts() if scanner[host].state() == "up"]
    if not active_hosts:
        return []

    port_hosts = " ".join(active_hosts)
    scanner.scan(hosts=port_hosts, arguments=f"-Pn -n -p {ports} --open")

    discovered: list[DiscoveredHost] = []
    for host in active_hosts:
        host_state = scanner[host]
        addresses = host_state.get("addresses", {})
        vendor_map = host_state.get("vendor", {})
        tcp_ports = sorted(host_state.get("tcp", {}).keys())
        discovered.append(
            DiscoveredHost(
                ip_address=host,
                mac_address=_normalize_mac(addresses.get("mac")),
                hostname=next(iter(host_state.get("hostnames", []) or []), {}).get("name"),
                vendor=next(iter(vendor_map.values()), None) if isinstance(vendor_map, dict) else None,
                device_type=_guess_device_type(tcp_ports),
                operating_system=None,
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
            device = NetworkDevice(
                ip_address=host.ip_address,
                mac_address=_normalize_mac(host.mac_address),
                hostname=host.hostname,
                vendor=host.vendor,
                device_type=host.device_type or _guess_device_type(host.open_ports or []),
                operating_system=host.operating_system,
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
            device.mac_address = _normalize_mac(host.mac_address) or device.mac_address
            device.hostname = host.hostname or device.hostname
            device.vendor = host.vendor or device.vendor
            device.device_type = host.device_type or device.device_type or _guess_device_type(host.open_ports or [])
            device.operating_system = host.operating_system or device.operating_system
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
