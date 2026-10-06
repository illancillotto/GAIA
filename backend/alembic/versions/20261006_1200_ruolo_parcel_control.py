"""Persistent parcel control, independent from historical role records."""

import sqlalchemy as sa
from alembic import op

revision = "20261006_1200"
down_revision = "20261005_1500"
branch_labels = None
depends_on = None


def user_column(name):
    return sa.Column(name, sa.Integer(), sa.ForeignKey("application_users.id"), nullable=False)


def upgrade():
    op.create_table("ruolo_parcel_control_index",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("identity_key", sa.String(64), nullable=False, unique=True),
        sa.Column("label", sa.String(400), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("cf_anomaly", sa.Boolean(), nullable=False),
        sa.Column("current_present", sa.Boolean(), nullable=False),
        sa.Column("original", sa.JSON(), nullable=False))
    for field in ("label", "active", "cf_anomaly", "current_present"):
        op.create_index(f"ix_ruolo_parcel_control_index_{field}", "ruolo_parcel_control_index", [field])
    op.create_table("ruolo_parcel_control_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("current_year", sa.Integer(), nullable=False),
        sa.Column("signatures", sa.JSON(), nullable=False),
        sa.Column("coverage", sa.JSON(), nullable=False),
        sa.Column("refreshed_at", sa.DateTime(timezone=True)), user_column("actor_id"))
    op.create_table("ruolo_parcel_control_cases",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("parcel_id", sa.Uuid(), sa.ForeignKey("ruolo_parcel_control_index.id", ondelete="RESTRICT"), unique=True),
        sa.Column("notice_id", sa.Uuid(), sa.ForeignKey("ruolo_avvisi.id", ondelete="RESTRICT"), unique=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False), user_column("responsible_id"),
        sa.Column("original", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("matches", sa.JSON(), nullable=False),
        sa.Column("parcels", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("(parcel_id IS NOT NULL AND notice_id IS NULL) OR (parcel_id IS NULL AND notice_id IS NOT NULL)", name="ck_parcel_control_case_origin"))
    op.create_index("ix_ruolo_parcel_control_cases_status", "ruolo_parcel_control_cases", ["status"])
    op.create_table("ruolo_parcel_control_proposals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("identity_key", sa.String(64), nullable=False, unique=True),
        sa.Column("case_id", sa.Uuid(), sa.ForeignKey("ruolo_parcel_control_cases.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False))
    op.create_index("ix_ruolo_parcel_control_proposals_case_id", "ruolo_parcel_control_proposals", ["case_id"])
    op.create_index("ix_ruolo_parcel_control_proposals_status", "ruolo_parcel_control_proposals", ["status"])
    op.create_table("ruolo_parcel_control_audit",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("command_id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("case_id", sa.Uuid(), sa.ForeignKey("ruolo_parcel_control_cases.id", ondelete="RESTRICT")),
        user_column("actor_id"), sa.Column("action", sa.String(40), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False), sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_ruolo_parcel_control_audit_case_id", "ruolo_parcel_control_audit", ["case_id"])


def downgrade():
    for name in ("audit", "proposals", "cases", "state", "index"):
        op.drop_table(f"ruolo_parcel_control_{name}")
