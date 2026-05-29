"""add inaz module

Revision ID: 20260529_0093
Revises: 20260521_0092
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa


revision = "20260529_0093"
down_revision = "20260521_0092"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("application_users", sa.Column("module_inaz", sa.Boolean(), nullable=False, server_default="false"))

    op.create_table(
        "inaz_collaborators",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("application_user_id", sa.Integer(), nullable=True),
        sa.Column("kint", sa.String(length=64), nullable=True),
        sa.Column("kkint", sa.String(length=255), nullable=True),
        sa.Column("employee_code", sa.String(length=32), nullable=False),
        sa.Column("company_code", sa.String(length=32), nullable=True),
        sa.Column("company_label", sa.String(length=255), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["application_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_code", "company_code", name="uq_inaz_collaborators_employee_company"),
    )
    op.create_index(op.f("ix_inaz_collaborators_application_user_id"), "inaz_collaborators", ["application_user_id"], unique=False)
    op.create_index(op.f("ix_inaz_collaborators_kint"), "inaz_collaborators", ["kint"], unique=False)
    op.create_index(op.f("ix_inaz_collaborators_employee_code"), "inaz_collaborators", ["employee_code"], unique=False)
    op.create_index(op.f("ix_inaz_collaborators_company_code"), "inaz_collaborators", ["company_code"], unique=False)
    op.create_index(op.f("ix_inaz_collaborators_name"), "inaz_collaborators", ["name"], unique=False)

    op.create_table(
        "inaz_import_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("filename", sa.String(length=300), nullable=True),
        sa.Column("requested_by_user_id", sa.Integer(), nullable=False),
        sa.Column("target_user_id", sa.Integer(), nullable=True),
        sa.Column("date_from", sa.Date(), nullable=True),
        sa.Column("date_to", sa.Date(), nullable=True),
        sa.Column("total_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_imported", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_errors", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("params_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["application_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_inaz_import_jobs_status"), "inaz_import_jobs", ["status"], unique=False)
    op.create_index(op.f("ix_inaz_import_jobs_requested_by_user_id"), "inaz_import_jobs", ["requested_by_user_id"], unique=False)
    op.create_index(op.f("ix_inaz_import_jobs_target_user_id"), "inaz_import_jobs", ["target_user_id"], unique=False)

    op.create_table(
        "inaz_daily_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("collaborator_id", sa.Uuid(), nullable=False),
        sa.Column("application_user_id", sa.Integer(), nullable=True),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("schedule_code", sa.String(length=32), nullable=True),
        sa.Column("teo_minutes", sa.Integer(), nullable=True),
        sa.Column("ordinary_minutes", sa.Integer(), nullable=True),
        sa.Column("absence_minutes", sa.Integer(), nullable=True),
        sa.Column("justified_minutes", sa.Integer(), nullable=True),
        sa.Column("maggiorazione_minutes", sa.Integer(), nullable=True),
        sa.Column("mpe_minutes", sa.Integer(), nullable=True),
        sa.Column("straordinario_minutes", sa.Integer(), nullable=True),
        sa.Column("stato", sa.String(length=120), nullable=True),
        sa.Column("evidenze", sa.Text(), nullable=True),
        sa.Column("raw_weekday", sa.String(length=16), nullable=True),
        sa.Column("raw_payload_json", sa.JSON(), nullable=True),
        sa.Column("source_job_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["application_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["collaborator_id"], ["inaz_collaborators.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_job_id"], ["inaz_import_jobs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("collaborator_id", "work_date", name="uq_inaz_daily_records_collaborator_date"),
    )
    op.create_index(op.f("ix_inaz_daily_records_collaborator_id"), "inaz_daily_records", ["collaborator_id"], unique=False)
    op.create_index(op.f("ix_inaz_daily_records_application_user_id"), "inaz_daily_records", ["application_user_id"], unique=False)
    op.create_index(op.f("ix_inaz_daily_records_work_date"), "inaz_daily_records", ["work_date"], unique=False)
    op.create_index(op.f("ix_inaz_daily_records_source_job_id"), "inaz_daily_records", ["source_job_id"], unique=False)

    op.create_table(
        "inaz_daily_punches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("daily_record_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("entry_time", sa.Time(), nullable=True),
        sa.Column("exit_time", sa.Time(), nullable=True),
        sa.ForeignKeyConstraint(["daily_record_id"], ["inaz_daily_records.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("daily_record_id", "sequence", name="uq_inaz_daily_punches_record_sequence"),
    )
    op.create_index(op.f("ix_inaz_daily_punches_daily_record_id"), "inaz_daily_punches", ["daily_record_id"], unique=False)

    op.create_table(
        "inaz_event_summaries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("collaborator_id", sa.Uuid(), nullable=False),
        sa.Column("application_user_id", sa.Integer(), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("event_code", sa.String(length=64), nullable=True),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("spettante_minutes", sa.Integer(), nullable=True),
        sa.Column("fruito_minutes", sa.Integer(), nullable=True),
        sa.Column("residuo_prec_minutes", sa.Integer(), nullable=True),
        sa.Column("saldo_minutes", sa.Integer(), nullable=True),
        sa.Column("autorizzato_minutes", sa.Integer(), nullable=True),
        sa.Column("pianificato_minutes", sa.Integer(), nullable=True),
        sa.Column("richiesto_minutes", sa.Integer(), nullable=True),
        sa.Column("saldo_totale_minutes", sa.Integer(), nullable=True),
        sa.Column("unitamisura", sa.String(length=32), nullable=True),
        sa.Column("raw_payload_json", sa.JSON(), nullable=True),
        sa.Column("source_job_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["application_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["collaborator_id"], ["inaz_collaborators.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_job_id"], ["inaz_import_jobs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "collaborator_id",
            "period_start",
            "period_end",
            "event_code",
            "description",
            name="uq_inaz_event_summaries_period_event",
        ),
    )
    op.create_index(op.f("ix_inaz_event_summaries_collaborator_id"), "inaz_event_summaries", ["collaborator_id"], unique=False)
    op.create_index(op.f("ix_inaz_event_summaries_application_user_id"), "inaz_event_summaries", ["application_user_id"], unique=False)
    op.create_index(op.f("ix_inaz_event_summaries_period_start"), "inaz_event_summaries", ["period_start"], unique=False)
    op.create_index(op.f("ix_inaz_event_summaries_period_end"), "inaz_event_summaries", ["period_end"], unique=False)
    op.create_index(op.f("ix_inaz_event_summaries_event_code"), "inaz_event_summaries", ["event_code"], unique=False)
    op.create_index(op.f("ix_inaz_event_summaries_source_job_id"), "inaz_event_summaries", ["source_job_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_inaz_event_summaries_source_job_id"), table_name="inaz_event_summaries")
    op.drop_index(op.f("ix_inaz_event_summaries_event_code"), table_name="inaz_event_summaries")
    op.drop_index(op.f("ix_inaz_event_summaries_period_end"), table_name="inaz_event_summaries")
    op.drop_index(op.f("ix_inaz_event_summaries_period_start"), table_name="inaz_event_summaries")
    op.drop_index(op.f("ix_inaz_event_summaries_application_user_id"), table_name="inaz_event_summaries")
    op.drop_index(op.f("ix_inaz_event_summaries_collaborator_id"), table_name="inaz_event_summaries")
    op.drop_table("inaz_event_summaries")

    op.drop_index(op.f("ix_inaz_daily_punches_daily_record_id"), table_name="inaz_daily_punches")
    op.drop_table("inaz_daily_punches")

    op.drop_index(op.f("ix_inaz_daily_records_source_job_id"), table_name="inaz_daily_records")
    op.drop_index(op.f("ix_inaz_daily_records_work_date"), table_name="inaz_daily_records")
    op.drop_index(op.f("ix_inaz_daily_records_application_user_id"), table_name="inaz_daily_records")
    op.drop_index(op.f("ix_inaz_daily_records_collaborator_id"), table_name="inaz_daily_records")
    op.drop_table("inaz_daily_records")

    op.drop_index(op.f("ix_inaz_import_jobs_target_user_id"), table_name="inaz_import_jobs")
    op.drop_index(op.f("ix_inaz_import_jobs_requested_by_user_id"), table_name="inaz_import_jobs")
    op.drop_index(op.f("ix_inaz_import_jobs_status"), table_name="inaz_import_jobs")
    op.drop_table("inaz_import_jobs")

    op.drop_index(op.f("ix_inaz_collaborators_name"), table_name="inaz_collaborators")
    op.drop_index(op.f("ix_inaz_collaborators_company_code"), table_name="inaz_collaborators")
    op.drop_index(op.f("ix_inaz_collaborators_employee_code"), table_name="inaz_collaborators")
    op.drop_index(op.f("ix_inaz_collaborators_kint"), table_name="inaz_collaborators")
    op.drop_index(op.f("ix_inaz_collaborators_application_user_id"), table_name="inaz_collaborators")
    op.drop_table("inaz_collaborators")

    op.drop_column("application_users", "module_inaz")
