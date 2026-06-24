"""add contract profile to inaz collaborators

Revision ID: 20260623_1200
Revises: 20260618_1100
Create Date: 2026-06-23 12:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260623_1200"
down_revision = "20260618_1100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("inaz_collaborators", sa.Column("contract_kind", sa.String(length=32), nullable=True))
    op.add_column("inaz_collaborators", sa.Column("standard_daily_minutes", sa.Integer(), nullable=True))
    op.create_index("ix_inaz_collaborators_contract_kind", "inaz_collaborators", ["contract_kind"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_inaz_collaborators_contract_kind", table_name="inaz_collaborators")
    op.drop_column("inaz_collaborators", "standard_daily_minutes")
    op.drop_column("inaz_collaborators", "contract_kind")
