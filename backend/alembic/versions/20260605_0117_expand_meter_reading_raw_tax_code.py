"""expand meter reading raw tax code

Revision ID: 20260605_0117
Revises: 20260605_0116
Create Date: 2026-06-05 12:20:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260605_0117"
down_revision: str | None = "20260605_0116"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "catasto_meter_readings",
        "codice_fiscale",
        existing_type=sa.String(length=32),
        type_=sa.String(length=255),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "catasto_meter_readings",
        "codice_fiscale",
        existing_type=sa.String(length=255),
        type_=sa.String(length=32),
        existing_nullable=True,
    )
