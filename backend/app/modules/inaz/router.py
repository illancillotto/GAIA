from __future__ import annotations

import tempfile
import uuid
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_module, require_role
from app.core.config import settings
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.inaz.models import (
    InazCollaborator,
    InazCollaboratorScheduleAssignment,
    InazDailyPunch,
    InazDailyRecord,
    InazEventSummary,
    InazHoliday,
    InazImportJob,
    InazScheduleRule,
    InazScheduleTemplate,
    InazSyncJob,
)
from app.modules.inaz.schemas import (
    InazCollaboratorApplicationUserUpdate,
    InazCollaboratorScheduleAssignmentCreate,
    InazCollaboratorScheduleAssignmentResponse,
    InazCollaboratorCalendarResponse,
    InazCollaboratorListResponse,
    InazCollaboratorResponse,
    InazCredentialCreate,
    InazCredentialResponse,
    InazCredentialTestResult,
    InazCredentialUpdate,
    InazCollaboratorSummaryResponse,
    InazDailyRecordListResponse,
    InazDailyRecordManualUpdate,
    InazDailyRecordResponse,
    InazEventSummaryResponse,
    InazHolidayBootstrapResponse,
    InazHolidayCreate,
    InazHolidayResponse,
    InazHolidayUpdate,
    InazImportJobListResponse,
    InazImportJobResponse,
    InazImportJsonResponse,
    InazImportPreviewResponse,
    InazModuleStatusResponse,
    InazScheduleRuleCreate,
    InazScheduleRuleResponse,
    InazScheduleRuleUpdate,
    InazScheduleTemplateCreate,
    InazScheduleTemplateResponse,
    InazScheduleTemplateUpdate,
    InazSyncJobCreateRequest,
    InazSyncJobListResponse,
    InazSyncJobResponse,
)
from app.modules.inaz.services.credentials import (
    create_credential,
    delete_credential,
    get_credential,
    list_credentials,
    test_credential,
    update_credential,
)
from app.modules.inaz.services.import_jobs import build_preview, run_import_job
from app.modules.inaz.services.parser import (
    detail_indicates_special_day,
    extract_detail_payload,
    load_json_payload,
    parse_import_payload,
    resolve_absence_cause,
    resolve_request_authorized_by,
    resolve_request_description,
    resolve_request_status,
    resolve_request_type,
)
from app.modules.inaz.services.schedule_engine import build_schedule_context, seed_holidays_for_year
from app.modules.inaz.services.sync_runtime import (
    build_period,
    delete_sync_artifact_dir,
    get_sync_artifact_dir,
    has_running_sync_job,
    launch_sync_worker,
    reconcile_stale_sync_jobs,
    resolve_sync_artifact_path,
    stop_sync_worker,
)
from app.modules.inaz.services.xlsm_export import DEFAULT_TEMPLATE_PATH, ExportTimesheetRow, compile_workbook

router = APIRouter(prefix="/inaz", tags=["inaz"])
RequireInazModule = Depends(require_module("inaz"))
RequireInazAdmin = Depends(require_role("super_admin", "admin"))


@router.get("", response_model=InazModuleStatusResponse)
def get_module_status(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireInazModule],
) -> InazModuleStatusResponse:
    return InazModuleStatusResponse(
        module="inaz",
        enabled=True,
        username=current_user.username,
        message="GAIA Inaz collaboratori module is enabled for the current user.",
    )


@router.get("/holidays", response_model=list[InazHolidayResponse])
def list_inaz_holidays(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequireInazAdmin],
    __: Annotated[ApplicationUser, RequireInazModule],
    year: int | None = Query(default=None, ge=2000, le=2100),
) -> list[InazHolidayResponse]:
    stmt = select(InazHoliday)
    if year is not None:
        stmt = stmt.where(InazHoliday.holiday_date >= date(year, 1, 1), InazHoliday.holiday_date <= date(year, 12, 31))
    items = db.execute(stmt.order_by(InazHoliday.holiday_date.asc(), InazHoliday.company_code.asc())).scalars().all()
    return [InazHolidayResponse.model_validate(item) for item in items]


@router.post("/holidays/bootstrap", response_model=InazHolidayBootstrapResponse)
def bootstrap_inaz_holidays(
    year: int = Query(..., ge=2000, le=2100),
    db: Annotated[Session, Depends(get_db)] = ...,
    _: Annotated[ApplicationUser, RequireInazAdmin] = ...,
    __: Annotated[ApplicationUser, RequireInazModule] = ...,
) -> InazHolidayBootstrapResponse:
    items = seed_holidays_for_year(db, year)
    db.commit()
    return InazHolidayBootstrapResponse(
        year=year,
        created=len(items),
        items=[InazHolidayResponse.model_validate(item) for item in items],
    )


