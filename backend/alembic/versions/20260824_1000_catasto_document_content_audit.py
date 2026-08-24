"""Persist structured AdE document content audit.

Revision ID: 20260824_1000
Revises: 20260824_0900
"""

from alembic import op
import sqlalchemy as sa


revision = "20260824_1000"
down_revision = "20260824_0900"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("catasto_documents", sa.Column("content_request_type", sa.String(length=32), nullable=True))
    op.add_column("catasto_documents", sa.Column("parcel_classification", sa.String(length=32), nullable=True))
    op.add_column("catasto_documents", sa.Column("parcel_suppressed_at", sa.Date(), nullable=True))
    op.add_column("catasto_documents", sa.Column("content_metadata_json", sa.JSON(), nullable=True))
    op.create_index(
        "ix_catasto_documents_content_request_type",
        "catasto_documents",
        ["content_request_type"],
    )
    op.create_index(
        "ix_catasto_documents_parcel_classification",
        "catasto_documents",
        ["parcel_classification"],
    )


def downgrade() -> None:
    op.drop_index("ix_catasto_documents_parcel_classification", table_name="catasto_documents")
    op.drop_index("ix_catasto_documents_content_request_type", table_name="catasto_documents")
    op.drop_column("catasto_documents", "content_metadata_json")
    op.drop_column("catasto_documents", "parcel_suppressed_at")
    op.drop_column("catasto_documents", "parcel_classification")
    op.drop_column("catasto_documents", "content_request_type")
