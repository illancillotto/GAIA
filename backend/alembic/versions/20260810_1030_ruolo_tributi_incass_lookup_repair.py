"""repair tributi euribor metadata and index incass notice lookup

Revision ID: 20260810_1030
Revises: 20260807_1200
Create Date: 2026-08-10
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260810_1030"
down_revision = "20260807_1200"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE ruolo_tributi_calculation_policies ADD COLUMN IF NOT EXISTS euribor_source_url TEXT")
        op.execute(
            "ALTER TABLE ruolo_tributi_calculation_policies "
            "ADD COLUMN IF NOT EXISTS euribor_reference_period VARCHAR(32)"
        )
        op.execute(
            "ALTER TABLE ruolo_tributi_calculation_policies "
            "ADD COLUMN IF NOT EXISTS euribor_fetched_at TIMESTAMP WITH TIME ZONE"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_ana_payment_notices_incass_anno_norm_tax "
            "ON ana_payment_notices ("
            "anno, "
            "upper(replace(coalesce(codice_fiscale, partita_iva, ''), ' ', ''))"
            ") "
            "WHERE source_system = 'incass' AND detail_url IS NOT NULL"
        )
        return

    inspector = sa.inspect(bind)
    columns = {
        column["name"]
        for column in inspector.get_columns("ruolo_tributi_calculation_policies")
    }
    with op.batch_alter_table("ruolo_tributi_calculation_policies") as batch:
        if "euribor_source_url" not in columns:
            batch.add_column(sa.Column("euribor_source_url", sa.Text(), nullable=True))
        if "euribor_reference_period" not in columns:
            batch.add_column(sa.Column("euribor_reference_period", sa.String(length=32), nullable=True))
        if "euribor_fetched_at" not in columns:
            batch.add_column(sa.Column("euribor_fetched_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_ana_payment_notices_incass_anno_norm_tax")
        # The Euribor columns are repaired with IF NOT EXISTS in upgrade()
        # because older environments may already have them from 20260730_1100.
        # Do not drop them here: downgrade must only revert the lookup index.
        return

    # Non-PostgreSQL upgrades only repair optional Euribor metadata columns and
    # do not create the expression index, so downgrade is intentionally a no-op.
    return
