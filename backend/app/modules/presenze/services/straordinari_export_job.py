from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path

from openpyxl import load_workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.presenze.models import PresenzeCollaborator, PresenzeDailyPunch, PresenzeDailyRecord

MONTHS_IT = [
    "Gennaio",
    "Febbraio",
    "Marzo",
    "Aprile",
    "Maggio",
    "Giugno",
    "Luglio",
    "Agosto",
    "Settembre",
    "Ottobre",
    "Novembre",
    "Dicembre",
]
DEFAULT_STRAORDINARI_TEMPLATE_CANDIDATES = (
    Path(settings.presenze_scraper_project_path).expanduser() / "Straordinari.xlsx",
    Path("/home/cbo/CursorProjects/inaz-scraper/Straordinari.xlsx"),
)
DEFAULT_STRAORDINARI_MOTIVATION = ""
STRAORDINARI_MAX_ROWS = 29


@dataclass(frozen=True)
class StraordinariPreviewItem:
    record_id: uuid.UUID
    work_date: date
    motivation: str
    start_time: str | None
    end_time: str | None
    duration_minutes: int


@dataclass(frozen=True)
class StraordinariExportItem:
    work_date: date
    motivation: str
    start_time: str | None
    end_time: str | None
    duration_minutes: int


def previous_month_period_start(reference_date: date | None = None) -> date:
    today = reference_date or date.today()
    if today.month == 1:
        return date(today.year - 1, 12, 1)
    return date(today.year, today.month - 1, 1)


def build_period_end(period_start: date) -> date:
    if period_start.month == 12:
        return date(period_start.year + 1, 1, 1)
    return date(period_start.year, period_start.month + 1, 1)


def resolve_straordinari_template_path(template_path: str | None) -> Path:
    if template_path:
        requested = Path(template_path).expanduser()
        if requested.exists():
            return requested
        raise FileNotFoundError(f"Template straordinari not found: {requested}")
    for candidate in DEFAULT_STRAORDINARI_TEMPLATE_CANDIDATES:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Template straordinari not found")


def list_straordinari_preview_items(
    db: Session,
    *,
    collaborator_id: uuid.UUID,
    period_start: date,
) -> tuple[PresenzeCollaborator, list[StraordinariPreviewItem]]:
    collaborator = db.get(PresenzeCollaborator, collaborator_id)
    if collaborator is None:
        raise ValueError("Collaboratore non trovato")
    period_end = build_period_end(period_start)
    records = db.execute(
        select(PresenzeDailyRecord)
        .where(
            PresenzeDailyRecord.collaborator_id == collaborator_id,
            PresenzeDailyRecord.work_date >= period_start,
            PresenzeDailyRecord.work_date < period_end,
        )
        .order_by(PresenzeDailyRecord.work_date.asc())
    ).scalars().all()
    if not records:
        return collaborator, []
    punches = db.execute(
        select(PresenzeDailyPunch)
        .where(PresenzeDailyPunch.daily_record_id.in_([record.id for record in records]))
        .order_by(PresenzeDailyPunch.daily_record_id.asc(), PresenzeDailyPunch.sequence.asc())
    ).scalars().all()
    punches_by_record_id: dict[uuid.UUID, list[PresenzeDailyPunch]] = {}
    for punch in punches:
        punches_by_record_id.setdefault(punch.daily_record_id, []).append(punch)

    items: list[StraordinariPreviewItem] = []
    for record in records:
        duration_minutes = effective_extra_minutes(record)
        if duration_minutes <= 0:
            continue
        start_time, end_time = resolve_overtime_interval(punches_by_record_id.get(record.id, []))
        items.append(
            StraordinariPreviewItem(
                record_id=record.id,
                work_date=record.work_date,
                motivation=(record.request_description or record.manual_note or DEFAULT_STRAORDINARI_MOTIVATION).strip(),
                start_time=start_time,
                end_time=end_time,
                duration_minutes=duration_minutes,
            )
        )
    return collaborator, items


