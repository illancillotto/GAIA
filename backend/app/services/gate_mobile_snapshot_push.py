"""Push complete monthly snapshots without retaining the preceding month's body."""

from collections.abc import Callable
from datetime import date
from typing import Any

import httpx
from sqlalchemy.orm import Session


def task_months(task: dict[str, Any]) -> list[str]:
    if isinstance(task.get("months"), list) and task["months"]:
        return [str(month) for month in task["months"]]
    if task.get("month"):
        return [str(task["month"])]
    today = date.today()
    current = today.strftime("%Y-%m")
    previous_year = today.year if today.month > 1 else today.year - 1
    previous_month = today.month - 1 if today.month > 1 else 12
    previous = f"{previous_year:04d}-{previous_month:02d}"
    return [current, previous]


async def push_monthly_snapshots(
    db: Session,
    client: httpx.AsyncClient,
    headers: dict[str, str],
    tasks: list[dict[str, Any]],
    collection: tuple[str, str],
    builder: Callable[..., dict[str, Any]],
) -> int:
    kind, count_key = collection
    total = 0
    for task in tasks:
        if task.get("type") == f"presenze_{kind}":
            for month in task_months(task):
                payload = builder(db, month=month)
                response = await client.post(
                    f"/api/mobile/connector/presenze/{kind}/snapshot", json=payload, headers=headers
                )
                response.raise_for_status()
                total += int(
                    response.json().get(count_key, {}).get("count", len(payload[count_key]))
                )
                # The response also owns the encoded request body.
                del response, payload
    return total
