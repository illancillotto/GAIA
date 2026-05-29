"""inaz credentials

Revision ID: 20260529_0100
Revises: 20260529_0099
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa


revision = "20260529_0100"
down_revision = "20260529_0099"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inaz_credentials",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("password_encrypted", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_authenticated_url", sa.String(length=1024), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.add_column("inaz_sync_jobs", sa.Column("credential_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_inaz_sync_jobs_credential_id_inaz_credentials",
        "inaz_sync_jobs",
        "inaz_credentials",
        ["credential_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_inaz_sync_jobs_credential_id"), "inaz_sync_jobs", ["credential_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_inaz_sync_jobs_credential_id"), table_name="inaz_sync_jobs")
    op.drop_constraint("fk_inaz_sync_jobs_credential_id_inaz_credentials", "inaz_sync_jobs", type_="foreignkey")
    op.drop_column("inaz_sync_jobs", "credential_id")
    op.drop_table("inaz_credentials")
