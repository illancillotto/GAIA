from __future__ import annotations

import tempfile
import uuid
from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.me.router.common import (
    RequirePresenzeModule,
    _cleanup_temp_dir,
    _convert_xlsx_to_pdf,
    _get_mapped_collaborator,
    _get_mapped_collaborator_or_409,
    _get_self_daily_record_or_404,
    _module_enabled,
)
from app.modules.me.schemas import (
    MeCapabilitiesResponse,
    MeModuleStatusResponse,
    MePresenzeDailyRecordListResponse,
    MePresenzeDailyRecordResponse,
    MePresenzeStatusResponse,
    MePresenzeSummaryResponse,
    MeStraordinariCollaboratorResponse,
    MeStraordinariExportRequest,
    MeStraordinariPreviewItemResponse,
    MeStraordinariPreviewResponse,
)
from app.modules.presenze.models import PresenzeDailyRecord, PresenzeEventSummary
from app.modules.presenze.router import _serialize_daily_record
from app.modules.presenze.schemas import PresenzeEventSummaryResponse
from app.modules.presenze.services.straordinari_export_job import (
    build_period_end as build_straordinari_period_end,
)
from app.modules.presenze.services.straordinari_export_job import (
    build_straordinari_export_items,
    format_duration_label,
    generate_straordinari_export,
    list_straordinari_preview_items,
    previous_month_period_start,
)

router = APIRouter(prefix="/me")


# Preserve legacy callable layout so the complexity ratchet remains comparable.
# fmt: off
@router.get("", response_model=MeModuleStatusResponse, response_model_exclude_none=True)
def get_me_status(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
) -> MeModuleStatusResponse:
    return MeModuleStatusResponse(
        module="me",
        enabled=True,
        username=current_user.username,
        capabilities=MeCapabilitiesResponse(
            presenze=_module_enabled(current_user, "presenze"),
            operazioni=_module_enabled(current_user, "operazioni"),
            network=_module_enabled(current_user, "rete"),
        ),
        message="GAIA self-service user module is enabled for the current user.",
    )


@router.get("/presenze", response_model=MePresenzeStatusResponse)
def get_me_presenze_status(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> MePresenzeStatusResponse:
    collaborator = _get_mapped_collaborator(db, current_user)
    if collaborator is None:
        return MePresenzeStatusResponse(
            module="presenze",
            enabled=True,
            mapped=False,
            message="No Presenze collaborator is currently mapped to the current user.",
        )

    return MePresenzeStatusResponse(
        module="presenze",
        enabled=True,
        mapped=True,
        collaborator_id=collaborator.id,
        collaborator_name=collaborator.name,
        employee_code=collaborator.employee_code,
        message="Presenze self-service data is available for the current user.",
    )


@router.get("/presenze/daily-records", response_model=MePresenzeDailyRecordListResponse)
def list_me_presenze_daily_records(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    collaborator_id: uuid.UUID | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=31, ge=1, le=200),
) -> MePresenzeDailyRecordListResponse:
    stmt = select(PresenzeDailyRecord).where(PresenzeDailyRecord.application_user_id == current_user.id)
    count_stmt = select(func.count(PresenzeDailyRecord.id)).where(PresenzeDailyRecord.application_user_id == current_user.id)

    if collaborator_id is not None:
        stmt = stmt.where(PresenzeDailyRecord.collaborator_id == collaborator_id)
        count_stmt = count_stmt.where(PresenzeDailyRecord.collaborator_id == collaborator_id)
    if date_from is not None:
        stmt = stmt.where(PresenzeDailyRecord.work_date >= date_from)
        count_stmt = count_stmt.where(PresenzeDailyRecord.work_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(PresenzeDailyRecord.work_date <= date_to)
        count_stmt = count_stmt.where(PresenzeDailyRecord.work_date <= date_to)
    if q:
        term = f"%{q.strip()}%"
        filters = or_(
            PresenzeDailyRecord.evidenze.ilike(term),
            PresenzeDailyRecord.stato.ilike(term),
            PresenzeDailyRecord.request_description.ilike(term),
            PresenzeDailyRecord.request_status.ilike(term),
            PresenzeDailyRecord.request_authorized_by.ilike(term),
            PresenzeDailyRecord.resolved_absence_cause.ilike(term),
        )
        stmt = stmt.where(filters)
        count_stmt = count_stmt.where(filters)

    rows = db.execute(
        stmt.order_by(PresenzeDailyRecord.work_date.asc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    total = db.execute(count_stmt).scalar_one()
    return MePresenzeDailyRecordListResponse(
        items=[_serialize_daily_record(db, row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/presenze/daily-records/{record_id}", response_model=MePresenzeDailyRecordResponse)
def get_me_presenze_daily_record(
    record_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> MePresenzeDailyRecordResponse:
    return MePresenzeDailyRecordResponse.model_validate(_serialize_daily_record(db, _get_self_daily_record_or_404(db, record_id, current_user)))


@router.get("/presenze/summary", response_model=MePresenzeSummaryResponse)
def get_me_presenze_summary(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    period_start: date = Query(...),
    period_end: date = Query(...),
) -> MePresenzeSummaryResponse:
    items = db.execute(
        select(PresenzeEventSummary)
        .where(
            PresenzeEventSummary.application_user_id == current_user.id,
            PresenzeEventSummary.period_start == period_start,
            PresenzeEventSummary.period_end == period_end,
        )
        .order_by(PresenzeEventSummary.description.asc())
    ).scalars().all()

    return MePresenzeSummaryResponse(
        period_start=period_start,
        period_end=period_end,
        items=[PresenzeEventSummaryResponse.model_validate(item) for item in items],
    )


@router.get("/presenze/straordinari/preview", response_model=MeStraordinariPreviewResponse)
def preview_me_straordinari_request(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> MeStraordinariPreviewResponse:
    collaborator = _get_mapped_collaborator_or_409(db, current_user)
    period_start = previous_month_period_start()
    period_end = date.fromordinal(build_straordinari_period_end(period_start).toordinal() - 1)
    _, items = list_straordinari_preview_items(db, collaborator_id=collaborator.id, period_start=period_start)
    return MeStraordinariPreviewResponse(
        collaborator=MeStraordinariCollaboratorResponse(
            id=collaborator.id,
            name=collaborator.name,
            employee_code=collaborator.employee_code,
        ),
        period_start=period_start,
        period_end=period_end,
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


@router.post("/presenze/straordinari/export/{artifact_format}")
def download_me_straordinari_request(
    artifact_format: str,
    payload: MeStraordinariExportRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> FileResponse:
    if artifact_format not in {"xlsx", "pdf"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Formato richiesta straordinari non supportato")
    collaborator = _get_mapped_collaborator_or_409(db, current_user)
    period_start = previous_month_period_start()
    requested_motivations = {item.record_id: item.motivation for item in payload.items}
    try:
        _, export_items = build_straordinari_export_items(
            db,
            collaborator_id=collaborator.id,
            period_start=period_start,
            requested_motivations=requested_motivations,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    temp_dir = Path(tempfile.mkdtemp(prefix="gaia_me_straordinari_"))
    try:
        xlsx_filename = generate_straordinari_export(
            collaborator_name=collaborator.name,
            period_start=period_start,
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
    except Exception:
        _cleanup_temp_dir(str(temp_dir))
        raise
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"{Path(xlsx_filename).stem}.pdf",
        background=BackgroundTask(_cleanup_temp_dir, str(temp_dir)),
    )
# fmt: on
