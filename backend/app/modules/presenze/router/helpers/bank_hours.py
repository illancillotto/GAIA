from __future__ import annotations

import uuid
from datetime import date

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.modules.presenze.models import (
    PresenzeBankHoursAdjustment,
    PresenzeCollaborator,
    PresenzeDailyPunch,
    PresenzeDailyRecord,
    PresenzeEventSummary,
)
from app.modules.presenze.router.helpers.collaborators import (
    _resolve_collaborator_contract_profile,
    _serialize_collaborator,
)
from app.modules.presenze.router.helpers.daily_records import (
    _build_classification_map,
    _build_monthly_night_bonus_map,
)
from app.modules.presenze.router.helpers.recovery import _build_user_label_map
from app.modules.presenze.router.helpers.schedules import (
    _load_latest_template_codes_by_collaborator,
)
from app.modules.presenze.schemas import (
    PresenzeBankHoursAdjustmentResponse,
    PresenzeBankHoursBalanceItemResponse,
    PresenzeBankHoursCollaboratorDetailResponse,
    PresenzeBankHoursCompensationSummaryResponse,
    PresenzeBankHoursDashboardResponse,
    PresenzeBankHoursLiquidationGuidanceResponse,
    PresenzeBankHoursSnapshotResponse,
)
from app.modules.presenze.services.bank_hours_guidance_config import (
    get_bank_hours_guidance_config,
)

# Keep extracted callable formatting stable for complexity-baseline matching.
# fmt: off

def _serialize_bank_hours_adjustments(
    db: Session,
    items: list[PresenzeBankHoursAdjustment],
) -> list[PresenzeBankHoursAdjustmentResponse]:
    user_ids = {
        value
        for item in items
        for value in (item.created_by_user_id, item.updated_by_user_id, item.reviewed_by_user_id)
        if value is not None
    }
    labels = _build_user_label_map(db, user_ids)
    return [
        PresenzeBankHoursAdjustmentResponse(
            id=item.id,
            collaborator_id=item.collaborator_id,
            adjustment_date=item.adjustment_date,
            delta_minutes=item.delta_minutes,
            kind=item.kind,
            approval_status=item.approval_status,
            reason=item.reason,
            note=item.note,
            approval_note=item.approval_note,
            created_by_user_id=item.created_by_user_id,
            updated_by_user_id=item.updated_by_user_id,
            reviewed_by_user_id=item.reviewed_by_user_id,
            created_by_label=labels.get(item.created_by_user_id) if item.created_by_user_id is not None else None,
            updated_by_label=labels.get(item.updated_by_user_id) if item.updated_by_user_id is not None else None,
            reviewed_by_label=labels.get(item.reviewed_by_user_id) if item.reviewed_by_user_id is not None else None,
            created_at=item.created_at,
            updated_at=item.updated_at,
            reviewed_at=item.reviewed_at,
        )
        for item in items
    ]

def _serialize_bank_hours_adjustment(
    db: Session,
    item: PresenzeBankHoursAdjustment,
) -> PresenzeBankHoursAdjustmentResponse:
    return _serialize_bank_hours_adjustments(db, [item])[0]