@router.post("/holidays", response_model=InazHolidayResponse, status_code=201)
def create_inaz_holiday(
    payload: InazHolidayCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequireInazAdmin],
    __: Annotated[ApplicationUser, RequireInazModule],
) -> InazHolidayResponse:
    item = InazHoliday(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return InazHolidayResponse.model_validate(item)


@router.patch("/holidays/{holiday_id}", response_model=InazHolidayResponse)
def update_inaz_holiday(
    holiday_id: int,
    payload: InazHolidayUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequireInazAdmin],
    __: Annotated[ApplicationUser, RequireInazModule],
) -> InazHolidayResponse:
    item = db.get(InazHoliday, holiday_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Holiday not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.add(item)
    db.commit()
    db.refresh(item)
    return InazHolidayResponse.model_validate(item)


@router.delete("/holidays/{holiday_id}", status_code=204)
def delete_inaz_holiday(
    holiday_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequireInazAdmin],
    __: Annotated[ApplicationUser, RequireInazModule],
) -> None:
    item = db.get(InazHoliday, holiday_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Holiday not found")
    db.delete(item)
    db.commit()


@router.get("/schedule/templates", response_model=list[InazScheduleTemplateResponse])
def list_schedule_templates(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequireInazAdmin],
    __: Annotated[ApplicationUser, RequireInazModule],
) -> list[InazScheduleTemplateResponse]:
    templates = db.execute(select(InazScheduleTemplate).order_by(InazScheduleTemplate.code.asc())).scalars().all()
    return [_serialize_schedule_template(db, item) for item in templates]


@router.post("/schedule/templates", response_model=InazScheduleTemplateResponse, status_code=201)
def create_schedule_template(
    payload: InazScheduleTemplateCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequireInazAdmin],
    __: Annotated[ApplicationUser, RequireInazModule],
) -> InazScheduleTemplateResponse:
    item = InazScheduleTemplate(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_schedule_template(db, item)


@router.patch("/schedule/templates/{template_id}", response_model=InazScheduleTemplateResponse)
def update_schedule_template(
    template_id: int,
    payload: InazScheduleTemplateUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequireInazAdmin],
    __: Annotated[ApplicationUser, RequireInazModule],
) -> InazScheduleTemplateResponse:
    item = db.get(InazScheduleTemplate, template_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Schedule template not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_schedule_template(db, item)


@router.delete("/schedule/templates/{template_id}", status_code=204)
def delete_schedule_template(
    template_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequireInazAdmin],
    __: Annotated[ApplicationUser, RequireInazModule],
) -> None:
    item = db.get(InazScheduleTemplate, template_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Schedule template not found")
    db.delete(item)
    db.commit()


@router.post("/schedule/templates/{template_id}/rules", response_model=InazScheduleRuleResponse, status_code=201)
def create_schedule_rule(
    template_id: int,
    payload: InazScheduleRuleCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequireInazAdmin],
    __: Annotated[ApplicationUser, RequireInazModule],
) -> InazScheduleRuleResponse:
    if db.get(InazScheduleTemplate, template_id) is None:
        raise HTTPException(status_code=404, detail="Schedule template not found")
    item = InazScheduleRule(template_id=template_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return InazScheduleRuleResponse.model_validate(item)


@router.patch("/schedule/rules/{rule_id}", response_model=InazScheduleRuleResponse)
def update_schedule_rule(
    rule_id: int,
    payload: InazScheduleRuleUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequireInazAdmin],
    __: Annotated[ApplicationUser, RequireInazModule],
) -> InazScheduleRuleResponse:
    item = db.get(InazScheduleRule, rule_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Schedule rule not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.add(item)
    db.commit()
    db.refresh(item)
    return InazScheduleRuleResponse.model_validate(item)


@router.delete("/schedule/rules/{rule_id}", status_code=204)
def delete_schedule_rule(
    rule_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequireInazAdmin],
    __: Annotated[ApplicationUser, RequireInazModule],
) -> None:
    item = db.get(InazScheduleRule, rule_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Schedule rule not found")
    db.delete(item)
    db.commit()


@router.get("/collaborators/{collaborator_id}/schedule-assignments", response_model=list[InazCollaboratorScheduleAssignmentResponse])
def list_collaborator_schedule_assignments(
    collaborator_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequireInazAdmin],
    __: Annotated[ApplicationUser, RequireInazModule],
) -> list[InazCollaboratorScheduleAssignmentResponse]:
    _get_collaborator_or_404(db, collaborator_id)
    rows = db.execute(
        select(InazCollaboratorScheduleAssignment)
        .where(InazCollaboratorScheduleAssignment.collaborator_id == collaborator_id)
        .order_by(InazCollaboratorScheduleAssignment.valid_from.desc(), InazCollaboratorScheduleAssignment.id.desc())
    ).scalars().all()
    return [_serialize_schedule_assignment(db, row) for row in rows]


