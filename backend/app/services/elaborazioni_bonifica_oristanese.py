from __future__ import annotations

from datetime import datetime, timezone
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bonifica_oristanese import BonificaOristaneseCredential
from app.modules.elaborazioni.bonifica_oristanese.models import (
    BonificaOristaneseCredentialCreate,
    BonificaOristaneseCredentialOut,
    BonificaOristaneseCredentialTestResult,
    BonificaOristaneseCredentialUpdate,
)
from app.modules.elaborazioni.bonifica_oristanese.session import BonificaOristaneseSessionManager
from app.services.catasto_credentials import get_credential_fernet

logger = logging.getLogger(__name__)

_MAX_CONSECUTIVE_FAILURES = 5


def _encrypt(plaintext: str) -> str:
    return get_credential_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def _decrypt(ciphertext: str) -> str:
    return get_credential_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")


def create_credential(db: Session, data: BonificaOristaneseCredentialCreate) -> BonificaOristaneseCredentialOut:
    credential = BonificaOristaneseCredential(
        label=data.label.strip(),
        login_identifier=data.login_identifier.strip(),
        password_encrypted=_encrypt(data.password),
        remember_me=data.remember_me,
        active=data.active,
    )
    db.add(credential)
    db.commit()
    db.refresh(credential)
    return BonificaOristaneseCredentialOut.model_validate(credential)


def list_credentials(db: Session) -> list[BonificaOristaneseCredentialOut]:
    rows = db.scalars(
        select(BonificaOristaneseCredential).order_by(BonificaOristaneseCredential.id.asc())
    ).all()
    return [BonificaOristaneseCredentialOut.model_validate(row) for row in rows]


def get_credential(db: Session, credential_id: int) -> BonificaOristaneseCredential | None:
    return db.get(BonificaOristaneseCredential, credential_id)


def update_credential(
    db: Session,
    credential_id: int,
    data: BonificaOristaneseCredentialUpdate,
) -> BonificaOristaneseCredentialOut | None:
    credential = db.get(BonificaOristaneseCredential, credential_id)
    if credential is None:
        return None
    if data.label is not None:
        credential.label = data.label.strip()
    if data.login_identifier is not None:
        credential.login_identifier = data.login_identifier.strip()
    if data.password is not None:
        credential.password_encrypted = _encrypt(data.password)
    if data.remember_me is not None:
        credential.remember_me = data.remember_me
    if data.active is not None:
        credential.active = data.active
        if data.active:
            credential.consecutive_failures = 0
    db.commit()
    db.refresh(credential)
    return BonificaOristaneseCredentialOut.model_validate(credential)


def delete_credential(db: Session, credential_id: int) -> bool:
    credential = db.get(BonificaOristaneseCredential, credential_id)
    if credential is None:
        return False
    db.delete(credential)
    db.commit()
    return True


def pick_credential(db: Session, credential_id: int | None = None) -> tuple[BonificaOristaneseCredential, str]:
    if credential_id is not None:
        credential = db.get(BonificaOristaneseCredential, credential_id)
        if credential is None:
            raise RuntimeError(f"Credenziale Bonifica Oristanese {credential_id} non trovata")
        if not credential.active:
            raise RuntimeError(f"Credenziale Bonifica Oristanese {credential_id} non attiva")
        return credential, _decrypt(credential.password_encrypted)

    credential = db.scalar(
        select(BonificaOristaneseCredential)
        .where(BonificaOristaneseCredential.active.is_(True))
        .order_by(
            BonificaOristaneseCredential.last_used_at.asc().nullsfirst(),
            BonificaOristaneseCredential.id.asc(),
        )
    )
    if credential is None:
        raise RuntimeError("Nessuna credenziale Bonifica Oristanese attiva disponibile")
    return credential, _decrypt(credential.password_encrypted)


def mark_credential_used(db: Session, credential_id: int, authenticated_url: str | None = None) -> None:
    credential = db.get(BonificaOristaneseCredential, credential_id)
    if credential is None:
        return
    credential.last_used_at = datetime.now(timezone.utc)
    credential.last_authenticated_url = authenticated_url
    credential.last_error = None
    credential.consecutive_failures = 0
    db.commit()


def mark_credential_error(db: Session, credential_id: int, error: str) -> None:
    credential = db.get(BonificaOristaneseCredential, credential_id)
    if credential is None:
        return
    credential.last_error = error[:500]
    credential.consecutive_failures += 1
    if credential.consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
        credential.active = False
        logger.warning(
            "Bonifica Oristanese: credenziale id=%d disabilitata dopo %d fallimenti consecutivi",
            credential.id,
            credential.consecutive_failures,
        )
    db.commit()


async def test_credential(db: Session, credential_id: int) -> BonificaOristaneseCredentialTestResult:
    credential = db.get(BonificaOristaneseCredential, credential_id)
    if credential is None:
        return BonificaOristaneseCredentialTestResult(ok=False, error="Credenziale non trovata")

    manager = BonificaOristaneseSessionManager(
        login_identifier=credential.login_identifier,
        password=_decrypt(credential.password_encrypted),
        remember_me=credential.remember_me,
    )
    try:
        session = await manager.login()
        mark_credential_used(db, credential_id, authenticated_url=session.authenticated_url)
        return BonificaOristaneseCredentialTestResult(
            ok=True,
            authenticated_url=session.authenticated_url,
            cookies=",".join(session.cookie_names[:12]) if session.cookie_names else None,
            error=None,
        )
    except Exception as exc:
        mark_credential_error(db, credential_id, str(exc))
        return BonificaOristaneseCredentialTestResult(ok=False, error=str(exc))
    finally:
        await manager.close()
