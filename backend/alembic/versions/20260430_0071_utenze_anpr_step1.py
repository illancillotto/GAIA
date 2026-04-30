"""utenze: add anpr sync tables and person fields

Revision ID: 20260430_0071
Revises: 20260429_0070
Create Date: 2026-04-30 10:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260430_0071"
down_revision = "20260429_0070"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ana_persons", sa.Column("anpr_id", sa.String(length=50), nullable=True))
    op.add_column("ana_persons", sa.Column("stato_anpr", sa.String(length=30), nullable=True))
    op.add_column("ana_persons", sa.Column("data_decesso", sa.Date(), nullable=True))
    op.add_column("ana_persons", sa.Column("luogo_decesso_comune", sa.String(length=100), nullable=True))
    op.add_column("ana_persons", sa.Column("last_anpr_check_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ana_persons", sa.Column("last_c030_check_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_ana_persons_anpr_id", "ana_persons", ["anpr_id"], unique=False)
    op.create_index("ix_ana_persons_stato_anpr", "ana_persons", ["stato_anpr"], unique=False)

    op.create_table(
        "anpr_check_log",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("call_type", sa.String(length=10), nullable=False),
        sa.Column("id_operazione_client", sa.String(length=100), nullable=False),
        sa.Column("id_operazione_anpr", sa.String(length=100), nullable=True),
        sa.Column("esito", sa.String(length=30), nullable=False),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("data_decesso_anpr", sa.Date(), nullable=True),
        sa.Column("triggered_by", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["subject_id"], ["ana_subjects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        """
        CREATE INDEX ix_anpr_check_log_subject_id_created_at_desc
        ON anpr_check_log (subject_id, created_at DESC)
        """
    )

    op.create_table(
        "anpr_sync_config",
        sa.Column("id", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("max_calls_per_day", sa.Integer(), server_default=sa.text("100"), nullable=False),
        sa.Column("job_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("job_cron", sa.String(length=50), server_default=sa.text("'0 2 * * *'"), nullable=False),
        sa.Column("lookback_years", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("retry_not_found_days", sa.Integer(), server_default=sa.text("90"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["application_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute("INSERT INTO anpr_sync_config (id) VALUES (1) ON CONFLICT DO NOTHING")


def downgrade() -> None:
    op.drop_table("anpr_sync_config")

    op.execute("DROP INDEX IF EXISTS ix_anpr_check_log_subject_id_created_at_desc")
    op.drop_table("anpr_check_log")

    op.drop_index("ix_ana_persons_stato_anpr", table_name="ana_persons")
    op.drop_index("ix_ana_persons_anpr_id", table_name="ana_persons")
    op.drop_column("ana_persons", "last_c030_check_at")
    op.drop_column("ana_persons", "last_anpr_check_at")
    op.drop_column("ana_persons", "luogo_decesso_comune")
    op.drop_column("ana_persons", "data_decesso")
    op.drop_column("ana_persons", "stato_anpr")
    op.drop_column("ana_persons", "anpr_id")
