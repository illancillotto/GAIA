"""Canonical subject documents linked to registered mail scans."""

import sqlalchemy as sa
from alembic import op

revision = "20261002_1030"
down_revision = "20261001_1600"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ruolo_registered_mail_documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("mail_id", sa.Uuid(), sa.ForeignKey("ruolo_tributi_registered_mails.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("document_id", sa.Uuid(), sa.ForeignKey("ana_documents.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("tracking_number", sa.String(12), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("scanned_on", sa.Date(), nullable=False),
        sa.Column("source_reference", sa.String(1024)),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("application_users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("mail_id", "sha256", name="uq_registered_mail_document_hash"),
        sa.UniqueConstraint("document_id", name="uq_registered_mail_document_document"),
    )
    op.create_index("ix_ruolo_registered_mail_documents_mail_id", "ruolo_registered_mail_documents", ["mail_id"])


def downgrade():
    op.drop_table("ruolo_registered_mail_documents")
