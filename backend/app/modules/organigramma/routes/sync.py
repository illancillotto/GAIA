from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.organigramma.deps import require_organigramma_manage_or_inaz
from app.modules.organigramma.schemas import WhiteCompanySyncResult
from app.modules.organigramma.services.inaz_preview import (
    InazOrganizationPreview,
    InazOrganizationSnapshot,
    preview_inaz_organization,
)
from app.modules.organigramma.services.whitecompany_sync import sync_from_whitecompany

router = APIRouter(prefix="/sync", tags=["organigramma/sync"])


@router.post("/whitecompany", response_model=WhiteCompanySyncResult)
def sync_whitecompany(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_organigramma_manage_or_inaz())],
) -> WhiteCompanySyncResult:
    return sync_from_whitecompany(db, user_id=current_user.id)


@router.post("/inaz/preview", response_model=InazOrganizationPreview)
def preview_inaz(
    snapshot: InazOrganizationSnapshot,
    db: Annotated[Session, Depends(get_db)],
    _current_user: Annotated[ApplicationUser, Depends(require_organigramma_manage_or_inaz())],
) -> InazOrganizationPreview:
    return preview_inaz_organization(db, snapshot)
