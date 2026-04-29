"""add capacitas history import jobs

Revision ID: 20260429_0068
Revises: 20260428_0067
Create Date: 2026-04-29 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260429_0068"
down_revision: str | None = "20260428_0067"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "capacitas_anagrafica_history_import_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("credential_id", sa.Integer(), nullable=True),
        sa.Column("requested_by_user_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["credential_id"], ["capacitas_credentials.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_capacitas_anagrafica_history_import_jobs_credential_id"),
        "capacitas_anagrafica_history_import_jobs",
        ["credential_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_capacitas_anagrafica_history_import_jobs_requested_by_user_id"),
        "capacitas_anagrafica_history_import_jobs",
        ["requested_by_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_capacitas_anagrafica_history_import_jobs_status"),
        "capacitas_anagrafica_history_import_jobs",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_capacitas_anagrafica_history_import_jobs_status"), table_name="capacitas_anagrafica_history_import_jobs")
    op.drop_index(
        op.f("ix_capacitas_anagrafica_history_import_jobs_requested_by_user_id"),
        table_name="capacitas_anagrafica_history_import_jobs",
    )
    op.drop_index(
        op.f("ix_capacitas_anagrafica_history_import_jobs_credential_id"),
        table_name="capacitas_anagrafica_history_import_jobs",
    )
    op.drop_table("capacitas_anagrafica_history_import_jobs")