def _build_bank_hours_dashboard(
    db: Session,
    *,
    date_from: date | None,
    date_to: date | None,
    q: str | None,
    negative_only: bool = False,
    pending_adjustments_only: bool = False,
    manual_adjustments_only: bool = False,
) -> PresenzeBankHoursDashboardResponse:
    collaborator_stmt = select(PresenzeCollaborator)
    if q:
        term = f"%{q.strip()}%"
        collaborator_stmt = collaborator_stmt.where(
            or_(
                PresenzeCollaborator.name.ilike(term),
                PresenzeCollaborator.employee_code.ilike(term),
                PresenzeCollaborator.company_code.ilike(term),
            )
        )
    collaborators = db.execute(collaborator_stmt.order_by(PresenzeCollaborator.name.asc())).scalars().all()
    collaborator_ids = [item.id for item in collaborators]
    template_codes_by_collaborator = _load_latest_template_codes_by_collaborator(db, collaborator_ids)
    snapshots_by_collaborator, adjustments_by_collaborator = _load_bank_hours_context(
        db,
        collaborator_ids,
        date_to=date_to,
    )

    items: list[PresenzeBankHoursBalanceItemResponse] = []
    imported_balance_total_minutes = 0
    approved_adjustment_total_minutes = 0
    effective_balance_total_minutes = 0
    liquidation_total_minutes = 0
    pending_adjustments_total = 0
    negative_balance_total = 0
    for collaborator in collaborators:
        profile, profile_source = _resolve_collaborator_contract_profile(
            db,
            collaborator,
            template_code=template_codes_by_collaborator.get(collaborator.id),
        )
        snapshots = snapshots_by_collaborator.get(collaborator.id, [])
        scoped_snapshots = [item for item in snapshots if (date_from is None or item.period_start >= date_from) and (date_to is None or item.period_end <= date_to)]
        latest_snapshot = snapshots[-1] if snapshots else None
        approved_adjustments = [
            item
            for item in adjustments_by_collaborator.get(collaborator.id, [])
            if item.approval_status == "approved" and (date_to is None or item.adjustment_date <= date_to)
        ]
        scoped_adjustments = [
            item
            for item in adjustments_by_collaborator.get(collaborator.id, [])
            if (date_from is None or item.adjustment_date >= date_from) and (date_to is None or item.adjustment_date <= date_to)
        ]
        approved_adjustment_minutes = sum(item.delta_minutes for item in approved_adjustments)
        pending_adjustment_count = sum(1 for item in scoped_adjustments if item.approval_status == "pending")
        manual_adjustment_count = len(scoped_adjustments)
        liquidation_minutes_total = sum(-item.delta_minutes for item in approved_adjustments if item.kind == "liquidation")
        imported_prev_balance_minutes = (latest_snapshot.residuo_prec_minutes or 0) if latest_snapshot is not None else 0
        imported_accrued_minutes = sum((item.spettante_minutes or 0) for item in scoped_snapshots)
        imported_used_minutes = sum((item.fruito_minutes or 0) for item in scoped_snapshots)
        imported_balance_minutes = (latest_snapshot.saldo_totale_minutes or 0) if latest_snapshot is not None else 0
        effective_balance_minutes = imported_balance_minutes + approved_adjustment_minutes
        available_debit_minutes = max(effective_balance_minutes, 0)
        item = PresenzeBankHoursBalanceItemResponse(
            collaborator_id=collaborator.id,
            employee_code=collaborator.employee_code,
            collaborator_name=collaborator.name,
            company_code=collaborator.company_code,
            application_user_id=collaborator.application_user_id,
            contract_kind=profile.contract_kind,
            standard_daily_minutes=profile.standard_daily_minutes,
            contract_profile_source=profile_source,
            imported_prev_balance_minutes=imported_prev_balance_minutes,
            imported_accrued_minutes=imported_accrued_minutes,
            imported_used_minutes=imported_used_minutes,
            imported_balance_minutes=imported_balance_minutes,
            approved_adjustment_minutes=approved_adjustment_minutes,
            effective_balance_minutes=effective_balance_minutes,
            available_debit_minutes=available_debit_minutes,
            available_debit_days=_minutes_to_standard_days(available_debit_minutes, profile.standard_daily_minutes),
            liquidation_minutes_total=liquidation_minutes_total,
            manual_adjustment_count=manual_adjustment_count,
            pending_adjustment_count=pending_adjustment_count,
            latest_snapshot_period_start=latest_snapshot.period_start if latest_snapshot is not None else None,
            latest_snapshot_period_end=latest_snapshot.period_end if latest_snapshot is not None else None,
            last_adjustment_date=scoped_adjustments[0].adjustment_date if scoped_adjustments else None,
            last_adjustment_status=scoped_adjustments[0].approval_status if scoped_adjustments else None,
        )
        include_item = bool(scoped_snapshots or scoped_adjustments or not q)
        if negative_only and effective_balance_minutes >= 0:
            include_item = False
        if pending_adjustments_only and pending_adjustment_count <= 0:
            include_item = False
        if manual_adjustments_only and manual_adjustment_count <= 0:
            include_item = False
        if include_item:
            items.append(item)
            imported_balance_total_minutes += imported_balance_minutes
            approved_adjustment_total_minutes += approved_adjustment_minutes
            effective_balance_total_minutes += effective_balance_minutes
            liquidation_total_minutes += liquidation_minutes_total
            pending_adjustments_total += pending_adjustment_count
            if effective_balance_minutes < 0:
                negative_balance_total += 1

    items.sort(
        key=lambda item: (
            -item.pending_adjustment_count,
            item.effective_balance_minutes,
            item.collaborator_name,
        )
    )
    return PresenzeBankHoursDashboardResponse(
        date_from=date_from,
        date_to=date_to,
        collaborators_total=len(items),
        imported_balance_total_minutes=imported_balance_total_minutes,
        approved_adjustment_total_minutes=approved_adjustment_total_minutes,
        effective_balance_total_minutes=effective_balance_total_minutes,
        liquidation_total_minutes=liquidation_total_minutes,
        pending_adjustments_total=pending_adjustments_total,
        negative_balance_total=negative_balance_total,
        items=items,
    )

