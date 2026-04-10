"""merge alembic heads after operazioni and riordino integration

Revision ID: 20260410_0036
Revises: 20260409_0033, 20260409_0035
Create Date: 2026-04-10
"""

from typing import Sequence, Union


revision: str = "20260410_0036"
down_revision: Union[str, Sequence[str], None] = ("20260409_0033", "20260409_0035")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
