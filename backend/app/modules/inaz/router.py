from __future__ import annotations

import tempfile
import uuid
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_module, require_role
from app.core.config import settings
from app.core.database import get_db
from app.core.datetime_compat import UTC
from app.models.application_user import ApplicationUser
from app.schemas.users import ApplicationUserResponse
from app.modules.inaz.models import (
    InazCollaborator,
    InazCollaboratorScheduleAssignment,
    InazCredential,
    InazDailyPunch,
    InazDailyRecord,
    InazEventSummary,
    InazHoliday,
    InazImportJob,
    InazScheduleRule,
    InazScheduleTemplate,
    InazSupervisorAssignment,
    InazSyncJob,
)
from app.modules.inaz.schemas import (
    InazAccessContextResponse,
    InazAutoSyncConfigResponse,
    InazAutoSyncConfigUpdate,
    InazScheduleBootstrapApplyRequest,
    InazScheduleBootstrapApplyResponse,
    InazScheduleBootstrapCollaboratorSuggestion,
    InazScheduleBootstrapPresetPreview,
    InazScheduleBootstrapPreviewResponse,
    InazScheduleBootstrapRulePreview,
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
    InazDashboardSummaryResponse,
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
    InazSupervisorAssignmentResponse,
    InazSupervisorAssignmentUpdate,
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
    extract_punch_terminal_labels,
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
from app.modules.inaz.services.auto_sync import get_auto_sync_config, serialize_auto_sync_config, update_auto_sync_config
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
from app.modules.accessi.org_structure import OrgStructureAssignment

router = APIRouter(prefix="/inaz", tags=["inaz"])
RequireInazModule = Depends(require_module("inaz"))
RequireInazAdmin = Depends(require_role("super_admin", "admin"))


@dataclass(frozen=True)
class _BootstrapRuleDefinition:
    label: str | None
    weekday: int | None
    recurrence_kind: str
    start_time: time
    end_time: time
    week_of_month: int | None = None
    interval_weeks: int | None = None
    anchor_date: date | None = None
    season_start_month: int | None = None
    season_start_day: int | None = None
    season_end_month: int | None = None
    season_end_day: int | None = None
    applies_on_holiday: bool = False
    ordinary_label: str | None = None
    sort_order: int = 0


@dataclass(frozen=True)
class _BootstrapTemplatePreset:
    preset_key: str
    template_code: str
    template_label: str
    template_notes: str
    source_schedule_codes: tuple[str, ...]
    rules: tuple[_BootstrapRuleDefinition, ...]


BOOTSTRAP_TEMPLATE_PRESETS: tuple[_BootstrapTemplatePreset, ...] = (
    _BootstrapTemplatePreset(
        preset_key="operai_0714_primo_terzo_sabato",
        template_code="OPE0714_1E3SAB",
        template_label="Operai 07:00-14:00 con 1° e 3° sabato",
        template_notes="Generato da INAZ: OPE0714 + OPESAB. Verificare i sabati 1° e 3° del mese.",
        source_schedule_codes=("OPE0714", "OPESAB"),
        rules=(
            _BootstrapRuleDefinition(
                label="Lun-Ven 07:00-14:00",
                weekday=0,
                recurrence_kind="weekly",
                start_time=time(7, 0),
                end_time=time(14, 0),
                ordinary_label="OPE0714",
                sort_order=0,
            ),
            _BootstrapRuleDefinition(
                label="Mar-Ven 07:00-14:00",
                weekday=1,
                recurrence_kind="weekly",
                start_time=time(7, 0),
                end_time=time(14, 0),
                ordinary_label="OPE0714",
                sort_order=1,
            ),
            _BootstrapRuleDefinition(
                label="Mer-Ven 07:00-14:00",
                weekday=2,
                recurrence_kind="weekly",
                start_time=time(7, 0),
                end_time=time(14, 0),
                ordinary_label="OPE0714",
                sort_order=2,
            ),
            _BootstrapRuleDefinition(
                label="Gio-Ven 07:00-14:00",
                weekday=3,
                recurrence_kind="weekly",
                start_time=time(7, 0),
                end_time=time(14, 0),
                ordinary_label="OPE0714",
                sort_order=3,
            ),
            _BootstrapRuleDefinition(
                label="Ven 07:00-14:00",
                weekday=4,
                recurrence_kind="weekly",
                start_time=time(7, 0),
                end_time=time(14, 0),
                ordinary_label="OPE0714",
                sort_order=4,
            ),
            _BootstrapRuleDefinition(
                label="1° sabato 07:00-13:30",
                weekday=5,
                recurrence_kind="first_weekday_of_month",
                start_time=time(7, 0),
                end_time=time(13, 30),
                ordinary_label="OPESAB",
                sort_order=10,
            ),
            _BootstrapRuleDefinition(
                label="3° sabato 07:00-13:30",
                weekday=5,
                recurrence_kind="nth_weekday_of_month",
                week_of_month=3,
                start_time=time(7, 0),
                end_time=time(13, 30),
                ordinary_label="OPESAB",
                sort_order=11,
            ),
        ),
    ),
    _BootstrapTemplatePreset(
        preset_key="impiegati_flessibile",
        template_code="IMP1_STD",
        template_label="Impiegati flessibile 07:35-14:00",
        template_notes="Generato da INAZ: IMP1.",
        source_schedule_codes=("IMP1",),
        rules=tuple(
            _BootstrapRuleDefinition(
                label=f"Giorno feriale {weekday}",
                weekday=weekday,
                recurrence_kind="weekly",
                start_time=time(7, 35),
                end_time=time(14, 0),
                ordinary_label="IMP1",
                sort_order=weekday,
            )
            for weekday in range(5)
        ),
    ),
    _BootstrapTemplatePreset(
        preset_key="impiegati_rientro",
        template_code="IMP1_RIENTRO",
        template_label="Impiegati con rientro 07:35-14:00 / 14:30-17:45",
        template_notes="Generato da INAZ: IMP1 + RIENTRO IMP.",
        source_schedule_codes=("IMP1", "RIENTRO IMP"),
        rules=(
            *tuple(
                _BootstrapRuleDefinition(
                    label=f"Giorno feriale {weekday}",
                    weekday=weekday,
                    recurrence_kind="weekly",
                    start_time=time(7, 35),
                    end_time=time(14, 0),
                    ordinary_label="IMP1",
                    sort_order=weekday,
                )
                for weekday in range(5)
            ),
            _BootstrapRuleDefinition(
                label="Rientro lunedi pomeriggio",
                weekday=0,
                recurrence_kind="weekly",
                start_time=time(14, 30),
                end_time=time(17, 45),
                ordinary_label="RIENTRO IMP",
                sort_order=10,
            ),
        ),
    ),
    _BootstrapTemplatePreset(
        preset_key="operai_0620_1356",
        template_code="OPE0736_STD",
        template_label="Operai 06:20-13:56",
        template_notes="Generato da INAZ: OPE0736.",
        source_schedule_codes=("OPE0736",),
        rules=tuple(
            _BootstrapRuleDefinition(
                label=f"Giorno feriale {weekday}",
                weekday=weekday,
                recurrence_kind="weekly",
                start_time=time(6, 20),
                end_time=time(13, 56),
                ordinary_label="OPE0736",
                sort_order=weekday,
            )
            for weekday in range(5)
        ),
    ),
)


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


@router.get("/access-context", response_model=InazAccessContextResponse)
def get_inaz_access_context(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireInazModule],
) -> InazAccessContextResponse:
    assigned_count = int(
        db.scalar(
            select(func.count(InazSupervisorAssignment.id)).where(InazSupervisorAssignment.supervisor_user_id == current_user.id)
        )
        or 0
    )
    hierarchy_scope_count = len(_hierarchy_scope_user_ids(db, current_user))
    return InazAccessContextResponse(
        can_view_all_data=_can_view_all_inaz_data(current_user),
        can_view_all_credentials=current_user.is_super_admin,
        can_manage_supervisors=_can_manage_supervisors(current_user),
        is_supervisor=assigned_count > 0 or hierarchy_scope_count > 0,
        assigned_collaborators_count=assigned_count + hierarchy_scope_count,
    )


