"""An explicit document revision never creates or sends a communication."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import require_section
from app.core.database import get_db
from app.models.application_user import ApplicationUser

from .policy import Conflict, Missing
from .source_repair import complete_portal_snapshot

router = APIRouter()


@router.post("/ruolo/candidates/{identity}/complete-portal-snapshot")
def complete_snapshot(
    identity: UUID,
    expected_source_sha256: str = Query(pattern=r"^[a-f0-9]{64}$"),
    db: Session = Depends(get_db),
    user: ApplicationUser = Depends(require_section("ruolo.tributi.manage_status")),
):
    try:
        result = complete_portal_snapshot(db, identity, expected_source_sha256, user.id)
        db.commit()
        return result
    except Missing as exc:
        db.rollback()
        raise HTTPException(404, detail=str(exc)) from exc
    except Conflict as exc:
        db.rollback()
        raise HTTPException(409, detail=str(exc)) from exc
