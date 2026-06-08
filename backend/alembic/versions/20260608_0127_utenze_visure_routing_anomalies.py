"""utenze visure routing anomalies

Revision ID: 20260608_0127
Revises: 20260608_0126
Create Date: 2026-06-08 18:40:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260608_0127"
down_revision = "20260608_0126"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ana_visure_routing_anomalies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_path", sa.String(length=1024), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("identifier", sa.String(length=64), nullable=True),
        sa.Column("identifier_kind", sa.String(length=16), nullable=True),
        sa.Column("reason", sa.String(length=64), nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=True),
        sa.Column("occurrences", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_path", name="uq_ana_visure_routing_anomalies_source_path"),
    )
    op.create_index(
        op.f("ix_ana_visure_routing_anomalies_source_path"),
        "ana_visure_routing_anomalies",
        ["source_path"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ana_visure_routing_anomalies_filename"),
        "ana_visure_routing_anomalies",
        ["filename"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ana_visure_routing_anomalies_identifier"),
        "ana_visure_routing_anomalies",
        ["identifier"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ana_visure_routing_anomalies_reason"),
        "ana_visure_routing_anomalies",
        ["reason"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_ana_visure_routing_anomalies_reason"), table_name="ana_visure_routing_anomalies")
    op.drop_index(op.f("ix_ana_visure_routing_anomalies_identifier"), table_name="ana_visure_routing_anomalies")
    op.drop_index(op.f("ix_ana_visure_routing_anomalies_filename"), table_name="ana_visure_routing_anomalies")
    op.drop_index(op.f("ix_ana_visure_routing_anomalies_source_path"), table_name="ana_visure_routing_anomalies")
    op.drop_table("ana_visure_routing_anomalies")
