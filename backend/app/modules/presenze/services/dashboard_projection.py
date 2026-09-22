from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.presenze.dashboard_models import PresenzeDashboardSnapshot
from app.modules.presenze.dashboard_schemas import (
    PresenzeDashboardCollaboratorResponse,
    PresenzeDashboardReviewCaseResponse,
)
from app.modules.presenze.models import PresenzeCollaborator, PresenzeDailyRecord
from app.modules.presenze.schemas import (
    PresenzeDashboardSummaryResponse,
)
from app.modules.presenze.services.operai_daily_policy import effective_extra_values
from app.modules.presenze.services.operai_rules import load_operai_rule_configs
from app.modules.presenze.services.parser import extract_detail_payload

SNAPSHOT_SCHEMA_VERSION = 1


def _number(value: int | None) -> int:
    return value if value is not None else 0


@dataclass
class _DashboardAggregation:
    totals: dict[str, int] = field(default_factory=dict)
    active_collaborator_ids: set[uuid.UUID] = field(default_factory=set)
    cause_stats: dict[str, int] = field(default_factory=dict)
    schedule_stats: dict[str, int] = field(default_factory=dict)

    def add(self, record: PresenzeDailyRecord, classification, *, uses_recovery_day: bool) -> None:
        detail = (
            extract_detail_payload(record.raw_payload_json)
            if isinstance(record.raw_payload_json, dict)
            else {}
        )
        self.active_collaborator_ids.add(record.collaborator_id)
        self._add_time_totals(record, classification)
        self._add_status_totals(record, classification, detail, uses_recovery_day)
        self._add_dimensions(record, detail)

    def _increment(self, key: str, value: int) -> None:
        self.totals[key] = self.totals.get(key, 0) + value

    def _add_time_totals(self, record: PresenzeDailyRecord, classification) -> None:
        ordinary = _number(record.ordinary_minutes)
        absence = _number(record.absence_minutes)
        trasferta = _number(record.trasferta_minutes)
        extra = effective_extra_values(record, classification)
        self._increment("ordinary", ordinary)
        self._increment("absence", absence)
        self._increment("straordinario", _number(extra["effective_straordinario_minutes"]))
        self._increment("mpe", _number(extra["effective_mpe_minutes"]))
        self._increment("extra", _number(extra["effective_extra_minutes"]))
        self._increment("km", _number(record.km_value))
        self._increment("trasferta", trasferta)
        self._increment("trasferta_days", int(trasferta > 0 or record.trasferta_montano))
        self._increment("trasferta_montano_days", int(record.trasferta_montano))
        self._increment("worked_days", int(ordinary > 0))
        self._increment("absence_days", int(absence > 0))
        self._increment("justified_days", int(_number(record.justified_minutes) > 0))

    def _add_status_totals(
        self,
        record: PresenzeDailyRecord,
        classification,
        detail: dict,
        uses_recovery_day: bool,
    ) -> None:
        detail_status = str(detail.get("status") or "").lower()
        has_anomaly = (
            bool(detail.get("anomalies"))
            or "anom" in detail_status
            or "anom" in str(record.stato or "").lower()
        )
        self._increment("anomaly", int(has_anomaly))
        self._increment("special", int(classification is not None and classification.special_day))
        self._increment(
            "recovery_matured",
            int(classification is not None and classification.grants_recovery_day),
        )
        self._increment("recovery_used", int(uses_recovery_day))

    def _add_dimensions(self, record: PresenzeDailyRecord, detail: dict) -> None:
        cause = (record.resolved_absence_cause or "").strip().lower()
        if cause:
            self.cause_stats[cause] = self.cause_stats.get(cause, 0) + 1
        schedule_code = (record.schedule_code or "").strip()
        if not schedule_code and isinstance(detail.get("programmed_schedule"), str):
            schedule_code = str(detail["programmed_schedule"]).split(" - ")[0].strip()
        if schedule_code:
            self.schedule_stats[schedule_code] = self.schedule_stats.get(schedule_code, 0) + 1

    def total(self, key: str) -> int:
        return self.totals.get(key, 0)

    def top_schedules(self) -> list[dict[str, int | str]]:
        ranked = sorted(self.schedule_stats.items(), key=lambda item: (-item[1], item[0]))
        return [{"code": code, "count": count} for code, count in ranked[:4]]


