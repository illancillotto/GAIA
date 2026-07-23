"""utenze document content classification

Revision ID: 20260723_1600
Revises: 20260723_1100
Create Date: 2026-07-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260723_1600"
down_revision = "20260723_1100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ana_documents", sa.Column("content_classification_status", sa.String(length=32), nullable=False, server_default="not_started"))
    op.add_column("ana_documents", sa.Column("content_category", sa.String(length=64), nullable=True))
    op.add_column("ana_documents", sa.Column("content_category_label", sa.String(length=128), nullable=True))
    op.add_column("ana_documents", sa.Column("content_confidence", sa.Float(), nullable=True))
    op.add_column("ana_documents", sa.Column("content_reason", sa.String(length=512), nullable=True))
    op.add_column("ana_documents", sa.Column("content_excerpt", sa.Text(), nullable=True))
    op.add_column("ana_documents", sa.Column("content_classification_source", sa.String(length=64), nullable=True))
    op.add_column("ana_documents", sa.Column("content_classified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ana_documents", sa.Column("content_classification_error", sa.Text(), nullable=True))
    op.create_index("ix_ana_documents_content_classification_status", "ana_documents", ["content_classification_status"])
    op.create_index("ix_ana_documents_content_category", "ana_documents", ["content_category"])


def downgrade() -> None:
    op.drop_index("ix_ana_documents_content_category", table_name="ana_documents")
    op.drop_index("ix_ana_documents_content_classification_status", table_name="ana_documents")
    op.drop_column("ana_documents", "content_classification_error")
    op.drop_column("ana_documents", "content_classified_at")
    op.drop_column("ana_documents", "content_classification_source")
    op.drop_column("ana_documents", "content_excerpt")
    op.drop_column("ana_documents", "content_reason")
    op.drop_column("ana_documents", "content_confidence")
    op.drop_column("ana_documents", "content_category_label")
    op.drop_column("ana_documents", "content_category")
    op.drop_column("ana_documents", "content_classification_status")
