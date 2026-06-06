"""add wiki telemetry metric tables

Revision ID: 20260606_0121
Revises: 20260605_0120
Create Date: 2026-06-06 08:23:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260606_0121"
down_revision: str | Sequence[str] | None = "20260605_0120"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True) if op.get_bind().dialect.name == "postgresql" else sa.String(length=36)

    op.create_table(
        "wiki_telemetry_daily_metrics",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("dimension_type", sa.String(length=32), nullable=False),
        sa.Column("dimension_key", sa.String(length=256), nullable=True),
        sa.Column("total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("denied_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("no_match_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("docs_only_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("live_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("logic_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hybrid_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("metric_date", "dimension_type", "dimension_key", name="uq_wiki_telemetry_daily_dimension"),
    )
    op.create_index("ix_wiki_telemetry_daily_metrics_id", "wiki_telemetry_daily_metrics", ["id"], unique=False)
    op.create_index(
        "ix_wiki_telemetry_daily_metrics_metric_date",
        "wiki_telemetry_daily_metrics",
        ["metric_date"],
        unique=False,
    )
    op.create_index(
        "ix_wiki_telemetry_daily_metrics_dimension_type",
        "wiki_telemetry_daily_metrics",
        ["dimension_type"],
        unique=False,
    )
    op.create_index(
        "ix_wiki_telemetry_daily_metrics_dimension_key",
        "wiki_telemetry_daily_metrics",
        ["dimension_key"],
        unique=False,
    )

    op.create_table(
        "wiki_telemetry_period_metrics",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("period_type", sa.String(length=16), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("dimension_type", sa.String(length=32), nullable=False),
        sa.Column("dimension_key", sa.String(length=256), nullable=True),
        sa.Column("total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("denied_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("no_match_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("docs_only_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("live_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("logic_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hybrid_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "period_type",
            "period_start",
            "dimension_type",
            "dimension_key",
            name="uq_wiki_telemetry_period_dimension",
        ),
    )
    op.create_index("ix_wiki_telemetry_period_metrics_id", "wiki_telemetry_period_metrics", ["id"], unique=False)
    op.create_index(
        "ix_wiki_telemetry_period_metrics_period_type",
        "wiki_telemetry_period_metrics",
        ["period_type"],
        unique=False,
    )
    op.create_index(
        "ix_wiki_telemetry_period_metrics_period_start",
        "wiki_telemetry_period_metrics",
        ["period_start"],
        unique=False,
    )
    op.create_index(
        "ix_wiki_telemetry_period_metrics_dimension_type",
        "wiki_telemetry_period_metrics",
        ["dimension_type"],
        unique=False,
    )
    op.create_index(
        "ix_wiki_telemetry_period_metrics_dimension_key",
        "wiki_telemetry_period_metrics",
        ["dimension_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_wiki_telemetry_period_metrics_dimension_key", table_name="wiki_telemetry_period_metrics")
    op.drop_index("ix_wiki_telemetry_period_metrics_dimension_type", table_name="wiki_telemetry_period_metrics")
    op.drop_index("ix_wiki_telemetry_period_metrics_period_start", table_name="wiki_telemetry_period_metrics")
    op.drop_index("ix_wiki_telemetry_period_metrics_period_type", table_name="wiki_telemetry_period_metrics")
    op.drop_index("ix_wiki_telemetry_period_metrics_id", table_name="wiki_telemetry_period_metrics")
    op.drop_table("wiki_telemetry_period_metrics")

    op.drop_index("ix_wiki_telemetry_daily_metrics_dimension_key", table_name="wiki_telemetry_daily_metrics")
    op.drop_index("ix_wiki_telemetry_daily_metrics_dimension_type", table_name="wiki_telemetry_daily_metrics")
    op.drop_index("ix_wiki_telemetry_daily_metrics_metric_date", table_name="wiki_telemetry_daily_metrics")
    op.drop_index("ix_wiki_telemetry_daily_metrics_id", table_name="wiki_telemetry_daily_metrics")
    op.drop_table("wiki_telemetry_daily_metrics")
