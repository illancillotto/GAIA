from __future__ import annotations

from functools import lru_cache
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.elaborazioni import ElaborazioneConnectionTest, ElaborazioneConnectionTestStatus, ElaborazioneCredential
from app.schemas.elaborazioni import (
    ElaborazioneCredentialCreateRequest,
    ElaborazioneCredentialTestRequest,
    ElaborazioneCredentialUpdateRequest,
)


class ElaborazioneCredentialConfigurationError(Exception):
    pass


class ElaborazioneCredentialNotFoundError(Exception):
    pass


class ElaborazioneConnectionTestNotFoundError(Exception):
    pass


@lru_cache(maxsize=1)
def get_credential_fernet() -> Fernet:
    if not settings.credential_master_key:
        raise ElaborazioneCredentialConfigurationError(
            "CREDENTIAL_MASTER_KEY is not configured for runtime credentials",
        )
    try:
        return Fernet(settings.credential_master_key.encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise ElaborazioneCredentialConfigurationError(
            "CREDENTIAL_MASTER_KEY is invalid for Fernet",
        ) from exc


def _normalize_label(label: str | None, sister_username: str) -> str:
    normalized = (label or "").strip()
    return normalized or sister_username.strip()


def list_credentials_for_user(db: Session, user_id: int) -> list[ElaborazioneCredential]:
    return list(
        db.scalars(
            select(ElaborazioneCredential)
            .where(ElaborazioneCredential.user_id == user_id)
            .order_by(
                ElaborazioneCredential.is_default.desc(),
                ElaborazioneCredential.active.desc(),
                ElaborazioneCredential.updated_at.desc(),
                ElaborazioneCredential.created_at.desc(),
            )
        ).all()
    )


def get_credential_for_user(db: Session, user_id: int, credential_id: UUID) -> ElaborazioneCredential | None:
    credential = db.get(ElaborazioneCredential, credential_id)
    if credential is None or credential.user_id != user_id:
        return None
    return credential


def get_default_credential_for_user(db: Session, user_id: int) -> ElaborazioneCredential | None:
    credentials = list_credentials_for_user(db, user_id)
    for credential in credentials:
        if credential.is_default:
            return credential
    return credentials[0] if credentials else None


def _pick_runnable_credential(credentials: list[ElaborazioneCredential]) -> ElaborazioneCredential | None:
    for credential in credentials:
        if credential.is_default and credential.active:
            return credential
    for credential in credentials:
        if credential.active:
            return credential
    return None


def get_runnable_credential_for_user(db: Session, user_id: int) -> ElaborazioneCredential | None:
    return _pick_runnable_credential(list_credentials_for_user(db, user_id))


def require_credentials_for_user(db: Session, user_id: int) -> ElaborazioneCredential:
    credential = get_runnable_credential_for_user(db, user_id)
    if credential is None:
        raise ElaborazioneCredentialNotFoundError("Active SISTER credentials required before starting a batch")
    return credential


def _ensure_single_default(db: Session, user_id: int, selected_id: UUID | None) -> None:
    credentials = list_credentials_for_user(db, user_id)
    selected_exists = False
    for credential in credentials:
        should_be_default = credential.id == selected_id if selected_id is not None else False
        if credential.is_default != should_be_default:
            credential.is_default = should_be_default
        if should_be_default:
            selected_exists = True

    if selected_exists:
        db.flush()
        return

    promoted: ElaborazioneCredential | None = None
    for credential in credentials:
        if credential.active:
            promoted = credential
            break
    if promoted is None and credentials:
        promoted = credentials[0]
    if promoted is not None:
        promoted.is_default = True
    db.flush()


def create_credential(
    db: Session,
    user_id: int,
    payload: ElaborazioneCredentialCreateRequest,
) -> ElaborazioneCredential:
    encrypted_password = get_credential_fernet().encrypt(payload.sister_password.strip().encode("utf-8"))
    credentials = list_credentials_for_user(db, user_id)
    make_default = payload.is_default or not credentials

    credential = ElaborazioneCredential(
        user_id=user_id,
        label=_normalize_label(payload.label, payload.sister_username),
        sister_username=payload.sister_username.strip(),
        sister_password_encrypted=encrypted_password,
        convenzione=payload.convenzione.strip() if payload.convenzione else None,
        codice_richiesta=payload.codice_richiesta.strip() if payload.codice_richiesta else None,
        ufficio_provinciale=payload.ufficio_provinciale.strip(),
        active=payload.active,
        is_default=make_default,
    )
    db.add(credential)
    db.flush()

    if make_default:
        _ensure_single_default(db, user_id, credential.id)
    elif not any(item.is_default for item in credentials):
        _ensure_single_default(db, user_id, credential.id)

    db.commit()
    db.refresh(credential)
    return credential


def update_credential(
    db: Session,
    user_id: int,
    credential_id: UUID,
    payload: ElaborazioneCredentialUpdateRequest,
) -> ElaborazioneCredential:
    credential = get_credential_for_user(db, user_id, credential_id)
    if credential is None:
        raise ElaborazioneCredentialNotFoundError(f"SISTER credential {credential_id} not found")

    if payload.label is not None:
        credential.label = _normalize_label(payload.label, payload.sister_username or credential.sister_username)
    if payload.sister_username is not None:
        credential.sister_username = payload.sister_username.strip()
        if payload.label is None and credential.label.strip() == "":
            credential.label = credential.sister_username
    if payload.sister_password is not None:
        credential.sister_password_encrypted = get_credential_fernet().encrypt(payload.sister_password.strip().encode("utf-8"))
    if payload.convenzione is not None:
        credential.convenzione = payload.convenzione.strip() or None
    if payload.codice_richiesta is not None:
        credential.codice_richiesta = payload.codice_richiesta.strip() or None
    if payload.ufficio_provinciale is not None:
        credential.ufficio_provinciale = payload.ufficio_provinciale.strip()
    if payload.active is not None:
        credential.active = payload.active
    if payload.is_default is not None:
        credential.is_default = payload.is_default

    db.flush()

    if credential.is_default:
        _ensure_single_default(db, user_id, credential.id)
    elif payload.active is False or payload.is_default is False:
        _ensure_single_default(db, user_id, None)

    db.commit()
    db.refresh(credential)
    return credential


def delete_credential(db: Session, user_id: int, credential_id: UUID) -> bool:
    credential = get_credential_for_user(db, user_id, credential_id)
    if credential is None:
        return False
    was_default = credential.is_default
    db.delete(credential)
    db.flush()
    if was_default:
        _ensure_single_default(db, user_id, None)
    db.commit()
    return True


def decrypt_credentials_password(credential: ElaborazioneCredential) -> str:
    try:
        return get_credential_fernet().decrypt(credential.sister_password_encrypted).decode("utf-8")
    except InvalidToken as exc:
        raise ElaborazioneCredentialConfigurationError(
            "Stored runtime credentials cannot be decrypted with current key",
        ) from exc


def decrypt_encrypted_secret(value: bytes) -> str:
    try:
        return get_credential_fernet().decrypt(value).decode("utf-8")
    except InvalidToken as exc:
        raise ElaborazioneCredentialConfigurationError(
            "Stored runtime connection test cannot be decrypted with current key",
        ) from exc


def queue_credentials_connection_test(
    db: Session,
    user_id: int,
    payload: ElaborazioneCredentialTestRequest | None = None,
) -> ElaborazioneConnectionTest:
    credential_id: UUID | None = None
    persist_verification = False

    if payload is not None and payload.credential_id is not None:
        credential = get_credential_for_user(db, user_id, payload.credential_id)
        if credential is None:
            raise ElaborazioneCredentialNotFoundError(f"SISTER credential {payload.credential_id} not found")
        sister_username = credential.sister_username
        sister_password_encrypted = credential.sister_password_encrypted
        ufficio_provinciale = credential.ufficio_provinciale
        credential_id = credential.id
        persist_verification = True
    elif payload is not None and payload.sister_username and payload.sister_password:
        sister_username = payload.sister_username.strip()
        sister_password_encrypted = get_credential_fernet().encrypt(payload.sister_password.strip().encode("utf-8"))
        ufficio_provinciale = (payload.ufficio_provinciale or "ORISTANO Territorio").strip()
    else:
        credential = require_credentials_for_user(db, user_id)
        sister_username = credential.sister_username
        sister_password_encrypted = credential.sister_password_encrypted
        ufficio_provinciale = credential.ufficio_provinciale
        credential_id = credential.id
        persist_verification = True

    connection_test = ElaborazioneConnectionTest(
        user_id=user_id,
        credential_id=credential_id,
        sister_username=sister_username,
        sister_password_encrypted=sister_password_encrypted,
        ufficio_provinciale=ufficio_provinciale,
        persist_verification=persist_verification,
        status=ElaborazioneConnectionTestStatus.PENDING.value,
        message="Queued for elaborazioni worker",
    )
    db.add(connection_test)
    db.commit()
    db.refresh(connection_test)
    return connection_test


def get_connection_test_for_user(db: Session, user_id: int, test_id: UUID) -> ElaborazioneConnectionTest:
    connection_test = db.scalar(
        select(ElaborazioneConnectionTest).where(
            ElaborazioneConnectionTest.id == test_id,
            ElaborazioneConnectionTest.user_id == user_id,
        ),
    )
    if connection_test is None:
        raise ElaborazioneConnectionTestNotFoundError(f"Connection test {test_id} not found")
    return connection_test
