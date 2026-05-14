"""ruolo: add AdE status scan metadata

Revision ID: 20260514_0078
Revises: 20260513_0077
Create Date: 2026-05-14 09:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260514_0078"
down_revision = "20260513_0077"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "catasto_visure_requests",
        sa.Column("purpose", sa.String(length=40), nullable=False, server_default="visura_pdf"),
    )
    op.add_column("catasto_visure_requests", sa.Column("target_ruolo_particella_id", sa.Uuid(), nullable=True))
    op.create_index(
        op.f("ix_catasto_visure_requests_purpose"),
        "catasto_visure_requests",
        ["purpose"],
        unique=False,
    )
    op.create_index(
        op.f("ix_catasto_visure_requests_target_ruolo_particella_id"),
        "catasto_visure_requests",
        ["target_ruolo_particella_id"],
        unique=False,
    )
    op.add_column("ruolo_particelle", sa.Column("ade_scan_status", sa.String(length=32), nullable=True))
    op.add_column("ruolo_particelle", sa.Column("ade_scan_classification", sa.String(length=32), nullable=True))
    op.add_column("ruolo_particelle", sa.Column("ade_scan_checked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ruolo_particelle", sa.Column("ade_scan_request_id", sa.Uuid(), nullable=True))
    op.add_column("ruolo_particelle", sa.Column("ade_scan_document_id", sa.Uuid(), nullable=True))
    op.add_column("ruolo_particelle", sa.Column("ade_scan_error", sa.Text(), nullable=True))
    op.add_column("ruolo_particelle", sa.Column("ade_scan_payload_json", sa.JSON(), nullable=True))
    op.create_index(op.f("ix_ruolo_particelle_ade_scan_status"), "ruolo_particelle", ["ade_scan_status"])
    op.create_index(
        op.f("ix_ruolo_particelle_ade_scan_classification"),
        "ruolo_particelle",
        ["ade_scan_classification"],
    )
    op.create_index(
        op.f("ix_ruolo_particelle_ade_scan_checked_at"),
        "ruolo_particelle",
        ["ade_scan_checked_at"],
    )
    op.create_index(
        op.f("ix_ruolo_particelle_ade_scan_request_id"),
        "ruolo_particelle",
        ["ade_scan_request_id"],
    )
    op.create_index(
        op.f("ix_ruolo_particelle_ade_scan_document_id"),
        "ruolo_particelle",
        ["ade_scan_document_id"],
    )
    op.create_foreign_key(
        "fk_ruolo_particelle_ade_scan_request_id",
        "ruolo_particelle",
        "catasto_visure_requests",
        ["ade_scan_request_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_ruolo_particelle_ade_scan_document_id",
        "ruolo_particelle",
        "catasto_documents",
        ["ade_scan_document_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_ruolo_particelle_ade_scan_document_id", "ruolo_particelle", type_="foreignkey")
    op.drop_constraint("fk_ruolo_particelle_ade_scan_request_id", "ruolo_particelle", type_="foreignkey")
    op.drop_index(op.f("ix_ruolo_particelle_ade_scan_document_id"), table_name="ruolo_particelle")
    op.drop_index(op.f("ix_ruolo_particelle_ade_scan_request_id"), table_name="ruolo_particelle")
    op.drop_index(op.f("ix_ruolo_particelle_ade_scan_checked_at"), table_name="ruolo_particelle")
    op.drop_index(op.f("ix_ruolo_particelle_ade_scan_classification"), table_name="ruolo_particelle")
    op.drop_index(op.f("ix_ruolo_particelle_ade_scan_status"), table_name="ruolo_particelle")
    op.drop_column("ruolo_particelle", "ade_scan_payload_json")
    op.drop_column("ruolo_particelle", "ade_scan_error")
    op.drop_column("ruolo_particelle", "ade_scan_document_id")
    op.drop_column("ruolo_particelle", "ade_scan_request_id")
    op.drop_column("ruolo_particelle", "ade_scan_checked_at")
    op.drop_column("ruolo_particelle", "ade_scan_classification")
    op.drop_column("ruolo_particelle", "ade_scan_status")

    op.drop_index(op.f("ix_catasto_visure_requests_target_ruolo_particella_id"), table_name="catasto_visure_requests")
    op.drop_index(op.f("ix_catasto_visure_requests_purpose"), table_name="catasto_visure_requests")
    op.drop_column("catasto_visure_requests", "target_ruolo_particella_id")
    op.drop_column("catasto_visure_requests", "purpose")
