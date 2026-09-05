from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.gis import catalog_queries, services
from app.modules.gis.schemas import (
    GisLayerFeatureListResponse,
    GisLayerMetadataUpdate,
    GisLayerResponse,
)

router = APIRouter()


# Preserve the measured legacy layout while keeping the new module formatter-safe.
# fmt: off
@router.get("/layers/{layer_id}", response_model=GisLayerResponse)
def get_layer(
    layer_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisLayerResponse:
    return services.get_layer(db, layer_id, current_user)


@router.patch("/layers/{layer_id}/metadata", response_model=GisLayerResponse)
def update_layer_metadata(
    layer_id: UUID,
    body: GisLayerMetadataUpdate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisLayerResponse:
    return services.update_layer_metadata(db, layer_id, body, current_user)


@router.post("/layers/{layer_id}/activate", response_model=GisLayerResponse)
def activate_layer(
    layer_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisLayerResponse:
    return services.set_layer_active(db, layer_id, True, current_user)


@router.post("/layers/{layer_id}/deactivate", response_model=GisLayerResponse)
def deactivate_layer(
    layer_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GisLayerResponse:
    return services.set_layer_active(db, layer_id, False, current_user)


@router.get("/layers/{layer_id}/features", response_model=GisLayerFeatureListResponse)
def list_layer_features(
    layer_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    query: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
) -> GisLayerFeatureListResponse:
    return catalog_queries.list_layer_features(
        db,
        layer_id,
        current_user,
        query=query,
        limit=limit,
        offset=offset,
    )
# fmt: on
