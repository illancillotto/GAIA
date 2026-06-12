"""network detection watchlist mode

Revision ID: 20260611_1715
Revises: 20260611_1700
Create Date: 2026-06-11 17:15:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260611_1715"
down_revision = "20260611_1700"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "network_detection_watchlist",
        sa.Column("rule_mode", sa.String(length=16), nullable=False, server_default="detect"),
    )
    op.create_index(op.f("ix_network_detection_watchlist_rule_mode"), "network_detection_watchlist", ["rule_mode"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_network_detection_watchlist_rule_mode"), table_name="network_detection_watchlist")
    op.drop_column("network_detection_watchlist", "rule_mode")
