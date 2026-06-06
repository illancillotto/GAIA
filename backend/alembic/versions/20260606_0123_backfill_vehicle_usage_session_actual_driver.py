"""backfill vehicle usage session actual driver from wc operator

Revision ID: 20260606_0123
Revises: 20260606_0122
Create Date: 2026-06-06 18:20:00
"""

from alembic import op
from sqlalchemy.orm import Session

from app.modules.operazioni.services.backfill_vehicle_usage_session_drivers import (
    backfill_vehicle_usage_session_actual_driver,
)


revision = "20260606_0123"
down_revision = "20260606_0122"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    session = Session(bind=bind)
    report = backfill_vehicle_usage_session_actual_driver(session, dry_run=False)
    print(f"vehicle usage session driver backfill report: {report.as_dict()}")


def downgrade() -> None:
    # Irreversible data backfill.
    return None
