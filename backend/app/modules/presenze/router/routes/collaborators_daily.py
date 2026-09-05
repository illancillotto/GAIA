from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.core.datetime_compat import UTC
from app.models.application_user import ApplicationUser
from app.modules.presenze.mapping_audit import (
    PresenzeCollaboratorApplicationUserUpdate,
    PresenzeCollaboratorMappingAuditResponse,
)
from app.modules.presenze.models import (
    PresenzeCollaborator,
    PresenzeDailyPunch,
    PresenzeDailyRecord,
    PresenzeEventSummary,
    PresenzeOperaiRuleConfig,
)
from app.modules.presenze.router.common import RequirePresenzeAdmin, RequirePresenzeModule
from app.modules.presenze.router.helpers.access import (
    _can_edit_daily_record,
    _can_validate_daily_record,
    _can_view_all_inaz_data,
)
from app.modules.presenze.router.helpers.collaborators import _serialize_collaborator
from app.modules.presenze.router.helpers.daily_records import (
    _build_classification_map,
    _build_collaborator_snapshot_map,
    _build_monthly_night_bonus_map,
    _build_operational_quality_map,
    _daily_record_has_anomaly,
    _filter_anomaly_rows,
    _get_collaborator_or_404,
    _get_daily_record_or_404,
    _month_end,
    _resolve_recent_month_values,
    _resolve_refresh_credential_for_user,
    _serialize_anomaly_list_item,
    _serialize_daily_record,
    _serialize_daily_record_matrix,
)
from app.modules.presenze.router.helpers.jobs import _create_sync_job_record
from app.modules.presenze.router.helpers.schedules import (
    _load_latest_template_codes_by_collaborator,
)
from app.modules.presenze.schemas import (
    PresenzeAnomalyListResponse,
    PresenzeAnomalyMonthSummaryItemResponse,
    PresenzeAnomalyMonthSummaryResponse,
    PresenzeCollaboratorCalendarResponse,
    PresenzeCollaboratorContractProfileUpdate,
    PresenzeCollaboratorListResponse,
    PresenzeCollaboratorResponse,
    PresenzeCollaboratorSummaryResponse,
    PresenzeDailyRecordListResponse,
    PresenzeDailyRecordManualUpdate,
    PresenzeDailyRecordResponse,
    PresenzeEventSummaryResponse,
    PresenzeOperaiRuleConfigResponse,
    PresenzeOperaiRuleConfigUpdate,
    PresenzeSyncJobResponse,
)
from app.modules.presenze.services.collaborator_mapping import (
    CollaboratorMappingConflictError,
    apply_collaborator_mapping,
    list_collaborator_mapping_audit,
)
from app.modules.presenze.services.contract_profile import (
    normalize_operai_group,
)
from app.modules.presenze.services.operai_rules import (
    ensure_operai_rule_configs,
    load_operai_rule_configs,
)
from app.modules.presenze.services.sync_runtime import (
    has_running_sync_job,
)
from app.modules.presenze.services.visibility_policy import (
    collaborator_visibility_filter,
    daily_record_visibility_filter,
    resolve_presenze_visibility,
)

# Keep extracted callable formatting stable for complexity-baseline matching.
# fmt: off

router = APIRouter(prefix="/presenze")

