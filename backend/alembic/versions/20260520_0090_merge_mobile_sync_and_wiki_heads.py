"""merge mobile sync and wiki heads

Revision ID: 20260520_0090
Revises: 20260520_0088, 20260520_0089
Create Date: 2026-05-20
"""

from typing import Sequence, Union


revision: str = "20260520_0090"
down_revision: Union[str, Sequence[str], None] = ("20260520_0088", "20260520_0089")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
