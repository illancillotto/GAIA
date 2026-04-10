"""Parsing helpers for Operazioni imports and dashboard filters."""

from __future__ import annotations

import re
from datetime import datetime, time


def parse_completion_time(text: str | None) -> int | None:
    """Parse '12 ore 46 minuti e 37 secondi' into total minutes."""
    if not text:
        return None

    total_minutes = 0
    normalized = text.strip().lower()

    ore = re.search(r"(\d+)\s+or[ae]", normalized)
    minuti = re.search(r"(\d+)\s+minut[io]", normalized)
    secondi = re.search(r"(\d+)\s+second[io]", normalized)

    if ore:
        total_minutes += int(ore.group(1)) * 60
    if minuti:
        total_minutes += int(minuti.group(1))
    if secondi:
        total_minutes += 1

    return total_minutes if total_minutes > 0 else None


def parse_italian_datetime(text: str | None) -> datetime | None:
    """Parse 'dd/MM/yyyy HH:mm' into datetime."""
    if not text:
        return None

    normalized = text.strip()
    if not normalized:
        return None

    try:
        return datetime.strptime(normalized, "%d/%m/%Y %H:%M")
    except ValueError:
        return None


def parse_date_filter(text: str | None, *, end_of_day: bool = False) -> datetime | None:
    """Parse ISO datetime or yyyy-mm-dd date filters from query params."""
    if not text:
        return None

    normalized = text.strip()
    if not normalized:
        return None

    if len(normalized) == 10:
        try:
            parsed_date = datetime.strptime(normalized, "%Y-%m-%d").date()
        except ValueError:
            parsed_date = None
        if parsed_date is not None:
            return datetime.combine(parsed_date, time.max if end_of_day else time.min)

    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        pass
    return None
