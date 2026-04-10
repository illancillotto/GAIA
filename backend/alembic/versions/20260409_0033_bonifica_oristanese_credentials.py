"""bonifica oristanese credentials

Revision ID: 20260409_0033
Revises: 20260405_0032
Create Date: 2026-04-09 09:15:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260409_0033"
down_revision = "20260405_0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bonifica_oristanese_credentials",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("login_identifier", sa.String(length=255), nullable=False),
        sa.Column("password_encrypted", sa.Text(), nullable=False),
        sa.Column("remember_me", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_authenticated_url", sa.String(length=1024), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_bonifica_oristanese_credentials_id",
        "bonifica_oristanese_credentials",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_bonifica_oristanese_credentials_id", table_name="bonifica_oristanese_credentials")
    op.drop_table("bonifica_oristanese_credentials")