@router.post("/collaborators/{collaborator_id}/schedule-assignments", response_model=InazCollaboratorScheduleAssignmentResponse, status_code=201)
def create_collaborator_schedule_assignment(
    collaborator_id: uuid.UUID,
    payload: InazCollaboratorScheduleAssignmentCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequireInazAdmin],
    __: Annotated[ApplicationUser, RequireInazModule],
) -> InazCollaboratorScheduleAssignmentResponse:
    _get_collaborator_or_404(db, collaborator_id)
    if db.get(InazScheduleTemplate, payload.template_id) is None:
        raise HTTPException(status_code=404, detail="Schedule template not found")
    item = InazCollaboratorScheduleAssignment(collaborator_id=collaborator_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_schedule_assignment(db, item)


@router.delete("/schedule-assignments/{assignment_id}", status_code=204)
def delete_schedule_assignment(
    assignment_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequireInazAdmin],
    __: Annotated[ApplicationUser, RequireInazModule],
) -> None:
    item = db.get(InazCollaboratorScheduleAssignment, assignment_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Schedule assignment not found")
    db.delete(item)
    db.commit()


@router.post("/credentials", response_model=InazCredentialResponse, status_code=201)
def create_inaz_credential(
    payload: InazCredentialCreate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireInazModule],
    db: Annotated[Session, Depends(get_db)],
) -> InazCredentialResponse:
    return create_credential(db, current_user.id, payload)


@router.get("/credentials", response_model=list[InazCredentialResponse])
def list_inaz_credentials(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireInazModule],
    db: Annotated[Session, Depends(get_db)],
) -> list[InazCredentialResponse]:
    return list_credentials(db, current_user)


@router.get("/credentials/{credential_id}", response_model=InazCredentialResponse)
def get_inaz_credential(
    credential_id: int,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireInazModule],
    db: Annotated[Session, Depends(get_db)],
) -> InazCredentialResponse:
    credential = get_credential(db, credential_id, current_user)
    if credential is None:
        raise HTTPException(status_code=404, detail="Credenziale Inaz non trovata")
    return InazCredentialResponse.model_validate(credential)


@router.patch("/credentials/{credential_id}", response_model=InazCredentialResponse)
def update_inaz_credential(
    credential_id: int,
    payload: InazCredentialUpdate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireInazModule],
    db: Annotated[Session, Depends(get_db)],
) -> InazCredentialResponse:
    credential = update_credential(db, credential_id, current_user, payload)
    if credential is None:
        raise HTTPException(status_code=404, detail="Credenziale Inaz non trovata")
    return credential


@router.delete("/credentials/{credential_id}", status_code=204)
def delete_inaz_credential(
    credential_id: int,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireInazModule],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    if not delete_credential(db, credential_id, current_user):
        raise HTTPException(status_code=404, detail="Credenziale Inaz non trovata")


@router.post("/credentials/{credential_id}/test", response_model=InazCredentialTestResult)
async def test_inaz_credential(
    credential_id: int,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireInazModule],
    db: Annotated[Session, Depends(get_db)],
) -> InazCredentialTestResult:
    result = await test_credential(db, current_user, credential_id)
    if not result.ok:
        raise HTTPException(status_code=502, detail=result.error)
    return result


