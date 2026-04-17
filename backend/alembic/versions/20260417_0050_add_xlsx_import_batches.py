"""add xlsx import batches table

Revision ID: 20260417_0050
Revises: 20260417_0049
Create Date: 2026-04-17
"""

from alembic import op
import sqlalchemy as sa

revision = "20260417_0050"
down_revision = "20260417_0049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ana_xlsx_import_batches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_user_id", sa.Integer(), nullable=True),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("inserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unchanged", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("anomalies", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("errors", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_log", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ana_xlsx_import_batches_status", "ana_xlsx_import_batches", ["status"], unique=False)
    op.create_index("ix_ana_xlsx_import_batches_requested_by", "ana_xlsx_import_batches", ["requested_by_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ana_xlsx_import_batches_requested_by", table_name="ana_xlsx_import_batches")
    op.drop_index("ix_ana_xlsx_import_batches_status", table_name="ana_xlsx_import_batches")
    op.drop_table("ana_xlsx_import_batches")
