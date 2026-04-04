"""visure request modes and diagnostics

Revision ID: 20260404_0028
Revises: 20260402_0027
Create Date: 2026-04-04 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260404_0028"
down_revision = "20260402_0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "catasto_batches",
        sa.Column("not_found_items", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("catasto_batches", sa.Column("report_json_path", sa.String(length=1024), nullable=True))
    op.add_column("catasto_batches", sa.Column("report_md_path", sa.String(length=1024), nullable=True))

    op.add_column(
        "catasto_visure_requests",
        sa.Column("search_mode", sa.String(length=32), nullable=False, server_default="immobile"),
    )
    op.add_column("catasto_visure_requests", sa.Column("subject_kind", sa.String(length=16), nullable=True))
    op.add_column("catasto_visure_requests", sa.Column("subject_id", sa.String(length=64), nullable=True))
    op.add_column("catasto_visure_requests", sa.Column("request_type", sa.String(length=32), nullable=True))
    op.add_column("catasto_visure_requests", sa.Column("intestazione", sa.String(length=255), nullable=True))
    op.add_column("catasto_visure_requests", sa.Column("artifact_dir", sa.String(length=1024), nullable=True))
    op.create_index("ix_catasto_visure_requests_search_mode", "catasto_visure_requests", ["search_mode"], unique=False)
    op.create_index("ix_catasto_visure_requests_subject_id", "catasto_visure_requests", ["subject_id"], unique=False)

    op.add_column(
        "catasto_documents",
        sa.Column("search_mode", sa.String(length=32), nullable=False, server_default="immobile"),
    )
    op.add_column("catasto_documents", sa.Column("subject_kind", sa.String(length=16), nullable=True))
    op.add_column("catasto_documents", sa.Column("subject_id", sa.String(length=64), nullable=True))
    op.add_column("catasto_documents", sa.Column("request_type", sa.String(length=32), nullable=True))
    op.add_column("catasto_documents", sa.Column("intestazione", sa.String(length=255), nullable=True))
    op.create_index("ix_catasto_documents_subject_id", "catasto_documents", ["subject_id"], unique=False)

    op.alter_column("catasto_visure_requests", "comune", existing_type=sa.String(length=255), nullable=True)
    op.alter_column("catasto_visure_requests", "catasto", existing_type=sa.String(length=64), nullable=True)
    op.alter_column("catasto_visure_requests", "foglio", existing_type=sa.String(length=64), nullable=True)
    op.alter_column("catasto_visure_requests", "particella", existing_type=sa.String(length=64), nullable=True)

    op.alter_column("catasto_documents", "comune", existing_type=sa.String(length=255), nullable=True)
    op.alter_column("catasto_documents", "catasto", existing_type=sa.String(length=64), nullable=True)
    op.alter_column("catasto_documents", "foglio", existing_type=sa.String(length=64), nullable=True)
    op.alter_column("catasto_documents", "particella", existing_type=sa.String(length=64), nullable=True)


def downgrade() -> None:
    op.alter_column("catasto_documents", "particella", existing_type=sa.String(length=64), nullable=False)
    op.alter_column("catasto_documents", "foglio", existing_type=sa.String(length=64), nullable=False)
    op.alter_column("catasto_documents", "catasto", existing_type=sa.String(length=64), nullable=False)
    op.alter_column("catasto_documents", "comune", existing_type=sa.String(length=255), nullable=False)

    op.alter_column("catasto_visure_requests", "particella", existing_type=sa.String(length=64), nullable=False)
    op.alter_column("catasto_visure_requests", "foglio", existing_type=sa.String(length=64), nullable=False)
    op.alter_column("catasto_visure_requests", "catasto", existing_type=sa.String(length=64), nullable=False)
    op.alter_column("catasto_visure_requests", "comune", existing_type=sa.String(length=255), nullable=False)

    op.drop_index("ix_catasto_documents_subject_id", table_name="catasto_documents")
    op.drop_column("catasto_documents", "intestazione")
    op.drop_column("catasto_documents", "request_type")
    op.drop_column("catasto_documents", "subject_id")
    op.drop_column("catasto_documents", "subject_kind")
    op.drop_column("catasto_documents", "search_mode")

    op.drop_index("ix_catasto_visure_requests_subject_id", table_name="catasto_visure_requests")
    op.drop_index("ix_catasto_visure_requests_search_mode", table_name="catasto_visure_requests")
    op.drop_column("catasto_visure_requests", "artifact_dir")
    op.drop_column("catasto_visure_requests", "intestazione")
    op.drop_column("catasto_visure_requests", "request_type")
    op.drop_column("catasto_visure_requests", "subject_id")
    op.drop_column("catasto_visure_requests", "subject_kind")
    op.drop_column("catasto_visure_requests", "search_mode")

    op.drop_column("catasto_batches", "report_md_path")
    op.drop_column("catasto_batches", "report_json_path")
    op.drop_column("catasto_batches", "not_found_items")