def build_dashboard_summary(
    db: Session,
    *,
    period_start: date,
    period_end: date,
    collaborator_filter=None,
    record_filter=None,
) -> PresenzeDashboardSummaryResponse:
    from app.modules.presenze.router.helpers.daily_records import (
        _build_classification_map,
        _record_uses_recovery_day,
    )

    collaborator_count_stmt = select(func.count(PresenzeCollaborator.id))
    record_stmt = select(PresenzeDailyRecord).where(
        PresenzeDailyRecord.work_date >= period_start,
        PresenzeDailyRecord.work_date <= period_end,
    )
    record_count_stmt = select(func.count(PresenzeDailyRecord.id)).where(
        PresenzeDailyRecord.work_date >= period_start,
        PresenzeDailyRecord.work_date <= period_end,
    )
    if collaborator_filter is not None:
        collaborator_count_stmt = collaborator_count_stmt.where(collaborator_filter)
    if record_filter is not None:
        record_stmt = record_stmt.where(record_filter)
        record_count_stmt = record_count_stmt.where(record_filter)

    collaborators_total = db.execute(collaborator_count_stmt).scalar_one()
    mapped_collaborators_total = db.execute(
        collaborator_count_stmt.where(PresenzeCollaborator.application_user_id.is_not(None))
    ).scalar_one()
    daily_records_total = db.execute(record_count_stmt).scalar_one()
    records = db.execute(record_stmt.order_by(PresenzeDailyRecord.work_date.asc())).scalars().all()
    classification_by_record_id = _build_classification_map(db, records)

    aggregation = _DashboardAggregation()
    for record in records:
        classification = classification_by_record_id.get(record.id)
        aggregation.add(
            record,
            classification,
            uses_recovery_day=_record_uses_recovery_day(record),
        )

    return PresenzeDashboardSummaryResponse(
        period_start=period_start,
        period_end=period_end,
        collaborators_total=collaborators_total,
        mapped_collaborators_total=mapped_collaborators_total,
        active_collaborators_total=len(aggregation.active_collaborator_ids),
        daily_records_total=daily_records_total,
        ordinary_minutes_total=aggregation.total("ordinary"),
        absence_minutes_total=aggregation.total("absence"),
        extra_minutes_total=aggregation.total("extra"),
        straordinario_minutes_total=aggregation.total("straordinario"),
        maggior_presenza_minutes_total=aggregation.total("mpe"),
        km_total=aggregation.total("km"),
        trasferta_minutes_total=aggregation.total("trasferta"),
        trasferta_days_total=aggregation.total("trasferta_days"),
        trasferta_montano_days_total=aggregation.total("trasferta_montano_days"),
        anomaly_total=aggregation.total("anomaly"),
        special_day_total=aggregation.total("special"),
        recovery_days_matured_total=aggregation.total("recovery_matured"),
        recovery_days_used_total=aggregation.total("recovery_used"),
        recovery_days_balance_total=aggregation.total("recovery_matured")
        - aggregation.total("recovery_used"),
        worked_days_total=aggregation.total("worked_days"),
        absence_days_total=aggregation.total("absence_days"),
        justified_days_total=aggregation.total("justified_days"),
        cause_stats=aggregation.cause_stats,
        schedule_stats=aggregation.top_schedules(),
    )


def build_dashboard_review_cases(
    db: Session,
    *,
    period_start: date,
    period_end: date,
    record_filter=None,
    limit: int = 5,
) -> list[PresenzeDashboardReviewCaseResponse]:
    from app.modules.presenze.router.helpers.daily_records import (
        _build_classification_map,
        _build_operational_quality_map,
    )

    stmt = select(PresenzeDailyRecord).where(
        PresenzeDailyRecord.work_date >= period_start,
        PresenzeDailyRecord.work_date <= period_end,
    )
    if record_filter is not None:
        stmt = stmt.where(record_filter)
    records = db.execute(stmt).scalars().all()
    if not records:
        return []

    collaborator_ids = {record.collaborator_id for record in records}
    collaborator_names = dict(
        db.execute(
            select(PresenzeCollaborator.id, PresenzeCollaborator.name).where(
                PresenzeCollaborator.id.in_(collaborator_ids)
            )
        ).all()
    )
    classifications = _build_classification_map(db, records)
    qualities = _build_operational_quality_map(
        db,
        records,
        classifications=classifications,
        operai_rule_configs=load_operai_rule_configs(db),
    )
    cases: list[tuple[int, PresenzeDashboardReviewCaseResponse]] = []
    for record in records:
        case = _build_review_case(
            record,
            qualities[record.id],
            classifications.get(record.id),
            collaborator_names,
        )
        if case is not None:
            cases.append(case)
    return [item for _, item in sorted(cases, key=lambda item: item[0])[:limit]]


