"""Audited reconciliation and immutable import conflict decisions.

Revision ID: 20260918_1500
Revises: 20260918_0900
"""

from alembic import op
import sqlalchemy as sa

revision = "20260918_1500"
down_revision = "20260918_0900"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("ruolo_notice_documents") as batch:
        batch.add_column(sa.Column("reconciled_into_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key(
            "fk_notice_document_reconciled", "ruolo_notice_documents",
            ["reconciled_into_id"], ["id"], ondelete="RESTRICT",
        )
        batch.create_check_constraint("ck_notice_document_reconciliation", "reconciled_into_id <> id")
        batch.create_index("ix_ruolo_notice_documents_reconciled_into_id", ["reconciled_into_id"])
    op.add_column("ruolo_notice_import_rows", sa.Column("resolution", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("ruolo_notice_import_rows", "resolution")
    with op.batch_alter_table("ruolo_notice_documents") as batch:
        batch.drop_index("ix_ruolo_notice_documents_reconciled_into_id")
        batch.drop_constraint("ck_notice_document_reconciliation", type_="check")
        batch.drop_constraint("fk_notice_document_reconciled", type_="foreignkey")
        batch.drop_column("reconciled_into_id")
