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
        return int(float(normalized))
    hours, minutes = normalized.split(":", 1)
    return int(hours) * 60 + int(minutes)


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
