"""audit domain minimum

Revision ID: 20260320_0003
Revises: 20260320_0002
Create Date: 2026-03-20 00:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260320_0003"
down_revision = "20260320_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nas_users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=120), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("source_uid", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_seen_snapshot_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_nas_users_id", "nas_users", ["id"], unique=False)
    op.create_index("ix_nas_users_username", "nas_users", ["username"], unique=True)

    op.create_table(
        "nas_groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("last_seen_snapshot_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_nas_groups_id", "nas_groups", ["id"], unique=False)
    op.create_index("ix_nas_groups_name", "nas_groups", ["name"], unique=True)

    op.create_table(
        "shares",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("path", sa.String(length=255), nullable=False),
        sa.Column("sector", sa.String(length=120), nullable=True),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("last_seen_snapshot_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_shares_id", "shares", ["id"], unique=False)
    op.create_index("ix_shares_name", "shares", ["name"], unique=True)
    op.create_index("ix_shares_path", "shares", ["path"], unique=True)

    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("snapshot_id", sa.Integer(), sa.ForeignKey("snapshots.id"), nullable=True),
        sa.Column("nas_user_id", sa.Integer(), sa.ForeignKey("nas_users.id"), nullable=False),
        sa.Column("share_id", sa.Integer(), sa.ForeignKey("shares.id"), nullable=False),
        sa.Column("reviewer_user_id", sa.Integer(), sa.ForeignKey("application_users.id"), nullable=False),
        sa.Column("decision", sa.String(length=50), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_reviews_id", "reviews", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_reviews_id", table_name="reviews")
    op.drop_table("reviews")
    op.drop_index("ix_shares_path", table_name="shares")
    op.drop_index("ix_shares_name", table_name="shares")
    op.drop_index("ix_shares_id", table_name="shares")
    op.drop_table("shares")
    op.drop_index("ix_nas_groups_name", table_name="nas_groups")
    op.drop_index("ix_nas_groups_id", table_name="nas_groups")
    op.drop_table("nas_groups")
    op.drop_index("ix_nas_users_username", table_name="nas_users")
    op.drop_index("ix_nas_users_id", table_name="nas_users")
    op.drop_table("nas_users")
