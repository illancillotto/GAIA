from __future__ import annotations

from datetime import datetime, timedelta
import ipaddress
import re

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.datetime_compat import UTC
from app.models.application_user import ApplicationUser
from app.modules.network.models import NetworkDevice, NetworkFirewall, NetworkFirewallEvent
from app.modules.network.services import get_network_dashboard_summary
from app.modules.network.sophos import list_network_firewalls

_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_DEVICE_HINT_RE = re.compile(
    r"(?:device|dispositivo|host|pc|computer)\s+(.+?)(?:\s+(?:in\s+rete|rete|network|con\s+ip|ip)\b|$)",
    re.IGNORECASE,
)


def _resolve_device_label(device: NetworkDevice) -> str:
    if device.assigned_user:
        return device.assigned_user.full_name or device.assigned_user.username
    if device.display_name:
        return device.display_name
    if device.hostname:
        return device.hostname
    return device.ip_address


def _extract_identifier(question: str) -> str | None:
    ip_match = _IPV4_RE.search(question)
    if ip_match:
        return ip_match.group(0)
    hint_match = _DEVICE_HINT_RE.search(question)
    if hint_match:
        value = hint_match.group(1).strip(" '\"")
        return value or None
    return None


def get_network_dashboard_summary_read_model(db: Session, current_user: ApplicationUser) -> dict[str, object]:
    return get_network_dashboard_summary(db)


def get_network_firewall_summary_read_model(db: Session, current_user: ApplicationUser) -> dict[str, object]:
    firewalls = list_network_firewalls(db)
    window_start = datetime.now(UTC) - timedelta(hours=24)
    total_events = db.scalar(
        select(func.count()).select_from(NetworkFirewallEvent).where(NetworkFirewallEvent.observed_at >= window_start)
    ) or 0
    blocked_events = db.scalar(
        select(func.count()).select_from(NetworkFirewallEvent).where(
            NetworkFirewallEvent.observed_at >= window_start,
            or_(
                NetworkFirewallEvent.event_type.ilike("%deny%"),
                NetworkFirewallEvent.event_type.ilike("%denied%"),
                NetworkFirewallEvent.event_type.ilike("%block%"),
                NetworkFirewallEvent.event_type.ilike("%drop%"),
            ),
        )
    ) or 0
    top_firewalls = [
        {
            "id": firewall.id,
            "name": firewall.name,
            "status": firewall.status,
            "management_ip": firewall.management_ip,
            "last_seen_at": firewall.last_seen_at,
        }
        for firewall in firewalls[:3]
    ]
    return {
        "firewall_count": len(firewalls),
        "online_firewalls": sum(1 for firewall in firewalls if firewall.status == "online"),
        "events_last_24h": int(total_events),
        "blocked_events_last_24h": int(blocked_events),
        "top_firewalls": top_firewalls,
    }


def get_network_device_read_model(db: Session, current_user: ApplicationUser, identifier: str | None) -> dict[str, object] | None:
    if not identifier:
        return None

    normalized_identifier = identifier.strip()
    device: NetworkDevice | None = None

    try:
        parsed_ip = str(ipaddress.ip_address(normalized_identifier))
    except ValueError:
        parsed_ip = None

    base_query = select(NetworkDevice).options(joinedload(NetworkDevice.assigned_user))
    if parsed_ip:
        device = db.scalar(base_query.where(NetworkDevice.ip_address == parsed_ip).limit(1))
    else:
        like_value = f"%{normalized_identifier.lower()}%"
        device = db.scalar(
            base_query.join(ApplicationUser, NetworkDevice.assigned_user_id == ApplicationUser.id, isouter=True)
            .where(
                or_(
                    func.lower(NetworkDevice.hostname).like(like_value),
                    func.lower(NetworkDevice.display_name).like(like_value),
                    func.lower(NetworkDevice.dns_name).like(like_value),
                    func.lower(NetworkDevice.asset_label).like(like_value),
                    func.lower(ApplicationUser.full_name).like(like_value),
                    func.lower(ApplicationUser.username).like(like_value),
                )
            )
            .limit(1)
        )

    if device is None:
        return None

    assigned_user = device.assigned_user
    return {
        "id": device.id,
        "ip_address": device.ip_address,
        "hostname": device.hostname,
        "display_name": device.display_name,
        "resolved_label": _resolve_device_label(device),
        "status": device.status,
        "device_type": device.device_type,
        "operating_system": device.operating_system,
        "location_hint": device.location_hint,
        "is_known_device": device.is_known_device,
        "is_monitored": device.is_monitored,
        "last_seen_at": device.last_seen_at,
        "assigned_user": {
            "username": assigned_user.username,
            "full_name": assigned_user.full_name,
            "office_location": assigned_user.office_location,
            "phone_extension": assigned_user.phone_extension,
        }
        if assigned_user is not None
        else None,
    }


def extract_network_device_identifier(question: str) -> str | None:
    return _extract_identifier(question)
