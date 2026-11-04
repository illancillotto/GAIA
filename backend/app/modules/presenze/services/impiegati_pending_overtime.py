"""Recover the afternoon of a flexible employee day still awaiting INAZ calculation."""

from __future__ import annotations

import re
from itertools import pairwise

from app.modules.presenze.models import PresenzeDailyRecord
from app.modules.presenze.services.parser import parse_clock, parse_schedule_code_from_detail


def effective_inaz_mpe_minutes(record: PresenzeDailyRecord) -> int | None:
    """Use the imported punch snapshot consistently in lists, totals and exports.

    The morning's provisional MPE is replaced, not added to the afternoon.
    Imported totals remain unchanged; administrative adjustments take precedence.
    """
    raw = getattr(record, "raw_payload_json", None)
    if not isinstance(raw, dict):
        return record.mpe_minutes
    ordinary_end = _pending_ordinary_end(record, raw)
    pairs = _complete_intervals(raw.get("punches"))
    if ordinary_end is None or not pairs:
        return record.mpe_minutes
    morning = [pair for pair in pairs if pair[0] < ordinary_end]
    afternoon = [pair for pair in pairs if pair[0] >= ordinary_end]
    if not morning or not afternoon:
        return record.mpe_minutes
    if morning[-1][1] < ordinary_end or afternoon[0][0] <= morning[-1][1]:
        return record.mpe_minutes
    return sum(end - start for start, end in afternoon)


def _pending_ordinary_end(record: PresenzeDailyRecord, raw: dict) -> int | None:
    status = raw.get("detail_status") or record.stato
    if str(status).strip().casefold() != "giornata da calcolare":
        return None
    code = parse_schedule_code_from_detail(raw.get("detail_effective_schedule"))
    if str(code or record.schedule_code).strip().upper() not in {"IMP1", "IMP2"}:
        return None
    if record.override_mpe_minutes is not None or record.override_straordinario_minutes is not None:
        return None
    if record.straordinario_minutes:
        return None
    slot = re.fullmatch(
        r"(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})", str(raw.get("detail_time_slots", ""))
    )
    if slot is None:
        return None
    interval = _interval(slot[1], slot[2])
    return interval[1] if interval is not None else None


def _complete_intervals(rows: object) -> list[tuple[int, int]]:
    if not isinstance(rows, list) or not rows:
        return []
    pairs = []
    for row in rows:
        if not isinstance(row, dict):
            return []
        pair = _interval(row.get("entry"), row.get("exit"))
        if pair is None:
            return []
        pairs.append(pair)
    pairs.sort()
    if any(left[1] > right[0] for left, right in pairwise(pairs)):
        return []
    return pairs


def _interval(entry: object, exit_: object) -> tuple[int, int] | None:
    start, end = _clock_minutes(entry), _clock_minutes(exit_)
    if start is None or end is None or end <= start:
        return None
    return start, end


def _clock_minutes(value: object) -> int | None:
    if not isinstance(value, str):
        return None
    clock = parse_clock(value)
    return clock.hour * 60 + clock.minute if clock is not None else None
