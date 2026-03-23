"""initial schema

Revision ID: 20260319_0001
Revises:
Create Date: 2026-03-19 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260319_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("checksum", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_snapshots_id", "snapshots", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_snapshots_id", table_name="snapshots")
    op.drop_table("snapshots")
