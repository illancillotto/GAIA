from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_admin_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.schemas.catasto_phase1 import (
    CatDeliveryPointsImportConfigResponse,
    CatDeliveryPointsImportConfigUpdateRequest,
    CatDeliveryPointsImportRunResponse,
)
from app.modules.catasto.services.delivery_points_config import (
    config_metadata,
    get_or_create_delivery_points_import_config,
    run_delivery_points_import_from_config,
    update_delivery_points_import_config,
)

router = APIRouter(prefix="/catasto/delivery-points", tags=["catasto-delivery-points-admin"])


@router.get("/import-config", response_model=CatDeliveryPointsImportConfigResponse)
def get_delivery_points_import_config(
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_admin_user),
) -> CatDeliveryPointsImportConfigResponse:
    config = get_or_create_delivery_points_import_config(db)
    metadata = config_metadata(config)
    return CatDeliveryPointsImportConfigResponse(
        root_path=metadata["root_path"],
        expected_with_meter_dir=str(metadata["expected_with_meter_dir"]),
        expected_without_meter_dir=str(metadata["expected_without_meter_dir"]),
        updated_by=metadata["updated_by"],
        updated_at=config.updated_at,
    )


@router.patch("/import-config", response_model=CatDeliveryPointsImportConfigResponse)
def patch_delivery_points_import_config(
    payload: CatDeliveryPointsImportConfigUpdateRequest,
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_admin_user),
) -> CatDeliveryPointsImportConfigResponse:
    config = update_delivery_points_import_config(
        db,
        root_path=payload.root_path,
        current_user=current_user,
    )
    metadata = config_metadata(config)
    return CatDeliveryPointsImportConfigResponse(
        root_path=metadata["root_path"],
        expected_with_meter_dir=str(metadata["expected_with_meter_dir"]),
        expected_without_meter_dir=str(metadata["expected_without_meter_dir"]),
        updated_by=metadata["updated_by"],
        updated_at=config.updated_at,
    )


@router.post("/import-from-config", response_model=CatDeliveryPointsImportRunResponse)
def import_delivery_points_from_config(
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_admin_user),
) -> CatDeliveryPointsImportRunResponse:
    try:
        config, stats = run_delivery_points_import_from_config(db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CatDeliveryPointsImportRunResponse(
        root_path=config.root_path or "",
        points_processed=stats["points_processed"],
        canals_processed=stats["canals_processed"],
        meter_readings_linked=stats["meter_readings_linked"],
        meter_readings_unlinked=stats["meter_readings_unlinked"],
    )
