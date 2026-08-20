"""Persist SISTER request correlation and execution fencing.

Revision ID: 20260820_0900
Revises: 20260810_1700
"""

from alembic import op
import sqlalchemy as sa


revision = "20260820_0900"
down_revision = "20260810_1700"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("catasto_documents", sa.Column("sha256", sa.String(length=64), nullable=True))
    op.add_column("catasto_visure_requests", sa.Column("execution_token", sa.Uuid(), nullable=True))
    op.add_column("catasto_visure_requests", sa.Column("sister_credential_id", sa.Uuid(), nullable=True))
    op.add_column("catasto_visure_requests", sa.Column("sister_remote_request_id", sa.String(length=128), nullable=True))
    op.add_column("catasto_visure_requests", sa.Column("sister_remote_request_url", sa.Text(), nullable=True))
    op.add_column("catasto_visure_requests", sa.Column("sister_remote_state", sa.String(length=32), nullable=True))
    op.add_column("catasto_visure_requests", sa.Column("sister_remote_baseline_keys", sa.JSON(), nullable=True))
    op.add_column("catasto_visure_requests", sa.Column("retry_not_before", sa.DateTime(timezone=True), nullable=True))
    op.add_column("catasto_visure_requests", sa.Column("last_error_code", sa.String(length=64), nullable=True))
    op.create_index(
        "ix_catasto_visure_requests_sister_credential_id",
        "catasto_visure_requests",
        ["sister_credential_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_catasto_visure_requests_sister_credential_id",
        "catasto_visure_requests",
        "catasto_credentials",
        ["sister_credential_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_catasto_visure_requests_sister_remote_request_id",
        "catasto_visure_requests",
        ["sister_remote_request_id"],
        unique=False,
    )
    op.create_index(
        "ix_catasto_visure_requests_sister_remote_state",
        "catasto_visure_requests",
        ["sister_remote_state"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_catasto_visure_requests_sister_remote_state", table_name="catasto_visure_requests")
    op.drop_index("ix_catasto_visure_requests_sister_remote_request_id", table_name="catasto_visure_requests")
    op.drop_constraint(
        "fk_catasto_visure_requests_sister_credential_id",
        "catasto_visure_requests",
        type_="foreignkey",
    )
    op.drop_index("ix_catasto_visure_requests_sister_credential_id", table_name="catasto_visure_requests")
    op.drop_column("catasto_visure_requests", "last_error_code")
    op.drop_column("catasto_visure_requests", "retry_not_before")
    op.drop_column("catasto_visure_requests", "sister_remote_state")
    op.drop_column("catasto_visure_requests", "sister_remote_baseline_keys")
    op.drop_column("catasto_visure_requests", "sister_remote_request_url")
    op.drop_column("catasto_visure_requests", "sister_remote_request_id")
    op.drop_column("catasto_visure_requests", "sister_credential_id")
    op.drop_column("catasto_visure_requests", "execution_token")
    op.drop_column("catasto_documents", "sha256")
