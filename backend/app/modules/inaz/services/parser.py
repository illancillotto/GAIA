from __future__ import annotations

from dataclasses import dataclass
import json
from datetime import date, datetime, time
from typing import Any


def parse_portal_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.strptime(value.strip(), "%d/%m/%Y").date()


def parse_clock(value: str | None) -> time | None:
    if not value:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(normalized, fmt).time()
        except ValueError:
            continue
    return None


def duration_to_minutes(value: str | None) -> int | None:
    if not value:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if ":" not in normalized:
        decimal_value = normalized.replace(" ", "")
        if "," in decimal_value and "." in decimal_value:
            decimal_value = decimal_value.replace(".", "").replace(",", ".")
        elif "," in decimal_value:
            decimal_value = decimal_value.replace(",", ".")
        return int(float(decimal_value))
    hours, minutes = normalized.split(":", 1)
    return int(hours) * 60 + int(minutes)


def normalize_portal_text(value: object | None) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text or None


def normalize_portal_key(value: object | None) -> str:
    normalized = normalize_portal_text(value)
    return (normalized or "").casefold()


def extract_detail_payload(daily_row: dict[str, Any]) -> dict[str, Any]:
    summary_map = daily_row.get("detail_day_summary") if isinstance(daily_row.get("detail_day_summary"), dict) else {}
    totals_map = daily_row.get("detail_day_totals") if isinstance(daily_row.get("detail_day_totals"), dict) else {}
    return {
        "title": normalize_portal_text(daily_row.get("detail_title")),
        "status": normalize_portal_text(daily_row.get("detail_status")),
        "programmed_schedule": normalize_portal_text(daily_row.get("detail_programmed_schedule")),
        "effective_schedule": normalize_portal_text(daily_row.get("detail_effective_schedule")),
        "time_slots": normalize_portal_text(daily_row.get("detail_time_slots")),
        "schedule_type": normalize_portal_text(daily_row.get("detail_schedule_type")),
        "theoretical_hours": normalize_portal_text(daily_row.get("detail_theoretical_hours")),
        "absence_hours": normalize_portal_text(daily_row.get("detail_absence_hours")),
        "day_summary": {
            normalize_portal_text(key) or "": normalize_portal_text(value) or ""
            for key, value in summary_map.items()
            if normalize_portal_text(key) and normalize_portal_text(value)
        },
        "day_totals": {
            normalize_portal_text(key) or "": normalize_portal_text(value) or ""
            for key, value in totals_map.items()
            if normalize_portal_text(key) and normalize_portal_text(value)
        },
        "requests": [
            {str(key): normalize_portal_text(value) or "" for key, value in item.items() if normalize_portal_text(value)}
            for item in (daily_row.get("detail_requests") or [])
            if isinstance(item, dict)
        ],
        "anomalies": [
            {str(key): normalize_portal_text(value) or "" for key, value in item.items() if normalize_portal_text(value)}
            for item in (daily_row.get("detail_anomalies") or [])
            if isinstance(item, dict)
        ],
        "text": normalize_portal_text(daily_row.get("detail_text")),
        "error": normalize_portal_text(daily_row.get("detail_error")),
    }


def parse_schedule_code_from_detail(value: str | None) -> str | None:
    normalized = normalize_portal_text(value)
    if not normalized:
        return None
    return normalized.split(" - ", 1)[0].strip() or None


def minutes_from_detail_maps(daily_row: dict[str, Any], *aliases: str) -> int | None:
    keys = {alias.casefold() for alias in aliases}
    detail = extract_detail_payload(daily_row)
    for source in (detail["day_summary"], detail["day_totals"]):
        for key, value in source.items():
            if normalize_portal_key(key) in keys:
                parsed = duration_to_minutes(value)
                if parsed is not None:
                    return parsed
    return None


def resolve_teo_minutes(daily_row: dict[str, Any]) -> int | None:
    return (
        minutes_from_detail_maps(daily_row, "Ore teoriche", "CARTELLINO Gruppo Ore Teoriche")
        or duration_to_minutes(normalize_portal_text(daily_row.get("detail_theoretical_hours")))
        or duration_to_minutes(daily_row.get("teo"))
    )


def resolve_ordinary_minutes(daily_row: dict[str, Any]) -> int | None:
    return minutes_from_detail_maps(daily_row, "Ore Ordinarie", "CARTELLINO Gruppo Ore Ordinarie") or duration_to_minutes(
        daily_row.get("ordinary")
    )


def resolve_absence_minutes(daily_row: dict[str, Any]) -> int | None:
    return (
        minutes_from_detail_maps(daily_row, "Ore Assenza", "CARTELLINO Gruppo Ore Assenza")
        or duration_to_minutes(normalize_portal_text(daily_row.get("detail_absence_hours")))
        or duration_to_minutes(daily_row.get("absence"))
    )


