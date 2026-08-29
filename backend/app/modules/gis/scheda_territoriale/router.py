from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.gis.scheda_territoriale import service
from app.modules.gis.schemas import (
    GisSchedaTerritorialeCreate,
    GisSchedaTerritorialeResponse,
)

router = APIRouter()


@router.post(
    "/scheda-territoriale",
    response_model=GisSchedaTerritorialeResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_sheet(
    body: GisSchedaTerritorialeCreate,
    background_tasks: BackgroundTasks,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisSchedaTerritorialeResponse:
    sheet = service.request_sheet(db, current_user, body.particella_id)
    background_tasks.add_task(service.run_generation, sheet.id)
    return GisSchedaTerritorialeResponse.model_validate(sheet)


@router.get(
    "/scheda-territoriale/{sheet_id}",
    response_model=GisSchedaTerritorialeResponse,
)
def get_sheet(
    sheet_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisSchedaTerritorialeResponse:
    return GisSchedaTerritorialeResponse.model_validate(
        service.get_sheet(db, current_user, sheet_id)
    )


@router.get("/scheda-territoriale/{sheet_id}/pdf")
def download_sheet(
    sheet_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    content, filename = service.download_sheet(db, current_user, sheet_id)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
