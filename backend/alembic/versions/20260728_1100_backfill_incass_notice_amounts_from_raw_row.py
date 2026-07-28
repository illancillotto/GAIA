"""backfill incass notice amounts from raw row

Revision ID: 20260728_1100
Revises: 20260728_0900
Create Date: 2026-07-28
"""

from __future__ import annotations

from alembic import op


revision = "20260728_1100"
down_revision = "20260728_0900"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE ana_payment_notices
        SET
            importo_carico = COALESCE(raw_row_json::jsonb ->> 'Carico', importo_carico),
            importo_sgravio = COALESCE(raw_row_json::jsonb ->> 'Sgravio', importo_sgravio),
            importo_riscosso = COALESCE(raw_row_json::jsonb ->> 'Riscosso', importo_riscosso),
            importo_residuo = COALESCE(raw_row_json::jsonb ->> 'Differenza', importo_residuo),
            importo_riporto = COALESCE(raw_row_json::jsonb ->> 'Riporto', importo_riporto),
            importo_rateizzato = COALESCE(raw_row_json::jsonb ->> 'Rateizzato', importo_rateizzato),
            importo_annullato = COALESCE(raw_row_json::jsonb ->> 'Annullato', importo_annullato)
        WHERE source_system = 'incass'
          AND raw_row_json IS NOT NULL
          AND raw_row_json::jsonb ? 'Avviso'
        """
    )


def downgrade() -> None:
    # Data-only correction: the previous stale values cannot be reconstructed.
    return None
