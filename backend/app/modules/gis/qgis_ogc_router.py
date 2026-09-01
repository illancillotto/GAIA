from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.gis import qgis_ogc_proxy

router = APIRouter()


@router.get("/ogc/layers/{layer_id}")
def proxy_qgis_ogc(
    layer_id: UUID,
    request: Request,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    payload = qgis_ogc_proxy.proxy_request(
        db,
        layer_id,
        current_user,
        request.query_params.multi_items(),
    )
    return Response(
        content=payload.content,
        status_code=payload.status_code,
        media_type=payload.media_type,
        headers={"X-GAIA-OGC-Mode": "read-only"},
    )


@router.post("/ogc/layers/{layer_id}")
def reject_qgis_wfs_transaction(
    layer_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    qgis_ogc_proxy.reject_write_request(db, layer_id, current_user)
