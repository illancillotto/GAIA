from __future__ import annotations

import calendar
import shutil
import subprocess
import uuid
from datetime import date
from pathlib import Path

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_module
from app.models.application_user import ApplicationUser
from app.modules.me.schemas import MeAssignedDeviceItem
from app.modules.network.models import NetworkDevice
from app.modules.network.router import _resolve_device_label
from app.modules.operazioni.models.activities import OperatorActivity
from app.modules.operazioni.models.vehicles import VehicleUsageSession
from app.modules.presenze.models import PresenzeCollaborator, PresenzeDailyRecord
from app.modules.presenze.services.parser import extract_detail_payload

# Preserve legacy callable layout so the complexity ratchet remains comparable.
# fmt: off
RequirePresenzeModule = Depends(require_module("presenze"))
RequireOperazioniModule = Depends(require_module("operazioni"))
RequireNetworkModule = Depends(require_module("rete"))


def _module_enabled(current_user: ApplicationUser, module_name: str) -> bool:
    return current_user.is_super_admin or module_name in current_user.enabled_modules


def _get_mapped_collaborator(db: Session, current_user: ApplicationUser) -> PresenzeCollaborator | None:
    return db.execute(
        select(PresenzeCollaborator)
        .where(PresenzeCollaborator.application_user_id == current_user.id)
        .order_by(
            PresenzeCollaborator.is_active.desc(),
            PresenzeCollaborator.last_seen_at.desc().nullslast(),
            PresenzeCollaborator.created_at.desc(),
        )
        .limit(1)
    ).scalar_one_or_none()


def _get_self_daily_record_or_404(db: Session, record_id: uuid.UUID, current_user: ApplicationUser) -> PresenzeDailyRecord:
    record = db.execute(
        select(PresenzeDailyRecord).where(
            PresenzeDailyRecord.id == record_id,
            PresenzeDailyRecord.application_user_id == current_user.id,
        )
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Daily record not found")
    return record


def _current_month_bounds() -> tuple[date, date]:
    today = date.today()
    start = today.replace(day=1)
    end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
    return start, end


def _resolve_period_bounds(period_start: date | None, period_end: date | None) -> tuple[date, date]:
    default_start, default_end = _current_month_bounds()
    resolved_start = period_start or default_start
    resolved_end = period_end or default_end
    if resolved_start > resolved_end:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid period range")
    return resolved_start, resolved_end


def _activity_duration_minutes(activity: OperatorActivity) -> int:
    if activity.duration_minutes_calculated is not None:
        return activity.duration_minutes_calculated
    return activity.duration_minutes_declared or 0


def _vehicle_session_km(session: VehicleUsageSession) -> float:
    if session.route_distance_km is not None:
        return float(session.route_distance_km)
    if session.end_odometer_km is not None:
        return float(session.end_odometer_km - session.start_odometer_km)
    if session.km_start is not None and session.km_end is not None:
        return float(session.km_end - session.km_start)
    return 0.0


def _daily_record_effective_extra_minutes(record: PresenzeDailyRecord) -> int:
    effective_straordinario = (
        record.override_straordinario_minutes
        if record.override_straordinario_minutes is not None
        else record.straordinario_minutes
    )
    effective_mpe = record.override_mpe_minutes if record.override_mpe_minutes is not None else record.mpe_minutes
    return (effective_straordinario or 0) + (effective_mpe or 0)


def _get_mapped_collaborator_or_409(db: Session, current_user: ApplicationUser) -> PresenzeCollaborator:
    collaborator = _get_mapped_collaborator(db, current_user)
    if collaborator is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nessun collaboratore Presenze associato all'utente corrente",
        )
    return collaborator


def _cleanup_temp_dir(path: str) -> None:
    shutil.rmtree(path, ignore_errors=True)


def _convert_xlsx_to_pdf(xlsx_path: Path, output_dir: Path) -> Path:
    binary = shutil.which("libreoffice") or shutil.which("soffice")
    if not binary:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LibreOffice non trovato: scarica l'Excel e stampalo oppure installa LibreOffice per il PDF.",
        )
    completed = subprocess.run(
        [binary, "--headless", "--convert-to", "pdf", "--outdir", str(output_dir), str(xlsx_path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if completed.returncode != 0:
        error_output = (completed.stderr or completed.stdout or "").strip()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Conversione PDF fallita: {error_output or completed.returncode}",
        )
    pdf_path = output_dir / f"{xlsx_path.stem}.pdf"
    if not pdf_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Conversione PDF completata senza file di output",
        )
    return pdf_path


def _daily_record_has_anomaly(record: PresenzeDailyRecord) -> bool:
    detail = extract_detail_payload(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else {}
    anomalies = detail.get("anomalies") or []
    detail_status = str(detail.get("status") or "").lower()
    stato = str(record.stato or "").lower()
    return bool(anomalies or "anom" in detail_status or "anom" in stato)


def _hours_from_minutes(minutes: int) -> float:
    return round(minutes / 60, 2)


def _serialize_assigned_device(device: NetworkDevice) -> MeAssignedDeviceItem:
    resolved_label, _ = _resolve_device_label(device)
    return MeAssignedDeviceItem(
        id=device.id,
        ip_address=device.ip_address,
        hostname=device.hostname,
        display_name=device.display_name,
        resolved_label=resolved_label,
        lifecycle_state=device.lifecycle_state,
        status=device.status,
        device_type=device.device_type,
        operating_system=device.operating_system,
        asset_label=device.asset_label,
        location_hint=device.location_hint,
        last_seen_at=device.last_seen_at,
        updated_at=device.updated_at,
    )
# fmt: on
