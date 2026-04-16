"""add subject source fields

Revision ID: 20260416_0046
Revises: 20260415_0045
Create Date: 2026-04-16
"""

from alembic import op
import sqlalchemy as sa


revision = "20260416_0046"
down_revision = "20260415_0045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ana_subjects",
        sa.Column("source_system", sa.String(length=32), nullable=False, server_default="gaia"),
    )
    op.add_column(
        "ana_subjects",
        sa.Column("source_external_id", sa.String(length=128), nullable=True),
    )
    op.create_index("ix_ana_subjects_source_system", "ana_subjects", ["source_system"], unique=False)
    op.create_index("ix_ana_subjects_source_external_id", "ana_subjects", ["source_external_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ana_subjects_source_external_id", table_name="ana_subjects")
    op.drop_index("ix_ana_subjects_source_system", table_name="ana_subjects")
    op.drop_column("ana_subjects", "source_external_id")
    op.drop_column("ana_subjects", "source_system")
