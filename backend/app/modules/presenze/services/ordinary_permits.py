"""First-level authorized ordinary permits cover their duration, never residual absence."""

from app.modules.presenze.services.inaz_absences import VALID_LEAVE_STATUSES
from app.modules.presenze.services.parser import extract_detail_payload


def permit_approved(status, author):
    code = (status or "").strip().upper()
    return code in VALID_LEAVE_STATUSES or (code == "RIC" and bool((author or "").strip()))


def permit_clock(value):
    import re

    match = re.fullmatch(r"(\d{2}):(\d{2})", str(value or ""))
    if not match or int(match[1]) >= 24 or int(match[2]) >= 60:
        return None
    return int(match[1]) * 60 + int(match[2])


def permit_interval(row):
    import re

    description = str(row.get("KEvento") or row.get("Descrizione") or "").lower()
    if not re.search(r"^p\.\s*ord\s*-|permesso ordinario", description):
        return None
    if str(row.get("richiestacanc", "NO")).upper() != "NO":
        return None
    if not permit_approved(row.get("Stato"), row.get("Author") or row.get("Autorizzato da")):
        return None
    start, end = permit_clock(row.get("Dalle")), permit_clock(row.get("Alle"))
    if None in (start, end):
        return None
    return (start, end) if end > start else None


def ordinary_permit_minutes(record):
    if not permit_approved(record.request_status, getattr(record, "request_authorized_by", None)):
        return 0
    raw = record.raw_payload_json if isinstance(record.raw_payload_json, dict) else {}
    rows = extract_detail_payload(raw)["requests"]
    intervals = sorted(interval for row in rows if (interval := permit_interval(row)) is not None)
    total, previous_end = 0, 0
    for start, end in intervals:
        total += max(0, end - max(start, previous_end))
        previous_end = max(previous_end, end)
    return max(total, record.justified_minutes or 0)
