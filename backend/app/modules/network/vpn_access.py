from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.datetime_compat import UTC
from app.models.application_user import ApplicationUser
from app.modules.network.models import NetworkVpnDevice, NetworkVpnSession

ACTIVE_DEVICE_STATUS = "active"
REVOKED_DEVICE_STATUS = "revoked"
BLOCKED_DEVICE_STATUS = "blocked"


@dataclass(frozen=True)
class VpnAccessDecision:
    device: NetworkVpnDevice | None
    session: NetworkVpnSession
    allowed: bool
    reason: str | None = None


class VpnDeviceLimitExceeded(Exception):
    def __init__(self, *, max_devices: int) -> None:
        self.max_devices = max_devices
        super().__init__(f"Limite dispositivi VPN raggiunto ({max_devices})")


class VpnDeviceRevoked(Exception):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


def _clean_optional(value: str | None, *, limit: int) -> str | None:
    cleaned = (value or "").strip()
    if not cleaned:
        return None
    return cleaned[:limit]


def hash_user_agent(user_agent: str | None) -> str | None:
    cleaned = _clean_optional(user_agent, limit=2048)
    if cleaned is None:
        return None
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()


def build_vpn_device_fingerprint(*, client_device_id: str | None, user_agent: str | None) -> str:
    client_id = _clean_optional(client_device_id, limit=128)
    if client_id:
        source = f"gaia-client-device-id:{client_id}"
    else:
        source = f"user-agent-fallback:{_clean_optional(user_agent, limit=512) or 'unknown'}"
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def count_active_vpn_devices(db: Session, *, user_id: int) -> int:
    return db.scalar(
        select(func.count(NetworkVpnDevice.id)).where(
            NetworkVpnDevice.user_id == user_id,
            NetworkVpnDevice.status == ACTIVE_DEVICE_STATUS,
        )
    ) or 0


def _record_session(
    db: Session,
    *,
    user: ApplicationUser,
    event_type: str,
    client_ip: str | None,
    device_fingerprint: str,
    user_agent: str | None,
    device: NetworkVpnDevice | None = None,
    blocked_reason: str | None = None,
) -> NetworkVpnSession:
    session = NetworkVpnSession(
        user_id=user.id,
        device_id=device.id if device else None,
        source="gaia_login",
        event_type=event_type,
        username=user.username,
        client_ip=_clean_optional(client_ip, limit=64),
        device_fingerprint=device_fingerprint,
        user_agent_hash=hash_user_agent(user_agent),
        user_agent_sample=_clean_optional(user_agent, limit=512),
        blocked_reason=blocked_reason,
        observed_at=_now(),
    )
    db.add(session)
    return session