def build_straordinari_export_items(
    db: Session,
    *,
    collaborator_id: uuid.UUID,
    period_start: date,
    requested_motivations: dict[uuid.UUID, str],
) -> tuple[PresenzeCollaborator, list[StraordinariExportItem]]:
    collaborator, preview_items = list_straordinari_preview_items(db, collaborator_id=collaborator_id, period_start=period_start)
    preview_by_record_id = {item.record_id: item for item in preview_items}
    if not requested_motivations:
        raise ValueError("Seleziona almeno una giornata di straordinario")

    missing_ids = [record_id for record_id in requested_motivations if record_id not in preview_by_record_id]
    if missing_ids:
        raise ValueError("Una o piu giornate selezionate non sono piu valide per il mese precedente")

    items = [
        StraordinariExportItem(
            work_date=preview_by_record_id[record_id].work_date,
            motivation=motivation.strip(),
            start_time=preview_by_record_id[record_id].start_time,
            end_time=preview_by_record_id[record_id].end_time,
            duration_minutes=preview_by_record_id[record_id].duration_minutes,
        )
        for record_id, motivation in requested_motivations.items()
    ]
    items.sort(key=lambda item: item.work_date)
    if len(items) > STRAORDINARI_MAX_ROWS:
        raise ValueError(f"Troppe righe per il template straordinari: massimo {STRAORDINARI_MAX_ROWS}")
    return collaborator, items


def generate_straordinari_export(
    *,
    collaborator_name: str,
    period_start: date,
    items: list[StraordinariExportItem],
    output_path: Path,
    template_path: str | None = None,
) -> str:
    if not items:
        raise ValueError("Nessuna giornata di straordinario da esportare")
    template = resolve_straordinari_template_path(template_path)
    workbook = load_workbook(template)
    worksheet = workbook.active
    try:
        worksheet["F7"] = collaborator_name
        worksheet["F9"] = MONTHS_IT[period_start.month - 1]
        worksheet["I9"] = period_start.year
        clear_existing_entries(worksheet)
        for offset, item in enumerate(sorted(items, key=lambda current: current.work_date), start=13):
            worksheet.cell(offset, 2).value = item.work_date.strftime("%d/%m/%Y")
            worksheet.cell(offset, 3).value = item.motivation
            worksheet.cell(offset, 8).value = item.start_time
            worksheet.cell(offset, 9).value = item.end_time
            duration_cell = worksheet.cell(offset, 10)
            duration_cell.value = item.duration_minutes / (24 * 60)
            duration_cell.number_format = "[h]:mm"
        total_cell = worksheet["H42"]
        total_cell.value = "=SUM(J13:J41)"
        total_cell.number_format = "[h]:mm"
        workbook.save(output_path)
    finally:
        workbook.close()
    return build_straordinari_filename(period_start)


def build_straordinari_filename(period_start: date) -> str:
    return f"Straordinari_{period_start.year}_{period_start.month:02d}_{MONTHS_IT[period_start.month - 1]}.xlsx"


def effective_extra_minutes(record: PresenzeDailyRecord) -> int:
    effective_straordinario = (
        record.override_straordinario_minutes
        if record.override_straordinario_minutes is not None
        else record.straordinario_minutes or 0
    )
    effective_mpe = record.override_mpe_minutes if record.override_mpe_minutes is not None else record.mpe_minutes or 0
    return effective_straordinario + effective_mpe


def resolve_overtime_interval(punches: list[PresenzeDailyPunch]) -> tuple[str | None, str | None]:
    start_candidate: time | None = None
    end_candidate: time | None = None
    for punch in punches:
        if punch.entry_time is not None:
            start_candidate = punch.entry_time
        if punch.exit_time is not None:
            end_candidate = punch.exit_time
    return format_time(start_candidate), format_time(end_candidate)


def format_time(value: time | None) -> str | None:
    if value is None:
        return None
    return value.strftime("%H:%M")


def format_duration_label(duration_minutes: int) -> str:
    hours, minutes = divmod(duration_minutes, 60)
    return f"{hours:02d}:{minutes:02d}"


def clear_existing_entries(worksheet) -> None:
    for row in range(13, 42):
        for column in (2, 3, 8, 9, 10, 11, 12, 13):
            worksheet.cell(row, column).value = None
