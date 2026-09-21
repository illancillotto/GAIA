"""Immutable source snapshots for the operational notice register."""

import sqlalchemy as sa
from alembic import op

revision = "20260918_0900"
down_revision = "20260917_0900"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ruolo_notice_import_batches",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("digest", sa.String(64), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("parser_version", sa.String(40), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column(
            "actor_id",
            sa.Integer(),
            sa.ForeignKey("application_users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "confirmed_by", sa.Integer(), sa.ForeignKey("application_users.id", ondelete="RESTRICT")
        ),
        sa.Column("reason", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("source", "digest", name="uq_notice_import_digest"),
    )
    op.create_table(
        "ruolo_notice_import_rows",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "batch_id",
            sa.Uuid(),
            sa.ForeignKey("ruolo_notice_import_batches.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("source_key", sa.String(200), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("anomalies", sa.JSON(), nullable=False),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column(
            "document_id",
            sa.Uuid(),
            sa.ForeignKey("ruolo_notice_documents.id", ondelete="RESTRICT"),
        ),
        sa.UniqueConstraint("batch_id", "row_number", name="uq_notice_import_row"),
    )
    op.create_index(
        "ix_ruolo_notice_import_rows_batch_id", "ruolo_notice_import_rows", ["batch_id"]
    )


def downgrade():
    op.drop_table("ruolo_notice_import_rows")
    op.drop_table("ruolo_notice_import_batches")
