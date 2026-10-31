"""Weekly slot and resumable on-disk state of a Capacitas ruoli export runner."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

STATUS_COMPLETED = "completed"
STATUS_PARTIAL = "partial"
ITEM_UPLOADED = "uploaded"
ITEM_EMPTY = "empty"
ITEM_FAILED = "failed"
DONE_ITEM_STATUSES = frozenset({ITEM_UPLOADED, ITEM_EMPTY})


@dataclass(frozen=True, slots=True)
class WeeklySchedule:
    weekday: int
    hour: int
    timezone: str

    def slot_for(self, now: datetime) -> datetime:
        """Most recent scheduled start not later than ``now``."""
        local_now = now.astimezone(ZoneInfo(self.timezone))
        days_back = (local_now.weekday() - self.weekday) % 7
        slot_day = local_now.date() - timedelta(days=days_back)
        slot = datetime.combine(slot_day, time(self.hour), tzinfo=local_now.tzinfo)
        return slot if slot <= local_now else slot - timedelta(days=7)

    def snapshot_label(self, now: datetime) -> str:
        return self.slot_for(now).date().isoformat()


@dataclass
class ExportRunState:
    snapshot: str = ""
    status: str = ""
    last_attempt_at: str = ""
    items: dict[str, dict[str, object]] = field(default_factory=dict)

    def is_done(self, file_name: str) -> bool:
        return self.items.get(file_name, {}).get("status") in DONE_ITEM_STATUSES

    def record(self, file_name: str, outcome: dict[str, object]) -> None:
        self.items[file_name] = outcome

    def start(self, snapshot: str, now: datetime) -> None:
        if snapshot != self.snapshot:
            self.snapshot, self.items = snapshot, {}
        self.status = STATUS_PARTIAL
        self.last_attempt_at = now.isoformat()

    def finish(self) -> None:
        failed = any(item.get("status") == ITEM_FAILED for item in self.items.values())
        self.status = STATUS_PARTIAL if failed else STATUS_COMPLETED

    def is_due(self, snapshot: str, now: datetime, retry_after: timedelta) -> bool:
        if snapshot != self.snapshot:
            return True
        if self.status == STATUS_COMPLETED:
            return False
        if not self.last_attempt_at:
            return True
        return datetime.fromisoformat(self.last_attempt_at) + retry_after <= now


class ExportStateStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> ExportRunState:
        if not self.path.exists():
            return ExportRunState()
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return ExportRunState(**payload)

    def save(self, state: ExportRunState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(asdict(state), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        os.replace(temporary, self.path)
