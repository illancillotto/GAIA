"""add catasto indici overview snapshots

Revision ID: 20260630_1100
Revises: 20260629_1230
Create Date: 2026-06-30 11:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260630_1100"
down_revision = "20260629_1230"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cat_indici_overview_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("anno_riferimento", sa.Integer(), nullable=False),
        sa.Column("source_signature", sa.String(length=255), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("anno_riferimento"),
    )
    op.create_index(
        op.f("ix_cat_indici_overview_snapshots_anno_riferimento"),
        "cat_indici_overview_snapshots",
        ["anno_riferimento"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_cat_indici_overview_snapshots_anno_riferimento"),
        table_name="cat_indici_overview_snapshots",
    )
    op.drop_table("cat_indici_overview_snapshots")
