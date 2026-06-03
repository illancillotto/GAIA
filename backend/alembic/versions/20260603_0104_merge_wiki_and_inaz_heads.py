"""merge wiki and inaz heads

Revision ID: 20260603_0104
Revises: 20260529_0104, 20260603_0103
Create Date: 2026-06-03
"""

from collections.abc import Sequence


revision: str = "20260603_0104"
down_revision: str | Sequence[str] | None = ("20260529_0104", "20260603_0103")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
