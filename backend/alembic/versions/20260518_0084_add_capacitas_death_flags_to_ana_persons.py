"""add capacitas death flags to ana_persons

Revision ID: 20260518_0084
Revises: 20260515_0083
Create Date: 2026-05-18 08:10:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260518_0084"
down_revision: str | None = "20260515_0083"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("ana_persons", sa.Column("capacitas_deceduto", sa.Boolean(), nullable=True))
    op.add_column("ana_persons", sa.Column("capacitas_last_check_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_ana_persons_capacitas_deceduto", "ana_persons", ["capacitas_deceduto"], unique=False)
    op.create_index("ix_ana_persons_capacitas_last_check_at", "ana_persons", ["capacitas_last_check_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ana_persons_capacitas_last_check_at", table_name="ana_persons")
    op.drop_index("ix_ana_persons_capacitas_deceduto", table_name="ana_persons")
    op.drop_column("ana_persons", "capacitas_last_check_at")
    op.drop_column("ana_persons", "capacitas_deceduto")