def _build_review_case(record, quality, classification, collaborator_names):
    detail = (
        extract_detail_payload(record.raw_payload_json)
        if isinstance(record.raw_payload_json, dict)
        else {}
    )
    anomalies = detail.get("anomalies") or []
    kind = _review_case_kind(quality.status, anomalies, detail.get("error"))
    if kind is None:
        return None
    extra_minutes = _number(
        effective_extra_values(record, classification)["effective_extra_minutes"]
    )
    priority = (0 if kind == "anomaly" else 1) * 1_000_000 - (
        quality.missing_minutes * 10 + extra_minutes
    )
    response = PresenzeDashboardReviewCaseResponse(
        record_id=record.id,
        collaborator_id=record.collaborator_id,
        collaborator_name=collaborator_names.get(
            record.collaborator_id, str(record.collaborator_id)
        ),
        work_date=record.work_date,
        schedule_label=detail.get("programmed_schedule") or record.schedule_code,
        kind=kind,
        reason=_review_case_reason(record, quality.notes, anomalies, detail),
        missing_minutes=quality.missing_minutes,
        extra_minutes=extra_minutes,
        request_description=record.request_description,
    )
    return priority, response


def _review_case_kind(status: str, anomalies: list, detail_error: object) -> str | None:
    if status == "blocking":
        return "anomaly"
    if status == "in_analysis":
        return "analysis"
    if status == "unknown" and (anomalies or detail_error):
        return "anomaly"
    return None


def _review_case_reason(record, notes: tuple[str, ...], anomalies: list, detail: dict) -> str:
    if anomalies:
        anomaly = anomalies[0]
        if isinstance(anomaly, dict):
            return str(
                anomaly.get("anomaliagiornata")
                or anomaly.get("Anomalia giornata")
                or anomaly.get("col_1")
                or "Anomalia da verificare"
            )
    operational_note = next((note for note in notes if note.strip()), None)
    return operational_note or str(
        detail.get("error") or detail.get("status") or record.stato or "Caso da verificare"
    )


def build_recent_collaborators(
    db: Session,
    *,
    collaborator_filter=None,
    limit: int = 6,
) -> list[PresenzeDashboardCollaboratorResponse]:
    stmt = select(PresenzeCollaborator)
    if collaborator_filter is not None:
        stmt = stmt.where(collaborator_filter)
    rows = db.execute(stmt.order_by(PresenzeCollaborator.name.asc()).limit(limit)).scalars().all()
    return [
        PresenzeDashboardCollaboratorResponse.model_validate(row, from_attributes=True)
        for row in rows
    ]


def build_dashboard_projection(
    db: Session,
    *,
    period_start: date,
    period_end: date,
    collaborator_filter=None,
    record_filter=None,
) -> dict:
    summary = build_dashboard_summary(
        db,
        period_start=period_start,
        period_end=period_end,
        collaborator_filter=collaborator_filter,
        record_filter=record_filter,
    )
    review_cases = build_dashboard_review_cases(
        db,
        period_start=period_start,
        period_end=period_end,
        record_filter=record_filter,
    )
    recent_collaborators = build_recent_collaborators(db, collaborator_filter=collaborator_filter)
    return {
        "summary": summary.model_dump(mode="json"),
        "review_cases": [item.model_dump(mode="json") for item in review_cases],
        "recent_collaborators": [item.model_dump(mode="json") for item in recent_collaborators],
    }


def publish_dashboard_snapshot(
    db: Session,
    *,
    period_start: date,
    period_end: date,
    source_sync_job_id: uuid.UUID,
) -> PresenzeDashboardSnapshot:
    payload = build_dashboard_projection(db, period_start=period_start, period_end=period_end)
    snapshot = db.execute(
        select(PresenzeDashboardSnapshot).where(
            PresenzeDashboardSnapshot.period_start == period_start,
            PresenzeDashboardSnapshot.period_end == period_end,
        )
    ).scalar_one_or_none()
    if snapshot is None:
        snapshot = PresenzeDashboardSnapshot(period_start=period_start, period_end=period_end)
    snapshot.source_sync_job_id = source_sync_job_id
    snapshot.schema_version = SNAPSHOT_SCHEMA_VERSION
    snapshot.payload_json = payload
    snapshot.generated_at = datetime.now(UTC)
    db.add(snapshot)
    db.flush()
    return snapshot


def get_dashboard_snapshot(
    db: Session,
    *,
    period_start: date,
    period_end: date,
) -> PresenzeDashboardSnapshot | None:
    return db.execute(
        select(PresenzeDashboardSnapshot).where(
            PresenzeDashboardSnapshot.period_start == period_start,
            PresenzeDashboardSnapshot.period_end == period_end,
            PresenzeDashboardSnapshot.schema_version == SNAPSHOT_SCHEMA_VERSION,
        )
    ).scalar_one_or_none()
