"""merge alembic heads

Revision ID: 20260617_1000
Revises: 20260611_0905, 20260611_1400, 20260617_0900
Create Date: 2026-06-17 10:00:00
"""

from collections.abc import Sequence


revision: str = "20260617_1000"
down_revision: str | Sequence[str] | None = ("20260611_0905", "20260611_1400", "20260617_0900")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
