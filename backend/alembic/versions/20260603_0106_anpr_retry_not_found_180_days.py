"""set anpr retry_not_found_days default to 180

Revision ID: 20260603_0106
Revises: 20260603_0105
Create Date: 2026-06-03
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260603_0106"
down_revision: str | Sequence[str] | None = "20260603_0105"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE anpr_sync_config ALTER COLUMN retry_not_found_days SET DEFAULT 180")
    op.execute("UPDATE anpr_sync_config SET retry_not_found_days = 180 WHERE retry_not_found_days = 90")


def downgrade() -> None:
    op.execute("UPDATE anpr_sync_config SET retry_not_found_days = 90 WHERE retry_not_found_days = 180")
    op.execute("ALTER TABLE anpr_sync_config ALTER COLUMN retry_not_found_days SET DEFAULT 90")
