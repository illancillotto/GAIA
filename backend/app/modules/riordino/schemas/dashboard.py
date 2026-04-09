"""Dashboard schemas."""

from __future__ import annotations

from app.modules.riordino.schemas.base import RiordinoSchema
from app.modules.riordino.schemas.event import EventResponse


class DashboardResponse(RiordinoSchema):
    practices_by_status: dict[str, int]
    practices_by_phase: dict[str, int]
    blocking_issues_open: int
    recent_events: list[EventResponse]
