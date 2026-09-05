from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.network.router.common import _require_network_module
from app.modules.network.router.helpers.traffic import _build_network_statistics_summary
from app.modules.network.schemas import (
    NetworkDashboardSummary,
    NetworkStatisticsSummary,
)
from app.modules.network.services import (
    get_network_dashboard_summary,
)
from app.modules.network.telemetry_rollups import (
    build_network_statistics_summary_from_rollups,
)

router = APIRouter()


# Keep extracted callable formatting stable for complexity-baseline matching.
# fmt: off

@router.get("/dashboard", response_model=NetworkDashboardSummary)
def get_dashboard(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NetworkDashboardSummary:
    _require_network_module(current_user)
    return NetworkDashboardSummary(**get_network_dashboard_summary(db))


@router.get("/statistics", response_model=NetworkStatisticsSummary)
def get_statistics(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
    window_hours: int = Query(default=24, ge=1, le=24 * 30),
) -> NetworkStatisticsSummary:
    _require_network_module(current_user)
    rollup_summary = build_network_statistics_summary_from_rollups(db, window_hours=window_hours)
    if rollup_summary is not None:
        return rollup_summary
    return _build_network_statistics_summary(db, window_hours=window_hours)


# fmt: on
