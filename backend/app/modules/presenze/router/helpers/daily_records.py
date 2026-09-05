from __future__ import annotations

import uuid
from datetime import date, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.presenze.models import (
    PRESENZE_CONTRACT_KIND_OPERAIO,
    PRESENZE_OPERAI_GROUP_CATASTO_MAGAZZINO,
    PresenzeCollaborator,
    PresenzeCredential,
    PresenzeDailyPunch,
    PresenzeDailyRecord,
)
from app.modules.presenze.router.helpers.access import (
    _can_access_collaborator,
    _can_access_daily_record,
)
from app.modules.presenze.schemas import (
    PresenzeAnomalyListItemResponse,
    PresenzeDailyRecordResponse,
)
from app.modules.presenze.services.auto_sync import (
    get_auto_sync_config,
)
from app.modules.presenze.services.credentials import (
    get_credential,
)
from app.modules.presenze.services.operational_quality import (
    build_daily_operational_quality,
    complete_punch_minutes,
)
from app.modules.presenze.services.parser import (
    detail_indicates_recovery_usage,
    detail_indicates_special_day,
    extract_detail_payload,
    extract_punch_terminal_labels,
    resolve_absence_cause,
    resolve_request_authorized_by,
    resolve_request_description,
    resolve_request_status,
    resolve_request_type,
)
from app.modules.presenze.services.schedule_engine import (
    build_schedule_context,
    classify_daily_record,
)

# Keep extracted callable formatting stable for complexity-baseline matching.
# fmt: off

