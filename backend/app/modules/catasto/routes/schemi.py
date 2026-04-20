from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.models.catasto_phase1 import CatSchemaContributo
from app.schemas.catasto_phase1 import CatSchemaContributoResponse

router = APIRouter(prefix="/catasto/schemi", tags=["catasto-schemi"])


@router.get("/", response_model=list[CatSchemaContributoResponse])
def list_schemi(db: Session = Depends(get_db), _: ApplicationUser = Depends(require_active_user)) -> list[CatSchemaContributo]:
    return list(db.execute(select(CatSchemaContributo).order_by(CatSchemaContributo.codice)).scalars().all())

