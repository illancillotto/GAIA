"""Store ownership and cadastral events extracted from historical SISTER visure."""

import sqlalchemy as sa
from alembic import op

revision = "20260923_1100"
down_revision = "20260923_0900"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "catasto_sister_history_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "extraction_id",
            sa.Uuid(),
            sa.ForeignKey("catasto_sister_extractions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_date", sa.Date(), nullable=True),
        sa.Column("act_date", sa.Date(), nullable=True),
        sa.Column("codice_fiscale", sa.String(16), nullable=True),
        sa.Column("denominazione", sa.String(500), nullable=True),
        sa.Column("diritto", sa.String(200), nullable=True),
        sa.Column("quota", sa.String(32), nullable=True),
        sa.Column("act_description", sa.Text(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
    )
    op.create_index("ix_catasto_sister_history_events_extraction_id", "catasto_sister_history_events", ["extraction_id"])
    op.create_index("ix_catasto_sister_history_events_from_date", "catasto_sister_history_events", ["from_date"])
    op.create_index("ix_catasto_sister_history_events_codice_fiscale", "catasto_sister_history_events", ["codice_fiscale"])


def downgrade() -> None:
    op.drop_index("ix_catasto_sister_history_events_codice_fiscale", table_name="catasto_sister_history_events")
    op.drop_index("ix_catasto_sister_history_events_from_date", table_name="catasto_sister_history_events")
    op.drop_index("ix_catasto_sister_history_events_extraction_id", table_name="catasto_sister_history_events")
    op.drop_table("catasto_sister_history_events")
