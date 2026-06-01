"""Add wiki conversation governance config table.

Revision ID: 20260529_0098
Revises: 20260529_0097
Create Date: 2026-05-29 09:55:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260529_0098"
down_revision = "20260529_0097"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wiki_conversation_governance_config",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fallback_heavy_threshold", sa.Integer(), nullable=False),
        sa.Column("no_match_repeated_threshold", sa.Integer(), nullable=False),
        sa.Column("high_latency_ms_threshold", sa.Integer(), nullable=False),
        sa.Column("data_complete_from", sa.Date(), nullable=True),
        sa.Column("last_backfill_at", sa.DateTime(), nullable=True),
        sa.Column("updated_by", sa.String(length=256), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        """
        INSERT INTO wiki_conversation_governance_config
            (id, fallback_heavy_threshold, no_match_repeated_threshold, high_latency_ms_threshold)
        VALUES
            (1, 2, 2, 1000)
        """
    )


def downgrade() -> None:
    op.drop_table("wiki_conversation_governance_config")