def _serialize_daily_record(
    db: Session,
    record: PresenzeDailyRecord,
    *,
    punches: list[PresenzeDailyPunch] | None = None,
    include_raw_payload: bool = True,
    classification=None,
    monthly_night_bonus=None,
    operai_rule_configs=None,
) -> PresenzeDailyRecordResponse:
    if punches is None:
        punches = db.execute(
            select(PresenzeDailyPunch)
            .where(PresenzeDailyPunch.daily_record_id == record.id)
            .order_by(PresenzeDailyPunch.sequence.asc())
        ).scalars().all()
    detail = extract_detail_payload(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else {}
    terminal_rows = extract_punch_terminal_labels(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else []
    detail_punch_rows = []
    for row in detail.get("punch_rows") or []:
        time_value = row.get("Ora") or row.get("ora") or row.get("col_1")
        direction = row.get("EU") or row.get("eu") or row.get("col_2")
        terminal_label = row.get("Term") or row.get("term") or row.get("col_4")
        detail_punch_rows.append(
            {
                "time": time_value,
                "direction": direction,
                "terminal_label": terminal_label,
                "raw": row,
            }
        )
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
    if classification is None:
        classification = _build_daily_record_classification(
            db,
            record,
            punches=punches,
        )
    uses_recovery_day = _record_uses_recovery_day(record)
    recovery_day_credit = 1 if classification.grants_recovery_day else 0
    recovery_day_debit = 1 if uses_recovery_day else 0
    if monthly_night_bonus is None:
        monthly_night_bonus = _build_monthly_night_bonus_map(db, [record], classifications={record.id: classification}).get(record.id)
    collaborator = db.get(PresenzeCollaborator, record.collaborator_id)
    catasto_saturday_coverage_counts = _build_catasto_saturday_coverage_counts(
        db,
        [record],
        {collaborator.id: collaborator} if collaborator is not None else {},
    )
    operational_quality = build_daily_operational_quality(
        collaborator,
        record,
        punches,
        classification=classification,
        operai_rule_configs=operai_rule_configs,
        catasto_month_saturday_coverage_count=catasto_saturday_coverage_counts.get(
            (record.collaborator_id, record.work_date.year, record.work_date.month)
        ),
    )
    return PresenzeDailyRecordResponse.model_validate(
        {
            **record.__dict__,
            "punches": serialized_punches,
            "effective_straordinario_minutes": effective_straordinario,
            "effective_mpe_minutes": effective_mpe,
            "effective_extra_minutes": (effective_straordinario or 0) + (effective_mpe or 0) or None,
            "operational_status": operational_quality.status,
            "operational_formula_code": operational_quality.formula_code,
            "operational_expected_minutes": operational_quality.expected_minutes,
            "operational_worked_minutes": operational_quality.worked_minutes,
            "operational_missing_minutes": operational_quality.missing_minutes,
            "operational_mpe_minutes": operational_quality.mpe_minutes,
            "operational_notes": list(operational_quality.notes),
            "night_minutes": classification.night_minutes,
            "festive_minutes": classification.festive_minutes,
            "festive_night_minutes": classification.festive_night_minutes,
            "ordinary_night_minutes": classification.ordinary_night_minutes,
            "overtime_day_minutes": classification.overtime_day_minutes,
            "overtime_night_minutes": classification.overtime_night_minutes,
            "overtime_festive_minutes": classification.overtime_festive_minutes,
            "overtime_festive_night_minutes": classification.overtime_festive_night_minutes,
            "shift_festive_day_minutes": classification.shift_festive_day_minutes,
            "shift_night_minutes": classification.shift_night_minutes,
            "shift_festive_night_minutes": classification.shift_festive_night_minutes,
            "monthly_night_shift_count": monthly_night_bonus["monthly_night_shift_count"] if monthly_night_bonus is not None else 0,
            "ordinary_night_bonus_threshold_met": monthly_night_bonus["ordinary_night_bonus_threshold_met"] if monthly_night_bonus is not None else False,
            "ordinary_night_bonus_rate": monthly_night_bonus["ordinary_night_bonus_rate"] if monthly_night_bonus is not None else None,
            "request_type": record.request_type
            or (resolve_request_type(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else None),
            "request_description": record.request_description
            or (resolve_request_description(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else None),
            "request_status": record.request_status
            or (resolve_request_status(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else None),
            "request_authorized_by": record.request_authorized_by
            or (resolve_request_authorized_by(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else None),
            "resolved_absence_cause": _resolved_absence_cause_for_response(record, classification),
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
            "detail_punch_rows": detail_punch_rows,
            "detail_text": detail.get("text"),
            "detail_error": detail.get("error"),
            "special_day": classification.special_day,
            "holiday_kind": classification.holiday_kind,
            "grants_recovery_day": classification.grants_recovery_day,
            "recovery_day_credit": recovery_day_credit,
            "uses_recovery_day": uses_recovery_day,
            "recovery_day_debit": recovery_day_debit,
            "recovery_day_balance_delta": recovery_day_credit - recovery_day_debit,
            "raw_payload_json": record.raw_payload_json if include_raw_payload else None,
        }
    )

def _build_collaborator_snapshot_map(
    db: Session,
    collaborator_ids: list[uuid.UUID],
) -> dict[uuid.UUID, PresenzeCollaborator]:
    if not collaborator_ids:
        return {}
    rows = db.execute(
        select(PresenzeCollaborator).where(PresenzeCollaborator.id.in_(collaborator_ids))
    ).scalars().all()
    return {row.id: row for row in rows}

def _daily_record_detail(record: PresenzeDailyRecord) -> dict[str, object]:
    return extract_detail_payload(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else {}

def _daily_record_has_anomaly(record: PresenzeDailyRecord) -> bool:
    detail = _daily_record_detail(record)
    detail_anomalies = detail.get("anomalies") or []
    detail_error = detail.get("error")
    return bool(detail_anomalies or detail_error)

def _daily_record_has_requests(record: PresenzeDailyRecord) -> bool:
    detail = _daily_record_detail(record)
    if detail.get("requests"):
        return True
    return any(
        (
            record.request_type,
            record.request_description,
            record.request_status,
            record.request_authorized_by,
        )
    )

def _daily_record_is_special_day(record: PresenzeDailyRecord) -> bool:
    if record.work_date.weekday() >= 5:
        return True
    if isinstance(record.raw_payload_json, dict) and detail_indicates_special_day(record.raw_payload_json):
        return True
    return False

def _classification_has_worked_time(classification) -> bool:
    worked_minutes = (
        (classification.ordinary_minutes or 0)
        + classification.overtime_day_minutes
        + classification.overtime_night_minutes
        + classification.overtime_festive_minutes
        + classification.overtime_festive_night_minutes
        + classification.shift_festive_day_minutes
        + classification.shift_night_minutes
        + classification.shift_festive_night_minutes
    )
    return worked_minutes > 0

def _resolved_absence_cause_for_response(record: PresenzeDailyRecord, classification) -> str | None:
    explicit_cause = record.resolved_absence_cause or (
        resolve_absence_cause(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else None
    )
    if explicit_cause:
        return explicit_cause
    if classification.holiday_kind == "ordinary" and classification.special_day and not _classification_has_worked_time(classification):
        return "festivita"
    return None

def _summarize_detail_values(detail_summary: dict[str, str]) -> str:
    if not detail_summary:
        return "—"
    return " · ".join(
        f"{label}: {value}"
        for label, value in list(detail_summary.items())[:3]
    )

def _serialize_anomaly_list_item(
    record: PresenzeDailyRecord,
    *,
    collaborator_map: dict[uuid.UUID, PresenzeCollaborator],
) -> PresenzeAnomalyListItemResponse:
    detail = _daily_record_detail(record)
    collaborator = collaborator_map.get(record.collaborator_id)
    effective_straordinario = (
        record.override_straordinario_minutes
        if record.override_straordinario_minutes is not None
        else record.straordinario_minutes
    ) or 0
    effective_mpe = (
        record.override_mpe_minutes if record.override_mpe_minutes is not None else record.mpe_minutes
    ) or 0
    company_parts = [part for part in (collaborator.company_label if collaborator else None, collaborator.company_code if collaborator else None) if part]
    company = company_parts[0] if company_parts else "—"
    return PresenzeAnomalyListItemResponse(
        id=record.id,
        collaborator_id=record.collaborator_id,
        work_date=record.work_date,
        collaborator_name=collaborator.name if collaborator is not None else str(record.collaborator_id),
        collaborator_code=collaborator.employee_code if collaborator is not None else "—",
        company=company,
        schedule_code=record.schedule_code,
        programmed_schedule=detail.get("programmed_schedule"),
        status=(detail.get("status") or record.stato),
        time_slots=detail.get("time_slots"),
        ordinary_minutes=record.ordinary_minutes,
        absence_minutes=record.absence_minutes,
        effective_extra_minutes=effective_straordinario + effective_mpe,
        km_value=record.km_value,
        special_day=_daily_record_is_special_day(record),
        has_anomalies=_daily_record_has_anomaly(record),
        has_requests=_daily_record_has_requests(record),
        evidenze=record.evidenze,
        summary=_summarize_detail_values(detail.get("day_summary") or {}),
    )

def _filter_anomaly_rows(
    rows: list[PresenzeDailyRecord],
    *,
    only_anomalies: bool,
    only_requests: bool,
) -> list[PresenzeDailyRecord]:
    filtered: list[PresenzeDailyRecord] = []
    for row in rows:
        has_anomalies = _daily_record_has_anomaly(row)
        has_requests = _daily_record_has_requests(row)
        if only_anomalies and not has_anomalies:
            continue
        if only_requests and not has_requests:
            continue
        filtered.append(row)
    return filtered

def _resolve_recent_month_values(*, months: int, anchor_month: str | None) -> list[str]:
    if anchor_month is None:
        cursor = date.today().replace(day=1)
    else:
        try:
            cursor = date.fromisoformat(f"{anchor_month}-01")
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="anchor_month must be in YYYY-MM format") from exc
    values: list[str] = []
    for _ in range(months):
        values.append(cursor.strftime("%Y-%m"))
        previous_month_end = cursor - timedelta(days=1)
        cursor = previous_month_end.replace(day=1)
    return values

def _month_end(value: date) -> date:
    next_month = (value.replace(day=28) + timedelta(days=4)).replace(day=1)
    return next_month - timedelta(days=1)

def _serialize_daily_record_matrix(
    record: PresenzeDailyRecord,
    *,
    classification=None,
    operational_quality=None,
    operai_rule_configs=None,
) -> PresenzeDailyRecordResponse:
    detail = extract_detail_payload(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else {}
    effective_straordinario = (
        record.override_straordinario_minutes
        if record.override_straordinario_minutes is not None
        else record.straordinario_minutes
    )
    effective_mpe = record.override_mpe_minutes if record.override_mpe_minutes is not None else record.mpe_minutes
    detail_anomalies = detail.get("anomalies") or []
    if classification is None:
        classification = _build_daily_record_classification(None, record, punches=[])
    if operational_quality is None:
        operational_quality = build_daily_operational_quality(
            None,
            record,
            [],
            classification=classification,
            operai_rule_configs=operai_rule_configs,
        )
    uses_recovery_day = _record_uses_recovery_day(record)
    recovery_day_credit = 1 if classification.grants_recovery_day else 0
    recovery_day_debit = 1 if uses_recovery_day else 0
    return PresenzeDailyRecordResponse.model_validate(
        {
            **record.__dict__,
            "punches": [],
            "effective_straordinario_minutes": effective_straordinario,
            "effective_mpe_minutes": effective_mpe,
            "effective_extra_minutes": (effective_straordinario or 0) + (effective_mpe or 0) or None,
            "operational_status": operational_quality.status,
            "operational_formula_code": operational_quality.formula_code,
            "operational_expected_minutes": operational_quality.expected_minutes,
            "operational_worked_minutes": operational_quality.worked_minutes,
            "operational_missing_minutes": operational_quality.missing_minutes,
            "operational_mpe_minutes": operational_quality.mpe_minutes,
            "operational_notes": list(operational_quality.notes),
            "night_minutes": classification.night_minutes,
            "festive_minutes": classification.festive_minutes,
            "festive_night_minutes": classification.festive_night_minutes,
            "ordinary_night_minutes": classification.ordinary_night_minutes,
            "overtime_day_minutes": classification.overtime_day_minutes,
            "overtime_night_minutes": classification.overtime_night_minutes,
            "overtime_festive_minutes": classification.overtime_festive_minutes,
            "overtime_festive_night_minutes": classification.overtime_festive_night_minutes,
            "shift_festive_day_minutes": classification.shift_festive_day_minutes,
            "shift_night_minutes": classification.shift_night_minutes,
            "shift_festive_night_minutes": classification.shift_festive_night_minutes,
            "monthly_night_shift_count": 0,
            "ordinary_night_bonus_threshold_met": False,
            "ordinary_night_bonus_rate": None,
            "request_type": record.request_type
            or (resolve_request_type(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else None),
            "request_description": record.request_description
            or (resolve_request_description(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else None),
            "request_status": record.request_status
            or (resolve_request_status(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else None),
            "request_authorized_by": record.request_authorized_by
            or (resolve_request_authorized_by(record.raw_payload_json) if isinstance(record.raw_payload_json, dict) else None),
            "resolved_absence_cause": _resolved_absence_cause_for_response(record, classification),
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
            "detail_punch_rows": [],
            "detail_text": None,
            "detail_error": detail.get("error"),
            "special_day": classification.special_day,
            "holiday_kind": classification.holiday_kind,
            "grants_recovery_day": classification.grants_recovery_day,
            "recovery_day_credit": recovery_day_credit,
            "uses_recovery_day": uses_recovery_day,
            "recovery_day_debit": recovery_day_debit,
            "recovery_day_balance_delta": recovery_day_credit - recovery_day_debit,
            "raw_payload_json": None,
        }
    )

def _get_collaborator_or_404(
    db: Session,
    collaborator_id: uuid.UUID,
    current_user: ApplicationUser | None = None,
) -> PresenzeCollaborator:
    collaborator = db.get(PresenzeCollaborator, collaborator_id)
    if collaborator is None or (current_user is not None and not _can_access_collaborator(db, current_user, collaborator)):
        raise HTTPException(status_code=404, detail="Collaborator not found")
    return collaborator

def _get_daily_record_or_404(
    db: Session,
    record_id: uuid.UUID,
    current_user: ApplicationUser | None = None,
) -> PresenzeDailyRecord:
    record = db.get(PresenzeDailyRecord, record_id)
    if record is None or (current_user is not None and not _can_access_daily_record(db, current_user, record)):
        raise HTTPException(status_code=404, detail="Daily record not found")
    return record

def _resolve_refresh_credential_for_user(
    db: Session,
    current_user: ApplicationUser,
) -> PresenzeCredential:
    auto_sync_config = get_auto_sync_config(db)
    if auto_sync_config.credential_id is not None:
        auto_sync_credential = get_credential(db, auto_sync_config.credential_id, current_user)
        if auto_sync_credential is not None and auto_sync_credential.active:
            return auto_sync_credential

    fallback_credential = db.execute(
        select(PresenzeCredential)
        .where(
            PresenzeCredential.application_user_id == current_user.id,
            PresenzeCredential.active.is_(True),
        )
        .order_by(PresenzeCredential.id.asc())
        .limit(1)
    ).scalar_one_or_none()
    if fallback_credential is None:
        raise HTTPException(
            status_code=409,
            detail="Nessuna credenziale Presenze attiva disponibile per recuperare i dati da INAZ",
        )
    return fallback_credential

def _build_daily_record_classification(
    db: Session | None,
    record: PresenzeDailyRecord,
    *,
    punches: list[PresenzeDailyPunch],
):
    schedule_context = None
    if db is not None:
        schedule_context = build_schedule_context(
            db,
            collaborator_ids=[record.collaborator_id],
            date_from=record.work_date,
            date_to=record.work_date,
        )
    collaborator = PresenzeCollaborator(
        id=record.collaborator_id,
        employee_code="",
        company_code=None,
        name="",
    )
    if db is not None:
        collaborator_row = db.get(PresenzeCollaborator, record.collaborator_id)
        if collaborator_row is not None:
            collaborator = collaborator_row
    return classify_daily_record(collaborator, record, punches, schedule_context)

def _record_uses_recovery_day(record: PresenzeDailyRecord) -> bool:
    raw_payload = record.raw_payload_json if isinstance(record.raw_payload_json, dict) else None
    if raw_payload is not None and detail_indicates_recovery_usage(raw_payload):
        return True
    cause = (record.resolved_absence_cause or "").strip().lower()
    if cause == "riposo":
        return True
    combined = " ".join(
        part
        for part in (
            record.request_description,
            record.evidenze,
            record.stato,
        )
        if part
    ).casefold()
    return any(marker in combined for marker in ("riposo compensativo", "riposo goduto", "giornata di recupero", "recupero"))

def _build_classification_map(
    db: Session,
    records: list[PresenzeDailyRecord],
    *,
    punches_by_record_id: dict[uuid.UUID, list[PresenzeDailyPunch]] | None = None,
):
    if not records:
        return {}
    collaborator_ids = sorted({record.collaborator_id for record in records})
    date_from = min(record.work_date for record in records)
    date_to = max(record.work_date for record in records)
    schedule_context = build_schedule_context(db, collaborator_ids=collaborator_ids, date_from=date_from, date_to=date_to)
    collaborators = {
        row.id: row
        for row in db.execute(select(PresenzeCollaborator).where(PresenzeCollaborator.id.in_(collaborator_ids))).scalars().all()
    }
    effective_punches_by_record_id = punches_by_record_id
    if effective_punches_by_record_id is None:
        effective_punches_by_record_id = {}
        punches = db.execute(
            select(PresenzeDailyPunch)
            .where(PresenzeDailyPunch.daily_record_id.in_([record.id for record in records]))
            .order_by(PresenzeDailyPunch.daily_record_id.asc(), PresenzeDailyPunch.sequence.asc())
        ).scalars().all()
        for punch in punches:
            effective_punches_by_record_id.setdefault(punch.daily_record_id, []).append(punch)
    classifications = {}
    for record in records:
        collaborator = collaborators.get(record.collaborator_id)
        if collaborator is None:
            collaborator = PresenzeCollaborator(id=record.collaborator_id, employee_code="", company_code=None, name="")
        punches = effective_punches_by_record_id.get(record.id, [])
        classifications[record.id] = classify_daily_record(collaborator, record, punches, schedule_context)
    return classifications

def _build_operational_quality_map(
    db: Session,
    records: list[PresenzeDailyRecord],
    *,
    punches_by_record_id: dict[uuid.UUID, list[PresenzeDailyPunch]] | None = None,
    classifications: dict[uuid.UUID, object] | None = None,
    operai_rule_configs=None,
):
    if not records:
        return {}
    collaborator_ids = sorted({record.collaborator_id for record in records})
    collaborators = {
        row.id: row
        for row in db.execute(select(PresenzeCollaborator).where(PresenzeCollaborator.id.in_(collaborator_ids))).scalars().all()
    }
    catasto_saturday_coverage_counts = _build_catasto_saturday_coverage_counts(db, records, collaborators)
    effective_punches_by_record_id = punches_by_record_id
    if effective_punches_by_record_id is None:
        effective_punches_by_record_id = {}
        punches = db.execute(
            select(PresenzeDailyPunch)
            .where(PresenzeDailyPunch.daily_record_id.in_([record.id for record in records]))
            .order_by(PresenzeDailyPunch.daily_record_id.asc(), PresenzeDailyPunch.sequence.asc())
        ).scalars().all()
        for punch in punches:
            effective_punches_by_record_id.setdefault(punch.daily_record_id, []).append(punch)
    qualities = {}
    for record in records:
        collaborator = collaborators.get(record.collaborator_id)
        punches = effective_punches_by_record_id.get(record.id, [])
        qualities[record.id] = build_daily_operational_quality(
            collaborator,
            record,
            punches,
            classification=(classifications or {}).get(record.id),
            operai_rule_configs=operai_rule_configs,
            catasto_month_saturday_coverage_count=catasto_saturday_coverage_counts.get(
                (record.collaborator_id, record.work_date.year, record.work_date.month)
            ),
        )
    return qualities

def _build_catasto_saturday_coverage_counts(
    db: Session,
    records: list[PresenzeDailyRecord],
    collaborators: dict[uuid.UUID, PresenzeCollaborator],
) -> dict[tuple[uuid.UUID, int, int], int]:
    month_keys = sorted(
        {
            (record.collaborator_id, record.work_date.year, record.work_date.month)
            for record in records
            if (
                (collaborator := collaborators.get(record.collaborator_id)) is not None
                and collaborator.contract_kind == PRESENZE_CONTRACT_KIND_OPERAIO
                and collaborator.operai_group == PRESENZE_OPERAI_GROUP_CATASTO_MAGAZZINO
            )
        }
    )
    if not month_keys:
        return {}

    counts: dict[tuple[uuid.UUID, int, int], int] = {key: 0 for key in month_keys}
    for collaborator_id, year, month in month_keys:
        month_start = date(year, month, 1)
        month_end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        saturday_records = db.execute(
            select(PresenzeDailyRecord)
            .where(
                PresenzeDailyRecord.collaborator_id == collaborator_id,
                PresenzeDailyRecord.work_date >= month_start,
                PresenzeDailyRecord.work_date < month_end,
            )
            .order_by(PresenzeDailyRecord.work_date.asc())
        ).scalars().all()
        saturday_records = [record for record in saturday_records if record.work_date.weekday() == 5]
        if not saturday_records:
            continue
        punches = db.execute(
            select(PresenzeDailyPunch)
            .where(PresenzeDailyPunch.daily_record_id.in_([record.id for record in saturday_records]))
            .order_by(PresenzeDailyPunch.daily_record_id.asc(), PresenzeDailyPunch.sequence.asc())
        ).scalars().all()
        punches_by_record_id: dict[uuid.UUID, list[PresenzeDailyPunch]] = {}
        for punch in punches:
            punches_by_record_id.setdefault(punch.daily_record_id, []).append(punch)
        for record in saturday_records:
            worked_minutes = complete_punch_minutes(punches_by_record_id.get(record.id, [])) or 0
            cause = record.resolved_absence_cause.strip().lower() if isinstance(record.resolved_absence_cause, str) else None
            justified_minutes = max(record.justified_minutes or 0, record.absence_minutes or 0)
            if worked_minutes > 0 or (cause in {"ferie", "permesso"} and justified_minutes > 0):
                counts[(collaborator_id, year, month)] += 1
    return counts

def _build_monthly_night_bonus_map(
    db: Session,
    records: list[PresenzeDailyRecord],
    *,
    classifications: dict[uuid.UUID, object] | None = None,
) -> dict[uuid.UUID, dict[str, int | bool | None]]:
    if not records:
        return {}

    month_keys = sorted({(record.collaborator_id, record.work_date.year, record.work_date.month) for record in records})
    month_ranges = {}
    for collaborator_id, year, month in month_keys:
        month_start = date(year, month, 1)
        month_end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        month_ranges[(collaborator_id, year, month)] = (month_start, month_end)

    collaborator_ids = sorted({collaborator_id for collaborator_id, _, _ in month_keys})
    global_start = min(start for start, _ in month_ranges.values())
    global_end_inclusive = max(end for _, end in month_ranges.values())
    monthly_records = db.execute(
        select(PresenzeDailyRecord)
        .where(
            PresenzeDailyRecord.collaborator_id.in_(collaborator_ids),
            PresenzeDailyRecord.work_date >= global_start,
            PresenzeDailyRecord.work_date < global_end_inclusive,
        )
        .order_by(PresenzeDailyRecord.collaborator_id.asc(), PresenzeDailyRecord.work_date.asc())
    ).scalars().all()
    monthly_record_ids = [row.id for row in monthly_records]
    punches_by_record_id: dict[uuid.UUID, list[PresenzeDailyPunch]] = {}
    if monthly_record_ids:
        punches = db.execute(
            select(PresenzeDailyPunch)
            .where(PresenzeDailyPunch.daily_record_id.in_(monthly_record_ids))
            .order_by(PresenzeDailyPunch.daily_record_id.asc(), PresenzeDailyPunch.sequence.asc())
        ).scalars().all()
        for punch in punches:
            punches_by_record_id.setdefault(punch.daily_record_id, []).append(punch)

    classification_map = _build_classification_map(db, monthly_records, punches_by_record_id=punches_by_record_id)
    if classifications is not None:
        classification_map.update(classifications)

    counts_by_month_key: dict[tuple[uuid.UUID, int, int], int] = {}
    for monthly_record in monthly_records:
        month_key = (monthly_record.collaborator_id, monthly_record.work_date.year, monthly_record.work_date.month)
        classification = classification_map.get(monthly_record.id)
        if classification is None:
            continue
        ordinary_night_total = (
            classification.ordinary_night_minutes
            + classification.shift_night_minutes
            + classification.shift_festive_night_minutes
        )
        if ordinary_night_total > 0:
            counts_by_month_key[month_key] = counts_by_month_key.get(month_key, 0) + 1

    result: dict[uuid.UUID, dict[str, int | bool | None]] = {}
    for record in records:
        month_key = (record.collaborator_id, record.work_date.year, record.work_date.month)
        count = counts_by_month_key.get(month_key, 0)
        result[record.id] = {
            "monthly_night_shift_count": count,
            "ordinary_night_bonus_threshold_met": count >= 20,
            "ordinary_night_bonus_rate": 15 if count >= 20 else (10 if count > 0 else None),
        }
    return result

# fmt: on

__all__ = [
    "_build_catasto_saturday_coverage_counts",
    "_build_classification_map",
    "_build_collaborator_snapshot_map",
    "_build_daily_record_classification",
    "_build_monthly_night_bonus_map",
    "_build_operational_quality_map",
    "_classification_has_worked_time",
    "_daily_record_detail",
    "_daily_record_has_anomaly",
    "_daily_record_has_requests",
    "_daily_record_is_special_day",
    "_filter_anomaly_rows",
    "_get_collaborator_or_404",
    "_get_daily_record_or_404",
    "_month_end",
    "_record_uses_recovery_day",
    "_resolve_recent_month_values",
    "_resolve_refresh_credential_for_user",
    "_resolved_absence_cause_for_response",
    "_serialize_anomaly_list_item",
    "_serialize_daily_record",
    "_serialize_daily_record_matrix",
    "_summarize_detail_values",
]
