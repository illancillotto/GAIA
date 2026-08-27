from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.models.elaborazioni import ElaborazioneBatch, ElaborazioneCredential
from app.services.elaborazioni_credentials import (
    ElaborazioneCredentialNotFoundError,
    get_credential_for_user,
    require_credentials_for_user,
)


def require_batch_credentials(db: Session, batch: ElaborazioneBatch, user_id: int) -> None:
    if batch.credential_id is not None:
        credential = get_credential_for_user(db, user_id, batch.credential_id)
        if credential is None or not credential.active:
            raise ElaborazioneCredentialNotFoundError("Selected SISTER credential is not active anymore")
        return
    if batch.credential_ids is None:
        require_credentials_for_user(db, user_id)
        return
    _require_selected_credentials(db, batch.credential_ids, user_id)


def _require_selected_credentials(db: Session, values: list[str], user_id: int) -> None:
    try:
        selected_ids = {UUID(str(value)) for value in values}
    except (TypeError, ValueError) as exc:
        raise ElaborazioneCredentialNotFoundError("Selected SISTER credential list is invalid") from exc
    if not selected_ids:
        raise ElaborazioneCredentialNotFoundError("Select at least one SISTER credential or use the automatic pool")

    owner = db.get(ApplicationUser, user_id)
    statement = select(ElaborazioneCredential).where(
        ElaborazioneCredential.id.in_(selected_ids),
        ElaborazioneCredential.active.is_(True),
    )
    if owner is None or not owner.is_super_admin:
        statement = statement.where(ElaborazioneCredential.user_id == user_id)
    credentials = list(db.scalars(statement))
    if {credential.id for credential in credentials} != selected_ids:
        raise ElaborazioneCredentialNotFoundError("One or more selected SISTER credentials are missing or inactive")


__all__ = ["require_batch_credentials"]
