from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from app.api.deps import require_active_user, require_module
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.me.router import _cleanup_temp_dir, _convert_xlsx_to_pdf, _get_mapped_collaborator_or_409
from app.modules.me.schemas import (
    MeStraordinariCollaboratorResponse,
    MeStraordinariExportRequest,
    MeStraordinariPreviewItemResponse,
    MeStraordinariPreviewResponse,
)
from app.modules.presenze.models import PresenzeCollaborator
from app.modules.presenze.services.straordinari_export_job import (
    build_period_end,
    build_straordinari_export_items,
    format_duration_label,
    generate_straordinari_export,
    list_straordinari_available_months,
    list_straordinari_preview_items,
)

router = APIRouter(prefix="/me/presenze/straordinari", tags=["me"])
RequirePresenzeModule = Depends(require_module("presenze"))


class MeStraordinariPeriodPreviewResponse(MeStraordinariPreviewResponse):
    available_months: list[date]


def _month_start(value: date) -> date:
    return date(value.year, value.month, 1)


def _build_preview_response(
    db: Session,
    collaborator: PresenzeCollaborator,
    period_start: date,
) -> MeStraordinariPeriodPreviewResponse:
    normalized_start = _month_start(period_start)
    period_end = date.fromordinal(build_period_end(normalized_start).toordinal() - 1)
    _, items = list_straordinari_preview_items(db, collaborator_id=collaborator.id, period_start=normalized_start)
    return MeStraordinariPeriodPreviewResponse(
        collaborator=MeStraordinariCollaboratorResponse(
            id=collaborator.id,
            name=collaborator.name,
            employee_code=collaborator.employee_code,
        ),
        period_start=normalized_start,
        period_end=period_end,
        available_months=list_straordinari_available_months(db, collaborator_id=collaborator.id),
        items=[
            MeStraordinariPreviewItemResponse(
                record_id=item.record_id,
                work_date=item.work_date,
                motivation=item.motivation,
                start_time=item.start_time,
                end_time=item.end_time,
                duration_minutes=item.duration_minutes,
                duration_label=format_duration_label(item.duration_minutes),
                original_duration_minutes=item.original_duration_minutes,
                pause_deduction_minutes=item.pause_deduction_minutes,
                lunch_break_minutes=item.lunch_break_minutes,
                duration_adjustment_reason=item.duration_adjustment_reason,
            )
            for item in items
        ],
    )


def _build_download_response(
    artifact_format: str,
    payload: MeStraordinariExportRequest,
    db: Session,
    collaborator: PresenzeCollaborator,
    period_start: date,
) -> FileResponse:
    requested_motivations = {item.record_id: item.motivation for item in payload.items}
    try:
        _, export_items = build_straordinari_export_items(
            db,
            collaborator_id=collaborator.id,
            period_start=_month_start(period_start),
            requested_motivations=requested_motivations,
        )
    except ValueError as exc:
        detail = str(exc).replace("mese precedente", "mese selezionato")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc

    temp_dir = Path(tempfile.mkdtemp(prefix="gaia_me_straordinari_"))
    try:
        xlsx_filename = generate_straordinari_export(
            collaborator_name=collaborator.name,
            period_start=_month_start(period_start),
            items=export_items,
            output_path=temp_dir / "straordinari.xlsx",
        )
        xlsx_path = temp_dir / "straordinari.xlsx"
        if artifact_format == "xlsx":
            return FileResponse(
                xlsx_path,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                filename=xlsx_filename,
                background=BackgroundTask(_cleanup_temp_dir, str(temp_dir)),
            )
        pdf_path = _convert_xlsx_to_pdf(xlsx_path, temp_dir)
    except Exception:  # noqa: BLE001 - the temporary export directory must be removed on every failure.
        _cleanup_temp_dir(str(temp_dir))
        raise

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"{Path(xlsx_filename).stem}.pdf",
        background=BackgroundTask(_cleanup_temp_dir, str(temp_dir)),
    )


@router.get("/preview/{period_start}", response_model=MeStraordinariPeriodPreviewResponse)
def preview_me_straordinari_period_request(
    period_start: date,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> MeStraordinariPeriodPreviewResponse:
    return _build_preview_response(db, _get_mapped_collaborator_or_409(db, current_user), period_start)


@router.post("/export/{artifact_format}/{period_start}")
def download_me_straordinari_period_request(
    artifact_format: str,
    period_start: date,
    payload: MeStraordinariExportRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> FileResponse:
    if artifact_format not in {"xlsx", "pdf"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Formato richiesta straordinari non supportato")
    collaborator = _get_mapped_collaborator_or_409(db, current_user)
    return _build_download_response(artifact_format, payload, db, collaborator, period_start)
