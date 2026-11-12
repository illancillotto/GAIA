"""Consult tax and cadastral history without creating or refreshing control cases."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import require_module, require_section
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.ruolo.services import parcel_history

router = APIRouter(
    prefix="/particelle/storia",
    tags=["ruolo-storia-particelle"],
    dependencies=[Depends(require_module("ruolo"))],
)
Database = Annotated[Session, Depends(get_db)]
Reader = Annotated[ApplicationUser, Depends(require_section("ruolo.avvisi"))]


class HistoryFilters(BaseModel):
    comune: str = Field(default="", max_length=100)
    foglio: str = Field(default="", max_length=10)
    particella: str = Field(default="", max_length=20)
    search: str = Field(default="", max_length=100)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)


@router.get("")
def listing(
    db: Database, user: Reader, filters: Annotated[HistoryFilters, Query()], response: Response
):
    response.headers["Cache-Control"] = "private, no-store"
    return parcel_history.list_parcels(db, filters)


@router.get("/{identity}")
def detail(identity: UUID, db: Database, user: Reader, response: Response):
    response.headers["Cache-Control"] = "private, no-store"
    try:
        return parcel_history.history(db, identity, user.id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
