"""network detection watchlist

Revision ID: 20260611_1700
Revises: 20260605_0120
Create Date: 2026-06-11 17:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260611_1700"
down_revision = "20260605_0120"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "network_detection_watchlist",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("match_type", sa.String(length=32), nullable=False),
        sa.Column("pattern", sa.String(length=1024), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("category", "match_type", "pattern", name="uq_network_detection_watchlist_rule"),
    )
    op.create_index(op.f("ix_network_detection_watchlist_id"), "network_detection_watchlist", ["id"], unique=False)
    op.create_index(op.f("ix_network_detection_watchlist_category"), "network_detection_watchlist", ["category"], unique=False)
    op.create_index(op.f("ix_network_detection_watchlist_match_type"), "network_detection_watchlist", ["match_type"], unique=False)
    op.create_index(op.f("ix_network_detection_watchlist_pattern"), "network_detection_watchlist", ["pattern"], unique=False)
    op.create_index(op.f("ix_network_detection_watchlist_is_active"), "network_detection_watchlist", ["is_active"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_network_detection_watchlist_is_active"), table_name="network_detection_watchlist")
    op.drop_index(op.f("ix_network_detection_watchlist_pattern"), table_name="network_detection_watchlist")
    op.drop_index(op.f("ix_network_detection_watchlist_match_type"), table_name="network_detection_watchlist")
    op.drop_index(op.f("ix_network_detection_watchlist_category"), table_name="network_detection_watchlist")
    op.drop_index(op.f("ix_network_detection_watchlist_id"), table_name="network_detection_watchlist")
    op.drop_table("network_detection_watchlist")
