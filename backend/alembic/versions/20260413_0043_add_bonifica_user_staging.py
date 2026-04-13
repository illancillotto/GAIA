"""add bonifica user staging

Revision ID: 20260413_0043
Revises: 20260413_0042
Create Date: 2026-04-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20260413_0043"
down_revision = "20260413_0042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bonifica_user_staging",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("wc_id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=True),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("user_type", sa.String(length=20), nullable=True),
        sa.Column("business_name", sa.String(length=300), nullable=True),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("tax", sa.String(length=20), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("mobile", sa.String(length=30), nullable=True),
        sa.Column("role", sa.String(length=50), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("wc_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_status", sa.String(length=20), nullable=False, server_default="new"),
        sa.Column("matched_subject_id", sa.Uuid(), nullable=True),
        sa.Column("mismatch_fields", sa.JSON(), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["matched_subject_id"], ["ana_subjects.id"]),
        sa.ForeignKeyConstraint(["reviewed_by"], ["application_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_bonifica_user_staging_wc_id"), "bonifica_user_staging", ["wc_id"], unique=True)
    op.create_index(op.f("ix_bonifica_user_staging_email"), "bonifica_user_staging", ["email"], unique=False)
    op.create_index(op.f("ix_bonifica_user_staging_user_type"), "bonifica_user_staging", ["user_type"], unique=False)
    op.create_index(op.f("ix_bonifica_user_staging_business_name"), "bonifica_user_staging", ["business_name"], unique=False)
    op.create_index(op.f("ix_bonifica_user_staging_first_name"), "bonifica_user_staging", ["first_name"], unique=False)
    op.create_index(op.f("ix_bonifica_user_staging_last_name"), "bonifica_user_staging", ["last_name"], unique=False)
    op.create_index(op.f("ix_bonifica_user_staging_tax"), "bonifica_user_staging", ["tax"], unique=False)
    op.create_index(op.f("ix_bonifica_user_staging_role"), "bonifica_user_staging", ["role"], unique=False)
    op.create_index(op.f("ix_bonifica_user_staging_review_status"), "bonifica_user_staging", ["review_status"], unique=False)
    op.create_index(op.f("ix_bonifica_user_staging_matched_subject_id"), "bonifica_user_staging", ["matched_subject_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_bonifica_user_staging_matched_subject_id"), table_name="bonifica_user_staging")
    op.drop_index(op.f("ix_bonifica_user_staging_review_status"), table_name="bonifica_user_staging")
    op.drop_index(op.f("ix_bonifica_user_staging_role"), table_name="bonifica_user_staging")
    op.drop_index(op.f("ix_bonifica_user_staging_tax"), table_name="bonifica_user_staging")
    op.drop_index(op.f("ix_bonifica_user_staging_last_name"), table_name="bonifica_user_staging")
    op.drop_index(op.f("ix_bonifica_user_staging_first_name"), table_name="bonifica_user_staging")
    op.drop_index(op.f("ix_bonifica_user_staging_business_name"), table_name="bonifica_user_staging")
    op.drop_index(op.f("ix_bonifica_user_staging_user_type"), table_name="bonifica_user_staging")
    op.drop_index(op.f("ix_bonifica_user_staging_email"), table_name="bonifica_user_staging")
    op.drop_index(op.f("ix_bonifica_user_staging_wc_id"), table_name="bonifica_user_staging")
    op.drop_table("bonifica_user_staging")
