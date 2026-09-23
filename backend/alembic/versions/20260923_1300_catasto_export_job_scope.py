"""catasto export jobs: multi distretti / comuni scope

Revision ID: 20260923_1300
Revises: 20260923_1230
Create Date: 2026-09-23
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260923_1300"
down_revision = "20260923_1230"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "catasto_distretto_export_jobs",
        sa.Column("scope_kind", sa.String(length=16), nullable=False, server_default="distretti"),
    )
    op.add_column("catasto_distretto_export_jobs", sa.Column("scope_values", sa.JSON(), nullable=True))
    op.alter_column(
        "catasto_distretto_export_jobs",
        "num_distretto",
        existing_type=sa.String(length=32),
        type_=sa.String(length=255),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "catasto_distretto_export_jobs",
        "num_distretto",
        existing_type=sa.String(length=255),
        type_=sa.String(length=32),
        existing_nullable=False,
    )
    op.drop_column("catasto_distretto_export_jobs", "scope_values")
    op.drop_column("catasto_distretto_export_jobs", "scope_kind")