@router.get("/application-users", response_model=list[ApplicationUserResponse])
def list_inaz_application_users(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, RequireInazAdmin],
    _: Annotated[ApplicationUser, RequireInazModule],
) -> list[ApplicationUserResponse]:
    if not _can_manage_supervisors(current_user):
        raise HTTPException(status_code=403, detail="Inaz user management requires admin privileges")
    rows = db.execute(
        select(ApplicationUser)
        .where(ApplicationUser.is_active.is_(True), ApplicationUser.module_inaz.is_(True))
        .order_by(ApplicationUser.full_name.asc(), ApplicationUser.username.asc())
    ).scalars().all()
    return [ApplicationUserResponse.model_validate(row) for row in rows]


@router.get("/supervisor-assignments", response_model=list[InazSupervisorAssignmentResponse])
def list_supervisor_assignments(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, RequireInazAdmin],
    _: Annotated[ApplicationUser, RequireInazModule],
    supervisor_user_id: int | None = Query(default=None),
) -> list[InazSupervisorAssignmentResponse]:
    if not _can_manage_supervisors(current_user):
        raise HTTPException(status_code=403, detail="Supervisor management requires admin privileges")
    stmt = select(InazSupervisorAssignment)
    if supervisor_user_id is not None:
        stmt = stmt.where(InazSupervisorAssignment.supervisor_user_id == supervisor_user_id)
    rows = db.execute(
        stmt.order_by(InazSupervisorAssignment.supervisor_user_id.asc(), InazSupervisorAssignment.collaborator_id.asc())
    ).scalars().all()
    return [_serialize_supervisor_assignment(db, row) for row in rows]


@router.put("/supervisor-assignments/{collaborator_id}", response_model=InazSupervisorAssignmentResponse | None)
def update_supervisor_assignment(
    collaborator_id: uuid.UUID,
    payload: InazSupervisorAssignmentUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, RequireInazAdmin],
    _: Annotated[ApplicationUser, RequireInazModule],
) -> InazSupervisorAssignmentResponse | None:
    if not _can_manage_supervisors(current_user):
        raise HTTPException(status_code=403, detail="Supervisor management requires admin privileges")
    _get_collaborator_or_404(db, collaborator_id)
    assignment = db.execute(
        select(InazSupervisorAssignment).where(InazSupervisorAssignment.collaborator_id == collaborator_id)
    ).scalar_one_or_none()

    if payload.supervisor_user_id is None:
        if assignment is not None:
            db.delete(assignment)
            db.commit()
        return None

    supervisor = db.get(ApplicationUser, payload.supervisor_user_id)
    if supervisor is None or not supervisor.is_active:
        raise HTTPException(status_code=404, detail="Supervisor user not found")
    if not supervisor.module_inaz and not supervisor.is_super_admin:
        raise HTTPException(status_code=409, detail="The selected user is not enabled for the Inaz module")
    if supervisor.role == "operator":
        raise HTTPException(status_code=409, detail="Operators cannot be assigned as Inaz supervisors")

    if assignment is None:
        assignment = InazSupervisorAssignment(
            supervisor_user_id=payload.supervisor_user_id,
            collaborator_id=collaborator_id,
            assigned_by_user_id=current_user.id,
        )
    else:
        assignment.supervisor_user_id = payload.supervisor_user_id
        assignment.assigned_by_user_id = current_user.id
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return _serialize_supervisor_assignment(db, assignment)


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


