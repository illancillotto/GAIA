from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.organigramma.deps import require_organigramma_read_or_inaz
from app.repositories.application_user import get_application_user_by_id
from app.modules.organigramma.schemas import VisibilityResult
from app.modules.organigramma.services import organigramma_service as svc

router = APIRouter(prefix="/visibility", tags=["organigramma/visibility"])


@router.get(
    "/{user_id}",
    response_model=VisibilityResult,
    dependencies=[Depends(require_organigramma_read_or_inaz())],
)
def get_visibility(user_id: int, db: Annotated[Session, Depends(get_db)]) -> VisibilityResult:
    """Simulatore "Chi vede chi": visibilità effettiva (gerarchia ∪ override) del viewer."""
    viewer = get_application_user_by_id(db, user_id)
    if viewer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return svc.build_visibility_result(db, viewer)