@router.get("/collaborators", response_model=PresenzeCollaboratorListResponse)
def list_collaborators(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    q: str | None = Query(default=None),
    mapped_only: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
) -> PresenzeCollaboratorListResponse:
    stmt = select(PresenzeCollaborator)
    count_stmt = select(func.count(PresenzeCollaborator.id))
    if not _can_view_all_inaz_data(current_user):
        visibility_filter = collaborator_visibility_filter(resolve_presenze_visibility(db, current_user))
        stmt = stmt.where(visibility_filter)
        count_stmt = count_stmt.where(visibility_filter)
    if q:
        term = f"%{q.strip()}%"
        condition = or_(
            PresenzeCollaborator.name.ilike(term),
            PresenzeCollaborator.employee_code.ilike(term),
            PresenzeCollaborator.company_code.ilike(term),
        )
        stmt = stmt.where(condition)
        count_stmt = count_stmt.where(condition)
    if mapped_only is True:
        stmt = stmt.where(PresenzeCollaborator.application_user_id.is_not(None))
        count_stmt = count_stmt.where(PresenzeCollaborator.application_user_id.is_not(None))
    if mapped_only is False:
        stmt = stmt.where(PresenzeCollaborator.application_user_id.is_(None))
        count_stmt = count_stmt.where(PresenzeCollaborator.application_user_id.is_(None))

    rows = db.execute(
        stmt.order_by(PresenzeCollaborator.name.asc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    total = db.execute(count_stmt).scalar_one()
    template_codes = _load_latest_template_codes_by_collaborator(db, [row.id for row in rows])
    return PresenzeCollaboratorListResponse(
        items=[_serialize_collaborator(db, row, template_code=template_codes.get(row.id)) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )

@router.put("/collaborators/{collaborator_id}/application-user", response_model=PresenzeCollaboratorResponse)
def map_collaborator_to_application_user(
    collaborator_id: uuid.UUID,
    payload: PresenzeCollaboratorApplicationUserUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeCollaboratorResponse:
    collaborator = _get_collaborator_or_404(db, collaborator_id)
    _apply_collaborator_mapping_or_raise(
        db,
        collaborator=collaborator,
        application_user_id=payload.application_user_id,
        changed_by=current_user,
        reason=payload.reason,
    )
    db.refresh(collaborator)
    return _serialize_collaborator(db, collaborator)

@router.get(
    "/collaborators/{collaborator_id}/application-user-audit",
    response_model=list[PresenzeCollaboratorMappingAuditResponse],
)
def get_collaborator_application_user_audit(
    collaborator_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> list[PresenzeCollaboratorMappingAuditResponse]:
    _get_collaborator_or_404(db, collaborator_id)
    return [
        PresenzeCollaboratorMappingAuditResponse.model_validate(item)
        for item in list_collaborator_mapping_audit(db, collaborator_id)
    ]

@router.put("/collaborators/{collaborator_id}/contract-profile", response_model=PresenzeCollaboratorResponse)
def update_collaborator_contract_profile(
    collaborator_id: uuid.UUID,
    payload: PresenzeCollaboratorContractProfileUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeCollaboratorResponse:
    collaborator = _get_collaborator_or_404(db, collaborator_id)
    collaborator.contract_kind = payload.contract_kind
    collaborator.operai_group = payload.operai_group
    collaborator.standard_daily_minutes = payload.standard_daily_minutes
    db.add(collaborator)
    db.commit()
    db.refresh(collaborator)
    return _serialize_collaborator(db, collaborator)

@router.get("/configuration/operai-rules", response_model=list[PresenzeOperaiRuleConfigResponse])
def list_operai_rule_configs(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> list[PresenzeOperaiRuleConfigResponse]:
    ensure_operai_rule_configs(db)
    db.commit()
    items = db.execute(select(PresenzeOperaiRuleConfig).order_by(PresenzeOperaiRuleConfig.code.asc())).scalars().all()
    return [PresenzeOperaiRuleConfigResponse.model_validate(item) for item in items]

@router.patch("/configuration/operai-rules/{rule_id}", response_model=PresenzeOperaiRuleConfigResponse)
def update_operai_rule_config(
    rule_id: int,
    payload: PresenzeOperaiRuleConfigUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeOperaiRuleConfigResponse:
    ensure_operai_rule_configs(db)
    db.commit()
    item = db.get(PresenzeOperaiRuleConfig, rule_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Operai rule config not found")
    data = payload.model_dump(exclude_unset=True)
    if "operai_group" in data:
        data["operai_group"] = normalize_operai_group(data["operai_group"])
    for key, value in data.items():
        setattr(item, key, value)
    db.add(item)
    db.commit()
    db.refresh(item)
    return PresenzeOperaiRuleConfigResponse.model_validate(item)

@router.get("/giornaliere", response_model=PresenzeDailyRecordListResponse)
def list_giornaliere(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    collaborator_id: uuid.UUID | None = Query(default=None),
    application_user_id: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    q: str | None = Query(default=None),
    include_punches: bool = Query(default=False),
    include_raw_payload: bool = Query(default=True),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=31, ge=1, le=5000),
) -> PresenzeDailyRecordListResponse:
    stmt = select(PresenzeDailyRecord)
    count_stmt = select(func.count(PresenzeDailyRecord.id))

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
        stmt.order_by(PresenzeDailyRecord.work_date.asc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    total = db.execute(count_stmt).scalar_one()
    punches_by_record_id: dict[uuid.UUID, list[PresenzeDailyPunch]] | None = None
    if include_punches and rows:
        punches = db.execute(
            select(PresenzeDailyPunch)
            .where(PresenzeDailyPunch.daily_record_id.in_([row.id for row in rows]))
            .order_by(PresenzeDailyPunch.daily_record_id.asc(), PresenzeDailyPunch.sequence.asc())
        ).scalars().all()
        punches_by_record_id = {}
        for punch in punches:
            punches_by_record_id.setdefault(punch.daily_record_id, []).append(punch)
    classification_by_record_id = _build_classification_map(db, rows, punches_by_record_id=punches_by_record_id)
    monthly_night_bonus_by_record_id = _build_monthly_night_bonus_map(db, rows, classifications=classification_by_record_id)
    operai_rule_configs = load_operai_rule_configs(db)
    return PresenzeDailyRecordListResponse(
        items=[
            _serialize_daily_record(
                db,
                row,
                punches=punches_by_record_id.get(row.id) if punches_by_record_id is not None else [],
                include_raw_payload=include_raw_payload,
                classification=classification_by_record_id.get(row.id),
                monthly_night_bonus=monthly_night_bonus_by_record_id.get(row.id),
                operai_rule_configs=operai_rule_configs,
            )
            for row in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )

@router.get("/anomalie", response_model=PresenzeAnomalyListResponse)
def list_anomalie_giornaliere(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    collaborator_id: uuid.UUID | None = Query(default=None),
    application_user_id: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    q: str | None = Query(default=None),
    only_anomalies: bool = Query(default=True),
    only_requests: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=5000),
) -> PresenzeAnomalyListResponse:
    stmt = select(PresenzeDailyRecord)
    stmt, _ = _apply_daily_record_filters(
        db,
        current_user,
        stmt=stmt,
        count_stmt=select(func.count(PresenzeDailyRecord.id)),
        collaborator_id=collaborator_id,
        application_user_id=application_user_id,
        date_from=date_from,
        date_to=date_to,
        q=q,
    )
    rows = db.execute(stmt.order_by(PresenzeDailyRecord.work_date.asc())).scalars().all()
    filtered_rows = _filter_anomaly_rows(rows, only_anomalies=only_anomalies, only_requests=only_requests)
    total = len(filtered_rows)
    page_rows = filtered_rows[(page - 1) * page_size : page * page_size]
    collaborator_ids = list({row.collaborator_id for row in page_rows})
    collaborator_map = _build_collaborator_snapshot_map(db, collaborator_ids)
    return PresenzeAnomalyListResponse(
        items=[_serialize_anomaly_list_item(row, collaborator_map=collaborator_map) for row in page_rows],
        total=total,
        page=page,
        page_size=page_size,
    )

@router.get("/anomalie/month-summary", response_model=PresenzeAnomalyMonthSummaryResponse)
def get_anomalie_month_summary(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    collaborator_id: uuid.UUID | None = Query(default=None),
    application_user_id: int | None = Query(default=None),
    months: int = Query(default=12, ge=1, le=24),
    anchor_month: str | None = Query(default=None),
) -> PresenzeAnomalyMonthSummaryResponse:
    month_values = _resolve_recent_month_values(months=months, anchor_month=anchor_month)
    if not month_values:
        return PresenzeAnomalyMonthSummaryResponse(items=[])
    first_month = month_values[-1]
    last_month = month_values[0]
    date_from = date.fromisoformat(f"{first_month}-01")
    date_to = _month_end(date.fromisoformat(f"{last_month}-01"))
    stmt = select(PresenzeDailyRecord)
    stmt, _ = _apply_daily_record_filters(
        db,
        current_user,
        stmt=stmt,
        count_stmt=select(func.count(PresenzeDailyRecord.id)),
        collaborator_id=collaborator_id,
        application_user_id=application_user_id,
        date_from=date_from,
        date_to=date_to,
        q=None,
    )
    rows = db.execute(stmt).scalars().all()
    counts = {month: 0 for month in month_values}
    for row in rows:
        if not _daily_record_has_anomaly(row):
            continue
        month_key = row.work_date.strftime("%Y-%m")
        if month_key in counts:
            counts[month_key] += 1
    return PresenzeAnomalyMonthSummaryResponse(
        items=[
            PresenzeAnomalyMonthSummaryItemResponse(month=month, count=counts[month])
            for month in month_values
            if counts[month] > 0
        ]
    )

@router.get("/giornaliere/matrix", response_model=PresenzeDailyRecordListResponse)
def list_giornaliere_matrix(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    collaborator_id: uuid.UUID | None = Query(default=None),
    application_user_id: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=31, ge=1, le=5000),
) -> PresenzeDailyRecordListResponse:
    stmt = select(PresenzeDailyRecord)
    count_stmt = select(func.count(PresenzeDailyRecord.id))

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
        stmt.order_by(PresenzeDailyRecord.work_date.asc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    total = db.execute(count_stmt).scalar_one()
    punches_by_record_id: dict[uuid.UUID, list[PresenzeDailyPunch]] = {}
    if rows:
        punches = db.execute(
            select(PresenzeDailyPunch)
            .where(PresenzeDailyPunch.daily_record_id.in_([row.id for row in rows]))
            .order_by(PresenzeDailyPunch.daily_record_id.asc(), PresenzeDailyPunch.sequence.asc())
        ).scalars().all()
        for punch in punches:
            punches_by_record_id.setdefault(punch.daily_record_id, []).append(punch)
    operai_rule_configs = load_operai_rule_configs(db)
    classification_by_record_id = _build_classification_map(db, rows, punches_by_record_id=punches_by_record_id)
    operational_quality_by_record_id = _build_operational_quality_map(
        db,
        rows,
        punches_by_record_id=punches_by_record_id,
        classifications=classification_by_record_id,
        operai_rule_configs=operai_rule_configs,
    )
    return PresenzeDailyRecordListResponse(
        items=[
            _serialize_daily_record_matrix(
                record,
                classification=classification_by_record_id.get(record.id),
                operational_quality=operational_quality_by_record_id.get(record.id),
                operai_rule_configs=operai_rule_configs,
            ).model_copy(
                update={
                    "monthly_night_shift_count": 0,
                    "ordinary_night_bonus_threshold_met": False,
                    "ordinary_night_bonus_rate": None,
                }
            )
            for record in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )

@router.get("/giornaliere/{record_id}", response_model=PresenzeDailyRecordResponse)
def get_giornaliera(
    record_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeDailyRecordResponse:
    return _serialize_daily_record(
        db,
        _get_daily_record_or_404(db, record_id, current_user),
        operai_rule_configs=load_operai_rule_configs(db),
    )

@router.patch("/giornaliere/{record_id}", response_model=PresenzeDailyRecordResponse)
def update_giornaliera(
    record_id: uuid.UUID,
    payload: PresenzeDailyRecordManualUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeDailyRecordResponse:
    record = _get_daily_record_or_404(db, record_id, current_user)
    payload_data = payload.model_dump(exclude_unset=True)
    validation_fields = {"validation_status", "validation_note"}
    manual_edit_fields = {
        "km_value",
        "trasferta_minutes",
        "trasferta_montano",
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

@router.post("/giornaliere/{record_id}/refresh-from-inaz", response_model=PresenzeSyncJobResponse)
def refresh_giornaliera_from_inaz(
    record_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeSyncJobResponse:
    if has_running_sync_job(db):
        raise HTTPException(status_code=409, detail="Another Presenze sync job is already pending or running")

    record = _get_daily_record_or_404(db, record_id, current_user)
    collaborator = _get_collaborator_or_404(db, record.collaborator_id, current_user)
    employee_code = (collaborator.employee_code or "").strip()
    if not employee_code:
        raise HTTPException(status_code=409, detail="Il collaboratore non ha una matricola INAZ configurata")

    credential = _resolve_refresh_credential_for_user(db, current_user)
    job = _create_sync_job_record(
        db,
        requested_by_user_id=current_user.id,
        credential_id=credential.id,
        year=record.work_date.year,
        month=record.work_date.month,
        collaborator_limit=1,
        employee_codes=[employee_code],
        period_start_override=record.work_date,
        period_end_override=record.work_date,
        params_overrides={
            "target_scope": "single_day_single_employee",
            "target_record_id": str(record.id),
            "target_collaborator_id": str(collaborator.id),
            "target_work_date": record.work_date.isoformat(),
        },
        trigger="manual_record_refresh",
    )
    return PresenzeSyncJobResponse.model_validate(job)

@router.get("/collaborators/{collaborator_id}/calendar", response_model=PresenzeCollaboratorCalendarResponse)
def get_collaborator_calendar(
    collaborator_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    date_from: date = Query(...),
    date_to: date = Query(...),
) -> PresenzeCollaboratorCalendarResponse:
    collaborator = _get_collaborator_or_404(db, collaborator_id, current_user)
    rows = db.execute(
        select(PresenzeDailyRecord)
        .where(
            PresenzeDailyRecord.collaborator_id == collaborator_id,
            PresenzeDailyRecord.work_date >= date_from,
            PresenzeDailyRecord.work_date <= date_to,
        )
        .order_by(PresenzeDailyRecord.work_date.asc())
    ).scalars().all()
    classification_by_record_id = _build_classification_map(db, rows)
    monthly_night_bonus_by_record_id = _build_monthly_night_bonus_map(db, rows, classifications=classification_by_record_id)
    return PresenzeCollaboratorCalendarResponse(
        collaborator=_serialize_collaborator(db, collaborator),
        date_from=date_from,
        date_to=date_to,
        items=[
            _serialize_daily_record(
                db,
                row,
                classification=classification_by_record_id.get(row.id),
                monthly_night_bonus=monthly_night_bonus_by_record_id.get(row.id),
            )
            for row in rows
        ],
    )

@router.get("/collaborators/{collaborator_id}/summary", response_model=PresenzeCollaboratorSummaryResponse)
def get_collaborator_summary(
    collaborator_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    period_start: date = Query(...),
    period_end: date = Query(...),
) -> PresenzeCollaboratorSummaryResponse:
    collaborator = _get_collaborator_or_404(db, collaborator_id, current_user)
    items = db.execute(
        select(PresenzeEventSummary)
        .where(
            PresenzeEventSummary.collaborator_id == collaborator_id,
            PresenzeEventSummary.period_start == period_start,
            PresenzeEventSummary.period_end == period_end,
        )
        .order_by(PresenzeEventSummary.description.asc())
    ).scalars().all()
    return PresenzeCollaboratorSummaryResponse(
        collaborator=_serialize_collaborator(db, collaborator),
        period_start=period_start,
        period_end=period_end,
        items=[PresenzeEventSummaryResponse.model_validate(item) for item in items],
    )

def _apply_collaborator_mapping_or_raise(
    db: Session,
    *,
    collaborator: PresenzeCollaborator,
    application_user_id: int | None,
    changed_by: ApplicationUser,
    reason: str,
) -> None:
    if application_user_id is not None and db.get(ApplicationUser, application_user_id) is None:
        raise HTTPException(status_code=404, detail="Application user not found")
    try:
        apply_collaborator_mapping(
            db,
            collaborator=collaborator,
            application_user_id=application_user_id,
            changed_by=changed_by,
            reason=reason,
        )
    except CollaboratorMappingConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail="Application user is already mapped to another collaborator",
        ) from exc

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
        visibility_filter = daily_record_visibility_filter(resolve_presenze_visibility(db, current_user))
        stmt = stmt.where(visibility_filter)
        count_stmt = count_stmt.where(visibility_filter)

    if collaborator_id is not None:
        stmt = stmt.where(PresenzeDailyRecord.collaborator_id == collaborator_id)
        count_stmt = count_stmt.where(PresenzeDailyRecord.collaborator_id == collaborator_id)
    if application_user_id is not None:
        stmt = stmt.where(PresenzeDailyRecord.application_user_id == application_user_id)
        count_stmt = count_stmt.where(PresenzeDailyRecord.application_user_id == application_user_id)
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

    return stmt, count_stmt

# fmt: on
