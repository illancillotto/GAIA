from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from openpyxl import load_workbook

from app.modules.inaz.models import InazCollaborator, InazDailyPunch, InazDailyRecord
from app.modules.inaz.services.parser import detail_indicates_special_day
from app.modules.inaz.services.schedule_engine import DayClassification, ScheduleContext, classify_daily_record

MONTHS_IT = [
    "gennaio",
    "febbraio",
    "marzo",
    "aprile",
    "maggio",
    "giugno",
    "luglio",
    "agosto",
    "settembre",
    "ottobre",
    "novembre",
    "dicembre",
]

DEFAULT_TEMPLATE_PATH = Path("/home/cbo/CursorProjects/inaz-scraper/Giornaliere/Giornaliere_2026_803_1.xlsm")


@dataclass
class ExportTimesheetRow:
    collaborator: InazCollaborator
    daily_rows: list[InazDailyRecord]
    punches_by_record_id: dict[str, list[InazDailyPunch]]


def minutes_to_excel_hours(value: int | None) -> float | None:
    if value is None:
        return None
    return value / 60


def normalize_request_display_label(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if " - " in normalized:
        _, right = normalized.split(" - ", 1)
        if right.strip():
            return right.strip()
    return normalized


def resolve_export_absence_code(row: InazDailyRecord) -> str | None:
    if row.request_description:
        return (normalize_request_display_label(row.request_description) or row.request_description)[:32]
    if row.resolved_absence_cause:
        labels = {
            "ferie": "Ferie",
            "permesso": "Permesso",
            "malattia": "Malattia",
            "riposo": "Riposo",
            "festivita": "Festivita",
            "banca_ore": "Banca ore",
            "assenza_da_giustificare": "Ass. da giustificare",
        }
        return labels.get(row.resolved_absence_cause, row.resolved_absence_cause.replace("_", " "))[:32]
    if row.evidenze:
        return row.evidenze[:32]
    return None


def is_festive(row: InazDailyRecord) -> bool:
    raw_payload = row.raw_payload_json if isinstance(row.raw_payload_json, dict) else None
    return (
        row.raw_weekday in {"S", "D"}
        or row.schedule_code in {"SAB", "DOM", "OPESAB"}
        or (raw_payload is not None and detail_indicates_special_day(raw_payload))
    )


def upsert_archive2_row(ws, collaborator: InazCollaborator, period_label: str) -> int:
    employee_code = int(collaborator.employee_code)
    existing_row = None
    for row in range(5, ws.max_row + 1):
        if ws.cell(row, 2).value == employee_code and ws.cell(row, 3).value == period_label:
            existing_row = row
            break
    if existing_row is None:
        existing_row = max(5, ws.max_row + 1)
        ws.cell(existing_row, 1).value = existing_row - 4
    ws.cell(existing_row, 2).value = employee_code
    ws.cell(existing_row, 3).value = period_label
    ws.cell(existing_row, 4).value = collaborator.name
    return existing_row


def write_archive2_daily_values(
    ws,
    row_index: int,
    export_row: ExportTimesheetRow,
    schedule_context: ScheduleContext | None = None,
) -> None:
    first_day_column = 8
    offsets = {
        "ordinary_ferial": 0,
        "ordinary_festive": 31,
        "justified": 93,
        "straordinario_ferial": 155,
        "straordinario_festive": 186,
        "maggiorazione": 342,
        "absence_code": 435,
        "absence_hours": 436,
    }
    for daily in export_row.daily_rows:
        col = first_day_column + daily.work_date.day - 1
        classification = resolve_day_classification(export_row, daily, schedule_context)
        festive = classification.special_day
        ordinary = minutes_to_excel_hours(classification.ordinary_minutes)
        justified = minutes_to_excel_hours(daily.justified_minutes)
        extra = minutes_to_excel_hours(classification.extra_minutes)
        maggiorazione = minutes_to_excel_hours(daily.maggiorazione_minutes)
        absence = minutes_to_excel_hours(daily.absence_minutes)

        if ordinary is not None:
            ws.cell(row_index, col + offsets["ordinary_festive" if festive else "ordinary_ferial"]).value = ordinary
        if justified is not None:
            ws.cell(row_index, col + offsets["justified"]).value = justified
        if extra is not None:
            ws.cell(row_index, col + offsets["straordinario_festive" if festive else "straordinario_ferial"]).value = extra
        if maggiorazione is not None:
            ws.cell(row_index, col + offsets["maggiorazione"]).value = maggiorazione
        if absence is not None:
            ws.cell(row_index, col + offsets["absence_hours"]).value = absence
        absence_code = resolve_export_absence_code(daily)
        if absence_code:
            ws.cell(row_index, col + offsets["absence_code"]).value = absence_code


def compile_workbook(
    *,
    template: Path,
    output: Path,
    rows: list[ExportTimesheetRow],
    period_start: date,
    employee_kind: str = "AVVENTIZI",
    schedule_context: ScheduleContext | None = None,
) -> None:
    workbook = load_workbook(template, keep_vba=True)
    archive2 = workbook["Archivio2"]
    giornaliera = workbook["Giornaliera2"] if "Giornaliera2" in workbook.sheetnames else workbook["Giornaliera"]
    giornaliera["A3"] = period_start.month
    giornaliera["C3"] = period_start.year
    giornaliera["B2"] = employee_kind
    month_name = MONTHS_IT[period_start.month - 1]
    period_label = f"{employee_kind}_{month_name}-{period_start.year}"

    for item in rows:
        row_index = upsert_archive2_row(archive2, item.collaborator, period_label)
        write_archive2_daily_values(archive2, row_index, item, schedule_context)

    workbook.save(output)


def resolve_day_classification(
    export_row: ExportTimesheetRow,
    daily: InazDailyRecord,
    schedule_context: ScheduleContext | None,
) -> DayClassification:
    punches = export_row.punches_by_record_id.get(str(daily.id), [])
    if schedule_context is None:
        effective_straordinario = (
            daily.override_straordinario_minutes
            if daily.override_straordinario_minutes is not None
            else daily.straordinario_minutes
        )
        effective_mpe = daily.override_mpe_minutes if daily.override_mpe_minutes is not None else daily.mpe_minutes
        imported_extra_total = (effective_straordinario or 0) + (effective_mpe or 0)
        return DayClassification(
            special_day=is_festive(daily),
            ordinary_minutes=daily.ordinary_minutes,
            extra_minutes=imported_extra_total or None,
            source="imported",
        )
    return classify_daily_record(export_row.collaborator, daily, punches, schedule_context)
