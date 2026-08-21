"""wiki mcp synthetic and docs schemas

Revision ID: 20260817_0200
Revises: 20260807_1200
Create Date: 2026-08-17
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260817_0200"
down_revision = "20260807_1200"
branch_labels = None
depends_on = None


def _uuid():
    return postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS mcp_synthetic")
    op.execute("CREATE SCHEMA IF NOT EXISTS mcp_docs")
    op.create_table(
        "dataset_versions",
        sa.Column("id", _uuid(), primary_key=True),
        sa.Column("dataset_version", sa.String(80), nullable=False, unique=True),
        sa.Column("seed", sa.String(120), nullable=False),
        sa.Column("generator_version", sa.String(40), nullable=False),
        sa.Column("schema_version", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema="mcp_synthetic",
    )
    for name, cols in {
        "subjects": [sa.Column("subject_type", sa.String(20), nullable=False), sa.Column("display_name", sa.String(200), nullable=False), sa.Column("synthetic_tax_id", sa.String(32), nullable=False), sa.Column("status", sa.String(30), nullable=False)],
        "municipalities": [sa.Column("name", sa.String(120), nullable=False), sa.Column("cadastral_code", sa.String(10), nullable=False)],
        "districts": [sa.Column("district_code", sa.String(20), nullable=False), sa.Column("name", sa.String(120), nullable=False)],
    }.items():
        op.create_table(name, sa.Column("id", _uuid(), primary_key=True), sa.Column("dataset_version", sa.String(80), nullable=False), *cols, schema="mcp_synthetic")
    op.create_table("parcels", sa.Column("id", _uuid(), primary_key=True), sa.Column("dataset_version", sa.String(80), nullable=False), sa.Column("municipality_id", _uuid(), nullable=False), sa.Column("district_code", sa.String(20)), sa.Column("sheet", sa.String(20), nullable=False), sa.Column("parcel_number", sa.String(40), nullable=False), sa.Column("subaltern", sa.String(20)), sa.Column("surface_m2", sa.Integer(), nullable=False), sa.Column("irrigable_surface_m2", sa.Integer()), sa.Column("is_current", sa.Boolean(), nullable=False), sa.Column("match_note", sa.String(120)), schema="mcp_synthetic")
    op.create_table("irrigation_accounts", sa.Column("id", _uuid(), primary_key=True), sa.Column("dataset_version", sa.String(80), nullable=False), sa.Column("account_code", sa.String(40), nullable=False), sa.Column("campaign_year", sa.Integer(), nullable=False), sa.Column("subject_label_raw", sa.String(200), nullable=False), sa.Column("amount_0648", sa.Numeric(12,2), nullable=False), sa.Column("amount_0985", sa.Numeric(12,2), nullable=False), sa.Column("note", sa.String(200)), schema="mcp_synthetic")
    op.create_table("subject_account_links", sa.Column("id", _uuid(), primary_key=True), sa.Column("dataset_version", sa.String(80), nullable=False), sa.Column("subject_id", _uuid(), nullable=False), sa.Column("account_id", _uuid(), nullable=False), sa.Column("relationship_type", sa.String(40), nullable=False), sa.Column("share_percent", sa.Numeric(5,2)), sa.UniqueConstraint("subject_id", "account_id", name="uq_mcp_subject_account"), schema="mcp_synthetic")
    op.create_table("account_parcel_links", sa.Column("id", _uuid(), primary_key=True), sa.Column("dataset_version", sa.String(80), nullable=False), sa.Column("account_id", _uuid(), nullable=False), sa.Column("parcel_id", _uuid(), nullable=False), sa.Column("link_status", sa.String(40), nullable=False), sa.UniqueConstraint("account_id", "parcel_id", name="uq_mcp_account_parcel"), schema="mcp_synthetic")
    op.create_table("role_notices", sa.Column("id", _uuid(), primary_key=True), sa.Column("dataset_version", sa.String(80), nullable=False), sa.Column("notice_code", sa.String(60), nullable=False), sa.Column("tax_year", sa.Integer(), nullable=False), sa.Column("subject_id", _uuid()), sa.Column("debtor_name_raw", sa.String(200), nullable=False), sa.Column("total_amount", sa.Numeric(12,2), nullable=False), sa.Column("workflow_status", sa.String(40)), schema="mcp_synthetic")
    op.create_table("role_items", sa.Column("id", _uuid(), primary_key=True), sa.Column("dataset_version", sa.String(80), nullable=False), sa.Column("notice_id", _uuid(), nullable=False), sa.Column("item_code", sa.String(60), nullable=False), sa.Column("parcel_id", _uuid()), sa.Column("description", sa.Text(), nullable=False), sa.Column("amount", sa.Numeric(12,2), nullable=False), schema="mcp_synthetic")
    op.create_table("role_payments", sa.Column("id", _uuid(), primary_key=True), sa.Column("dataset_version", sa.String(80), nullable=False), sa.Column("notice_id", _uuid(), nullable=False), sa.Column("payment_reference", sa.String(80), nullable=False), sa.Column("amount", sa.Numeric(12,2), nullable=False), sa.Column("paid_at", sa.DateTime(timezone=True)), sa.Column("status", sa.String(30), nullable=False), schema="mcp_synthetic")
    op.create_table("corpora", sa.Column("id", _uuid(), primary_key=True), sa.Column("corpus_version", sa.String(80), nullable=False, unique=True), sa.Column("status", sa.String(30), nullable=False), sa.Column("manifest_hash", sa.String(80), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), schema="mcp_docs")
    op.create_table("documents", sa.Column("id", _uuid(), primary_key=True), sa.Column("corpus_version", sa.String(80), nullable=False), sa.Column("path", sa.String(600), nullable=False), sa.Column("document_hash", sa.String(80), nullable=False), sa.Column("domain", sa.String(80), nullable=False), sa.Column("category", sa.String(80), nullable=False), sa.Column("status", sa.String(30), nullable=False), sa.Column("decision", sa.String(30), nullable=False), sa.Column("reason", sa.Text(), nullable=False), sa.Column("title", sa.String(300), nullable=False), schema="mcp_docs")
    op.create_table("chunks", sa.Column("id", _uuid(), primary_key=True), sa.Column("corpus_version", sa.String(80), nullable=False), sa.Column("document_id", _uuid(), nullable=False), sa.Column("path", sa.String(600), nullable=False), sa.Column("chunk_index", sa.Integer(), nullable=False), sa.Column("section_title", sa.String(300)), sa.Column("content", sa.Text(), nullable=False), sa.Column("token_count", sa.Integer(), nullable=False), sa.Column("search_text", sa.Text(), nullable=False), schema="mcp_docs")


def downgrade() -> None:
    for schema, tables in [("mcp_docs", ["chunks", "documents", "corpora"]), ("mcp_synthetic", ["role_payments", "role_items", "role_notices", "account_parcel_links", "subject_account_links", "irrigation_accounts", "parcels", "districts", "municipalities", "subjects", "dataset_versions"] )]:
        for table in tables:
            op.drop_table(table, schema=schema)
        op.execute(f"DROP SCHEMA IF EXISTS {schema}")