def _build_bank_hours_collaborator_detail(
    db: Session,
    collaborator: PresenzeCollaborator,
    *,
    date_from: date | None,
    date_to: date | None,
) -> PresenzeBankHoursCollaboratorDetailResponse:
    profile, profile_source = _resolve_collaborator_contract_profile(
        db,
        collaborator,
        template_code=_load_latest_template_codes_by_collaborator(db, [collaborator.id]).get(collaborator.id),
    )
    snapshots_by_collaborator, adjustments_by_collaborator = _load_bank_hours_context(
        db,
        [collaborator.id],
        date_to=date_to,
    )
    snapshots = [
        item
        for item in snapshots_by_collaborator.get(collaborator.id, [])
        if (date_from is None or item.period_start >= date_from) and (date_to is None or item.period_end <= date_to)
    ]
    adjustments = [
        item
        for item in adjustments_by_collaborator.get(collaborator.id, [])
        if (date_from is None or item.adjustment_date >= date_from) and (date_to is None or item.adjustment_date <= date_to)
    ]
    latest_snapshot = snapshots_by_collaborator.get(collaborator.id, [])[-1] if snapshots_by_collaborator.get(collaborator.id) else None
    approved_adjustment_minutes = sum(
        item.delta_minutes
        for item in adjustments_by_collaborator.get(collaborator.id, [])
        if item.approval_status == "approved" and (date_to is None or item.adjustment_date <= date_to)
    )
    imported_balance_minutes = (latest_snapshot.saldo_totale_minutes or 0) if latest_snapshot is not None else 0
    effective_balance_minutes = imported_balance_minutes + approved_adjustment_minutes
    available_debit_minutes = max(effective_balance_minutes, 0)
    guidance_config = get_bank_hours_guidance_config(db)
    compensation_summary = _build_bank_hours_compensation_summary(
        db,
        collaborator_id=collaborator.id,
        date_from=date_from,
        date_to=date_to,
    )
    return PresenzeBankHoursCollaboratorDetailResponse(
        collaborator=_serialize_collaborator(db, collaborator),
        contract_profile_source=profile_source,
        date_from=date_from,
        date_to=date_to,
        imported_balance_minutes=imported_balance_minutes,
        approved_adjustment_minutes=approved_adjustment_minutes,
        effective_balance_minutes=effective_balance_minutes,
        available_debit_minutes=available_debit_minutes,
        available_debit_days=_minutes_to_standard_days(available_debit_minutes, profile.standard_daily_minutes),
        compensation_summary=compensation_summary,
        liquidation_guidance=_build_bank_hours_liquidation_guidance(
            available_debit_minutes=available_debit_minutes,
            standard_daily_minutes=profile.standard_daily_minutes,
            contract_profile_source=profile_source,
            compensation_summary=compensation_summary,
            guidance_config=guidance_config,
        ),
        snapshots=[_serialize_bank_hours_snapshot(item) for item in reversed(snapshots)],
        adjustments=_serialize_bank_hours_adjustments(db, adjustments),
    )

