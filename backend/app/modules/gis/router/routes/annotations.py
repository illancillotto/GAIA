from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.gis import services
from app.modules.gis.schemas import (
    GisAnnotationCreate,
    GisAnnotationResponse,
    GisAnnotationStatus,
    GisAnnotationUpdate,
)

router = APIRouter()


# Preserve the measured legacy layout while keeping the new module formatter-safe.
# fmt: off
@router.get(
    "/layers/{layer_id}/annotations", response_model=list[GisAnnotationResponse]
)
def list_annotations(
    layer_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    status_filter: GisAnnotationStatus | None = Query(None, alias="status"),
    feature_id: str | None = None,
) -> list[GisAnnotationResponse]:
    return services.list_annotations(db, layer_id, current_user, status_filter=status_filter, feature_id=feature_id)


@router.post(
    "/layers/{layer_id}/annotations",
    response_model=GisAnnotationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_annotation(
    layer_id: UUID,
    body: GisAnnotationCreate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisAnnotationResponse:
    return services.create_annotation(db, layer_id, body, current_user)


@router.patch(
    "/layers/{layer_id}/annotations/{annotation_id}",
    response_model=GisAnnotationResponse,
)
def update_annotation(
    layer_id: UUID,
    annotation_id: UUID,
    body: GisAnnotationUpdate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisAnnotationResponse:
    return services.update_annotation(db, layer_id, annotation_id, body, current_user)


@router.post(
    "/layers/{layer_id}/annotations/{annotation_id}/in-review",
    response_model=GisAnnotationResponse,
)
def mark_annotation_in_review(
    layer_id: UUID,
    annotation_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisAnnotationResponse:
    return services.set_annotation_status(db, layer_id, annotation_id, GisAnnotationStatus.in_review, current_user)


@router.post(
    "/layers/{layer_id}/annotations/{annotation_id}/close",
    response_model=GisAnnotationResponse,
)
def close_annotation(
    layer_id: UUID,
    annotation_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisAnnotationResponse:
    return services.set_annotation_status(db, layer_id, annotation_id, GisAnnotationStatus.closed, current_user)


@router.post(
    "/layers/{layer_id}/annotations/{annotation_id}/reject",
    response_model=GisAnnotationResponse,
)
def reject_annotation(
    layer_id: UUID,
    annotation_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisAnnotationResponse:
    return services.set_annotation_status(db, layer_id, annotation_id, GisAnnotationStatus.rejected, current_user)
# fmt: on
