from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.dotazioni.models import DotazioneAsset
from app.modules.organigramma.models import OrgAssignment
from app.services.permission_resolver import can_access_section


def allowed(db: Session, actor: ApplicationUser, action: str) -> bool:
    return can_access_section(db, actor, f"dotazioni.{action}")


def require_action(db: Session, actor: ApplicationUser, action: str) -> None:
    if not allowed(db, actor, action):
        raise HTTPException(403, "Permesso Dotazioni insufficiente")


def member_unit_ids(db: Session, user_id: int) -> set:
    now = datetime.now(UTC)
    return set(
        db.scalars(
            select(OrgAssignment.org_unit_id).where(
                OrgAssignment.user_id == user_id,
                OrgAssignment.active.is_(True),
                (OrgAssignment.valid_from.is_(None) | (OrgAssignment.valid_from <= now)),
                (OrgAssignment.valid_to.is_(None) | (OrgAssignment.valid_to > now)),
            )
        ).all()
    )


def require_take_scope(
    db: Session, actor: ApplicationUser, asset: DotazioneAsset, holder_id: int
) -> None:
    require_action(db, actor, "custody")
    if allowed(db, actor, "manage"):
        return
    if holder_id != actor.id or asset.assigned_org_unit_id not in member_unit_ids(db, actor.id):
        raise HTTPException(403, "Dotazione fuori dal proprio perimetro")


def require_close_scope(db: Session, actor: ApplicationUser, holder_id: int) -> None:
    require_action(db, actor, "custody")
    if holder_id != actor.id and not allowed(db, actor, "manage"):
        raise HTTPException(403, "Solo il custode o un gestore puo chiudere la custodia")