def register_vpn_login_device(
    db: Session,
    *,
    user: ApplicationUser,
    client_device_id: str | None,
    device_label: str | None,
    user_agent: str | None,
    client_ip: str | None,
    max_devices: int,
    enforcement_enabled: bool,
) -> VpnAccessDecision:
    normalized_max_devices = max(max_devices, 1)
    fingerprint = build_vpn_device_fingerprint(client_device_id=client_device_id, user_agent=user_agent)
    user_agent_hash = hash_user_agent(user_agent)
    now = _now()
    device = db.scalar(
        select(NetworkVpnDevice).where(
            NetworkVpnDevice.user_id == user.id,
            NetworkVpnDevice.device_fingerprint == fingerprint,
        )
    )

    if device is not None:
        if device.status in {REVOKED_DEVICE_STATUS, BLOCKED_DEVICE_STATUS}:
            session = _record_session(
                db,
                user=user,
                event_type="login_blocked",
                client_ip=client_ip,
                device_fingerprint=fingerprint,
                user_agent=user_agent,
                device=device,
                blocked_reason=f"device_{device.status}",
            )
            db.commit()
            raise VpnDeviceRevoked(f"Dispositivo VPN {device.status}")

        device.client_device_id = _clean_optional(client_device_id, limit=128)
        device.display_name = _clean_optional(device_label, limit=255) or device.display_name
        device.user_agent_hash = user_agent_hash
        device.user_agent_sample = _clean_optional(user_agent, limit=512)
        device.last_client_ip = _clean_optional(client_ip, limit=64)
        device.last_seen_at = now
        db.add(device)
        session = _record_session(
            db,
            user=user,
            event_type="login_allowed",
            client_ip=client_ip,
            device_fingerprint=fingerprint,
            user_agent=user_agent,
            device=device,
        )
        db.commit()
        db.refresh(device)
        db.refresh(session)
        return VpnAccessDecision(device=device, session=session, allowed=True)

    active_count = count_active_vpn_devices(db, user_id=user.id)
    if enforcement_enabled and active_count >= normalized_max_devices:
        session = _record_session(
            db,
            user=user,
            event_type="login_blocked",
            client_ip=client_ip,
            device_fingerprint=fingerprint,
            user_agent=user_agent,
            blocked_reason=f"max_active_devices:{normalized_max_devices}",
        )
        db.commit()
        db.refresh(session)
        raise VpnDeviceLimitExceeded(max_devices=normalized_max_devices)

    device = NetworkVpnDevice(
        user_id=user.id,
        device_fingerprint=fingerprint,
        client_device_id=_clean_optional(client_device_id, limit=128),
        display_name=_clean_optional(device_label, limit=255),
        status=ACTIVE_DEVICE_STATUS,
        user_agent_hash=user_agent_hash,
        user_agent_sample=_clean_optional(user_agent, limit=512),
        first_client_ip=_clean_optional(client_ip, limit=64),
        last_client_ip=_clean_optional(client_ip, limit=64),
        first_seen_at=now,
        last_seen_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(device)
    db.flush()
    session = _record_session(
        db,
        user=user,
        event_type="login_allowed",
        client_ip=client_ip,
        device_fingerprint=fingerprint,
        user_agent=user_agent,
        device=device,
    )
    db.commit()
    db.refresh(device)
    db.refresh(session)
    return VpnAccessDecision(device=device, session=session, allowed=True)


def list_vpn_devices(
    db: Session,
    *,
    user_id: int | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[NetworkVpnDevice], int]:
    query = select(NetworkVpnDevice)
    count_query = select(func.count(NetworkVpnDevice.id))
    if user_id is not None:
        query = query.where(NetworkVpnDevice.user_id == user_id)
        count_query = count_query.where(NetworkVpnDevice.user_id == user_id)
    if status:
        query = query.where(NetworkVpnDevice.status == status)
        count_query = count_query.where(NetworkVpnDevice.status == status)
    total = db.scalar(count_query) or 0
    devices = db.scalars(query.order_by(NetworkVpnDevice.last_seen_at.desc()).offset(skip).limit(limit)).all()
    return devices, total


def list_vpn_sessions(
    db: Session,
    *,
    user_id: int | None = None,
    event_type: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[NetworkVpnSession], int]:
    query = select(NetworkVpnSession)
    count_query = select(func.count(NetworkVpnSession.id))
    if user_id is not None:
        query = query.where(NetworkVpnSession.user_id == user_id)
        count_query = count_query.where(NetworkVpnSession.user_id == user_id)
    if event_type:
        query = query.where(NetworkVpnSession.event_type == event_type)
        count_query = count_query.where(NetworkVpnSession.event_type == event_type)
    total = db.scalar(count_query) or 0
    sessions = db.scalars(query.order_by(NetworkVpnSession.observed_at.desc()).offset(skip).limit(limit)).all()
    return sessions, total


def update_vpn_device_status(db: Session, *, device_id: int, status: str) -> NetworkVpnDevice | None:
    device = db.get(NetworkVpnDevice, device_id)
    if device is None:
        return None
    device.status = status
    device.updated_at = _now()
    db.add(device)
    db.commit()
    db.refresh(device)
    return device
