from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.application_user import ApplicationUser
from app.models.catasto_phase1 import CatDeliveryPointsImportConfig, CatDeliveryPointsImportJob
from app.modules.catasto.services.delivery_points_import import (
    POINT_FOLDER_WITH_METER,
    POINT_FOLDER_WITHOUT_METER,
    import_delivery_points_2026_def,
)


_DELIVERY_POINTS_IMPORT_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="delivery-points-import")


def get_or_create_delivery_points_import_config(db: Session) -> CatDeliveryPointsImportConfig:
    config = db.get(CatDeliveryPointsImportConfig, 1)
    if config is not None:
        return config
    config = CatDeliveryPointsImportConfig(id=1)
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def update_delivery_points_import_config(
    db: Session,
    *,
    root_path: str | None,
    current_user: ApplicationUser | None,
) -> CatDeliveryPointsImportConfig:
    config = get_or_create_delivery_points_import_config(db)
    if root_path and root_path.strip():
        stripped_path = root_path.strip()
        normalized_path = (
            stripped_path
            if stripped_path.lower().startswith("smb://")
            else str(Path(stripped_path).expanduser())
        )
    else:
        normalized_path = None
    config.root_path = normalized_path
    config.updated_by = current_user.username if current_user is not None else "system"
    db.commit()
    db.refresh(config)
    return config


def run_delivery_points_import_from_config(db: Session) -> tuple[CatDeliveryPointsImportConfig, dict[str, int]]:
    config = get_or_create_delivery_points_import_config(db)
    if not config.root_path:
        raise ValueError("Cartella sorgente NAS non configurata.")
    stats = import_delivery_points_2026_def(db, root_path=config.root_path)
    return config, stats


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_delivery_points_import_job(
    db: Session,
    *,
    current_user: ApplicationUser | None,
) -> CatDeliveryPointsImportJob:
    config = get_or_create_delivery_points_import_config(db)
    if not config.root_path:
        raise ValueError("Cartella sorgente NAS non configurata.")

    running_job = db.execute(
        select(CatDeliveryPointsImportJob).where(CatDeliveryPointsImportJob.status.in_(("pending", "running")))
    ).scalar_one_or_none()
    if running_job is not None:
        raise ValueError("Import punti di consegna gia in corso.")

    job = CatDeliveryPointsImportJob(
        status="pending",
        root_path=config.root_path,
        requested_by=current_user.username if current_user is not None else "system",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_delivery_points_import_job(db: Session, job_id: UUID) -> CatDeliveryPointsImportJob | None:
    return db.get(CatDeliveryPointsImportJob, job_id)


def run_delivery_points_import_job(job_id: UUID) -> None:
    db = SessionLocal()
    try:
        job = db.get(CatDeliveryPointsImportJob, job_id)
        if job is None:
            return

        job.status = "running"
        job.started_at = _utc_now()
        job.updated_at = job.started_at
        db.commit()

        try:
            stats = import_delivery_points_2026_def(db, root_path=job.root_path)
        except Exception as exc:
            db.rollback()
            job = db.get(CatDeliveryPointsImportJob, job_id)
            if job is not None:
                completed_at = _utc_now()
                job.status = "failed"
                job.error_message = str(exc)
                job.completed_at = completed_at
                job.updated_at = completed_at
                db.commit()
            return

        job = db.get(CatDeliveryPointsImportJob, job_id)
        if job is None:
            return
        completed_at = _utc_now()
        job.status = "completed"
        job.points_processed = stats["points_processed"]
        job.canals_processed = stats["canals_processed"]
        job.meter_readings_linked = stats["meter_readings_linked"]
        job.meter_readings_unlinked = stats["meter_readings_unlinked"]
        job.completed_at = completed_at
        job.updated_at = completed_at
        db.commit()
    finally:
        db.close()


def submit_delivery_points_import_job(job_id: UUID) -> None:
    _DELIVERY_POINTS_IMPORT_EXECUTOR.submit(run_delivery_points_import_job, job_id)


def config_metadata(config: CatDeliveryPointsImportConfig) -> dict[str, str | None]:
    return {
        "root_path": config.root_path,
        "expected_with_meter_dir": POINT_FOLDER_WITH_METER,
        "expected_without_meter_dir": POINT_FOLDER_WITHOUT_METER,
        "updated_by": config.updated_by,
    }
