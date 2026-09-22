from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.modules.presenze.dashboard_models import PresenzeDashboardSnapshot


def invalidate_all_dashboard_snapshots(db: Session) -> None:
    db.execute(delete(PresenzeDashboardSnapshot))
