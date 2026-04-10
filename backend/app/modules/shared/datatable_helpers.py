from __future__ import annotations

from typing import Any


def build_datatable_params(
    *,
    draw: int = 1,
    start: int = 0,
    length: int = 50,
    columns_count: int = 3,
    search_value: str = "",
    extra_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "draw": draw,
        "start": start,
        "length": length,
        "search[value]": search_value,
        "search[regex]": "false",
    }

    for index in range(columns_count):
        params[f"columns[{index}][data]"] = str(index)
        params[f"columns[{index}][name]"] = ""
        params[f"columns[{index}][searchable]"] = "true"
        params[f"columns[{index}][orderable]"] = "true"
        params[f"columns[{index}][search][value]"] = ""
        params[f"columns[{index}][search][regex]"] = "false"

    if extra_params:
        params.update(extra_params)

    return params
