"""capacitas credentials

Revision ID: 20260402_0027
Revises: 20260401_0026
Create Date: 2026-04-02 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260402_0027"
down_revision = "20260401_0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "capacitas_credentials",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("password_encrypted", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("allowed_hours_start", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("allowed_hours_end", sa.Integer(), nullable=False, server_default="23"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_capacitas_credentials_id", "capacitas_credentials", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_capacitas_credentials_id", table_name="capacitas_credentials")
    op.drop_table("capacitas_credentials")
