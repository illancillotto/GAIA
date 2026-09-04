from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def partition_valid_year_rows(rows: Iterable[Any]) -> tuple[list[Any], tuple[dict[str, Any], ...]]:
    valid = []
    invalid = []
    for row in rows:
        raw_year = _get(row, "anno")
        try:
            year = int(str(raw_year).strip())
        except (TypeError, ValueError):
            year = 0
        if 1900 <= year <= 2100:
            valid.append(row)
            continue
        invalid.append(
            {
                "external_id": _clean(_get(row, "external_row_id")),
                "domanda_numero": _clean(_get(row, "domanda")),
                "anno": raw_year,
                "reason": "Anno Capacitas assente o fuori intervallo 1900-2100",
            }
        )
    return valid, tuple(invalid)


def valid_year_rows(rows: Iterable[Any], invalid_rows: list[dict[str, Any]]) -> list[Any]:
    valid, discarded = partition_valid_year_rows(rows)
    invalid_rows.extend(discarded)
    return valid


def _get(value: Any, name: str) -> Any:
    return value.get(name) if isinstance(value, dict) else getattr(value, name, None)


def _clean(value: Any) -> str | None:
    cleaned = str(value).strip() if value is not None else ""
    return cleaned or None
