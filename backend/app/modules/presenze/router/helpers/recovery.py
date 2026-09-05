from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.presenze.models import (
    PresenzeCollaborator,
    PresenzeDailyRecord,
    PresenzeRecoveryAdjustment,
)
from app.modules.presenze.router.helpers.daily_records import (
    _build_classification_map,
    _record_uses_recovery_day,
)
from app.modules.presenze.schemas import (
    PresenzeRecoveryAdjustmentResponse,
    PresenzeRecoveryBalanceItemResponse,
    PresenzeRecoveryDashboardResponse,
)

# Keep extracted callable formatting stable for complexity-baseline matching.
# fmt: off

def _build_user_label_map(db: Session, user_ids: set[int]) -> dict[int, str]:
    if not user_ids:
        return {}
    users = db.execute(select(ApplicationUser).where(ApplicationUser.id.in_(user_ids))).scalars().all()
    return {user.id: (user.full_name or user.username) for user in users}

def _serialize_recovery_adjustments(
    db: Session,
    items: list[PresenzeRecoveryAdjustment],
) -> list[PresenzeRecoveryAdjustmentResponse]:
    user_ids = {
        value
        for item in items
        for value in (item.created_by_user_id, item.updated_by_user_id, item.reviewed_by_user_id)
        if value is not None
    }
    labels = _build_user_label_map(db, user_ids)
    return [
        PresenzeRecoveryAdjustmentResponse(
            id=item.id,
            collaborator_id=item.collaborator_id,
            adjustment_date=item.adjustment_date,
            delta_days=item.delta_days,
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

def _serialize_recovery_adjustment(
    db: Session,
    item: PresenzeRecoveryAdjustment,
) -> PresenzeRecoveryAdjustmentResponse:
    return _serialize_recovery_adjustments(db, [item])[0]

def _build_recovery_dashboard(
    db: Session,
    *,
    date_from: date | None,
    date_to: date | None,
    q: str | None,
    negative_only: bool = False,
    pending_validation_only: bool = False,
    pending_adjustments_only: bool = False,
    manual_adjustments_only: bool = False,
) -> PresenzeRecoveryDashboardResponse:
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

    records: list[PresenzeDailyRecord] = []
    adjustments: list[PresenzeRecoveryAdjustment] = []
    if collaborator_ids:
        record_stmt = select(PresenzeDailyRecord).where(PresenzeDailyRecord.collaborator_id.in_(collaborator_ids))
        adjustment_stmt = select(PresenzeRecoveryAdjustment).where(
            PresenzeRecoveryAdjustment.collaborator_id.in_(collaborator_ids)
        )
        if date_from is not None:
            record_stmt = record_stmt.where(PresenzeDailyRecord.work_date >= date_from)
            adjustment_stmt = adjustment_stmt.where(PresenzeRecoveryAdjustment.adjustment_date >= date_from)
        if date_to is not None:
            record_stmt = record_stmt.where(PresenzeDailyRecord.work_date <= date_to)
            adjustment_stmt = adjustment_stmt.where(PresenzeRecoveryAdjustment.adjustment_date <= date_to)
        records = db.execute(record_stmt.order_by(PresenzeDailyRecord.work_date.asc())).scalars().all()
        adjustments = db.execute(
            adjustment_stmt.order_by(PresenzeRecoveryAdjustment.adjustment_date.desc())
        ).scalars().all()

    classification_by_record_id = _build_classification_map(db, records)
    adjustment_totals_by_collaborator: dict[uuid.UUID, int] = {}
    last_adjustment_date_by_collaborator: dict[uuid.UUID, date] = {}
    last_adjustment_status_by_collaborator: dict[uuid.UUID, str] = {}
    adjustment_count_by_collaborator: dict[uuid.UUID, int] = {}
    pending_adjustment_count_by_collaborator: dict[uuid.UUID, int] = {}
    for item in adjustments:
        adjustment_count_by_collaborator[item.collaborator_id] = adjustment_count_by_collaborator.get(item.collaborator_id, 0) + 1
        if item.approval_status == "approved":
            adjustment_totals_by_collaborator[item.collaborator_id] = adjustment_totals_by_collaborator.get(item.collaborator_id, 0) + item.delta_days
        if item.approval_status == "pending":
            pending_adjustment_count_by_collaborator[item.collaborator_id] = pending_adjustment_count_by_collaborator.get(item.collaborator_id, 0) + 1
        if item.collaborator_id not in last_adjustment_date_by_collaborator:
            last_adjustment_date_by_collaborator[item.collaborator_id] = item.adjustment_date
            last_adjustment_status_by_collaborator[item.collaborator_id] = item.approval_status

    aggregates: dict[uuid.UUID, dict[str, int | date | None]] = {
        item.id: {
            "matured_days": 0,
            "used_days": 0,
            "pending_validation_count": 0,
            "last_matured_date": None,
            "last_used_date": None,
        }
        for item in collaborators
    }
    for record in records:
        bucket = aggregates.setdefault(
            record.collaborator_id,
            {
                "matured_days": 0,
                "used_days": 0,
                "pending_validation_count": 0,
                "last_matured_date": None,
                "last_used_date": None,
            },
        )
        classification = classification_by_record_id.get(record.id)
        uses_recovery = _record_uses_recovery_day(record)
        if classification is not None and classification.grants_recovery_day:
            bucket["matured_days"] = int(bucket["matured_days"]) + 1
            if bucket["last_matured_date"] is None or record.work_date > bucket["last_matured_date"]:
                bucket["last_matured_date"] = record.work_date
        if uses_recovery:
            bucket["used_days"] = int(bucket["used_days"]) + 1
            if bucket["last_used_date"] is None or record.work_date > bucket["last_used_date"]:
                bucket["last_used_date"] = record.work_date
        if record.validation_status != "validated" and ((classification is not None and classification.grants_recovery_day) or uses_recovery):
            bucket["pending_validation_count"] = int(bucket["pending_validation_count"]) + 1

    items: list[PresenzeRecoveryBalanceItemResponse] = []
    matured_total = 0
    used_total = 0
    manual_total = 0
    pending_total = 0
    pending_adjustments_total = 0
    negative_total = 0
    balance_total = 0
    for collaborator in collaborators:
        bucket = aggregates.get(collaborator.id) or {}
        matured_days = int(bucket.get("matured_days") or 0)
        used_days = int(bucket.get("used_days") or 0)
        manual_delta_days = adjustment_totals_by_collaborator.get(collaborator.id, 0)
        pending_validation_count = int(bucket.get("pending_validation_count") or 0)
        manual_adjustment_count = adjustment_count_by_collaborator.get(collaborator.id, 0)
        pending_adjustment_count = pending_adjustment_count_by_collaborator.get(collaborator.id, 0)
        balance_days = matured_days - used_days + manual_delta_days
        item = PresenzeRecoveryBalanceItemResponse(
            collaborator_id=collaborator.id,
            employee_code=collaborator.employee_code,
            collaborator_name=collaborator.name,
            company_code=collaborator.company_code,
            application_user_id=collaborator.application_user_id,
            matured_days=matured_days,
            used_days=used_days,
            manual_delta_days=manual_delta_days,
            balance_days=balance_days,
            pending_validation_count=pending_validation_count,
            manual_adjustment_count=manual_adjustment_count,
            pending_adjustment_count=pending_adjustment_count,
            last_matured_date=bucket.get("last_matured_date"),
            last_used_date=bucket.get("last_used_date"),
            last_adjustment_date=last_adjustment_date_by_collaborator.get(collaborator.id),
            last_adjustment_status=last_adjustment_status_by_collaborator.get(collaborator.id),
        )
        include_item = matured_days or used_days or manual_delta_days or pending_validation_count or manual_adjustment_count or not q
        if negative_only and balance_days >= 0:
            include_item = False
        if pending_validation_only and pending_validation_count <= 0:
            include_item = False
        if pending_adjustments_only and pending_adjustment_count <= 0:
            include_item = False
        if manual_adjustments_only and manual_adjustment_count <= 0:
            include_item = False
        if include_item:
            items.append(item)
            matured_total += matured_days
            used_total += used_days
            manual_total += manual_delta_days
            pending_total += pending_validation_count
            pending_adjustments_total += pending_adjustment_count
            balance_total += balance_days
            if balance_days < 0:
                negative_total += 1

    items.sort(
        key=lambda item: (
            -item.pending_validation_count,
            -item.pending_adjustment_count,
            item.balance_days,
            item.collaborator_name,
        )
    )
    return PresenzeRecoveryDashboardResponse(
        date_from=date_from,
        date_to=date_to,
        collaborators_total=len(items),
        matured_days_total=matured_total,
        used_days_total=used_total,
        manual_delta_days_total=manual_total,
        balance_days_total=balance_total,
        pending_validation_total=pending_total,
        pending_adjustments_total=pending_adjustments_total,
        negative_balance_total=negative_total,
        items=items,
    )

# fmt: on

__all__ = [
    "_build_recovery_dashboard",
    "_build_user_label_map",
    "_serialize_recovery_adjustment",
    "_serialize_recovery_adjustments",
]