@router.get("/collaborators", response_model=InazCollaboratorListResponse)
def list_collaborators(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireInazModule],
    q: str | None = Query(default=None),
    mapped_only: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
) -> InazCollaboratorListResponse:
    stmt = select(InazCollaborator)
    count_stmt = select(func.count(InazCollaborator.id))
    if not _is_admin_user(current_user):
        stmt = stmt.where(InazCollaborator.owner_user_id == current_user.id)
        count_stmt = count_stmt.where(InazCollaborator.owner_user_id == current_user.id)
    if q:
        term = f"%{q.strip()}%"
        condition = or_(
            InazCollaborator.name.ilike(term),
            InazCollaborator.employee_code.ilike(term),
            InazCollaborator.company_code.ilike(term),
        )
        stmt = stmt.where(condition)
        count_stmt = count_stmt.where(condition)
    if mapped_only is True:
        stmt = stmt.where(InazCollaborator.application_user_id.is_not(None))
        count_stmt = count_stmt.where(InazCollaborator.application_user_id.is_not(None))
    if mapped_only is False:
        stmt = stmt.where(InazCollaborator.application_user_id.is_(None))
        count_stmt = count_stmt.where(InazCollaborator.application_user_id.is_(None))

    rows = db.execute(
        stmt.order_by(InazCollaborator.name.asc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    total = db.execute(count_stmt).scalar_one()
    return InazCollaboratorListResponse(
        items=[InazCollaboratorResponse.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.put("/collaborators/{collaborator_id}/application-user", response_model=InazCollaboratorResponse)
def map_collaborator_to_application_user(
    collaborator_id: uuid.UUID,
    payload: InazCollaboratorApplicationUserUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequireInazAdmin],
    __: Annotated[ApplicationUser, RequireInazModule],
) -> InazCollaboratorResponse:
    collaborator = _get_collaborator_or_404(db, collaborator_id)
    if payload.application_user_id is not None and db.get(ApplicationUser, payload.application_user_id) is None:
        raise HTTPException(status_code=404, detail="Application user not found")
    collaborator.application_user_id = payload.application_user_id
    db.add(collaborator)
    db.query(InazDailyRecord).filter(InazDailyRecord.collaborator_id == collaborator.id).update(
        {"application_user_id": payload.application_user_id}
    )
    db.query(InazEventSummary).filter(InazEventSummary.collaborator_id == collaborator.id).update(
        {"application_user_id": payload.application_user_id}
    )
    db.commit()
    db.refresh(collaborator)
    return InazCollaboratorResponse.model_validate(collaborator)


@router.get("/giornaliere", response_model=InazDailyRecordListResponse)
def list_giornaliere(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireInazModule],
    collaborator_id: uuid.UUID | None = Query(default=None),
    application_user_id: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=31, ge=1, le=200),
) -> InazDailyRecordListResponse:
    stmt = select(InazDailyRecord)
    count_stmt = select(func.count(InazDailyRecord.id))

    if not _is_admin_user(current_user):
        stmt = stmt.where(InazDailyRecord.owner_user_id == current_user.id)
        count_stmt = count_stmt.where(InazDailyRecord.owner_user_id == current_user.id)

    if collaborator_id is not None:
        stmt = stmt.where(InazDailyRecord.collaborator_id == collaborator_id)
        count_stmt = count_stmt.where(InazDailyRecord.collaborator_id == collaborator_id)
    if application_user_id is not None:
        stmt = stmt.where(InazDailyRecord.application_user_id == application_user_id)
        count_stmt = count_stmt.where(InazDailyRecord.application_user_id == application_user_id)
    if date_from is not None:
        stmt = stmt.where(InazDailyRecord.work_date >= date_from)
        count_stmt = count_stmt.where(InazDailyRecord.work_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(InazDailyRecord.work_date <= date_to)
        count_stmt = count_stmt.where(InazDailyRecord.work_date <= date_to)
    if q:
        term = f"%{q.strip()}%"
        filters = or_(
            InazDailyRecord.evidenze.ilike(term),
            InazDailyRecord.stato.ilike(term),
            InazDailyRecord.request_description.ilike(term),
            InazDailyRecord.request_status.ilike(term),
            InazDailyRecord.request_authorized_by.ilike(term),
            InazDailyRecord.resolved_absence_cause.ilike(term),
        )
        stmt = stmt.where(filters)
        count_stmt = count_stmt.where(filters)

    rows = db.execute(
        stmt.order_by(InazDailyRecord.work_date.asc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    total = db.execute(count_stmt).scalar_one()
    return InazDailyRecordListResponse(
        items=[_serialize_daily_record(db, row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/giornaliere/{record_id}", response_model=InazDailyRecordResponse)
def get_giornaliera(
    record_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireInazModule],
) -> InazDailyRecordResponse:
    return _serialize_daily_record(db, _get_daily_record_or_404(db, record_id, current_user))


@router.patch("/giornaliere/{record_id}", response_model=InazDailyRecordResponse)
def update_giornaliera(
    record_id: uuid.UUID,
    payload: InazDailyRecordManualUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireInazModule],
) -> InazDailyRecordResponse:
    record = _get_daily_record_or_404(db, record_id, current_user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    db.add(record)
    db.commit()
    db.refresh(record)
    return _serialize_daily_record(db, record)


@router.get("/collaborators/{collaborator_id}/calendar", response_model=InazCollaboratorCalendarResponse)
def get_collaborator_calendar(
    collaborator_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireInazModule],
    date_from: date = Query(...),
    date_to: date = Query(...),
) -> InazCollaboratorCalendarResponse:
    collaborator = _get_collaborator_or_404(db, collaborator_id, current_user)
    rows = db.execute(
        select(InazDailyRecord)
        .where(
            InazDailyRecord.collaborator_id == collaborator_id,
            InazDailyRecord.work_date >= date_from,
            InazDailyRecord.work_date <= date_to,
        )
        .order_by(InazDailyRecord.work_date.asc())
    ).scalars().all()
    return InazCollaboratorCalendarResponse(
        collaborator=InazCollaboratorResponse.model_validate(collaborator),
        date_from=date_from,
        date_to=date_to,
        items=[_serialize_daily_record(db, row) for row in rows],
    )


@router.get("/collaborators/{collaborator_id}/summary", response_model=InazCollaboratorSummaryResponse)
def get_collaborator_summary(
    collaborator_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireInazModule],
    period_start: date = Query(...),
    period_end: date = Query(...),
) -> InazCollaboratorSummaryResponse:
    collaborator = _get_collaborator_or_404(db, collaborator_id, current_user)
    items = db.execute(
        select(InazEventSummary)
        .where(
            InazEventSummary.collaborator_id == collaborator_id,
            InazEventSummary.period_start == period_start,
            InazEventSummary.period_end == period_end,
        )
        .order_by(InazEventSummary.description.asc())
    ).scalars().all()
    return InazCollaboratorSummaryResponse(
        collaborator=InazCollaboratorResponse.model_validate(collaborator),
        period_start=period_start,
        period_end=period_end,
        items=[InazEventSummaryResponse.model_validate(item) for item in items],
    )


@router.post("/import/preview", response_model=InazImportPreviewResponse)
async def preview_import_json(
    file: UploadFile = File(...),
    _: Annotated[ApplicationUser, RequireInazAdmin] = ...,
    __: Annotated[ApplicationUser, RequireInazModule] = ...,
) -> InazImportPreviewResponse:
    content = await file.read()
    parsed = parse_import_payload(load_json_payload(content))
    return build_preview(parsed)


@router.post("/import/json", response_model=InazImportJsonResponse)
async def import_json(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, RequireInazAdmin],
    _: Annotated[ApplicationUser, RequireInazModule],
    file: UploadFile = File(...),
) -> InazImportJsonResponse:
    content = await file.read()
    parsed = parse_import_payload(load_json_payload(content))
    try:
        return run_import_job(
            db,
            parsed=parsed,
            requested_by_user_id=current_user.id,
            filename=file.filename,
            params_json={"format": "collaboratori-json"},
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/import/jobs", response_model=InazImportJobListResponse)
def list_import_jobs(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireInazModule],
) -> InazImportJobListResponse:
    stmt = select(InazImportJob)
    if not _is_admin_user(current_user):
        stmt = stmt.where(InazImportJob.requested_by_user_id == current_user.id)
    jobs = db.execute(stmt.order_by(InazImportJob.created_at.desc())).scalars().all()
    return InazImportJobListResponse(items=[InazImportJobResponse.model_validate(job) for job in jobs], total=len(jobs))


@router.get("/import/jobs/{job_id}", response_model=InazImportJobResponse)
def get_import_job(
    job_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireInazModule],
) -> InazImportJobResponse:
    job = db.get(InazImportJob, job_id)
    if job is None or (not _is_admin_user(current_user) and job.requested_by_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Import job not found")
    return InazImportJobResponse.model_validate(job)


@router.post("/sync/jobs", response_model=InazSyncJobResponse)
def create_sync_job(
    payload: InazSyncJobCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireInazModule],
) -> InazSyncJobResponse:
    if has_running_sync_job(db):
        raise HTTPException(status_code=409, detail="Another Inaz sync job is already pending or running")
    credential = get_credential(db, payload.credential_id, current_user)
    if credential is None:
        raise HTTPException(status_code=404, detail="Credenziale Inaz non trovata")
    if not credential.active:
        raise HTTPException(status_code=409, detail="La credenziale Inaz selezionata non e attiva")

    period_start, period_end = build_period(payload.year, payload.month)
    job = InazSyncJob(
        status="pending",
        requested_by_user_id=current_user.id,
        credential_id=payload.credential_id,
        period_start=period_start,
        period_end=period_end,
        collaborator_limit=payload.collaborator_limit,
        max_attempts=settings.inaz_sync_max_attempts,
        params_json={
            "auth_mode": "credential",
            "year": payload.year,
            "month": payload.month,
        },
    )
    db.add(job)
    db.flush()

    artifact_dir = get_sync_artifact_dir(str(job.id))
    artifact_dir.mkdir(parents=True, exist_ok=True)
    job.worker_log_path = str(artifact_dir / "worker.log")
    job.json_artifact_path = str(artifact_dir / "inaz_collaboratori.json")

    try:
        job.worker_pid = launch_sync_worker(job)
    except Exception as exc:
        job.status = "failed"
        job.error_detail = str(exc)
        job.finished_at = datetime.now(UTC)
        db.add(job)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Unable to start Inaz sync worker: {exc}") from exc

    db.add(job)
    db.commit()
    db.refresh(job)
    return InazSyncJobResponse.model_validate(job)


@router.get("/sync/jobs", response_model=InazSyncJobListResponse)
def list_sync_jobs(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireInazModule],
) -> InazSyncJobListResponse:
    reconcile_stale_sync_jobs(db)
    stmt = select(InazSyncJob)
    if current_user.role not in {"admin", "super_admin"}:
        stmt = stmt.where(InazSyncJob.requested_by_user_id == current_user.id)
    jobs = db.execute(stmt.order_by(InazSyncJob.created_at.desc())).scalars().all()
    return InazSyncJobListResponse(items=[InazSyncJobResponse.model_validate(job) for job in jobs], total=len(jobs))


@router.get("/sync/jobs/{job_id}", response_model=InazSyncJobResponse)
def get_sync_job(
    job_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireInazModule],
) -> InazSyncJobResponse:
    reconcile_stale_sync_jobs(db)
    job = db.get(InazSyncJob, job_id)
    if job is None or (current_user.role not in {"admin", "super_admin"} and job.requested_by_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Sync job not found")
    return InazSyncJobResponse.model_validate(job)


@router.post("/sync/jobs/{job_id}/retry", response_model=InazSyncJobResponse)
def retry_sync_job(
    job_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireInazModule],
) -> InazSyncJobResponse:
    if has_running_sync_job(db):
        raise HTTPException(status_code=409, detail="Another Inaz sync job is already pending or running")

    job = db.get(InazSyncJob, job_id)
    if job is None or (current_user.role not in {"admin", "super_admin"} and job.requested_by_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Sync job not found")
    if job.status not in {"failed", "completed"}:
        raise HTTPException(status_code=409, detail="Sync job is not retryable in the current state")
    if job.credential_id is None:
        raise HTTPException(status_code=409, detail="Questo job usa una configurazione legacy. Crea una nuova sync con una credenziale Inaz salvata.")
    checkpoint = dict((job.params_json or {}).get("checkpoint") or {})
    completed_employee_codes = checkpoint.get("completed_employee_codes")
    has_resume_checkpoint = isinstance(completed_employee_codes, list) and len(completed_employee_codes) > 0
    if job.attempt_count >= job.max_attempts and not has_resume_checkpoint:
        raise HTTPException(status_code=409, detail="Sync job reached the configured max attempts")

    job.status = "pending"
    job.error_detail = None
    job.started_at = None
    job.finished_at = None
    try:
        job.worker_pid = launch_sync_worker(job)
    except Exception as exc:
        job.status = "failed"
        job.error_detail = str(exc)
        job.finished_at = datetime.now(UTC)
        db.add(job)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Unable to restart Inaz sync worker: {exc}") from exc

    db.add(job)
    db.commit()
    db.refresh(job)
    return InazSyncJobResponse.model_validate(job)


@router.get("/sync/jobs/{job_id}/artifacts/{artifact_name}")
def download_sync_job_artifact(
    job_id: uuid.UUID,
    artifact_name: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireInazModule],
) -> FileResponse:
    job = db.get(InazSyncJob, job_id)
    if job is None or (current_user.role not in {"admin", "super_admin"} and job.requested_by_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Sync job not found")
    try:
        artifact_path = resolve_sync_artifact_path(str(job.id), artifact_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not artifact_path.exists():
        raise HTTPException(status_code=404, detail="Sync job artifact not found")
    media_type = {
        "json": "application/json",
        "summary": "application/json",
        "progress": "application/json",
        "events": "application/x-ndjson",
        "log": "text/plain; charset=utf-8",
    }.get(artifact_name, "application/octet-stream")
    return FileResponse(artifact_path, media_type=media_type, filename=artifact_path.name)


@router.post("/sync/jobs/{job_id}/cancel", response_model=InazSyncJobResponse)
def cancel_sync_job(
    job_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireInazModule],
) -> InazSyncJobResponse:
    job = db.get(InazSyncJob, job_id)
    if job is None or (current_user.role not in {"admin", "super_admin"} and job.requested_by_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Sync job not found")
    if job.status not in {"pending", "running"}:
        raise HTTPException(status_code=409, detail="Sync job cannot be cancelled in the current state")
    try:
        stop_sync_worker(job)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    job.status = "cancelled"
    job.error_detail = "Sync job cancelled by user"
    job.finished_at = datetime.now(UTC)
    db.add(job)
    db.commit()
    db.refresh(job)
    return InazSyncJobResponse.model_validate(job)


@router.delete("/sync/jobs/{job_id}", status_code=204)
def delete_sync_job(
    job_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireInazModule],
) -> Response:
    job = db.get(InazSyncJob, job_id)
    if job is None or (current_user.role not in {"admin", "super_admin"} and job.requested_by_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Sync job not found")
    if job.status not in {"failed", "cancelled", "completed"}:
        raise HTTPException(status_code=409, detail="Only terminal sync jobs can be deleted")

    delete_sync_artifact_dir(str(job.id))
    db.delete(job)
    db.commit()
    return Response(status_code=204)


@router.get("/export/giornaliere.xlsm")
def export_giornaliere_xlsm(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequireInazAdmin],
    __: Annotated[ApplicationUser, RequireInazModule],
    period_start: date = Query(...),
    collaborator_id: list[uuid.UUID] | None = Query(default=None),
    employee_kind: str = Query(default="AVVENTIZI"),
    template_path: str | None = Query(default=None),
) -> FileResponse:
    template = Path(template_path) if template_path else DEFAULT_TEMPLATE_PATH
    if not template.exists():
        raise HTTPException(status_code=404, detail=f"Template XLSM not found: {template}")

    collaborators_stmt = select(InazCollaborator)
    if collaborator_id:
        collaborators_stmt = collaborators_stmt.where(InazCollaborator.id.in_(collaborator_id))
    collaborators = db.execute(collaborators_stmt.order_by(InazCollaborator.employee_code.asc())).scalars().all()
    if period_start.month == 12:
        period_end = date(period_start.year + 1, 1, 1)
    else:
        period_end = date(period_start.year, period_start.month + 1, 1)
    schedule_context = build_schedule_context(
        db,
        collaborator_ids=[item.id for item in collaborators],
        date_from=period_start,
        date_to=period_end,
    )
    export_rows: list[ExportTimesheetRow] = []
    for collaborator in collaborators:
        daily_rows = db.execute(
            select(InazDailyRecord)
            .where(
                InazDailyRecord.collaborator_id == collaborator.id,
                InazDailyRecord.work_date >= period_start,
                InazDailyRecord.work_date < period_end,
            )
            .order_by(InazDailyRecord.work_date.asc())
        ).scalars().all()
        if daily_rows:
            punches = db.execute(
                select(InazDailyPunch).where(InazDailyPunch.daily_record_id.in_([item.id for item in daily_rows]))
            ).scalars().all()
            punches_by_record_id: dict[str, list[InazDailyPunch]] = {}
            for punch in punches:
                punches_by_record_id.setdefault(str(punch.daily_record_id), []).append(punch)
            export_rows.append(
                ExportTimesheetRow(
                    collaborator=collaborator,
                    daily_rows=daily_rows,
                    punches_by_record_id=punches_by_record_id,
                )
            )

    if not export_rows:
        raise HTTPException(status_code=404, detail="No daily rows found for the selected period")

    with tempfile.NamedTemporaryFile(prefix="inaz_", suffix=".xlsm", delete=False) as tmp:
        output_path = Path(tmp.name)
    compile_workbook(
        template=template,
        output=output_path,
        rows=export_rows,
        period_start=period_start,
        employee_kind=employee_kind,
        schedule_context=schedule_context,
    )
    return FileResponse(output_path, media_type="application/vnd.ms-excel.sheet.macroEnabled.12", filename=output_path.name)


def _serialize_daily_record(db: Session, record: InazDailyRecord) -> InazDailyRecordResponse:
    punches = db.execute(
        select(InazDailyPunch).where(InazDailyPunch.daily_record_id == record.id).order_by(InazDailyPunch.sequence.asc())
    ).scalars().all()
    detail = extract_detail_payload(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else {}
    effective_straordinario = (
        record.override_straordinario_minutes
        if record.override_straordinario_minutes is not None
        else record.straordinario_minutes
    )
    effective_mpe = record.override_mpe_minutes if record.override_mpe_minutes is not None else record.mpe_minutes
    return InazDailyRecordResponse.model_validate(
        {
            **record.__dict__,
            "punches": punches,
            "effective_straordinario_minutes": effective_straordinario,
            "effective_mpe_minutes": effective_mpe,
            "effective_extra_minutes": (effective_straordinario or 0) + (effective_mpe or 0) or None,
            "request_type": record.request_type
            or (resolve_request_type(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else None),
            "request_description": record.request_description
            or (resolve_request_description(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else None),
            "request_status": record.request_status
            or (resolve_request_status(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else None),
            "request_authorized_by": record.request_authorized_by
            or (resolve_request_authorized_by(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else None),
            "resolved_absence_cause": record.resolved_absence_cause
            or (resolve_absence_cause(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else None),
            "detail_title": detail.get("title"),
            "detail_status": detail.get("status"),
            "detail_programmed_schedule": detail.get("programmed_schedule"),
            "detail_effective_schedule": detail.get("effective_schedule"),
            "detail_time_slots": detail.get("time_slots"),
            "detail_schedule_type": detail.get("schedule_type"),
            "detail_theoretical_hours": detail.get("theoretical_hours"),
            "detail_absence_hours": detail.get("absence_hours"),
            "detail_day_summary": detail.get("day_summary") or {},
            "detail_day_totals": detail.get("day_totals") or {},
            "detail_requests": detail.get("requests") or [],
            "detail_anomalies": detail.get("anomalies") or [],
            "detail_text": detail.get("text"),
            "detail_error": detail.get("error"),
            "special_day": detail_indicates_special_day(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else None,
        }
    )


def _get_collaborator_or_404(db: Session, collaborator_id: uuid.UUID, current_user: ApplicationUser | None = None) -> InazCollaborator:
    collaborator = db.get(InazCollaborator, collaborator_id)
    if collaborator is None or (
        current_user is not None and not _is_admin_user(current_user) and collaborator.owner_user_id != current_user.id
    ):
        raise HTTPException(status_code=404, detail="Collaborator not found")
    return collaborator


def _get_daily_record_or_404(db: Session, record_id: uuid.UUID, current_user: ApplicationUser | None = None) -> InazDailyRecord:
    record = db.get(InazDailyRecord, record_id)
    if record is None or (
        current_user is not None and not _is_admin_user(current_user) and record.owner_user_id != current_user.id
    ):
        raise HTTPException(status_code=404, detail="Daily record not found")
    return record


def _is_admin_user(current_user: ApplicationUser) -> bool:
    return current_user.role in {"admin", "super_admin"}


def _serialize_schedule_template(db: Session, template: InazScheduleTemplate) -> InazScheduleTemplateResponse:
    rules = db.execute(
        select(InazScheduleRule)
        .where(InazScheduleRule.template_id == template.id)
        .order_by(InazScheduleRule.sort_order.asc(), InazScheduleRule.id.asc())
    ).scalars().all()
    return InazScheduleTemplateResponse.model_validate({**template.__dict__, "rules": rules})


def _serialize_schedule_assignment(
    db: Session,
    assignment: InazCollaboratorScheduleAssignment,
) -> InazCollaboratorScheduleAssignmentResponse:
    template = db.get(InazScheduleTemplate, assignment.template_id)
    serialized_template = _serialize_schedule_template(db, template) if template is not None else None
    return InazCollaboratorScheduleAssignmentResponse.model_validate({**assignment.__dict__, "template": serialized_template})
