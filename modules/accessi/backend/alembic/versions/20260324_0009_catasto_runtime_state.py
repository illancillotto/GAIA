"""catasto runtime state

Revision ID: 20260324_0009
Revises: 20260324_0008
Create Date: 2026-03-24 00:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260324_0009"
down_revision = "20260324_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("catasto_batches", sa.Column("current_operation", sa.Text(), nullable=True))

    op.add_column("catasto_visure_requests", sa.Column("current_operation", sa.Text(), nullable=True))
    op.add_column("catasto_visure_requests", sa.Column("captcha_image_path", sa.String(length=1024), nullable=True))
    op.add_column("catasto_visure_requests", sa.Column("captcha_requested_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("catasto_visure_requests", sa.Column("captcha_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("catasto_visure_requests", sa.Column("captcha_manual_solution", sa.String(length=64), nullable=True))
    op.add_column(
        "catasto_visure_requests",
        sa.Column("captcha_skip_requested", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("catasto_visure_requests", "captcha_skip_requested")
    op.drop_column("catasto_visure_requests", "captcha_manual_solution")
    op.drop_column("catasto_visure_requests", "captcha_expires_at")
    op.drop_column("catasto_visure_requests", "captcha_requested_at")
    op.drop_column("catasto_visure_requests", "captcha_image_path")
    op.drop_column("catasto_visure_requests", "current_operation")
    op.drop_column("catasto_batches", "current_operation")