def _load_bank_hours_context(
    db: Session,
    collaborator_ids: list[uuid.UUID],
    *,
    date_to: date | None,
) -> tuple[dict[uuid.UUID, list[PresenzeEventSummary]], dict[uuid.UUID, list[PresenzeBankHoursAdjustment]]]:
    snapshots_by_collaborator: dict[uuid.UUID, list[PresenzeEventSummary]] = {}
    adjustments_by_collaborator: dict[uuid.UUID, list[PresenzeBankHoursAdjustment]] = {}
    if not collaborator_ids:
        return snapshots_by_collaborator, adjustments_by_collaborator

    summary_stmt = select(PresenzeEventSummary).where(PresenzeEventSummary.collaborator_id.in_(collaborator_ids))
    if date_to is not None:
        summary_stmt = summary_stmt.where(PresenzeEventSummary.period_end <= date_to)
    summaries = db.execute(
        summary_stmt.order_by(PresenzeEventSummary.collaborator_id.asc(), PresenzeEventSummary.period_start.asc())
    ).scalars().all()
    for item in summaries:
        if not _is_bank_hours_summary(item):
            continue
        snapshots_by_collaborator.setdefault(item.collaborator_id, []).append(item)

    adjustment_stmt = select(PresenzeBankHoursAdjustment).where(
        PresenzeBankHoursAdjustment.collaborator_id.in_(collaborator_ids)
    )
    if date_to is not None:
        adjustment_stmt = adjustment_stmt.where(PresenzeBankHoursAdjustment.adjustment_date <= date_to)
    adjustments = db.execute(
        adjustment_stmt.order_by(
            PresenzeBankHoursAdjustment.adjustment_date.desc(),
            PresenzeBankHoursAdjustment.created_at.desc(),
        )
    ).scalars().all()
    for item in adjustments:
        adjustments_by_collaborator.setdefault(item.collaborator_id, []).append(item)
    return snapshots_by_collaborator, adjustments_by_collaborator

