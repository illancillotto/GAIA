"""add autodoc fields to vehicle

Revision ID: 20260521_0091
Revises: 20260520_0090
Create Date: 2026-05-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260521_0091"
down_revision: Union[str, Sequence[str], None] = "20260520_0090"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("vehicle", sa.Column("autodoc_url", sa.String(length=1024), nullable=True))
    op.add_column("vehicle", sa.Column("autodoc_title", sa.String(length=255), nullable=True))
    op.add_column("vehicle", sa.Column("autodoc_data", sa.JSON(), nullable=True))
    op.add_column(
        "vehicle",
        sa.Column("autodoc_synced_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("vehicle", sa.Column("autodoc_sync_error", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("vehicle", "autodoc_sync_error")
    op.drop_column("vehicle", "autodoc_synced_at")
    op.drop_column("vehicle", "autodoc_data")
    op.drop_column("vehicle", "autodoc_title")
    op.drop_column("vehicle", "autodoc_url")
