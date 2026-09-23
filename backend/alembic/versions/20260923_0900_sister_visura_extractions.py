"""Persist parsed SISTER visura snapshots and owners."""

import sqlalchemy as sa
from alembic import op

revision = "20260923_0900"
down_revision = "20260922_1000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "catasto_sister_extractions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("catasto_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parser_version", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("pdf_sha256", sa.String(64), nullable=False),
        sa.Column("observed_at", sa.Date(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("document_id", name="uq_catasto_sister_extractions_document"),
    )
    op.create_index("ix_catasto_sister_extractions_document_id", "catasto_sister_extractions", ["document_id"])
    op.create_index("ix_catasto_sister_extractions_status", "catasto_sister_extractions", ["status"])
    op.create_index("ix_catasto_sister_extractions_pdf_sha256", "catasto_sister_extractions", ["pdf_sha256"])
    op.create_index("ix_catasto_sister_extractions_observed_at", "catasto_sister_extractions", ["observed_at"])
    op.create_table(
        "catasto_sister_parcels",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("extraction_id", sa.Uuid(), sa.ForeignKey("catasto_sister_extractions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cat_particella_id", sa.Uuid(), sa.ForeignKey("cat_particelle.id", ondelete="SET NULL"), nullable=True),
        sa.Column("comune_nome", sa.String(100), nullable=True),
        sa.Column("comune_codice", sa.String(10), nullable=True),
        sa.Column("foglio", sa.String(20), nullable=True),
        sa.Column("particella", sa.String(30), nullable=True),
        sa.Column("subalterno", sa.String(20), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
    )
    op.create_index("ix_catasto_sister_parcels_extraction_id", "catasto_sister_parcels", ["extraction_id"])
    op.create_index("ix_catasto_sister_parcels_cat_particella_id", "catasto_sister_parcels", ["cat_particella_id"])
    op.create_index("ix_catasto_sister_parcels_comune_codice", "catasto_sister_parcels", ["comune_codice"])
    op.create_table(
        "catasto_sister_owners",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("sister_parcel_id", sa.Uuid(), sa.ForeignKey("catasto_sister_parcels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cat_intestatario_id", sa.Uuid(), sa.ForeignKey("cat_intestatari.id", ondelete="SET NULL"), nullable=True),
        sa.Column("codice_fiscale", sa.String(16), nullable=True),
        sa.Column("denominazione", sa.String(500), nullable=True),
        sa.Column("cognome", sa.String(150), nullable=True),
        sa.Column("nome", sa.String(150), nullable=True),
        sa.Column("data_nascita", sa.Date(), nullable=True),
        sa.Column("luogo_nascita", sa.String(200), nullable=True),
        sa.Column("diritto", sa.String(200), nullable=True),
        sa.Column("quota", sa.String(32), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
    )
    op.create_index("ix_catasto_sister_owners_sister_parcel_id", "catasto_sister_owners", ["sister_parcel_id"])
    op.create_index("ix_catasto_sister_owners_cat_intestatario_id", "catasto_sister_owners", ["cat_intestatario_id"])
    op.create_index("ix_catasto_sister_owners_codice_fiscale", "catasto_sister_owners", ["codice_fiscale"])


def downgrade() -> None:
    op.drop_index("ix_catasto_sister_owners_codice_fiscale", table_name="catasto_sister_owners")
    op.drop_index("ix_catasto_sister_owners_cat_intestatario_id", table_name="catasto_sister_owners")
    op.drop_index("ix_catasto_sister_owners_sister_parcel_id", table_name="catasto_sister_owners")
    op.drop_table("catasto_sister_owners")
    op.drop_index("ix_catasto_sister_parcels_comune_codice", table_name="catasto_sister_parcels")
    op.drop_index("ix_catasto_sister_parcels_cat_particella_id", table_name="catasto_sister_parcels")
    op.drop_index("ix_catasto_sister_parcels_extraction_id", table_name="catasto_sister_parcels")
    op.drop_table("catasto_sister_parcels")
    op.drop_index("ix_catasto_sister_extractions_observed_at", table_name="catasto_sister_extractions")
    op.drop_index("ix_catasto_sister_extractions_pdf_sha256", table_name="catasto_sister_extractions")
    op.drop_index("ix_catasto_sister_extractions_status", table_name="catasto_sister_extractions")
    op.drop_index("ix_catasto_sister_extractions_document_id", table_name="catasto_sister_extractions")
    op.drop_table("catasto_sister_extractions")
