"""Add an atomic registry for ruolo tributi reminder notice numbers.

Revision ID: 20260825_1100
Revises: 20260824_1000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260825_1100"
down_revision = "20260824_1000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ruolo_tributi_notice_numbers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("emission_year", sa.Integer(), nullable=False),
        sa.Column("progressive", sa.Integer(), nullable=False),
        sa.Column("notice_number", sa.String(length=40), nullable=False),
        sa.Column("identity_key", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("emission_year", "progressive", name="uq_ruolo_tributi_notice_year_progressive"),
        sa.UniqueConstraint("identity_key", name="uq_ruolo_tributi_notice_identity"),
        sa.UniqueConstraint("notice_number", name="uq_ruolo_tributi_notice_number"),
    )
    op.create_index(
        "ix_ruolo_tributi_notice_numbers_emission_year",
        "ruolo_tributi_notice_numbers",
        ["emission_year"],
    )
    op.create_index(
        "ix_ruolo_tributi_notice_numbers_status",
        "ruolo_tributi_notice_numbers",
        ["status"],
    )
    op.add_column("ruolo_tributi_reminder_batch_items", sa.Column("notice_number_id", sa.Uuid(), nullable=True))
    op.create_index(
        "ix_ruolo_tributi_reminder_batch_items_notice_number_id",
        "ruolo_tributi_reminder_batch_items",
        ["notice_number_id"],
    )
    op.create_foreign_key(
        "fk_ruolo_tributi_reminder_batch_items_notice_number_id",
        "ruolo_tributi_reminder_batch_items",
        "ruolo_tributi_notice_numbers",
        ["notice_number_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_ruolo_tributi_reminder_batch_items_notice_number_id",
        "ruolo_tributi_reminder_batch_items",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_ruolo_tributi_reminder_batch_items_notice_number_id",
        table_name="ruolo_tributi_reminder_batch_items",
    )
    op.drop_column("ruolo_tributi_reminder_batch_items", "notice_number_id")
    op.drop_index("ix_ruolo_tributi_notice_numbers_status", table_name="ruolo_tributi_notice_numbers")
    op.drop_index("ix_ruolo_tributi_notice_numbers_emission_year", table_name="ruolo_tributi_notice_numbers")
    op.drop_table("ruolo_tributi_notice_numbers")
