"""backfill incass notice row metadata

Revision ID: 20260728_1110
Revises: 20260728_1100
Create Date: 2026-07-28
"""

from __future__ import annotations

from alembic import op


revision = "20260728_1110"
down_revision = "20260728_1100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE ana_payment_notices
        SET
            data_pagamento = CASE
                WHEN raw_row_json::jsonb ->> 'DataPagamento' ~ '^\\d{2}/\\d{2}/\\d{4}'
                    THEN to_date(left(raw_row_json::jsonb ->> 'DataPagamento', 10), 'DD/MM/YYYY')
                WHEN raw_row_json::jsonb ->> 'DataPagamento' ~ '^\\d{4}-\\d{2}-\\d{2}'
                    THEN to_date(left(raw_row_json::jsonb ->> 'DataPagamento', 10), 'YYYY-MM-DD')
                ELSE data_pagamento
            END,
            data_scadenza = CASE
                WHEN raw_row_json::jsonb ->> 'DataScad' ~ '^\\d{2}/\\d{2}/\\d{4}'
                    THEN to_date(left(raw_row_json::jsonb ->> 'DataScad', 10), 'DD/MM/YYYY')
                WHEN raw_row_json::jsonb ->> 'DataScad' ~ '^\\d{4}-\\d{2}-\\d{2}'
                    THEN to_date(left(raw_row_json::jsonb ->> 'DataScad', 10), 'YYYY-MM-DD')
                ELSE data_scadenza
            END,
            ultimo_invio = COALESCE(NULLIF(raw_row_json::jsonb ->> 'UltimoInvio', ''), ultimo_invio)
        WHERE source_system = 'incass'
          AND raw_row_json IS NOT NULL
          AND raw_row_json::jsonb ? 'Avviso'
        """
    )


def downgrade() -> None:
    # Data-only correction: the previous stale values cannot be reconstructed.
    return None
