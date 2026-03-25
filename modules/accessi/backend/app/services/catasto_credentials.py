from __future__ import annotations

from functools import lru_cache
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.catasto import CatastoConnectionTest, CatastoConnectionTestStatus, CatastoCredential
from app.schemas.catasto import CatastoCredentialUpsertRequest


class CatastoCredentialConfigurationError(Exception):
    pass


class CatastoCredentialNotFoundError(Exception):
    pass


class CatastoConnectionTestNotFoundError(Exception):
    pass


@lru_cache(maxsize=1)
def get_credential_fernet() -> Fernet:
    if not settings.credential_master_key:
        raise CatastoCredentialConfigurationError(
            "CREDENTIAL_MASTER_KEY is not configured for Catasto credentials",
        )
    try:
        return Fernet(settings.credential_master_key.encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise CatastoCredentialConfigurationError(
            "CREDENTIAL_MASTER_KEY is invalid for Fernet",
        ) from exc


def get_credentials_for_user(db: Session, user_id: int) -> CatastoCredential | None:
    return db.scalar(select(CatastoCredential).where(CatastoCredential.user_id == user_id))


def require_credentials_for_user(db: Session, user_id: int) -> CatastoCredential:
    credential = get_credentials_for_user(db, user_id)
    if credential is None:
        raise CatastoCredentialNotFoundError("Saved SISTER credentials required before starting a batch")
    return credential


def upsert_credentials(
    db: Session,
    user_id: int,
    payload: CatastoCredentialUpsertRequest,
) -> CatastoCredential:
    encrypted_password = get_credential_fernet().encrypt(payload.sister_password.strip().encode("utf-8"))
    credential = get_credentials_for_user(db, user_id)
    if credential is None:
        credential = CatastoCredential(
            user_id=user_id,
            sister_username=payload.sister_username.strip(),
            sister_password_encrypted=encrypted_password,
            convenzione=payload.convenzione.strip() if payload.convenzione else None,
            codice_richiesta=payload.codice_richiesta.strip() if payload.codice_richiesta else None,
            ufficio_provinciale=payload.ufficio_provinciale.strip(),
        )
        db.add(credential)
    else:
        credential.sister_username = payload.sister_username.strip()
        credential.sister_password_encrypted = encrypted_password
        credential.convenzione = payload.convenzione.strip() if payload.convenzione else None
        credential.codice_richiesta = payload.codice_richiesta.strip() if payload.codice_richiesta else None
        credential.ufficio_provinciale = payload.ufficio_provinciale.strip()
    db.commit()
    db.refresh(credential)
    return credential


def delete_credentials(db: Session, user_id: int) -> bool:
    credential = get_credentials_for_user(db, user_id)
    if credential is None:
        return False
    db.delete(credential)
    db.commit()
    return True


def decrypt_credentials_password(credential: CatastoCredential) -> str:
    try:
        return get_credential_fernet().decrypt(credential.sister_password_encrypted).decode("utf-8")
    except InvalidToken as exc:
        raise CatastoCredentialConfigurationError(
            "Stored Catasto credentials cannot be decrypted with current key",
        ) from exc


def decrypt_encrypted_secret(value: bytes) -> str:
    try:
        return get_credential_fernet().decrypt(value).decode("utf-8")
    except InvalidToken as exc:
        raise CatastoCredentialConfigurationError(
            "Stored Catasto connection test cannot be decrypted with current key",
        ) from exc


def queue_credentials_connection_test(
    db: Session,
    user_id: int,
    payload: CatastoCredentialUpsertRequest | None = None,
) -> CatastoConnectionTest:
    credential = get_credentials_for_user(db, user_id)

    if payload is None:
        if credential is None:
            raise CatastoCredentialNotFoundError("Saved SISTER credentials required before testing the connection")
        sister_username = credential.sister_username
        sister_password_encrypted = credential.sister_password_encrypted
        ufficio_provinciale = credential.ufficio_provinciale
        credential_id = credential.id
        persist_verification = True
    else:
        sister_username = payload.sister_username.strip()
        sister_password_encrypted = get_credential_fernet().encrypt(payload.sister_password.strip().encode("utf-8"))
        ufficio_provinciale = payload.ufficio_provinciale.strip()
        credential_id = None
        persist_verification = False

    connection_test = CatastoConnectionTest(
        user_id=user_id,
        credential_id=credential_id,
        sister_username=sister_username,
        sister_password_encrypted=sister_password_encrypted,
        ufficio_provinciale=ufficio_provinciale,
        persist_verification=persist_verification,
        status=CatastoConnectionTestStatus.PENDING.value,
        message="Queued for Catasto worker",
    )
    db.add(connection_test)
    db.commit()
    db.refresh(connection_test)
    return connection_test


def get_connection_test_for_user(db: Session, user_id: int, test_id: UUID) -> CatastoConnectionTest:
    connection_test = db.scalar(
        select(CatastoConnectionTest).where(
            CatastoConnectionTest.id == test_id,
            CatastoConnectionTest.user_id == user_id,
        ),
    )
    if connection_test is None:
        raise CatastoConnectionTestNotFoundError(f"Connection test {test_id} not found")
    return connection_test
