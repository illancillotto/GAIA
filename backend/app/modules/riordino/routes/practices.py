"""Practice and timeline routes."""

from __future__ import annotations

import math
from io import BytesIO
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_module, require_section
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.riordino.schemas import EventResponse, PracticeCreate, PracticeDetailResponse, PracticeListResponse, PracticeResponse, PracticeUpdate
from app.modules.riordino.services import (
    archive_practice,
    complete_practice,
    create_practice,
    delete_practice,
    export_practice_dossier_zip,
    export_practice_summary_csv,
    get_practice_detail,
    list_practices,
    update_practice,
)

router = APIRouter(dependencies=[Depends(require_module("riordino")), Depends(require_section("riordino.practices"))])


@router.post("", response_model=PracticeResponse, status_code=status.HTTP_201_CREATED)
def create_practice_endpoint(
    payload: PracticeCreate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    practice = create_practice(db, payload.model_dump(), current_user.id)
    db.commit()
    db.refresh(practice)
    return practice


@router.get("", response_model=PracticeListResponse)
def list_practices_endpoint(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    status_filter: str | None = Query(None, alias="status"),
    municipality: str | None = None,
    phase: str | None = None,
    owner: int | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
):
    items, total = list_practices(db, status_filter=status_filter, municipality=municipality, phase=phase, owner=owner, page=page, per_page=per_page)
    return PracticeListResponse(
        items=[PracticeResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=math.ceil(total / per_page) if per_page else 0,
    )


@router.get("/{practice_id}", response_model=PracticeDetailResponse)
def get_practice_detail_endpoint(
    practice_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    practice, counts = get_practice_detail(db, practice_id)
    response = PracticeDetailResponse.model_validate(practice)
    response.issues_count, response.appeals_count, response.documents_count = counts
    return response


@router.patch("/{practice_id}", response_model=PracticeResponse)
def update_practice_endpoint(
    practice_id: UUID,
    payload: PracticeUpdate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    practice = update_practice(db, practice_id, payload.model_dump(exclude_unset=True), current_user.id)
    db.commit()
    db.refresh(practice)
    return practice


@router.delete("/{practice_id}", response_model=PracticeResponse)
def delete_practice_endpoint(
    practice_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    practice = delete_practice(db, practice_id, current_user)
    db.commit()
    db.refresh(practice)
    return practice


@router.post("/{practice_id}/archive", response_model=PracticeResponse)
def archive_practice_endpoint(
    practice_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    practice = archive_practice(db, practice_id, current_user)
    db.commit()
    db.refresh(practice)
    return practice


@router.post("/{practice_id}/complete", response_model=PracticeResponse)
def complete_practice_endpoint(
    practice_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    practice = complete_practice(db, practice_id, current_user)
    db.commit()
    db.refresh(practice)
    return practice


@router.get("/{practice_id}/events", response_model=list[EventResponse])
def list_practice_events_endpoint(
    practice_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    practice, _ = get_practice_detail(db, practice_id)
    return [EventResponse.model_validate(event) for event in practice.events]


@router.get("/{practice_id}/export/summary")
def export_practice_summary_endpoint(
    practice_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, Depends(require_section("riordino.export"))],
    db: Annotated[Session, Depends(get_db)],
):
    content, filename = export_practice_summary_csv(db, practice_id)
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{practice_id}/export/dossier")
def export_practice_dossier_endpoint(
    practice_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, Depends(require_section("riordino.export"))],
    db: Annotated[Session, Depends(get_db)],
):
    archive_buffer, filename = export_practice_dossier_zip(db, practice_id)
    return StreamingResponse(
        archive_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
