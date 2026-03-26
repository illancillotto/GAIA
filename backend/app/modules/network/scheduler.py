from __future__ import annotations

from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.modules.network.services import run_network_scan


def execute_scheduled_scan() -> None:
    db: Session = SessionLocal()
    try:
        run_network_scan(db, initiated_by="scheduler")
    finally:
        db.close()


def run_scheduler() -> None:
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        execute_scheduled_scan,
        "interval",
        seconds=settings.network_scan_interval_seconds,
        id="network-scan",
        replace_existing=True,
    )
    scheduler.start()
