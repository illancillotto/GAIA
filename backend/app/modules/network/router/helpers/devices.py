import ipaddress
import json
import urllib.error
import urllib.request
from typing import Any

from fastapi import HTTPException, status

from app.models.application_user import ApplicationUser
from app.modules.network.models import (
    DevicePosition,
    NetworkDevice,
    NetworkScanDevice,
)
from app.modules.network.schemas import (
    DevicePositionResponse,
    NetworkAssignedUserSummary,
    NetworkDeviceResponse,
    NetworkDeviceTrafficSummary,
    NetworkIpWhoisResponse,
)
from app.modules.network.services import (
    metadata_sources_to_dict,
)

# Keep extracted callable formatting stable for complexity-baseline matching.
# fmt: off

def _resolve_device_label(device: NetworkDevice) -> tuple[str, str]:
    if device.assigned_user:
        if device.assigned_user.full_name:
            return device.assigned_user.full_name, "application_user"
        return device.assigned_user.username, "application_user"
    if device.display_name:
        return device.display_name, "device"
    if device.hostname:
        return device.hostname, "hostname"
    return device.ip_address, "ip_address"


def _serialize_device(
    device: NetworkDevice,
    *,
    positions: list[DevicePosition] | None = None,
    scan_history: list[NetworkScanDevice] | None = None,
    traffic_summary: NetworkDeviceTrafficSummary | None = None,
) -> NetworkDeviceResponse:
    resolved_label, label_source = _resolve_device_label(device)
    payload = {
        "id": device.id,
        "last_scan_id": device.last_scan_id,
        "assigned_user_id": device.assigned_user_id,
        "ip_address": device.ip_address,
        "mac_address": device.mac_address,
        "hostname": device.hostname,
        "hostname_source": device.hostname_source,
        "display_name": device.display_name,
        "resolved_label": resolved_label,
        "label_source": label_source,
        "lifecycle_state": device.lifecycle_state,
        "asset_label": device.asset_label,
        "vendor": device.vendor,
        "model_name": device.model_name,
        "device_type": device.device_type,
        "operating_system": device.operating_system,
        "dns_name": device.dns_name,
        "location_hint": device.location_hint,
        "notes": device.notes,
        "is_known_device": device.is_known_device,
        "metadata_sources": metadata_sources_to_dict(device.metadata_sources),
        "status": device.status,
        "is_monitored": device.is_monitored,
        "open_ports": device.open_ports,
        "first_seen_at": device.first_seen_at,
        "last_seen_at": device.last_seen_at,
        "created_at": device.created_at,
        "updated_at": device.updated_at,
        "assigned_user": _serialize_assigned_user(device.assigned_user) if device.assigned_user else None,
        "retired_at": device.retired_at,
        "positions": [DevicePositionResponse.model_validate(position) for position in positions or []],
        "scan_history": [
            {
                "scan_id": item.scan_id,
                "observed_at": item.observed_at,
                "status": item.status,
                "hostname": item.hostname,
                "ip_address": item.ip_address,
                "mac_address": item.mac_address,
                "open_ports": item.open_ports,
            }
            for item in scan_history or []
        ],
        "traffic_summary": traffic_summary,
    }
    return NetworkDeviceResponse.model_validate(payload)


def _extract_rdap_entity_names(payload: dict[str, Any]) -> list[str]:
    names: list[str] = []
    entities = payload.get("entities")
    if not isinstance(entities, list):
        return names

    for entity in entities:
        if not isinstance(entity, dict):
            continue
        vcard = entity.get("vcardArray")
        if not (isinstance(vcard, list) and len(vcard) == 2 and isinstance(vcard[1], list)):
            continue
        for item in vcard[1]:
            if (
                isinstance(item, list)
                and len(item) >= 4
                and item[0] in {"fn", "org"}
                and isinstance(item[3], str)
                and item[3].strip()
            ):
                names.append(item[3].strip())
                break
    return list(dict.fromkeys(names))


def _summarize_ip_whois(ip_address: str) -> NetworkIpWhoisResponse:
    try:
        parsed_ip = ipaddress.ip_address(ip_address)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid IP address: {ip_address}") from exc

    if parsed_ip.is_private:
        return NetworkIpWhoisResponse(
            ip_address=str(parsed_ip),
            scope="IP privato",
            is_private=True,
            rdap_status="not_applicable",
            label="Rete interna GAIA/LAN privata",
        )
    if parsed_ip.is_loopback:
        return NetworkIpWhoisResponse(
            ip_address=str(parsed_ip),
            scope="Loopback locale",
            is_loopback=True,
            rdap_status="not_applicable",
            label="Indirizzo locale della macchina stessa",
        )
    if parsed_ip.is_link_local:
        return NetworkIpWhoisResponse(
            ip_address=str(parsed_ip),
            scope="Link-local",
            is_link_local=True,
            rdap_status="not_applicable",
            label="Indirizzo autoconfigurato non instradato su Internet",
        )

    external_url = f"https://rdap.org/ip/{parsed_ip}"
    try:
        with urllib.request.urlopen(external_url, timeout=4) as response:
            payload = json.load(response)
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return NetworkIpWhoisResponse(
            ip_address=str(parsed_ip),
            scope="IP pubblico",
            rdap_status="unavailable",
            external_url=external_url,
        )

    start_address = payload.get("startAddress")
    end_address = payload.get("endAddress")
    cidr: list[str] = []
    if isinstance(start_address, str) and isinstance(end_address, str):
        try:
            cidr = [str(item) for item in ipaddress.summarize_address_range(ipaddress.ip_address(start_address), ipaddress.ip_address(end_address))]
        except ValueError:
            cidr = []

    entity_names = _extract_rdap_entity_names(payload)
    label = entity_names[0] if entity_names else None
    network_name = payload.get("name") if isinstance(payload.get("name"), str) else None
    handle = payload.get("handle") if isinstance(payload.get("handle"), str) else None
    country = payload.get("country") if isinstance(payload.get("country"), str) else None

    return NetworkIpWhoisResponse(
        ip_address=str(parsed_ip),
        scope="IP pubblico",
        rdap_status="ok",
        label=label,
        network_name=network_name,
        handle=handle,
        country=country,
        start_address=start_address if isinstance(start_address, str) else None,
        end_address=end_address if isinstance(end_address, str) else None,
        cidr=cidr,
        entities=entity_names,
        external_url=external_url,
        raw=payload,
    )


def _serialize_assigned_user(user: ApplicationUser) -> NetworkAssignedUserSummary:
    return NetworkAssignedUserSummary(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        full_name=user.full_name,
        office_location=user.office_location,
        phone_extension=user.phone_extension,
        is_placeholder_profile=((not user.is_active) and user.email.endswith("@users.local")),
    )


# fmt: on
