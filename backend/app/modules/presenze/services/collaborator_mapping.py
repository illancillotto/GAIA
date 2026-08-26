from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.presenze.mapping_audit import PresenzeCollaboratorMappingAudit
from app.modules.presenze.models import (
    PresenzeCollaborator,
    PresenzeDailyRecord,
    PresenzeEventSummary,
)

MAPPING_UNIQUE_INDEX = "uq_presenze_collaborators_application_user_id"


class CollaboratorMappingConflictError(Exception):
    pass


def apply_collaborator_mapping(
    db: Session,
    *,
    collaborator: PresenzeCollaborator,
    application_user_id: int | None,
    changed_by: ApplicationUser,
    reason: str,
) -> bool:
    previous_user_id = collaborator.application_user_id
    if previous_user_id == application_user_id:
        return False
    if application_user_id is not None and _mapping_owner_exists(
        db, application_user_id=application_user_id, excluded_collaborator_id=collaborator.id
    ):
        raise CollaboratorMappingConflictError

    collaborator.application_user_id = application_user_id
    db.add(collaborator)
    db.add(
        PresenzeCollaboratorMappingAudit(
            collaborator_id=collaborator.id,
            previous_application_user_id=previous_user_id,
            new_application_user_id=application_user_id,
            changed_by_user_id=changed_by.id,
            changed_by_username=changed_by.username,
            action=_mapping_action(previous_user_id, application_user_id),
            source="api",
            reason=reason.strip(),
        )
    )
    db.query(PresenzeDailyRecord).filter(PresenzeDailyRecord.collaborator_id == collaborator.id).update(
        {"application_user_id": application_user_id}
    )
    db.query(PresenzeEventSummary).filter(PresenzeEventSummary.collaborator_id == collaborator.id).update(
        {"application_user_id": application_user_id}
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _is_mapping_unique_violation(exc):
            raise CollaboratorMappingConflictError from exc
        raise
    return True


def list_collaborator_mapping_audit(
    db: Session, collaborator_id: uuid.UUID
) -> list[PresenzeCollaboratorMappingAudit]:
    return list(
        db.scalars(
            select(PresenzeCollaboratorMappingAudit)
            .where(PresenzeCollaboratorMappingAudit.collaborator_id == collaborator_id)
            .order_by(
                PresenzeCollaboratorMappingAudit.created_at.desc(),
                PresenzeCollaboratorMappingAudit.id.desc(),
            )
        )
    )


def _mapping_owner_exists(
    db: Session, *, application_user_id: int, excluded_collaborator_id: uuid.UUID
) -> bool:
    owner_id = db.scalar(
        select(PresenzeCollaborator.id).where(
            PresenzeCollaborator.application_user_id == application_user_id,
            PresenzeCollaborator.id != excluded_collaborator_id,
        )
    )
    return owner_id is not None


def _mapping_action(previous_user_id: int | None, new_user_id: int | None) -> str:
    if previous_user_id is None:
        return "map"
    if new_user_id is None:
        return "unmap"
    return "remap"


def _is_mapping_unique_violation(exc: IntegrityError) -> bool:
    constraint_name = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
    if constraint_name == MAPPING_UNIQUE_INDEX:
        return True
    message = str(exc.orig)
    return MAPPING_UNIQUE_INDEX in message or (
        "UNIQUE constraint failed" in message
        and "presenze_collaborators.application_user_id" in message
    )