def _build_bank_hours_compensation_summary(
    db: Session,
    *,
    collaborator_id: uuid.UUID,
    date_from: date | None,
    date_to: date | None,
) -> PresenzeBankHoursCompensationSummaryResponse:
    record_stmt = select(PresenzeDailyRecord).where(PresenzeDailyRecord.collaborator_id == collaborator_id)
    if date_from is not None:
        record_stmt = record_stmt.where(PresenzeDailyRecord.work_date >= date_from)
    if date_to is not None:
        record_stmt = record_stmt.where(PresenzeDailyRecord.work_date <= date_to)
    records = db.execute(record_stmt.order_by(PresenzeDailyRecord.work_date.asc())).scalars().all()
    if not records:
        return PresenzeBankHoursCompensationSummaryResponse()

    punches = db.execute(
        select(PresenzeDailyPunch)
        .where(PresenzeDailyPunch.daily_record_id.in_([record.id for record in records]))
        .order_by(PresenzeDailyPunch.daily_record_id.asc(), PresenzeDailyPunch.sequence.asc())
    ).scalars().all()
    punches_by_record_id: dict[uuid.UUID, list[PresenzeDailyPunch]] = {}
    for punch in punches:
        punches_by_record_id.setdefault(punch.daily_record_id, []).append(punch)

    classifications = _build_classification_map(db, records, punches_by_record_id=punches_by_record_id)
    monthly_night_bonus = _build_monthly_night_bonus_map(db, records, classifications=classifications)

    worked_days_total = 0
    night_shift_days_total = 0
    night_minutes_total = 0
    festive_minutes_total = 0
    festive_night_minutes_total = 0
    ordinary_night_minutes_total = 0
    overtime_day_minutes_total = 0
    overtime_night_minutes_total = 0
    overtime_festive_minutes_total = 0
    overtime_festive_night_minutes_total = 0
    shift_festive_day_minutes_total = 0
    shift_night_minutes_total = 0
    shift_festive_night_minutes_total = 0
    max_monthly_night_shift_count = 0
    ordinary_night_bonus_threshold_met = False
    ordinary_night_bonus_rate: int | None = None

    for record in records:
        classification = classifications.get(record.id)
        if classification is None:
            continue
        imported_extra_minutes = (record.straordinario_minutes or 0) + (record.mpe_minutes or 0)
        punch_candidate_minutes = _complete_punch_minutes(punches_by_record_id.get(record.id, [])) if imported_extra_minutes > 0 else 0
        if (record.ordinary_minutes or 0) > 0 or (record.straordinario_minutes or 0) > 0 or (record.mpe_minutes or 0) > 0:
            worked_days_total += 1
        night_minutes_total += classification.night_minutes
        festive_minutes_total += classification.festive_minutes
        festive_night_minutes_total += classification.festive_night_minutes
        ordinary_night_minutes_total += classification.ordinary_night_minutes
        overtime_day_minutes_total += max(classification.overtime_day_minutes, imported_extra_minutes, punch_candidate_minutes)
        overtime_night_minutes_total += classification.overtime_night_minutes
        overtime_festive_minutes_total += classification.overtime_festive_minutes
        overtime_festive_night_minutes_total += classification.overtime_festive_night_minutes
        shift_festive_day_minutes_total += classification.shift_festive_day_minutes
        shift_night_minutes_total += classification.shift_night_minutes
        shift_festive_night_minutes_total += classification.shift_festive_night_minutes
        if classification.ordinary_night_minutes + classification.shift_night_minutes + classification.shift_festive_night_minutes > 0:
            night_shift_days_total += 1
        night_bonus = monthly_night_bonus.get(record.id)
        if night_bonus is None:
            continue
        monthly_count = int(night_bonus["monthly_night_shift_count"] or 0)
        max_monthly_night_shift_count = max(max_monthly_night_shift_count, monthly_count)
        if bool(night_bonus["ordinary_night_bonus_threshold_met"]):
            ordinary_night_bonus_threshold_met = True
        bonus_rate = night_bonus["ordinary_night_bonus_rate"]
        if bonus_rate is not None:
            ordinary_night_bonus_rate = max(ordinary_night_bonus_rate or 0, int(bonus_rate))

    return PresenzeBankHoursCompensationSummaryResponse(
        records_total=len(records),
        worked_days_total=worked_days_total,
        night_minutes_total=night_minutes_total,
        festive_minutes_total=festive_minutes_total,
        festive_night_minutes_total=festive_night_minutes_total,
        ordinary_night_minutes_total=ordinary_night_minutes_total,
        overtime_day_minutes_total=overtime_day_minutes_total,
        overtime_night_minutes_total=overtime_night_minutes_total,
        overtime_festive_minutes_total=overtime_festive_minutes_total,
        overtime_festive_night_minutes_total=overtime_festive_night_minutes_total,
        shift_festive_day_minutes_total=shift_festive_day_minutes_total,
        shift_night_minutes_total=shift_night_minutes_total,
        shift_festive_night_minutes_total=shift_festive_night_minutes_total,
        night_shift_days_total=night_shift_days_total,
        max_monthly_night_shift_count=max_monthly_night_shift_count,
        ordinary_night_bonus_threshold_met=ordinary_night_bonus_threshold_met,
        ordinary_night_bonus_rate=ordinary_night_bonus_rate,
    )

def _complete_punch_minutes(punches: list[PresenzeDailyPunch]) -> int:
    worked_minutes = 0
    for punch in punches:
        if punch.entry_time is None or punch.exit_time is None:
            continue
        start_minutes = punch.entry_time.hour * 60 + punch.entry_time.minute
        end_minutes = punch.exit_time.hour * 60 + punch.exit_time.minute
        if end_minutes < start_minutes:
            end_minutes += 24 * 60
        worked_minutes += end_minutes - start_minutes
    return worked_minutes

