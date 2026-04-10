"""GIS routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_module, require_section
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.riordino.schemas import GisLinkCreate, GisLinkResponse, GisLinkUpdate
from app.modules.riordino.services import create_gis_link, list_gis_links, update_gis_link

router = APIRouter(dependencies=[Depends(require_module("riordino")), Depends(require_section("riordino.gis"))])


@router.post("/{practice_id}/gis-links", response_model=GisLinkResponse)
def create_gis_link_endpoint(
    practice_id: UUID,
    payload: GisLinkCreate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    link = create_gis_link(db, practice_id, payload.model_dump(), current_user)
    db.commit()
    db.refresh(link)
    return link


@router.get("/{practice_id}/gis-links", response_model=list[GisLinkResponse])
def list_gis_links_endpoint(
    practice_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return [GisLinkResponse.model_validate(item) for item in list_gis_links(db, practice_id)]


@router.patch("/{practice_id}/gis-links/{link_id}", response_model=GisLinkResponse)
def update_gis_link_endpoint(
    practice_id: UUID,
    link_id: UUID,
    payload: GisLinkUpdate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    link = update_gis_link(db, practice_id, link_id, payload.model_dump(exclude_unset=True), current_user)
    db.commit()
    db.refresh(link)
    return link
