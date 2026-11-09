"""Daily inCASS snapshot journal and outbox; independent additive branch.

Deliberately branches from the last committed head: concurrent uncommitted
Presenze migrations are not dependencies of this feature. Upgrade with
`alembic upgrade incass_incremental@head` or `alembic upgrade heads`.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261109_1000"
down_revision = "20261103_1200"
branch_labels = ("incass_incremental",)
depends_on = None


def upgrade():
    op.create_table(
        "incass_incremental_cycles",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer, nullable=False),
        sa.Column("expected", sa.JSON, nullable=False),
        sa.Column("artifacts", sa.JSON, nullable=False),
        sa.Column("report", sa.JSON, nullable=False),
        sa.Column("rows", sa.JSON, nullable=False),
    )
    op.create_table(
        "incass_incremental_head",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("cycle_id", sa.String(64), sa.ForeignKey("incass_incremental_cycles.id")),
        sa.Column("full_audit_at", sa.DateTime(timezone=True)),
    )
    op.execute(sa.text("INSERT INTO incass_incremental_head (id) VALUES (1)"))
    op.create_table(
        "incass_incremental_changes",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("cycle_id", sa.String(64), sa.ForeignKey("incass_incremental_cycles.id"), nullable=False),
        sa.Column("notice_key", sa.String(128), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer, nullable=False),
        sa.Column("old", sa.JSON),
        sa.Column("new", sa.JSON),
        sa.Column("fields", sa.JSON, nullable=False),
        sa.Column("result", sa.JSON, nullable=False),
    )
    for column in ("cycle_id", "notice_key"):
        op.create_index(f"ix_incass_incremental_changes_{column}", "incass_incremental_changes", [column])


def downgrade():
    op.drop_table("incass_incremental_changes")
    op.drop_table("incass_incremental_head")
    op.drop_table("incass_incremental_cycles")
