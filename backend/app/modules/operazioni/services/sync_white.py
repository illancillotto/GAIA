from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.elaborazioni.bonifica_oristanese.apps.reports.client import BonificaReportRow
from app.modules.operazioni.models.reports import (
    FieldReport,
    FieldReportCategory,
    FieldReportSeverity,
    InternalCase,
    InternalCaseEvent,
)
from app.modules.operazioni.services.parsing import parse_italian_datetime

STATUS_MAPPING = {
    "completato": "resolved",
    "in lavorazione": "in_progress",
    "non presa in carico": "open",
}


@dataclass(frozen=True)
class WhiteReportsSyncResult:
    synced: int
    skipped: int
    errors: list[str]
    total_events_created: int


def _to_decimal(value: str | None) -> Decimal | None:
    if not value:
        return None
    try:
        return Decimal(value.replace(",", "."))
    except InvalidOperation:
        return None


def _get_or_create_default_severity(db: Session) -> FieldReportSeverity:
    severity = db.scalar(select(FieldReportSeverity).where(FieldReportSeverity.code == "normal"))
    if severity:
        return severity

    severity = FieldReportSeverity(
        code="normal",
        name="Normale",
        rank_order=20,
        color_hex="#64748b",
        is_active=True,
    )
    db.add(severity)
    db.flush()
    return severity


def _resolve_category(db: Session, report_type_name: str) -> FieldReportCategory:
    category = db.scalar(
        select(FieldReportCategory).where(FieldReportCategory.name == report_type_name[:150])
    )
    if category is None:
        category = db.scalar(
            select(FieldReportCategory).where(FieldReportCategory.code == "categoria_white")
        )
    if category is None:
        category = FieldReportCategory(
            code="categoria_white",
            name=report_type_name[:150],
            description="Categoria White Company creata in fallback durante sync report.",
            is_active=True,
            sort_order=0,
        )
        db.add(category)
        db.flush()
    return category


def sync_white_reports(
    *,
    db: Session,
    current_user: ApplicationUser,
    rows: list[BonificaReportRow],
) -> WhiteReportsSyncResult:
    severity = _get_or_create_default_severity(db)
    synced = 0
    skipped = 0
    total_events_created = 0
    errors: list[str] = []

    for row in rows:
        if db.scalar(select(FieldReport.id).where(FieldReport.external_code == row.external_code)):
            skipped += 1
            continue

        try:
            category = _resolve_category(db, row.report_type_name)
            report_status = STATUS_MAPPING.get((row.status_text or "").strip().lower(), "open")
            report_created_at = parse_italian_datetime(row.created_at_text)

            report_payload = {
                "external_code": row.external_code,
                "report_number": f"REP-WHITE-{row.external_code}",
                "reporter_user_id": current_user.id,
                "created_by_user_id": current_user.id,
                "updated_by_user_id": current_user.id,
                "title": row.report_type_name,
                "description": row.description,
                "reporter_name": row.reporter_name,
                "area_code": row.area_code,
                "latitude": _to_decimal(row.latitude_text),
                "longitude": _to_decimal(row.longitude_text),
                "assigned_responsibles": row.assigned_responsibles,
                "completion_time_text": None,
                "completion_time_minutes": None,
                "source_system": "white",
                "status": report_status,
                "category_id": category.id,
                "severity_id": severity.id,
            }
            if report_created_at is not None:
                report_payload["created_at"] = report_created_at
                report_payload["server_received_at"] = report_created_at

            report = FieldReport(**report_payload)
            db.add(report)
            db.flush()

            case_payload = {
                "case_number": f"CAS-WHITE-{row.external_code}",
                "source_report_id": report.id,
                "title": row.report_type_name,
                "description": row.description,
                "category_id": category.id,
                "severity_id": severity.id,
                "status": "archived" if row.archived else report_status,
                "created_by_user_id": current_user.id,
                "updated_by_user_id": current_user.id,
            }
            if report_created_at is not None:
                case_payload["created_at"] = report_created_at

            case = InternalCase(**case_payload)
            db.add(case)
            db.flush()
            report.internal_case_id = case.id

            imported_event = InternalCaseEvent(
                internal_case_id=case.id,
                event_type="imported",
                event_at=report_created_at or report.created_at,
                actor_user_id=current_user.id,
                note="Sync automatico White Company da provider Bonifica Oristanese",
            )
            db.add(imported_event)
            total_events_created += 1
            synced += 1
        except Exception as exc:  # pragma: no cover - defensive branch
            errors.append(f"{row.external_code}: {exc}")

    db.commit()
    return WhiteReportsSyncResult(
        synced=synced,
        skipped=skipped,
        errors=errors,
        total_events_created=total_events_created,
    )
