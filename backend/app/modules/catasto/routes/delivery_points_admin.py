from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
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
    create_delivery_points_import_job,
    get_delivery_points_import_job,
    get_or_create_delivery_points_import_config,
    submit_delivery_points_import_job,
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


def _job_response(job) -> CatDeliveryPointsImportRunResponse:
    return CatDeliveryPointsImportRunResponse(
        job_id=job.id,
        status=job.status,
        root_path=job.root_path,
        requested_by=job.requested_by,
        error_message=job.error_message,
        points_processed=job.points_processed,
        canals_processed=job.canals_processed,
        meter_readings_linked=job.meter_readings_linked,
        meter_readings_unlinked=job.meter_readings_unlinked,
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.post("/import-from-config", response_model=CatDeliveryPointsImportRunResponse)
def import_delivery_points_from_config(
    db: Session = Depends(get_db),
    current_user: ApplicationUser = Depends(require_admin_user),
) -> CatDeliveryPointsImportRunResponse:
    try:
        job = create_delivery_points_import_job(db, current_user=current_user)
    except ValueError as exc:
        message = str(exc)
        status_code = status.HTTP_409_CONFLICT if "gia in corso" in message else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=message) from exc
    submit_delivery_points_import_job(job.id)
    return _job_response(job)


@router.get("/import-jobs/{job_id}", response_model=CatDeliveryPointsImportRunResponse)
def get_delivery_points_import_job_status(
    job_id: UUID,
    db: Session = Depends(get_db),
    _: ApplicationUser = Depends(require_admin_user),
) -> CatDeliveryPointsImportRunResponse:
    job = get_delivery_points_import_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import punti di consegna non trovato.")
    return _job_response(job)
