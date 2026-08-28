from __future__ import annotations

import hashlib
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.application_user import ApplicationUser
from app.models.catasto_phase1 import CatParticella
from app.modules.gis import artifact_storage, services
from app.modules.gis.models import GisAuditLog, GisSchedaTerritoriale
from app.modules.gis.scheda_territoriale.collector import collect_sheet_snapshot
from app.modules.gis.scheda_territoriale.renderer import render_pdf


def _audit(
    db: Session,
    event_type: str,
    sheet: GisSchedaTerritoriale,
    actor_id: int | None,
    payload: dict | None = None,
) -> None:
    db.add(
        GisAuditLog(
            event_type=event_type,
            actor_user_id=actor_id,
            target_type="gis_scheda_territoriale",
            target_id=sheet.id,
            payload_json=payload or {},
        )
    )


def request_sheet(
    db: Session, user: ApplicationUser, parcel_id: UUID
) -> GisSchedaTerritoriale:
    if db.get(CatParticella, parcel_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Particella non trovata")
    sheet = GisSchedaTerritoriale(
        particella_id=parcel_id,
        requested_by_user_id=user.id,
        status="queued",
        source_snapshot_json={"status": "pending"},
    )
    db.add(sheet)
    db.flush()
    _audit(db, "scheda_territoriale.requested", sheet, user.id)
    db.commit()
    db.refresh(sheet)
    return sheet


def _authorized(sheet: GisSchedaTerritoriale, user: ApplicationUser) -> bool:
    return services.is_gis_admin(user) or sheet.requested_by_user_id == user.id


def get_sheet(
    db: Session, user: ApplicationUser, sheet_id: UUID
) -> GisSchedaTerritoriale:
    sheet = db.get(GisSchedaTerritoriale, sheet_id)
    if sheet is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scheda non trovata")
    if not _authorized(sheet, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Accesso alla scheda negato")
    return sheet


def download_sheet(
    db: Session, user: ApplicationUser, sheet_id: UUID
) -> tuple[bytes, str]:
    sheet = get_sheet(db, user, sheet_id)
    if sheet.status != "completed" or not sheet.artifact_path:
        raise HTTPException(status.HTTP_409_CONFLICT, "PDF non ancora disponibile")
    try:
        content = artifact_storage.read_artifact(sheet.artifact_path)
    except (OSError, FileNotFoundError) as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "PDF non trovato") from exc
    return content, f"scheda-territoriale-{sheet.particella_id}.pdf"


def prune_completed_sheets(db: Session, retention_count: int) -> int:
    sheets = db.scalars(
        select(GisSchedaTerritoriale)
        .where(GisSchedaTerritoriale.status == "completed")
        .order_by(GisSchedaTerritoriale.completed_at.desc())
    ).all()
    removed = 0
    for sheet in sheets[retention_count:]:
        if sheet.artifact_path:
            artifact_storage.delete_artifact(sheet.artifact_path)
        db.delete(sheet)
        removed += 1
    if removed:
        db.commit()
    return removed


def _artifact_path(sheet: GisSchedaTerritoriale) -> str:
    return str(Path(settings.gis_scheda_artifact_root) / f"{sheet.id}.pdf")


def _complete_generation(
    db: Session,
    sheet: GisSchedaTerritoriale,
    pdf: bytes,
) -> None:
    destination = _artifact_path(sheet)
    with tempfile.TemporaryDirectory(prefix="gaia-gis-sheet-") as temporary:
        source = Path(temporary) / "sheet.pdf"
        source.write_bytes(pdf)
        artifact_storage.publish_artifact(source, destination)
    sheet.status = "completed"
    sheet.artifact_path = destination
    sheet.checksum_sha256 = hashlib.sha256(pdf).hexdigest()
    sheet.completed_at = datetime.now(UTC)
    _audit(
        db,
        "scheda_territoriale.completed",
        sheet,
        sheet.requested_by_user_id,
        {"checksum_sha256": sheet.checksum_sha256},
    )
    db.commit()
    prune_completed_sheets(db, settings.gis_scheda_retention_count)


def _fail_generation(
    db: Session, sheet: GisSchedaTerritoriale, error: Exception
) -> None:
    sheet.status = "failed"
    sheet.error_message = str(error)
    if (
        not sheet.source_snapshot_json
        or sheet.source_snapshot_json.get("status") == "pending"
    ):
        sheet.source_snapshot_json = {
            "status": "failed_before_collection",
            "error": str(error),
            "collected_at": datetime.now(UTC).isoformat(),
        }
    _audit(
        db,
        "scheda_territoriale.failed",
        sheet,
        sheet.requested_by_user_id,
        {"error": str(error)},
    )
    db.commit()


def run_generation(
    sheet_id: UUID,
    db_factory: Callable[[], Session] = SessionLocal,
) -> None:
    with db_factory() as db:
        sheet = db.get(GisSchedaTerritoriale, sheet_id)
        if sheet is None:
            return
        try:
            sheet.status = "processing"
            db.commit()
            user = db.get(ApplicationUser, sheet.requested_by_user_id)
            if user is None:
                raise RuntimeError("Utente richiedente non disponibile")
            snapshot = collect_sheet_snapshot(db, user, sheet.particella_id)
            sheet.source_snapshot_json = jsonable_encoder(snapshot)
            db.commit()
            _complete_generation(db, sheet, render_pdf(snapshot))
        except Exception as exc:  # noqa: BLE001 - background job must persist failure
            db.rollback()
            sheet = db.get(GisSchedaTerritoriale, sheet_id)
            if sheet is not None:
                _fail_generation(db, sheet, exc)
