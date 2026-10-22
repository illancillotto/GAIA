"""STEP credentials: Fernet-encrypted, auto-disabled after repeated failures."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.elaborazioni.step.models import StepCredential
from app.modules.elaborazioni.step.schemas import (
    StepCredentialCreate,
    StepCredentialOut,
    StepCredentialUpdate,
)
from app.services.catasto_credentials import get_credential_fernet

logger = logging.getLogger(__name__)

# STEP behaviour on repeated wrong logins is unknown: stop early to avoid an account lock.
MAX_CONSECUTIVE_FAILURES = 3


def _encrypt(plaintext: str) -> str:
    return get_credential_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_password(ciphertext: str) -> str:
    return get_credential_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")


def create_credential(db: Session, data: StepCredentialCreate) -> StepCredentialOut:
    credential = StepCredential(
        label=data.label.strip(),
        username=data.username.strip(),
        password_encrypted=_encrypt(data.password),
        portal_url=data.portal_url,
        active=data.active,
        min_delay_ms=data.min_delay_ms,
        consecutive_failures=0,
    )
    db.add(credential)
    db.commit()
    db.refresh(credential)
    return StepCredentialOut.model_validate(credential)


def list_credentials(db: Session) -> list[StepCredentialOut]:
    rows = db.scalars(select(StepCredential).order_by(StepCredential.id.asc())).all()
    return [StepCredentialOut.model_validate(row) for row in rows]


def update_credential(
    db: Session, credential_id: int, data: StepCredentialUpdate
) -> StepCredentialOut | None:
    credential = db.get(StepCredential, credential_id)
    if credential is None:
        return None
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    password = changes.pop("password", None)
    for name, value in changes.items():
        setattr(credential, name, value.strip() if name in {"label", "username"} else value)
    if password is not None:
        credential.password_encrypted = _encrypt(password)
    if data.active:
        credential.consecutive_failures = 0
    db.commit()
    db.refresh(credential)
    return StepCredentialOut.model_validate(credential)


def delete_credential(db: Session, credential_id: int) -> bool:
    credential = db.get(StepCredential, credential_id)
    if credential is None:
        return False
    db.delete(credential)
    db.commit()
    return True


def pick_credential(db: Session, credential_id: int | None = None) -> tuple[StepCredential, str]:
    if credential_id is not None:
        credential = db.get(StepCredential, credential_id)
        if credential is None or not credential.active:
            raise RuntimeError(f"Credenziale STEP {credential_id} non trovata o non attiva")
    else:
        credential = db.scalar(
            select(StepCredential)
            .where(StepCredential.active.is_(True))
            .order_by(StepCredential.last_used_at.asc().nullsfirst(), StepCredential.id.asc())
        )
        if credential is None:
            raise RuntimeError("Nessuna credenziale STEP attiva")
    return credential, decrypt_password(credential.password_encrypted)


def has_available_credential(db: Session, credential_id: int | None = None) -> bool:
    try:
        pick_credential(db, credential_id)
    except RuntimeError:
        return False
    return True


def mark_credential_used(db: Session, credential_id: int) -> None:
    credential = db.get(StepCredential, credential_id)
    if credential is None:
        return
    credential.last_used_at = datetime.now(UTC)
    credential.last_error = None
    credential.consecutive_failures = 0
    db.commit()


def mark_credential_error(db: Session, credential_id: int | None, error: str) -> None:
    credential = db.get(StepCredential, credential_id) if credential_id is not None else None
    if credential is None:
        return
    credential.last_error = error[:1000]
    credential.consecutive_failures += 1
    if credential.consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
        credential.active = False
        logger.warning(
            "STEP: credenziale id=%d disabilitata dopo %d fallimenti consecutivi",
            credential.id,
            credential.consecutive_failures,
        )
    db.commit()
