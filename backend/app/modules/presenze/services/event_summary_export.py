from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Iterable, Sequence
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.modules.presenze.models import PresenzeCollaborator, PresenzeEventSummary
from app.modules.presenze.services.parser import duration_to_minutes

EVENT_VALUE_KEYS = (
    "spettante",
    "fruito",
    "residuoprec",
    "saldo",
    "autorizzato",
    "proposto",
    "richiesto",
    "totale",
)

BASE_EXPORT_FIELDS = (
    "summary_id",
    "collaborator_id",
    "employee_code",
    "collaborator_name",
    "company_code",
    "company_label",
    "is_active",
    "kint",
    "kkint",
    "period_start",
    "period_end",
    "event_code",
    "description",
    "valid_from",
    "valid_to",
    "unit_code",
    "unit_label",
)

AUDIT_EXPORT_FIELDS = (
    "owner_user_id",
    "application_user_id",
    "source_job_id",
    "created_at",
    "updated_at",
    "raw_payload_json",
)


def export_fieldnames() -> list[str]:
    value_fields = [
        field
        for key in EVENT_VALUE_KEYS
        for field in (f"{key}_raw", f"{key}_minutes", f"{key}_days")
    ]
    return [*BASE_EXPORT_FIELDS, *value_fields, *AUDIT_EXPORT_FIELDS]


def event_unit_label(unit_code: str | None) -> str:
    if unit_code == "2":
        return "ore"
    if unit_code == "3":
        return "giorni"
    return "non specificata"


def _raw_values(summary: PresenzeEventSummary) -> dict[str, Any]:
    payload = summary.raw_payload_json
    if not isinstance(payload, dict):
        return {}
    values = payload.get("values")
    return values if isinstance(values, dict) else {}


def _raw_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _decimal_days(value: str) -> str:
    if not value:
        return ""
    normalized = value.replace(" ", "")
    if "," in normalized and "." in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    elif "," in normalized:
        normalized = normalized.replace(",", ".")
    try:
        return format(Decimal(normalized), "f")
    except InvalidOperation:
        return ""


def _value_columns(key: str, raw_value: Any, unit_code: str | None) -> dict[str, str | int]:
    raw = _raw_text(raw_value)
    minutes = duration_to_minutes(raw) if raw and unit_code == "2" else None
    days = _decimal_days(raw) if unit_code == "3" else ""
    return {
        f"{key}_raw": raw,
        f"{key}_minutes": "" if minutes is None else minutes,
        f"{key}_days": days,
    }


def build_export_row(collaborator: PresenzeCollaborator, summary: PresenzeEventSummary) -> dict[str, Any]:
    values = _raw_values(summary)
    row: dict[str, Any] = {
        "summary_id": str(summary.id),
        "collaborator_id": str(collaborator.id),
        "employee_code": collaborator.employee_code,
        "collaborator_name": collaborator.name,
        "company_code": collaborator.company_code,
        "company_label": collaborator.company_label,
        "is_active": collaborator.is_active,
        "kint": collaborator.kint,
        "kkint": collaborator.kkint,
        "period_start": summary.period_start.isoformat(),
        "period_end": summary.period_end.isoformat(),
        "event_code": summary.event_code,
        "description": summary.description,
        "valid_from": summary.valid_from.isoformat() if summary.valid_from else "",
        "valid_to": summary.valid_to.isoformat() if summary.valid_to else "",
        "unit_code": summary.unitamisura,
        "unit_label": event_unit_label(summary.unitamisura),
        "owner_user_id": summary.owner_user_id,
        "application_user_id": summary.application_user_id,
        "source_job_id": str(summary.source_job_id) if summary.source_job_id else "",
        "created_at": summary.created_at.isoformat() if summary.created_at else "",
        "updated_at": summary.updated_at.isoformat() if summary.updated_at else "",
        "raw_payload_json": json.dumps(summary.raw_payload_json, ensure_ascii=False, sort_keys=True),
    }
    for key in EVENT_VALUE_KEYS:
        row.update(_value_columns(key, values.get(key), summary.unitamisura))
    return row


def load_export_records(
    db: Session,
    *,
    period_start: date | None = None,
    period_end: date | None = None,
    employee_codes: Sequence[str] | None = None,
    active_only: bool = False,
) -> list[tuple[PresenzeCollaborator, PresenzeEventSummary]]:
    stmt = select(PresenzeCollaborator, PresenzeEventSummary).join(
        PresenzeEventSummary,
        PresenzeEventSummary.collaborator_id == PresenzeCollaborator.id,
    )
    if period_start is not None:
        stmt = stmt.where(PresenzeEventSummary.period_start == period_start)
    if period_end is not None:
        stmt = stmt.where(PresenzeEventSummary.period_end == period_end)
    if employee_codes:
        stmt = stmt.where(PresenzeCollaborator.employee_code.in_(employee_codes))
    if active_only:
        stmt = stmt.where(PresenzeCollaborator.is_active.is_(True))
    stmt = stmt.order_by(
        PresenzeCollaborator.employee_code.asc(),
        PresenzeEventSummary.period_start.asc(),
        PresenzeEventSummary.period_end.asc(),
        PresenzeEventSummary.description.asc(),
    )
    return [(collaborator, summary) for collaborator, summary in db.execute(stmt).all()]


def write_export_csv(
    output_path: Path,
    records: Iterable[tuple[PresenzeCollaborator, PresenzeEventSummary]],
) -> int:
    count = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=export_fieldnames())
        writer.writeheader()
        for collaborator, summary in records:
            writer.writerow(build_export_row(collaborator, summary))
            count += 1
    return count


def build_session_factory(db_url: str | None):
    if not db_url:
        from app.core.database import SessionLocal

        return SessionLocal, None
    engine = create_engine(db_url, pool_pre_ping=True)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False), engine


def parse_iso_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def default_export_filename(now: datetime | None = None) -> str:
    timestamp = (now or datetime.now(UTC)).strftime("%Y%m%d_%H%M%S")
    return f"gaia_presenze_riepilogo_eventi_completo_{timestamp}.csv"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Esporta tutti i riepiloghi eventi INAZ presenti in GAIA senza filtri impliciti sulla descrizione.",
    )
    parser.add_argument("--output", help="Percorso CSV di output.")
    parser.add_argument("--db-url", help="DATABASE_URL alternativo.")
    parser.add_argument("--period-start", help="Periodo snapshot iniziale YYYY-MM-DD.")
    parser.add_argument("--period-end", help="Periodo snapshot finale YYYY-MM-DD.")
    parser.add_argument("--employee-code", action="append", dest="employee_codes")
    parser.add_argument("--active-only", action="store_true")
    return parser.parse_args(argv)


def run_export(args: argparse.Namespace) -> tuple[Path, int]:
    output_path = Path(args.output or default_export_filename()).expanduser().resolve()
    session_factory, engine = build_session_factory(args.db_url)
    try:
        with session_factory() as db:
            records = load_export_records(
                db,
                period_start=parse_iso_date(args.period_start),
                period_end=parse_iso_date(args.period_end),
                employee_codes=args.employee_codes,
                active_only=args.active_only,
            )
            count = write_export_csv(output_path, records)
    finally:
        if engine is not None:
            engine.dispose()
    return output_path, count


def main(argv: Sequence[str] | None = None) -> int:
    output_path, count = run_export(parse_args(argv))
    print(f"Esportate {count} righe in {output_path}")
    return 0