def resolve_justified_minutes(daily_row: dict[str, Any]) -> int | None:
    return minutes_from_detail_maps(
        daily_row,
        "Ore Assenza Giustificate",
        "CARTELLINO Gruppo Ore Assenza Giustificate",
        "Assenza Giustificata",
    ) or duration_to_minutes(daily_row.get("justified"))


def resolve_maggiorazione_minutes(daily_row: dict[str, Any]) -> int | None:
    return minutes_from_detail_maps(
        daily_row,
        "Ore Maggiorazione",
        "CARTELLINO Gruppo Ore Maggiorazione",
    ) or duration_to_minutes(daily_row.get("maggiorazione"))


def resolve_mpe_minutes(daily_row: dict[str, Any]) -> int | None:
    return minutes_from_detail_maps(
        daily_row,
        "Ore Maggior Presenza",
        "CARTELLINO Gruppo Ore Maggior Presenza",
        "Extra orario",
    ) or duration_to_minutes(daily_row.get("mpe"))


def resolve_straordinario_minutes(daily_row: dict[str, Any]) -> int | None:
    return minutes_from_detail_maps(
        daily_row,
        "Ore Straordinario",
        "CARTELLINO Gruppo Ore Straordinario",
    ) or duration_to_minutes(daily_row.get("straordinario"))


def resolve_schedule_code(daily_row: dict[str, Any]) -> str | None:
    return normalize_portal_text(daily_row.get("schedule_code")) or parse_schedule_code_from_detail(
        daily_row.get("detail_programmed_schedule")
    )


def resolve_stato(daily_row: dict[str, Any]) -> str | None:
    return normalize_portal_text(daily_row.get("detail_status")) or normalize_portal_text(daily_row.get("stato"))


def resolve_evidenze(daily_row: dict[str, Any]) -> str | None:
    explicit = normalize_portal_text(daily_row.get("evidenze"))
    if explicit:
        return explicit
    detail = extract_detail_payload(daily_row)
    labels: list[str] = []
    for anomaly in detail["anomalies"]:
        value = normalize_portal_text(anomaly.get("Anomalia giornata") or anomaly.get("col_1"))
        if value:
            labels.append(value)
    for request in detail["requests"]:
        value = normalize_portal_text(request.get("Descrizione") or request.get("Tipo") or request.get("col_2"))
        if value:
            labels.append(value)
    if not labels:
        return None
    return " | ".join(dict.fromkeys(labels))


def detail_indicates_special_day(daily_row: dict[str, Any]) -> bool:
    detail = extract_detail_payload(daily_row)
    special_labels = {
        "festivita goduta",
        "festività goduta",
        "riposo goduto",
        "riposo compensativo",
    }
    for key in detail["day_summary"]:
        if normalize_portal_key(key) in special_labels:
            return True
    return False


def detail_has_authoritative_classification(daily_row: dict[str, Any]) -> bool:
    detail = extract_detail_payload(daily_row)
    if detail["day_summary"] or detail["day_totals"]:
        return True
    return any(
        (
            detail["status"],
            detail["programmed_schedule"],
            detail["effective_schedule"],
            detail["time_slots"],
            detail["theoretical_hours"],
            detail["absence_hours"],
        )
    )


@dataclass
class ParsedCollaboratorPayload:
    collaborator: dict[str, Any]
    company_label: str | None
    period_start: date
    period_end: date
    daily_rows: list[dict[str, Any]]
    summary_rows: list[dict[str, Any]]


@dataclass
class ParsedImportPayload:
    period_start: date
    period_end: date
    collaborators: list[ParsedCollaboratorPayload]
    errors: list[str]


def load_json_payload(content: bytes) -> dict[str, Any]:
    payload = json.loads(content.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Unsupported JSON payload")
    return payload


def parse_import_payload(payload: dict[str, Any]) -> ParsedImportPayload:
    period_start = parse_portal_date(payload.get("period_start"))
    period_end = parse_portal_date(payload.get("period_end"))
    if period_start is None or period_end is None:
        raise ValueError("Payload missing period_start/period_end")

    collaborators: list[ParsedCollaboratorPayload] = []
    errors: list[str] = []
    for index, item in enumerate(payload.get("employees", []), start=1):
        try:
            collaborator = item["collaborator"]
            if not collaborator.get("employee_code"):
                raise ValueError("missing employee_code")
            collaborator_period_start = parse_portal_date(item.get("period_start")) or period_start
            collaborator_period_end = parse_portal_date(item.get("period_end")) or period_end
            collaborators.append(
                ParsedCollaboratorPayload(
                    collaborator=collaborator,
                    company_label=item.get("company_label"),
                    period_start=collaborator_period_start,
                    period_end=collaborator_period_end,
                    daily_rows=[row for row in item.get("daily_rows", []) if isinstance(row, dict)],
                    summary_rows=[row for row in item.get("summary_rows", []) if isinstance(row, dict)],
                )
            )
        except Exception as exc:
            errors.append(f"employee {index}: {exc}")

    return ParsedImportPayload(
        period_start=period_start,
        period_end=period_end,
        collaborators=collaborators,
        errors=errors,
    )
