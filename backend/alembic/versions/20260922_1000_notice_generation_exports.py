"""Persist immutable notice exports and individual delivery claims."""

import sqlalchemy as sa
from alembic import op

revision = "20260922_1000"
down_revision = "20260922_0900"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ruolo_notice_generation_exports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("confirmation_id", sa.Uuid(), sa.ForeignKey("ruolo_notice_generation_confirmations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("manifest", sa.JSON(), nullable=False),
        sa.Column("artifact", sa.LargeBinary(), nullable=False),
        sa.Column("artifact_sha256", sa.String(64), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("application_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("confirmation_id"),
    )
    op.create_table(
        "ruolo_notice_export_claims",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("export_id", sa.Uuid(), sa.ForeignKey("ruolo_notice_generation_exports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("application_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ruolo_notice_export_claims_export_id", "ruolo_notice_export_claims", ["export_id"])
    op.create_table(
        "ruolo_notice_export_identities",
        sa.Column("identity_key", sa.String(64), primary_key=True),
        sa.Column("export_id", sa.Uuid(), sa.ForeignKey("ruolo_notice_generation_exports.id", ondelete="RESTRICT"), nullable=False),
    )
    op.create_index("ix_ruolo_notice_export_identities_export_id", "ruolo_notice_export_identities", ["export_id"])


def downgrade():
    op.drop_index("ix_ruolo_notice_export_identities_export_id", table_name="ruolo_notice_export_identities")
    op.drop_table("ruolo_notice_export_identities")
    op.drop_index("ix_ruolo_notice_export_claims_export_id", table_name="ruolo_notice_export_claims")
    op.drop_table("ruolo_notice_export_claims")
    op.drop_table("ruolo_notice_generation_exports")
