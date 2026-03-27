"""anagrafica mvp backend

Revision ID: 20260327_0018
Revises: 20260327_0017
Create Date: 2026-03-27 10:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260327_0018"
down_revision = "20260327_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ana_subjects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=False, server_default="unknown"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("source_name_raw", sa.String(length=512), nullable=False),
        sa.Column("nas_folder_path", sa.String(length=1024), nullable=True),
        sa.Column("nas_folder_letter", sa.String(length=32), nullable=True),
        sa.Column("requires_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nas_folder_path", name="uq_ana_subjects_nas_folder_path"),
    )
    op.create_index("ix_ana_subjects_subject_type", "ana_subjects", ["subject_type"], unique=False)
    op.create_index("ix_ana_subjects_status", "ana_subjects", ["status"], unique=False)
    op.create_index("ix_ana_subjects_nas_folder_letter", "ana_subjects", ["nas_folder_letter"], unique=False)

    op.create_table(
        "ana_persons",
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("cognome", sa.String(length=255), nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("codice_fiscale", sa.String(length=32), nullable=False),
        sa.Column("data_nascita", sa.Date(), nullable=True),
        sa.Column("comune_nascita", sa.String(length=255), nullable=True),
        sa.Column("indirizzo", sa.String(length=255), nullable=True),
        sa.Column("comune_residenza", sa.String(length=255), nullable=True),
        sa.Column("cap", sa.String(length=16), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("telefono", sa.String(length=64), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["subject_id"], ["ana_subjects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("subject_id"),
        sa.UniqueConstraint("codice_fiscale", name="uq_ana_persons_codice_fiscale"),
    )
    op.create_index("ix_ana_persons_cognome", "ana_persons", ["cognome"], unique=False)
    op.create_index("ix_ana_persons_nome", "ana_persons", ["nome"], unique=False)
    op.create_index("ix_ana_persons_codice_fiscale", "ana_persons", ["codice_fiscale"], unique=False)

    op.create_table(
        "ana_companies",
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("ragione_sociale", sa.String(length=255), nullable=False),
        sa.Column("partita_iva", sa.String(length=32), nullable=False),
        sa.Column("codice_fiscale", sa.String(length=32), nullable=True),
        sa.Column("forma_giuridica", sa.String(length=128), nullable=True),
        sa.Column("sede_legale", sa.String(length=255), nullable=True),
        sa.Column("comune_sede", sa.String(length=255), nullable=True),
        sa.Column("cap", sa.String(length=16), nullable=True),
        sa.Column("email_pec", sa.String(length=255), nullable=True),
        sa.Column("telefono", sa.String(length=64), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["subject_id"], ["ana_subjects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("subject_id"),
        sa.UniqueConstraint("partita_iva", name="uq_ana_companies_partita_iva"),
    )
    op.create_index("ix_ana_companies_ragione_sociale", "ana_companies", ["ragione_sociale"], unique=False)
    op.create_index("ix_ana_companies_partita_iva", "ana_companies", ["partita_iva"], unique=False)
    op.create_index("ix_ana_companies_codice_fiscale", "ana_companies", ["codice_fiscale"], unique=False)

    op.create_table(
        "ana_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("doc_type", sa.String(length=64), nullable=False, server_default="altro"),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("nas_path", sa.String(length=1024), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("file_modified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("classification_source", sa.String(length=32), nullable=False, server_default="auto"),
        sa.Column("storage_type", sa.String(length=32), nullable=False, server_default="nas_link"),
        sa.Column("local_path", sa.String(length=1024), nullable=True),
        sa.Column("mime_type", sa.String(length=255), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["subject_id"], ["ana_subjects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ana_documents_subject_id", "ana_documents", ["subject_id"], unique=False)
    op.create_index("ix_ana_documents_doc_type", "ana_documents", ["doc_type"], unique=False)

    op.create_table(
        "ana_import_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_user_id", sa.Integer(), nullable=True),
        sa.Column("letter", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("total_folders", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("imported_ok", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("imported_errors", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warning_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("log_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ana_import_jobs_requested_by_user_id", "ana_import_jobs", ["requested_by_user_id"], unique=False)
    op.create_index("ix_ana_import_jobs_letter", "ana_import_jobs", ["letter"], unique=False)
    op.create_index("ix_ana_import_jobs_status", "ana_import_jobs", ["status"], unique=False)

    op.create_table(
        "ana_audit_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("changed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("diff_json", sa.JSON(), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subject_id"], ["ana_subjects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ana_audit_log_subject_id", "ana_audit_log", ["subject_id"], unique=False)
    op.create_index("ix_ana_audit_log_changed_by_user_id", "ana_audit_log", ["changed_by_user_id"], unique=False)
    op.create_index("ix_ana_audit_log_action", "ana_audit_log", ["action"], unique=False)
    op.create_index("ix_ana_audit_log_changed_at", "ana_audit_log", ["changed_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ana_audit_log_changed_at", table_name="ana_audit_log")
    op.drop_index("ix_ana_audit_log_action", table_name="ana_audit_log")
    op.drop_index("ix_ana_audit_log_changed_by_user_id", table_name="ana_audit_log")
    op.drop_index("ix_ana_audit_log_subject_id", table_name="ana_audit_log")
    op.drop_table("ana_audit_log")

    op.drop_index("ix_ana_import_jobs_status", table_name="ana_import_jobs")
    op.drop_index("ix_ana_import_jobs_letter", table_name="ana_import_jobs")
    op.drop_index("ix_ana_import_jobs_requested_by_user_id", table_name="ana_import_jobs")
    op.drop_table("ana_import_jobs")

    op.drop_index("ix_ana_documents_doc_type", table_name="ana_documents")
    op.drop_index("ix_ana_documents_subject_id", table_name="ana_documents")
    op.drop_table("ana_documents")

    op.drop_index("ix_ana_companies_codice_fiscale", table_name="ana_companies")
    op.drop_index("ix_ana_companies_partita_iva", table_name="ana_companies")
    op.drop_index("ix_ana_companies_ragione_sociale", table_name="ana_companies")
    op.drop_table("ana_companies")

    op.drop_index("ix_ana_persons_codice_fiscale", table_name="ana_persons")
    op.drop_index("ix_ana_persons_nome", table_name="ana_persons")
    op.drop_index("ix_ana_persons_cognome", table_name="ana_persons")
    op.drop_table("ana_persons")

    op.drop_index("ix_ana_subjects_nas_folder_letter", table_name="ana_subjects")
    op.drop_index("ix_ana_subjects_status", table_name="ana_subjects")
    op.drop_index("ix_ana_subjects_subject_type", table_name="ana_subjects")
    op.drop_table("ana_subjects")
