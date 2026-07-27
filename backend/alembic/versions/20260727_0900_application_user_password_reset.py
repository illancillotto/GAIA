"""application user password reset tokens

Revision ID: 20260727_0900
Revises: 20260723_1600
Create Date: 2026-07-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260727_0900"
down_revision = "20260723_1600"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "application_user_password_reset_tokens",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("requested_identifier", sa.String(length=255), nullable=True),
        sa.Column("requested_ip", sa.String(length=64), nullable=True),
        sa.Column("requested_user_agent", sa.String(length=512), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["application_users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_application_user_password_reset_tokens_token_hash",
        "application_user_password_reset_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_application_user_password_reset_tokens_user_id",
        "application_user_password_reset_tokens",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_application_user_password_reset_tokens_user_id", table_name="application_user_password_reset_tokens")
    op.drop_index("ix_application_user_password_reset_tokens_token_hash", table_name="application_user_password_reset_tokens")
    op.drop_table("application_user_password_reset_tokens")
