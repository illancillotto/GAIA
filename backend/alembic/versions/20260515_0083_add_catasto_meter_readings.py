"""catasto meter readings

Revision ID: 20260515_0083
Revises: 20260515_0082
Create Date: 2026-05-15 17:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260515_0083"
down_revision: str | None = "20260515_0082"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "catasto_meter_reading_imports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("distretto_id", sa.Uuid(), nullable=False),
        sa.Column("anno", sa.Integer(), nullable=False),
        sa.Column("filename_originale", sa.String(length=255), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=True),
        sa.Column("stato", sa.String(length=32), nullable=False),
        sa.Column("totale_righe", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("righe_importate", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("righe_con_warning", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("righe_scartate", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("uploaded_by", sa.Integer(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_report", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["distretto_id"], ["cat_distretti.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["application_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_catasto_meter_reading_imports_distretto_id"), "catasto_meter_reading_imports", ["distretto_id"], unique=False)
    op.create_index(op.f("ix_catasto_meter_reading_imports_anno"), "catasto_meter_reading_imports", ["anno"], unique=False)
    op.create_index(op.f("ix_catasto_meter_reading_imports_file_hash"), "catasto_meter_reading_imports", ["file_hash"], unique=False)
    op.create_index(op.f("ix_catasto_meter_reading_imports_stato"), "catasto_meter_reading_imports", ["stato"], unique=False)

    op.create_table(
        "catasto_meter_readings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("import_id", sa.Uuid(), nullable=True),
        sa.Column("distretto_id", sa.Uuid(), nullable=False),
        sa.Column("anno", sa.Integer(), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=True),
        sa.Column("excel_id", sa.String(length=64), nullable=True),
        sa.Column("punto_consegna", sa.String(length=128), nullable=False),
        sa.Column("matricola", sa.String(length=128), nullable=True),
        sa.Column("sigillo", sa.String(length=128), nullable=True),
        sa.Column("tipologia_idrante", sa.String(length=255), nullable=True),
        sa.Column("firmware_version", sa.String(length=128), nullable=True),
        sa.Column("battery_level", sa.String(length=64), nullable=True),
        sa.Column("lettura_iniziale", sa.Numeric(precision=14, scale=3), nullable=True),
        sa.Column("lettura_finale", sa.Numeric(precision=14, scale=3), nullable=True),
        sa.Column("consumo_mc", sa.Numeric(precision=14, scale=3), nullable=True),
        sa.Column("data_lettura", sa.Date(), nullable=True),
        sa.Column("operatore_lettura", sa.String(length=255), nullable=True),
        sa.Column("intervento_da_eseguire", sa.Text(), nullable=True),
        sa.Column("intervento_eseguito", sa.Text(), nullable=True),
        sa.Column("operatore_intervento", sa.String(length=255), nullable=True),
        sa.Column("data_intervento", sa.Date(), nullable=True),
        sa.Column("dui", sa.String(length=128), nullable=True),
        sa.Column("codice_fiscale", sa.String(length=32), nullable=True),
        sa.Column("codice_fiscale_normalizzato", sa.String(length=32), nullable=True),
        sa.Column("subject_id", sa.Uuid(), nullable=True),
        sa.Column("coltura", sa.String(length=255), nullable=True),
        sa.Column("tariffa", sa.String(length=128), nullable=True),
        sa.Column("fondo_chiuso", sa.String(length=128), nullable=True),
        sa.Column("telefono", sa.String(length=64), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("validation_status", sa.String(length=32), nullable=False),
        sa.Column("validation_messages", sa.JSON(), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("mobile_session_id", sa.String(length=64), nullable=True),
        sa.Column("gps_lat", sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column("gps_lng", sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column("photo_url", sa.String(length=1024), nullable=True),
        sa.Column("offline_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sync_status", sa.String(length=32), nullable=True),
        sa.Column("device_id", sa.String(length=128), nullable=True),
        sa.Column("mobile_operator_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["distretto_id"], ["cat_distretti.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["import_id"], ["catasto_meter_reading_imports.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subject_id"], ["ana_subjects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("anno", "distretto_id", "punto_consegna", name="uq_catasto_meter_readings_ref"),
    )
    op.create_index(op.f("ix_catasto_meter_readings_import_id"), "catasto_meter_readings", ["import_id"], unique=False)
    op.create_index(op.f("ix_catasto_meter_readings_distretto_id"), "catasto_meter_readings", ["distretto_id"], unique=False)
    op.create_index(op.f("ix_catasto_meter_readings_anno"), "catasto_meter_readings", ["anno"], unique=False)
    op.create_index(op.f("ix_catasto_meter_readings_punto_consegna"), "catasto_meter_readings", ["punto_consegna"], unique=False)
    op.create_index(op.f("ix_catasto_meter_readings_matricola"), "catasto_meter_readings", ["matricola"], unique=False)
    op.create_index(op.f("ix_catasto_meter_readings_codice_fiscale"), "catasto_meter_readings", ["codice_fiscale"], unique=False)
    op.create_index(
        op.f("ix_catasto_meter_readings_codice_fiscale_normalizzato"),
        "catasto_meter_readings",
        ["codice_fiscale_normalizzato"],
        unique=False,
    )
    op.create_index(op.f("ix_catasto_meter_readings_subject_id"), "catasto_meter_readings", ["subject_id"], unique=False)
    op.create_index(op.f("ix_catasto_meter_readings_validation_status"), "catasto_meter_readings", ["validation_status"], unique=False)
    op.create_index(op.f("ix_catasto_meter_readings_source"), "catasto_meter_readings", ["source"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_catasto_meter_readings_source"), table_name="catasto_meter_readings")
    op.drop_index(op.f("ix_catasto_meter_readings_validation_status"), table_name="catasto_meter_readings")
    op.drop_index(op.f("ix_catasto_meter_readings_subject_id"), table_name="catasto_meter_readings")
    op.drop_index(op.f("ix_catasto_meter_readings_codice_fiscale_normalizzato"), table_name="catasto_meter_readings")
    op.drop_index(op.f("ix_catasto_meter_readings_codice_fiscale"), table_name="catasto_meter_readings")
    op.drop_index(op.f("ix_catasto_meter_readings_matricola"), table_name="catasto_meter_readings")
    op.drop_index(op.f("ix_catasto_meter_readings_punto_consegna"), table_name="catasto_meter_readings")
    op.drop_index(op.f("ix_catasto_meter_readings_anno"), table_name="catasto_meter_readings")
    op.drop_index(op.f("ix_catasto_meter_readings_distretto_id"), table_name="catasto_meter_readings")
    op.drop_index(op.f("ix_catasto_meter_readings_import_id"), table_name="catasto_meter_readings")
    op.drop_table("catasto_meter_readings")

    op.drop_index(op.f("ix_catasto_meter_reading_imports_stato"), table_name="catasto_meter_reading_imports")
    op.drop_index(op.f("ix_catasto_meter_reading_imports_file_hash"), table_name="catasto_meter_reading_imports")
    op.drop_index(op.f("ix_catasto_meter_reading_imports_anno"), table_name="catasto_meter_reading_imports")
    op.drop_index(op.f("ix_catasto_meter_reading_imports_distretto_id"), table_name="catasto_meter_reading_imports")
    op.drop_table("catasto_meter_reading_imports")
