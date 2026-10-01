"""Structured INAZ union leave codes and the amount actually justified by INAZ."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.presenze.models import PresenzeDailyRecord

UNION_LEAVE_CODES = frozenset({"ASS.SIN", "PSIEST", "PSIRSA"})
VALID_LEAVE_STATUSES = frozenset({"FRU", "ACC", "AUT", "APPROVATO", "AUTORIZZATO"})


def inaz_event_code(value: str | None) -> str | None:
    code = (value or "").split(" - ", 1)[0].strip().upper()
    return code or None


def union_leave_code(record: PresenzeDailyRecord) -> str | None:
    from app.modules.presenze.services.parser import resolve_request_code

    structured = resolve_request_code(
        record.raw_payload_json if isinstance(record.raw_payload_json, dict) else {}
    )
    return structured or inaz_event_code(record.request_description)


def union_leave_minutes(record: PresenzeDailyRecord) -> int | None:
    """None means another cause; zero means union leave not justified/approved.

    absence_minutes may contain the whole theoretical day even for a partial
    leave. Only justified_minutes can cover the missing part of union leave.
    """
    if union_leave_code(record) not in UNION_LEAVE_CODES:
        return None
    if (record.request_status or "").strip().upper() not in VALID_LEAVE_STATUSES:
        return 0
    return max(0, record.justified_minutes or 0)


def union_leave_covers_day(record: PresenzeDailyRecord) -> bool:
    minutes = union_leave_minutes(record)
    return (
        minutes is not None
        and minutes > 0
        and (record.teo_minutes or 0) > 0
        and (record.ordinary_minutes or 0) + minutes >= record.teo_minutes
    )


LEGACY_ABSENCE_MARKERS = (
    ("ferie", "ferie"),
    ("permesso", "permesso"),
    ("malattia", "malattia"),
    ("riposo", "riposo"),
    ("festivit", "festivita"),
    ("banca ore", "banca_ore"),
    ("giustific", "assenza_da_giustificare"),
)


def normalized_absence_cause(
    code: str | None, description: str | None, evidence: str | None
) -> str | None:
    """Structured union codes precede the unchanged legacy text classification."""
    if (code or inaz_event_code(description)) in UNION_LEAVE_CODES:
        return "permesso_sindacale"
    from app.modules.presenze.services.parser import normalize_portal_key

    for value in (description, evidence):
        normalized = normalize_portal_key(value)
        for marker, cause in LEGACY_ABSENCE_MARKERS:
            if marker in normalized:
                return cause
    return None


def covered_inaz_absence_minutes(
    record: PresenzeDailyRecord, allowed_causes: tuple[str, ...], expected_minutes: int
) -> int:
    union_minutes = union_leave_minutes(record)
    if union_minutes is not None:
        return min(union_minutes, expected_minutes)
    cause = record.resolved_absence_cause
    normalized = cause.strip().lower() if isinstance(cause, str) else None
    if normalized not in allowed_causes:
        return 0
    return max(record.absence_minutes or 0, record.justified_minutes or 0)