@router.get("/configuration/schedule-bootstrap-preview", response_model=InazScheduleBootstrapPreviewResponse)
def get_schedule_bootstrap_preview(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequireInazAdmin],
    __: Annotated[ApplicationUser, RequireInazModule],
) -> InazScheduleBootstrapPreviewResponse:
    return _build_schedule_bootstrap_preview(db)


@router.post("/configuration/schedule-bootstrap-apply", response_model=InazScheduleBootstrapApplyResponse)
def apply_schedule_bootstrap(
    payload: InazScheduleBootstrapApplyRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequireInazAdmin],
    __: Annotated[ApplicationUser, RequireInazModule],
) -> InazScheduleBootstrapApplyResponse:
    preview = _build_schedule_bootstrap_preview(db)
    existing_templates = {
        item.code: item for item in db.execute(select(InazScheduleTemplate)).scalars().all()
    }
    created_templates = 0
    created_assignments = 0
    skipped_existing_templates = 0
    skipped_existing_assignments = 0
    template_codes: list[str] = []
    assigned_employee_codes: list[str] = []

    if payload.create_missing_templates:
        for preset in preview.presets:
            if preset.already_exists:
                skipped_existing_templates += 1
                continue
            preset_def = _preset_by_template_code(preset.template_code)
            if preset_def is None:
                continue
            template = InazScheduleTemplate(
                code=preset_def.template_code,
                label=preset_def.template_label,
                company_code="53",
                is_active=True,
                notes=preset_def.template_notes,
            )
            db.add(template)
            db.flush()
            for rule in preset_def.rules:
                db.add(
                    InazScheduleRule(
                        template_id=template.id,
                        label=rule.label,
                        weekday=rule.weekday,
                        recurrence_kind=rule.recurrence_kind,
                        week_of_month=rule.week_of_month,
                        interval_weeks=rule.interval_weeks,
                        anchor_date=rule.anchor_date,
                        start_time=rule.start_time,
                        end_time=rule.end_time,
                        season_start_month=rule.season_start_month,
                        season_start_day=rule.season_start_day,
                        season_end_month=rule.season_end_month,
                        season_end_day=rule.season_end_day,
                        applies_on_holiday=rule.applies_on_holiday,
                        ordinary_label=rule.ordinary_label,
                        sort_order=rule.sort_order,
                    )
                )
            existing_templates[template.code] = template
            created_templates += 1
            template_codes.append(template.code)

    if payload.assign_unassigned_collaborators:
        for suggestion in preview.collaborator_suggestions:
            if suggestion.suggested_template_code is None:
                continue
            if suggestion.suggestion_confidence != "high":
                skipped_existing_assignments += 1
                continue
            if suggestion.already_assigned:
                skipped_existing_assignments += 1
                continue
            template = existing_templates.get(suggestion.suggested_template_code)
            if template is None:
                skipped_existing_assignments += 1
                continue
            db.add(
                InazCollaboratorScheduleAssignment(
                    collaborator_id=suggestion.collaborator_id,
                    template_id=template.id,
                    notes=f"Bootstrap automatico da schedule code INAZ: {', '.join(suggestion.schedule_codes)}",
                )
            )
            created_assignments += 1
            assigned_employee_codes.append(suggestion.employee_code)

    db.commit()
    return InazScheduleBootstrapApplyResponse(
        created_templates=created_templates,
        created_assignments=created_assignments,
        skipped_existing_templates=skipped_existing_templates,
        skipped_existing_assignments=skipped_existing_assignments,
        template_codes=template_codes,
        assigned_employee_codes=assigned_employee_codes,
    )


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
    if not _can_view_all_inaz_data(current_user):
        hierarchy_scope = _hierarchy_scope_user_ids(db, current_user)
        visible_collaborator_ids = select(InazSupervisorAssignment.collaborator_id).where(
            InazSupervisorAssignment.supervisor_user_id == current_user.id
        )
        visibility_filter = or_(
            InazCollaborator.owner_user_id == current_user.id,
            InazCollaborator.id.in_(visible_collaborator_ids),
            InazCollaborator.owner_user_id.in_(hierarchy_scope),
            InazCollaborator.application_user_id.in_(hierarchy_scope),
        )
        stmt = stmt.where(visibility_filter)
        count_stmt = count_stmt.where(visibility_filter)
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
    include_punches: bool = Query(default=False),
    include_raw_payload: bool = Query(default=True),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=31, ge=1, le=5000),
) -> InazDailyRecordListResponse:
    stmt = select(InazDailyRecord)
    count_stmt = select(func.count(InazDailyRecord.id))

    stmt, count_stmt = _apply_daily_record_filters(
        db,
        current_user,
        stmt=stmt,
        count_stmt=count_stmt,
        collaborator_id=collaborator_id,
        application_user_id=application_user_id,
        date_from=date_from,
        date_to=date_to,
        q=q,
    )

    rows = db.execute(
        stmt.order_by(InazDailyRecord.work_date.asc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    total = db.execute(count_stmt).scalar_one()
    punches_by_record_id: dict[uuid.UUID, list[InazDailyPunch]] | None = None
    if include_punches and rows:
        punches = db.execute(
            select(InazDailyPunch)
            .where(InazDailyPunch.daily_record_id.in_([row.id for row in rows]))
            .order_by(InazDailyPunch.daily_record_id.asc(), InazDailyPunch.sequence.asc())
        ).scalars().all()
        punches_by_record_id = {}
        for punch in punches:
            punches_by_record_id.setdefault(punch.daily_record_id, []).append(punch)
    return InazDailyRecordListResponse(
        items=[
            _serialize_daily_record(
                db,
                row,
                punches=punches_by_record_id.get(row.id) if punches_by_record_id is not None else [],
                include_raw_payload=include_raw_payload,
            )
            for row in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/giornaliere/matrix", response_model=InazDailyRecordListResponse)
def list_giornaliere_matrix(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireInazModule],
    collaborator_id: uuid.UUID | None = Query(default=None),
    application_user_id: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=31, ge=1, le=5000),
) -> InazDailyRecordListResponse:
    stmt = select(InazDailyRecord)
    count_stmt = select(func.count(InazDailyRecord.id))

    stmt, count_stmt = _apply_daily_record_filters(
        db,
        current_user,
        stmt=stmt,
        count_stmt=count_stmt,
        collaborator_id=collaborator_id,
        application_user_id=application_user_id,
        date_from=date_from,
        date_to=date_to,
        q=q,
    )

    rows = db.execute(
        stmt.order_by(InazDailyRecord.work_date.asc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    total = db.execute(count_stmt).scalar_one()
    return InazDailyRecordListResponse(
        items=[_serialize_daily_record_matrix(record) for record in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def _apply_daily_record_filters(
    db: Session,
    current_user: ApplicationUser,
    *,
    stmt,
    count_stmt,
    collaborator_id: uuid.UUID | None,
    application_user_id: int | None,
    date_from: date | None,
    date_to: date | None,
    q: str | None,
):

    if not _can_view_all_inaz_data(current_user):
        hierarchy_scope = _hierarchy_scope_user_ids(db, current_user)
        visible_collaborator_ids = select(InazSupervisorAssignment.collaborator_id).where(
            InazSupervisorAssignment.supervisor_user_id == current_user.id
        )
        visibility_filter = or_(
            InazDailyRecord.owner_user_id == current_user.id,
            InazDailyRecord.collaborator_id.in_(visible_collaborator_ids),
            InazDailyRecord.owner_user_id.in_(hierarchy_scope),
            InazDailyRecord.application_user_id.in_(hierarchy_scope),
        )
        stmt = stmt.where(visibility_filter)
        count_stmt = count_stmt.where(visibility_filter)

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

    return stmt, count_stmt


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
    payload_data = payload.model_dump(exclude_unset=True)
    validation_fields = {"validation_status", "validation_note"}
    manual_edit_fields = {
        "km_value",
        "reperibilita_unit",
        "reperibilita_quantity",
        "override_straordinario_minutes",
        "override_mpe_minutes",
        "manual_note",
    }
    if any(field in payload_data for field in manual_edit_fields) and not _can_edit_daily_record(current_user, record):
        raise HTTPException(status_code=403, detail="Edit privileges required for this daily record")
    if any(field in payload_data for field in validation_fields) and not _can_validate_daily_record(db, current_user, record):
        raise HTTPException(status_code=403, detail="Validation privileges required for this daily record")
    for field, value in payload_data.items():
        setattr(record, field, value)
    if "validation_status" in payload_data:
        if record.validation_status == "validated":
            record.validated_by_user_id = current_user.id
            record.validated_at = datetime.now(UTC)
        else:
            record.validated_by_user_id = None
            record.validated_at = None
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
    if not _can_view_all_inaz_data(current_user):
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
    if job is None or (not _can_view_all_inaz_data(current_user) and job.requested_by_user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Import job not found")
    return InazImportJobResponse.model_validate(job)


def _create_sync_job_record(
    db: Session,
    *,
    requested_by_user_id: int,
    credential_id: int,
    year: int,
    month: int,
    collaborator_limit: int | None,
    trigger: str = "manual",
) -> InazSyncJob:
    credential = db.get(InazCredential, credential_id)
    if credential is None:
        raise HTTPException(status_code=404, detail="Credenziale Inaz non trovata")
    if not credential.active:
        raise HTTPException(status_code=409, detail="La credenziale Inaz selezionata non e attiva")

    period_start, period_end = build_period(year, month)
    job = InazSyncJob(
        status="pending",
        requested_by_user_id=requested_by_user_id,
        credential_id=credential_id,
        period_start=period_start,
        period_end=period_end,
        collaborator_limit=collaborator_limit,
        max_attempts=settings.inaz_sync_max_attempts,
        params_json={
            "auth_mode": "credential",
            "year": year,
            "month": month,
            "trigger": trigger,
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
    return job


@router.get("/sync/config", response_model=InazAutoSyncConfigResponse)
def get_sync_config(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireInazModule],
) -> InazAutoSyncConfigResponse:
    _ = current_user
    return serialize_auto_sync_config(get_auto_sync_config(db))


@router.put("/sync/config", response_model=InazAutoSyncConfigResponse)
def put_sync_config(
    payload: InazAutoSyncConfigUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireInazModule],
) -> InazAutoSyncConfigResponse:
    config = update_auto_sync_config(db, payload, user_id=current_user.id)
    return serialize_auto_sync_config(config)


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
    job = _create_sync_job_record(
        db,
        requested_by_user_id=current_user.id,
        credential_id=credential.id,
        year=payload.year,
        month=payload.month,
        collaborator_limit=payload.collaborator_limit,
        trigger="manual",
    )
    return InazSyncJobResponse.model_validate(job)


@router.get("/sync/jobs", response_model=InazSyncJobListResponse)
def list_sync_jobs(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireInazModule],
    limit: int | None = Query(default=None, ge=1, le=100),
) -> InazSyncJobListResponse:
    reconcile_stale_sync_jobs(db)
    stmt = select(InazSyncJob)
    count_stmt = select(func.count(InazSyncJob.id))
    if not _can_view_all_inaz_data(current_user):
        visibility_filter = InazSyncJob.requested_by_user_id == current_user.id
        stmt = stmt.where(visibility_filter)
        count_stmt = count_stmt.where(visibility_filter)
    stmt = stmt.order_by(InazSyncJob.created_at.desc())
    if limit is not None:
        stmt = stmt.limit(limit)
    jobs = db.execute(stmt).scalars().all()
    total = db.execute(count_stmt).scalar_one()
    return InazSyncJobListResponse(items=[InazSyncJobResponse.model_validate(job) for job in jobs], total=total)


@router.get("/sync/jobs/{job_id}", response_model=InazSyncJobResponse)
def get_sync_job(
    job_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireInazModule],
) -> InazSyncJobResponse:
    reconcile_stale_sync_jobs(db)
    job = db.get(InazSyncJob, job_id)
    if job is None or (not _can_view_all_inaz_data(current_user) and job.requested_by_user_id != current_user.id):
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
    if job is None or (not _can_view_all_inaz_data(current_user) and job.requested_by_user_id != current_user.id):
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
    if job is None or (not _can_view_all_inaz_data(current_user) and job.requested_by_user_id != current_user.id):
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
    if job is None or (not _can_view_all_inaz_data(current_user) and job.requested_by_user_id != current_user.id):
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
    if job is None or (not _can_view_all_inaz_data(current_user) and job.requested_by_user_id != current_user.id):
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


@router.get("/dashboard/summary", response_model=InazDashboardSummaryResponse)
def get_dashboard_summary(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequireInazModule],
    period_start: date = Query(...),
    period_end: date = Query(...),
) -> InazDashboardSummaryResponse:
    collaborator_stmt = select(InazCollaborator)
    collaborator_count_stmt = select(func.count(InazCollaborator.id))
    record_stmt = select(InazDailyRecord).where(
        InazDailyRecord.work_date >= period_start,
        InazDailyRecord.work_date <= period_end,
    )
    record_count_stmt = select(func.count(InazDailyRecord.id)).where(
        InazDailyRecord.work_date >= period_start,
        InazDailyRecord.work_date <= period_end,
    )

    if not _can_view_all_inaz_data(current_user):
        hierarchy_scope = _hierarchy_scope_user_ids(db, current_user)
        visible_collaborator_ids = select(InazSupervisorAssignment.collaborator_id).where(
            InazSupervisorAssignment.supervisor_user_id == current_user.id
        )
        collaborator_visibility_filter = or_(
            InazCollaborator.owner_user_id == current_user.id,
            InazCollaborator.id.in_(visible_collaborator_ids),
            InazCollaborator.owner_user_id.in_(hierarchy_scope),
            InazCollaborator.application_user_id.in_(hierarchy_scope),
        )
        record_visibility_filter = or_(
            InazDailyRecord.owner_user_id == current_user.id,
            InazDailyRecord.collaborator_id.in_(visible_collaborator_ids),
            InazDailyRecord.owner_user_id.in_(hierarchy_scope),
            InazDailyRecord.application_user_id.in_(hierarchy_scope),
        )
        collaborator_stmt = collaborator_stmt.where(collaborator_visibility_filter)
        collaborator_count_stmt = collaborator_count_stmt.where(collaborator_visibility_filter)
        record_stmt = record_stmt.where(record_visibility_filter)
        record_count_stmt = record_count_stmt.where(record_visibility_filter)

    collaborators_total = db.execute(collaborator_count_stmt).scalar_one()
    mapped_collaborators_total = db.execute(
        collaborator_count_stmt.where(InazCollaborator.application_user_id.is_not(None))
    ).scalar_one()
    daily_records_total = db.execute(record_count_stmt).scalar_one()

    records = db.execute(record_stmt.order_by(InazDailyRecord.work_date.asc())).scalars().all()

    ordinary_minutes_total = 0
    absence_minutes_total = 0
    extra_minutes_total = 0
    straordinario_minutes_total = 0
    maggior_presenza_minutes_total = 0
    km_total = 0
    anomaly_total = 0
    special_day_total = 0
    worked_days_total = 0
    absence_days_total = 0
    justified_days_total = 0
    active_collaborator_ids: set[uuid.UUID] = set()
    cause_stats: dict[str, int] = {}
    schedule_stats: dict[str, int] = {}

    for record in records:
        active_collaborator_ids.add(record.collaborator_id)
        ordinary_minutes_total += record.ordinary_minutes or 0
        absence_minutes_total += record.absence_minutes or 0
        effective_straordinario = (
            record.override_straordinario_minutes
            if record.override_straordinario_minutes is not None
            else record.straordinario_minutes or 0
        )
        effective_mpe = record.override_mpe_minutes if record.override_mpe_minutes is not None else record.mpe_minutes or 0
        straordinario_minutes_total += effective_straordinario
        maggior_presenza_minutes_total += effective_mpe
        extra_minutes_total += effective_straordinario + effective_mpe
        km_total += record.km_value or 0
        if (record.ordinary_minutes or 0) > 0:
            worked_days_total += 1
        if (record.absence_minutes or 0) > 0:
            absence_days_total += 1
        if (record.justified_minutes or 0) > 0:
            justified_days_total += 1

        detail = extract_detail_payload(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else {}
        anomalies = detail.get("anomalies") or []
        detail_status = str(detail.get("status") or "").lower()
        stato = str(record.stato or "").lower()
        if anomalies or "anom" in detail_status or "anom" in stato:
            anomaly_total += 1
        if detail_indicates_special_day(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else False:
            special_day_total += 1

        cause = (record.resolved_absence_cause or "").strip().lower()
        if cause:
            cause_stats[cause] = (cause_stats.get(cause) or 0) + 1

        schedule_code = (record.schedule_code or "").strip()
        if not schedule_code and isinstance(detail.get("programmed_schedule"), str):
            schedule_code = str(detail["programmed_schedule"]).split(" - ")[0].strip()
        if schedule_code:
            schedule_stats[schedule_code] = (schedule_stats.get(schedule_code) or 0) + 1

    top_schedule_stats = [
        {"code": code, "count": count}
        for code, count in sorted(schedule_stats.items(), key=lambda item: (-item[1], item[0]))[:4]
    ]

    return InazDashboardSummaryResponse(
        period_start=period_start,
        period_end=period_end,
        collaborators_total=collaborators_total,
        mapped_collaborators_total=mapped_collaborators_total,
        active_collaborators_total=len(active_collaborator_ids),
        daily_records_total=daily_records_total,
        ordinary_minutes_total=ordinary_minutes_total,
        absence_minutes_total=absence_minutes_total,
        extra_minutes_total=extra_minutes_total,
        straordinario_minutes_total=straordinario_minutes_total,
        maggior_presenza_minutes_total=maggior_presenza_minutes_total,
        km_total=km_total,
        anomaly_total=anomaly_total,
        special_day_total=special_day_total,
        worked_days_total=worked_days_total,
        absence_days_total=absence_days_total,
        justified_days_total=justified_days_total,
        cause_stats=cause_stats,
        schedule_stats=top_schedule_stats,
    )


def _build_schedule_bootstrap_preview(db: Session) -> InazScheduleBootstrapPreviewResponse:
    collaborators = db.execute(select(InazCollaborator).order_by(InazCollaborator.employee_code.asc())).scalars().all()
    assignment_rows = db.execute(select(InazCollaboratorScheduleAssignment)).scalars().all()
    collaborator_ids = [item.id for item in collaborators]
    assignment_by_collaborator = {row.collaborator_id: row for row in assignment_rows}

    record_rows = db.execute(
        select(InazDailyRecord.collaborator_id, InazDailyRecord.schedule_code).where(
            InazDailyRecord.collaborator_id.in_(collaborator_ids),
            InazDailyRecord.schedule_code.is_not(None),
        )
    ).all()

    schedule_counts_by_collaborator: dict[uuid.UUID, dict[str, int]] = {}
    total_schedule_counts: dict[str, int] = {}
    collaborators_by_schedule_code: dict[str, set[uuid.UUID]] = {}
    for collaborator_id, schedule_code in record_rows:
        normalized_code = (schedule_code or "").strip().upper()
        if not normalized_code:
            continue
        schedule_counts_by_collaborator.setdefault(collaborator_id, {})
        schedule_counts_by_collaborator[collaborator_id][normalized_code] = (
            schedule_counts_by_collaborator[collaborator_id].get(normalized_code, 0) + 1
        )
        total_schedule_counts[normalized_code] = total_schedule_counts.get(normalized_code, 0) + 1
        collaborators_by_schedule_code.setdefault(normalized_code, set()).add(collaborator_id)

    existing_templates = db.execute(select(InazScheduleTemplate)).scalars().all()
    existing_template_codes = {item.code.strip().upper() for item in existing_templates}

    presets: list[InazScheduleBootstrapPresetPreview] = []
    for preset in BOOTSTRAP_TEMPLATE_PRESETS:
        detected_records_count = sum(total_schedule_counts.get(code, 0) for code in preset.source_schedule_codes)
        detected_collaborators: set[uuid.UUID] = set()
        for code in preset.source_schedule_codes:
            detected_collaborators.update(collaborators_by_schedule_code.get(code, set()))
        if detected_records_count <= 0 and not detected_collaborators:
            continue
        presets.append(
            InazScheduleBootstrapPresetPreview(
                preset_key=preset.preset_key,
                template_code=preset.template_code,
                template_label=preset.template_label,
                template_notes=preset.template_notes,
                source_schedule_codes=list(preset.source_schedule_codes),
                detected_records_count=detected_records_count,
                detected_collaborators_count=len(detected_collaborators),
                already_exists=preset.template_code.strip().upper() in existing_template_codes,
                rules=[
                    InazScheduleBootstrapRulePreview(
                        label=rule.label,
                        weekday=rule.weekday,
                        recurrence_kind=rule.recurrence_kind,
                        week_of_month=rule.week_of_month,
                        interval_weeks=rule.interval_weeks,
                        anchor_date=rule.anchor_date,
                        start_time=rule.start_time,
                        end_time=rule.end_time,
                        season_start_month=rule.season_start_month,
                        season_start_day=rule.season_start_day,
                        season_end_month=rule.season_end_month,
                        season_end_day=rule.season_end_day,
                        applies_on_holiday=rule.applies_on_holiday,
                        ordinary_label=rule.ordinary_label,
                        sort_order=rule.sort_order,
                    )
                    for rule in preset.rules
                ],
            )
        )

    collaborator_suggestions: list[InazScheduleBootstrapCollaboratorSuggestion] = []
    for collaborator in collaborators:
        code_counts = schedule_counts_by_collaborator.get(collaborator.id, {})
        sorted_codes = [code for code, _ in sorted(code_counts.items(), key=lambda item: (-item[1], item[0]))]
        preset, confidence, reason = _suggest_bootstrap_preset(sorted_codes, code_counts)
        collaborator_suggestions.append(
            InazScheduleBootstrapCollaboratorSuggestion(
                collaborator_id=collaborator.id,
                employee_code=collaborator.employee_code,
                collaborator_name=collaborator.name,
                company_code=collaborator.company_code,
                dominant_schedule_code=sorted_codes[0] if sorted_codes else None,
                schedule_codes=sorted_codes,
                suggested_template_code=preset.template_code if preset is not None else None,
                suggested_template_label=preset.template_label if preset is not None else None,
                suggestion_confidence=confidence,
                suggestion_reason=reason,
                already_assigned=collaborator.id in assignment_by_collaborator,
            )
        )

    collaborator_suggestions.sort(
        key=lambda item: (
            item.already_assigned,
            item.suggestion_confidence == "none",
            item.suggestion_confidence == "low",
            item.employee_code,
        )
    )

    return InazScheduleBootstrapPreviewResponse(
        detected_collaborators_total=len(collaborators),
        collaborators_with_suggestion_total=sum(1 for item in collaborator_suggestions if item.suggested_template_code is not None),
        collaborators_without_assignment_total=sum(1 for item in collaborator_suggestions if not item.already_assigned),
        presets=presets,
        collaborator_suggestions=collaborator_suggestions,
    )


def _suggest_bootstrap_preset(
    sorted_codes: list[str],
    code_counts: dict[str, int],
) -> tuple[_BootstrapTemplatePreset | None, str, str | None]:
    code_set = set(sorted_codes)
    if "OPE0714" in code_set:
        return (
            _preset_by_key("operai_0714_primo_terzo_sabato"),
            "high",
            "Sono stati rilevati codici operai compatibili con il turno 07:00-14:00 e il sabato 07:00-13:30.",
        )
    if "RIENTRO IMP" in code_set:
        return (
            _preset_by_key("impiegati_rientro"),
            "high",
            "E' presente il codice di rientro impiegati, quindi il profilo con rientro e il piu coerente.",
        )
    if "IMP1" in code_set:
        return (
            _preset_by_key("impiegati_flessibile"),
            "high",
            "Il codice IMP1 e stato rilevato in modo coerente sui dati storici.",
        )
    if "OPE0736" in code_set:
        return (
            _preset_by_key("operai_0620_1356"),
            "high",
            "Il codice OPE0736 e stato rilevato in modo coerente sui dati storici.",
        )
    probable_preset = _suggest_probable_bootstrap_preset(sorted_codes, code_counts)
    if probable_preset is not None:
        return probable_preset
    return None, "none", None


def _suggest_probable_bootstrap_preset(
    sorted_codes: list[str],
    code_counts: dict[str, int],
) -> tuple[_BootstrapTemplatePreset | None, str, str | None] | None:
    if not sorted_codes:
        return None
    dominant_code = sorted_codes[0]
    total_count = sum(code_counts.values())
    dominant_count = code_counts.get(dominant_code, 0)
    dominance_ratio = (dominant_count / total_count) if total_count > 0 else 0

    if dominant_code == "OPESAB":
        return (
            _preset_by_key("operai_0714_primo_terzo_sabato"),
            "medium" if dominance_ratio >= 0.6 else "low",
            "E' stato rilevato soprattutto OPESAB: il sistema propone il profilo operai con sabato, ma richiede conferma.",
        )
    if dominant_code == "IMP1":
        return (
            _preset_by_key("impiegati_flessibile"),
            "medium" if dominance_ratio >= 0.6 else "low",
            "E' stato rilevato soprattutto IMP1: il sistema propone il profilo impiegati standard, ma richiede conferma.",
        )
    if dominant_code == "RIENTRO IMP":
        return (
            _preset_by_key("impiegati_rientro"),
            "medium" if dominance_ratio >= 0.6 else "low",
            "E' stato rilevato soprattutto RIENTRO IMP: il sistema propone il profilo con rientro, ma richiede conferma.",
        )
    if dominant_code == "OPE0736":
        return (
            _preset_by_key("operai_0620_1356"),
            "medium" if dominance_ratio >= 0.6 else "low",
            "E' stato rilevato soprattutto OPE0736: il sistema propone il profilo operai 06:20-13:56, ma richiede conferma.",
        )
    return None


def _preset_by_key(preset_key: str) -> _BootstrapTemplatePreset | None:
    for preset in BOOTSTRAP_TEMPLATE_PRESETS:
        if preset.preset_key == preset_key:
            return preset
    return None


def _preset_by_template_code(template_code: str) -> _BootstrapTemplatePreset | None:
    normalized = template_code.strip().upper()
    for preset in BOOTSTRAP_TEMPLATE_PRESETS:
        if preset.template_code.strip().upper() == normalized:
            return preset
    return None


def _serialize_daily_record(
    db: Session,
    record: InazDailyRecord,
    *,
    punches: list[InazDailyPunch] | None = None,
    include_raw_payload: bool = True,
) -> InazDailyRecordResponse:
    if punches is None:
        punches = db.execute(
            select(InazDailyPunch).where(InazDailyPunch.daily_record_id == record.id).order_by(InazDailyPunch.sequence.asc())
        ).scalars().all()
    detail = extract_detail_payload(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else {}
    terminal_rows = extract_punch_terminal_labels(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else []
    serialized_punches = []
    for punch in punches:
        terminal_label = punch.terminal_label
        if terminal_label is None:
            entry = punch.entry_time.strftime("%H:%M") if punch.entry_time else None
            exit_value = punch.exit_time.strftime("%H:%M") if punch.exit_time else None
            terminal_label = next(
                (
                    item["terminal_label"]
                    for item in terminal_rows
                    if (item["direction"] == "E" and item["time"] == entry)
                    or (item["direction"] == "U" and item["time"] == exit_value)
                ),
                None,
            )
        serialized_punches.append(
            {
                "id": punch.id,
                "daily_record_id": punch.daily_record_id,
                "sequence": punch.sequence,
                "entry_time": punch.entry_time,
                "exit_time": punch.exit_time,
                "terminal_label": terminal_label,
            }
        )
    effective_straordinario = (
        record.override_straordinario_minutes
        if record.override_straordinario_minutes is not None
        else record.straordinario_minutes
    )
    effective_mpe = record.override_mpe_minutes if record.override_mpe_minutes is not None else record.mpe_minutes
    return InazDailyRecordResponse.model_validate(
        {
            **record.__dict__,
            "punches": serialized_punches,
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
            "raw_payload_json": record.raw_payload_json if include_raw_payload else None,
        }
    )


def _serialize_daily_record_matrix(record: InazDailyRecord) -> InazDailyRecordResponse:
    detail = extract_detail_payload(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else {}
    effective_straordinario = (
        record.override_straordinario_minutes
        if record.override_straordinario_minutes is not None
        else record.straordinario_minutes
    )
    effective_mpe = record.override_mpe_minutes if record.override_mpe_minutes is not None else record.mpe_minutes
    detail_anomalies = detail.get("anomalies") or []
    return InazDailyRecordResponse.model_validate(
        {
            **record.__dict__,
            "punches": [],
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
            "detail_title": None,
            "detail_status": detail.get("status"),
            "detail_programmed_schedule": detail.get("programmed_schedule"),
            "detail_effective_schedule": None,
            "detail_time_slots": None,
            "detail_schedule_type": None,
            "detail_theoretical_hours": None,
            "detail_absence_hours": None,
            "detail_day_summary": {},
            "detail_day_totals": {},
            "detail_requests": [],
            "detail_anomalies": detail_anomalies,
            "detail_text": None,
            "detail_error": detail.get("error"),
            "special_day": detail_indicates_special_day(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else None,
            "raw_payload_json": None,
        }
    )


def _get_collaborator_or_404(db: Session, collaborator_id: uuid.UUID, current_user: ApplicationUser | None = None) -> InazCollaborator:
    collaborator = db.get(InazCollaborator, collaborator_id)
    if collaborator is None or (current_user is not None and not _can_access_collaborator(db, current_user, collaborator)):
        raise HTTPException(status_code=404, detail="Collaborator not found")
    return collaborator


def _get_daily_record_or_404(db: Session, record_id: uuid.UUID, current_user: ApplicationUser | None = None) -> InazDailyRecord:
    record = db.get(InazDailyRecord, record_id)
    if record is None or (current_user is not None and not _can_access_daily_record(db, current_user, record)):
        raise HTTPException(status_code=404, detail="Daily record not found")
    return record


def _is_admin_user(current_user: ApplicationUser) -> bool:
    return current_user.role in {"admin", "super_admin"}


def _is_hr_manager(current_user: ApplicationUser) -> bool:
    return current_user.role == "hr_manager"


def _can_view_all_inaz_data(current_user: ApplicationUser) -> bool:
    return _is_admin_user(current_user) or _is_hr_manager(current_user)


def _can_manage_supervisors(current_user: ApplicationUser) -> bool:
    return _is_admin_user(current_user)


def _has_supervisor_assignment(db: Session, current_user: ApplicationUser, collaborator_id: uuid.UUID) -> bool:
    assignment = db.execute(
        select(InazSupervisorAssignment.id).where(
            InazSupervisorAssignment.supervisor_user_id == current_user.id,
            InazSupervisorAssignment.collaborator_id == collaborator_id,
        )
    ).scalar_one_or_none()
    return assignment is not None


def _hierarchy_scope_user_ids(db: Session, current_user: ApplicationUser) -> set[int]:
    assignments = db.scalars(select(OrgStructureAssignment)).all()
    children_by_manager: dict[int, list[int]] = {}
    for assignment in assignments:
        if assignment.manager_user_id is None:
            continue
        children_by_manager.setdefault(assignment.manager_user_id, []).append(assignment.application_user_id)
    scope: set[int] = set()
    queue = list(children_by_manager.get(current_user.id, []))
    while queue:
        user_id = queue.pop(0)
        if user_id in scope:
            continue
        scope.add(user_id)
        queue.extend(children_by_manager.get(user_id, []))
    return scope


def _can_access_by_hierarchy(current_user: ApplicationUser, *, owner_user_id: int | None, application_user_id: int | None, hierarchy_scope: set[int]) -> bool:
    if owner_user_id == current_user.id:
        return True
    if owner_user_id is not None and owner_user_id in hierarchy_scope:
        return True
    if application_user_id is not None and application_user_id in hierarchy_scope:
        return True
    return False


def _can_access_collaborator(db: Session, current_user: ApplicationUser, collaborator: InazCollaborator) -> bool:
    if _can_view_all_inaz_data(current_user):
        return True
    hierarchy_scope = _hierarchy_scope_user_ids(db, current_user)
    if _can_access_by_hierarchy(
        current_user,
        owner_user_id=collaborator.owner_user_id,
        application_user_id=collaborator.application_user_id,
        hierarchy_scope=hierarchy_scope,
    ):
        return True
    return _has_supervisor_assignment(db, current_user, collaborator.id)


def _can_access_daily_record(db: Session, current_user: ApplicationUser, record: InazDailyRecord) -> bool:
    if _can_view_all_inaz_data(current_user):
        return True
    hierarchy_scope = _hierarchy_scope_user_ids(db, current_user)
    if _can_access_by_hierarchy(
        current_user,
        owner_user_id=record.owner_user_id,
        application_user_id=record.application_user_id,
        hierarchy_scope=hierarchy_scope,
    ):
        return True
    return _has_supervisor_assignment(db, current_user, record.collaborator_id)


def _can_validate_daily_record(db: Session, current_user: ApplicationUser, record: InazDailyRecord) -> bool:
    if _can_view_all_inaz_data(current_user):
        return True
    hierarchy_scope = _hierarchy_scope_user_ids(db, current_user)
    if _can_access_by_hierarchy(
        current_user,
        owner_user_id=record.owner_user_id,
        application_user_id=record.application_user_id,
        hierarchy_scope=hierarchy_scope,
    ):
        return True
    return _has_supervisor_assignment(db, current_user, record.collaborator_id)


def _can_edit_daily_record(current_user: ApplicationUser, record: InazDailyRecord) -> bool:
    if _can_view_all_inaz_data(current_user):
        return True
    return record.owner_user_id == current_user.id


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


def _serialize_supervisor_assignment(
    db: Session,
    assignment: InazSupervisorAssignment,
) -> InazSupervisorAssignmentResponse:
    collaborator = db.get(InazCollaborator, assignment.collaborator_id)
    supervisor = db.get(ApplicationUser, assignment.supervisor_user_id)
    supervisor_payload = None
    if supervisor is not None:
        supervisor_payload = {
            "id": supervisor.id,
            "username": supervisor.username,
            "full_name": supervisor.full_name,
            "email": supervisor.email,
            "role": supervisor.role,
            "is_active": supervisor.is_active,
        }
    return InazSupervisorAssignmentResponse.model_validate(
        {
            **assignment.__dict__,
            "supervisor": supervisor_payload,
            "collaborator": InazCollaboratorResponse.model_validate(collaborator) if collaborator is not None else None,
        }
    )