def _build_bank_hours_liquidation_guidance(
    *,
    available_debit_minutes: int,
    standard_daily_minutes: int | None,
    contract_profile_source: str,
    compensation_summary: PresenzeBankHoursCompensationSummaryResponse,
    guidance_config,
) -> PresenzeBankHoursLiquidationGuidanceResponse:
    included_overtime_buckets: list[str] = []
    candidate_minutes_from_overtime = 0
    if guidance_config.include_overtime_day:
        candidate_minutes_from_overtime += compensation_summary.overtime_day_minutes_total
        included_overtime_buckets.append("overtime_day")
    if guidance_config.include_overtime_night:
        candidate_minutes_from_overtime += compensation_summary.overtime_night_minutes_total
        included_overtime_buckets.append("overtime_night")
    if guidance_config.include_overtime_festive:
        candidate_minutes_from_overtime += compensation_summary.overtime_festive_minutes_total
        included_overtime_buckets.append("overtime_festive")
    if guidance_config.include_overtime_festive_night:
        candidate_minutes_from_overtime += compensation_summary.overtime_festive_night_minutes_total
        included_overtime_buckets.append("overtime_festive_night")
    requires_profile_review = contract_profile_source == "missing" or (
        contract_profile_source == "derived" and not guidance_config.allow_derived_profile
    )
    notes: list[str] = []
    reason_code: str = "ok"
    liquidable_minutes = 0
    keep_in_bank_minutes = 0
    review_minutes = 0

    if available_debit_minutes <= 0:
        reason_code = "no_available_balance"
        notes.append("Il collaboratore non ha saldo banca ore disponibile da liquidare nel periodo selezionato.")
    elif candidate_minutes_from_overtime <= 0:
        reason_code = "no_overtime_candidate"
        keep_in_bank_minutes = available_debit_minutes
        notes.append("Nel periodo selezionato non risultano minuti di straordinario candidabili a liquidazione automatica.")
    elif requires_profile_review:
        reason_code = "missing_profile"
        review_minutes = min(available_debit_minutes, candidate_minutes_from_overtime)
        keep_in_bank_minutes = max(available_debit_minutes - review_minutes, 0)
        if contract_profile_source == "derived":
            notes.append("Il profilo contrattuale e derivato dal template e la configurazione corrente richiede revisione HR prima di liquidare.")
        else:
            notes.append("Il profilo contrattuale non e completo: prima di liquidare conviene confermare operaio/impiegato e orario standard.")
    else:
        liquidable_minutes = min(available_debit_minutes, candidate_minutes_from_overtime)
        keep_in_bank_minutes = max(available_debit_minutes - liquidable_minutes, 0)
        notes.append("La proposta usa il minore tra saldo banca ore disponibile e straordinario del periodo classificato dal motore CCNL.")

    if 0 < liquidable_minutes < guidance_config.min_suggested_minutes:
        review_minutes += liquidable_minutes
        liquidable_minutes = 0
        reason_code = "partial_review"
        notes.append(
            f"La proposta resta sotto la soglia minima configurata di {guidance_config.min_suggested_minutes} minuti e viene rimessa a revisione HR."
        )

    if (
        not requires_profile_review
        and available_debit_minutes > 0
        and candidate_minutes_from_overtime > 0
        and candidate_minutes_from_overtime < available_debit_minutes
    ):
        notes.append("Una quota del saldo resta in banca ore perche non trova copertura nello straordinario del periodo selezionato.")

    if requires_profile_review and review_minutes > 0 and available_debit_minutes > review_minutes:
        reason_code = "partial_review"
        notes.append("Una parte del saldo resta in banca ore, mentre la quota candidata richiede validazione HR.")

    if compensation_summary.ordinary_night_bonus_rate is not None:
        notes.append(
            f"Nel periodo e presente notturno con soglia Art. 82 valorizzata al {compensation_summary.ordinary_night_bonus_rate}%."
        )

    return PresenzeBankHoursLiquidationGuidanceResponse(
        allow_derived_profile=guidance_config.allow_derived_profile,
        included_overtime_buckets=included_overtime_buckets,
        min_suggested_minutes=guidance_config.min_suggested_minutes,
        available_minutes=available_debit_minutes,
        candidate_minutes_from_overtime=candidate_minutes_from_overtime,
        suggested_minutes=liquidable_minutes,
        suggested_days=_minutes_to_standard_days(liquidable_minutes, standard_daily_minutes),
        liquidable_minutes=liquidable_minutes,
        keep_in_bank_minutes=keep_in_bank_minutes,
        review_minutes=review_minutes,
        requires_profile_review=requires_profile_review,
        reason_code=reason_code,
        notes=notes,
    )

