from __future__ import annotations

from datetime import datetime, timezone
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.capacitas import CapacitasCredential
from app.modules.elaborazioni.capacitas.models import (
    CapacitasCredentialCreate,
    CapacitasCredentialOut,
    CapacitasCredentialUpdate,
)
from app.modules.elaborazioni.capacitas.session import CapacitasSessionManager
from app.services.catasto_credentials import get_credential_fernet

logger = logging.getLogger(__name__)

_MAX_CONSECUTIVE_FAILURES = 5


def _encrypt(plaintext: str) -> str:
    return get_credential_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def _decrypt(ciphertext: str) -> str:
    return get_credential_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")


def create_credential(db: Session, data: CapacitasCredentialCreate) -> CapacitasCredentialOut:
    credential = CapacitasCredential(
        label=data.label.strip(),
        username=data.username.strip(),
        password_encrypted=_encrypt(data.password),
        active=data.active,
        allowed_hours_start=data.allowed_hours_start,
        allowed_hours_end=data.allowed_hours_end,
    )
    db.add(credential)
    db.commit()
    db.refresh(credential)
    return CapacitasCredentialOut.model_validate(credential)


def list_credentials(db: Session) -> list[CapacitasCredentialOut]:
    rows = db.scalars(select(CapacitasCredential).order_by(CapacitasCredential.id.asc())).all()
    return [CapacitasCredentialOut.model_validate(row) for row in rows]


def get_credential(db: Session, credential_id: int) -> CapacitasCredential | None:
    return db.get(CapacitasCredential, credential_id)


def update_credential(db: Session, credential_id: int, data: CapacitasCredentialUpdate) -> CapacitasCredentialOut | None:
    credential = db.get(CapacitasCredential, credential_id)
    if credential is None:
        return None
    if data.label is not None:
        credential.label = data.label.strip()
    if data.username is not None:
        credential.username = data.username.strip()
    if data.password is not None:
        credential.password_encrypted = _encrypt(data.password)
    if data.active is not None:
        credential.active = data.active
        if data.active:
            credential.consecutive_failures = 0
    if data.allowed_hours_start is not None:
        credential.allowed_hours_start = data.allowed_hours_start
    if data.allowed_hours_end is not None:
        credential.allowed_hours_end = data.allowed_hours_end
    db.commit()
    db.refresh(credential)
    return CapacitasCredentialOut.model_validate(credential)


def delete_credential(db: Session, credential_id: int) -> bool:
    credential = db.get(CapacitasCredential, credential_id)
    if credential is None:
        return False
    db.delete(credential)
    db.commit()
    return True


def _is_in_allowed_hours(credential: CapacitasCredential) -> bool:
    current_hour = datetime.now().hour
    start = credential.allowed_hours_start
    end = credential.allowed_hours_end
    if start <= end:
        return start <= current_hour <= end
    return current_hour >= start or current_hour <= end


def pick_credential(db: Session, credential_id: int | None = None) -> tuple[CapacitasCredential, str]:
    if credential_id is not None:
        credential = db.get(CapacitasCredential, credential_id)
        if credential is None:
            raise RuntimeError(f"Credenziale {credential_id} non trovata")
        if not credential.active:
            raise RuntimeError(f"Credenziale {credential_id} non attiva")
        if not _is_in_allowed_hours(credential):
            raise RuntimeError(
                f"Credenziale {credential_id} fuori fascia oraria "
                f"({credential.allowed_hours_start}-{credential.allowed_hours_end})",
            )
    else:
        candidates = db.scalars(
            select(CapacitasCredential)
            .where(CapacitasCredential.active.is_(True))
            .order_by(CapacitasCredential.last_used_at.asc().nullsfirst(), CapacitasCredential.id.asc()),
        ).all()
        candidates = [candidate for candidate in candidates if _is_in_allowed_hours(candidate)]
        if not candidates:
            raise RuntimeError(
                "Nessuna credenziale Capacitas disponibile: nessuna credenziale attiva nella fascia oraria corrente",
            )
        credential = candidates[0]

    return credential, _decrypt(credential.password_encrypted)


def mark_credential_used(db: Session, credential_id: int) -> None:
    credential = db.get(CapacitasCredential, credential_id)
    if credential is None:
        return
    credential.last_used_at = datetime.now(timezone.utc)
    credential.last_error = None
    credential.consecutive_failures = 0
    db.commit()


def mark_credential_error(db: Session, credential_id: int, error: str) -> None:
    credential = db.get(CapacitasCredential, credential_id)
    if credential is None:
        return
    credential.last_error = error[:500]
    credential.consecutive_failures += 1
    if credential.consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
        credential.active = False
        logger.warning(
            "Capacitas: credenziale id=%d disabilitata dopo %d fallimenti consecutivi",
            credential.id,
            credential.consecutive_failures,
        )
    db.commit()


async def test_credential(db: Session, credential_id: int) -> dict[str, str | bool | None]:
    credential = db.get(CapacitasCredential, credential_id)
    if credential is None:
        return {"ok": False, "token": None, "error": "Credenziale non trovata"}

    try:
        manager = CapacitasSessionManager(credential.username, _decrypt(credential.password_encrypted))
        session = await manager.login()
        await manager.close()
        mark_credential_used(db, credential_id)
        return {"ok": True, "token": f"{session.token[:8]}...", "error": None}
    except Exception as exc:
        mark_credential_error(db, credential_id, str(exc))
        return {"ok": False, "token": None, "error": str(exc)}
