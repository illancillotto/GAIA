from __future__ import annotations

from datetime import datetime, timezone
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.inaz.models import InazCredential
from app.modules.inaz.schemas import InazCredentialCreate, InazCredentialResponse, InazCredentialTestResult, InazCredentialUpdate
from app.modules.inaz.services.live_login import test_login_with_credentials
from app.services.catasto_credentials import get_credential_fernet

logger = logging.getLogger(__name__)

_MAX_CONSECUTIVE_FAILURES = 5


def _encrypt(plaintext: str) -> str:
    return get_credential_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def _decrypt(ciphertext: str) -> str:
    return get_credential_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")


def user_can_access_credential(current_user: ApplicationUser, credential: InazCredential) -> bool:
    return current_user.role in {"admin", "super_admin"} or credential.application_user_id == current_user.id


def create_credential(db: Session, owner_user_id: int, data: InazCredentialCreate) -> InazCredentialResponse:
    credential = InazCredential(
        application_user_id=owner_user_id,
        label=data.label.strip(),
        username=data.username.strip(),
        password_encrypted=_encrypt(data.password),
        active=data.active,
    )
    db.add(credential)
    db.commit()
    db.refresh(credential)
    return InazCredentialResponse.model_validate(credential)


def list_credentials(db: Session, current_user: ApplicationUser) -> list[InazCredentialResponse]:
    stmt = select(InazCredential)
    if current_user.role not in {"admin", "super_admin"}:
        stmt = stmt.where(InazCredential.application_user_id == current_user.id)
    rows = db.scalars(stmt.order_by(InazCredential.id.asc())).all()
    return [InazCredentialResponse.model_validate(row) for row in rows]


def get_credential(db: Session, credential_id: int, current_user: ApplicationUser | None = None) -> InazCredential | None:
    credential = db.get(InazCredential, credential_id)
    if credential is None:
        return None
    if current_user is not None and not user_can_access_credential(current_user, credential):
        return None
    return credential


def update_credential(db: Session, credential_id: int, current_user: ApplicationUser, data: InazCredentialUpdate) -> InazCredentialResponse | None:
    credential = get_credential(db, credential_id, current_user)
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
    db.commit()
    db.refresh(credential)
    return InazCredentialResponse.model_validate(credential)


def delete_credential(db: Session, credential_id: int, current_user: ApplicationUser) -> bool:
    credential = get_credential(db, credential_id, current_user)
    if credential is None:
        return False
    db.delete(credential)
    db.commit()
    return True


def pick_credential(db: Session, current_user: ApplicationUser, credential_id: int | None = None) -> tuple[InazCredential, str]:
    if credential_id is not None:
        credential = get_credential(db, credential_id, current_user)
        if credential is None:
            raise RuntimeError(f"Credenziale Inaz {credential_id} non trovata")
        if not credential.active:
            raise RuntimeError(f"Credenziale Inaz {credential_id} non attiva")
        return credential, _decrypt(credential.password_encrypted)

    credential = db.scalar(select(InazCredential).where(InazCredential.application_user_id == current_user.id, InazCredential.active.is_(True)))
    if credential is None:
        raise RuntimeError("Nessuna credenziale Inaz attiva disponibile")
    return credential, _decrypt(credential.password_encrypted)


def mark_credential_used(db: Session, credential_id: int, authenticated_url: str | None = None) -> None:
    credential = db.get(InazCredential, credential_id)
    if credential is None:
        return
    credential.last_used_at = datetime.now(timezone.utc)
    credential.last_authenticated_url = authenticated_url
    credential.last_error = None
    credential.consecutive_failures = 0
    db.commit()


def mark_credential_error(db: Session, credential_id: int, error: str) -> None:
    credential = db.get(InazCredential, credential_id)
    if credential is None:
        return
    credential.last_error = error[:500]
    credential.consecutive_failures += 1
    if credential.consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
        credential.active = False
        logger.warning(
            "Inaz: credenziale id=%d disabilitata dopo %d fallimenti consecutivi",
            credential.id,
            credential.consecutive_failures,
        )
    db.commit()


async def test_credential(db: Session, current_user: ApplicationUser, credential_id: int) -> InazCredentialTestResult:
    credential = get_credential(db, credential_id, current_user)
    if credential is None:
        return InazCredentialTestResult(ok=False, error="Credenziale non trovata")

    try:
        result = await test_login_with_credentials(
            username=credential.username,
            password=_decrypt(credential.password_encrypted),
        )
        mark_credential_used(db, credential_id, result["authenticated_url"])
        return InazCredentialTestResult(
            ok=True,
            authenticated_url=result["authenticated_url"],
            cookies=result["cookies"],
            error=None,
        )
    except Exception as exc:
        mark_credential_error(db, credential_id, str(exc))
        return InazCredentialTestResult(ok=False, error=str(exc))