def _validate_bank_hours_adjustment_balance(
    db: Session,
    item: PresenzeBankHoursAdjustment,
    *,
    current_item_id: uuid.UUID | None = None,
) -> None:
    if item.delta_minutes >= 0:
        return
    available_minutes = _resolve_bank_hours_available_minutes(
        db,
        item.collaborator_id,
        up_to_date=item.adjustment_date,
        exclude_adjustment_id=current_item_id if item.approval_status != "approved" else None,
    )
    if available_minutes + item.delta_minutes < 0:
        raise HTTPException(
            status_code=409,
            detail="La rettifica banca ore supera il saldo disponibile alla data selezionata.",
        )

def _resolve_bank_hours_available_minutes(
    db: Session,
    collaborator_id: uuid.UUID,
    *,
    up_to_date: date,
    exclude_adjustment_id: uuid.UUID | None = None,
) -> int:
    summaries = db.execute(
        select(PresenzeEventSummary)
        .where(
            PresenzeEventSummary.collaborator_id == collaborator_id,
            PresenzeEventSummary.period_start <= up_to_date,
        )
        .order_by(PresenzeEventSummary.period_start.asc(), PresenzeEventSummary.period_end.asc())
    ).scalars().all()
    latest_summary = next((item for item in reversed(summaries) if _is_bank_hours_summary(item)), None)
    imported_balance_minutes = latest_summary.saldo_totale_minutes if latest_summary is not None and latest_summary.saldo_totale_minutes is not None else 0
    adjustment_stmt = select(PresenzeBankHoursAdjustment).where(
        PresenzeBankHoursAdjustment.collaborator_id == collaborator_id,
        PresenzeBankHoursAdjustment.approval_status == "approved",
        PresenzeBankHoursAdjustment.adjustment_date <= up_to_date,
    )
    approved_adjustments = db.execute(
        adjustment_stmt.order_by(PresenzeBankHoursAdjustment.adjustment_date.asc())
    ).scalars().all()
    adjustment_total = 0
    for current_item in approved_adjustments:
        if exclude_adjustment_id is not None and current_item.id == exclude_adjustment_id:
            continue
        adjustment_total += current_item.delta_minutes
    return imported_balance_minutes + adjustment_total

def _is_bank_hours_summary(item: PresenzeEventSummary) -> bool:
    return "banca ore" in (item.description or "").strip().casefold()

def _serialize_bank_hours_snapshot(item: PresenzeEventSummary) -> PresenzeBankHoursSnapshotResponse:
    return PresenzeBankHoursSnapshotResponse(
        collaborator_id=item.collaborator_id,
        period_start=item.period_start,
        period_end=item.period_end,
        description=item.description,
        residuo_prec_minutes=item.residuo_prec_minutes or 0,
        spettante_minutes=item.spettante_minutes or 0,
        fruito_minutes=item.fruito_minutes or 0,
        saldo_minutes=item.saldo_minutes or 0,
        saldo_totale_minutes=item.saldo_totale_minutes or 0,
        source_job_id=item.source_job_id,
    )

def _minutes_to_standard_days(minutes: int, standard_daily_minutes: int | None) -> float | None:
    if standard_daily_minutes is None or standard_daily_minutes <= 0:
        return None
    return round(minutes / standard_daily_minutes, 2)

# fmt: on

__all__ = [
    "_build_bank_hours_collaborator_detail",
    "_build_bank_hours_compensation_summary",
    "_build_bank_hours_dashboard",
    "_build_bank_hours_liquidation_guidance",
    "_complete_punch_minutes",
    "_is_bank_hours_summary",
    "_load_bank_hours_context",
    "_minutes_to_standard_days",
    "_resolve_bank_hours_available_minutes",
    "_serialize_bank_hours_adjustment",
    "_serialize_bank_hours_adjustments",
    "_serialize_bank_hours_snapshot",
    "_validate_bank_hours_adjustment_balance",
]
