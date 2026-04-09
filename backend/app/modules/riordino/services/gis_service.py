"""GIS services."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.riordino.enums import EventType
from app.modules.riordino.models import RiordinoGisLink
from app.modules.riordino.repositories import PracticeRepository
from app.modules.riordino.services.common import create_event, utcnow


def list_gis_links(db: Session, practice_id: UUID) -> list[RiordinoGisLink]:
    return list(db.scalars(select(RiordinoGisLink).where(RiordinoGisLink.practice_id == practice_id).order_by(RiordinoGisLink.created_at.desc())))


def create_gis_link(db: Session, practice_id: UUID, data: dict, current_user) -> RiordinoGisLink:
    if not PracticeRepository(db).get(practice_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practice not found")
    link = RiordinoGisLink(practice_id=practice_id, **data)
    db.add(link)
    db.flush()
    create_event(db, practice_id=practice_id, created_by=current_user.id, event_type=EventType.gis_link_created, payload_json={"gis_link_id": str(link.id)})
    return link


def update_gis_link(db: Session, practice_id: UUID, link_id: UUID, data: dict, current_user) -> RiordinoGisLink:
    link = db.scalar(select(RiordinoGisLink).where(RiordinoGisLink.practice_id == practice_id, RiordinoGisLink.id == link_id))
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GIS link not found")
    for key, value in data.items():
        if value is not None:
            setattr(link, key, value)
    if "sync_status" in data:
        link.last_synced_at = utcnow()
    create_event(db, practice_id=practice_id, created_by=current_user.id, event_type=EventType.gis_updated, payload_json={"gis_link_id": str(link.id)})
    db.flush()
    return link
