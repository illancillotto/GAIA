from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.search.schemas import OperationalSearchResponse
from app.modules.search.service import search_operational


router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=OperationalSearchResponse)
def operational_search(
    q: Annotated[str, Query(min_length=2, max_length=120)],
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    limit: Annotated[int, Query(ge=1, le=30)] = 12,
) -> OperationalSearchResponse:
    return search_operational(db, current_user, q, limit=limit)
