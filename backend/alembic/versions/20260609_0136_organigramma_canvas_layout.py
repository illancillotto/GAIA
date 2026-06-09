"""organigramma canvas layout metadata

Revision ID: 20260609_0136
Revises: 20260608_0135
Create Date: 2026-06-09 19:10:00
"""

from __future__ import annotations

from collections import defaultdict

from alembic import op
import sqlalchemy as sa


revision = "20260609_0136"
down_revision = "20260608_0135"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "org_unit",
        sa.Column("canvas_x", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "org_unit",
        sa.Column("canvas_y", sa.Integer(), nullable=False, server_default="0"),
    )

    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT id, parent_id, sort_order, nome FROM org_unit ORDER BY sort_order, nome")
    ).mappings().all()
    if rows:
        children: dict[str | None, list[dict]] = defaultdict(list)
        for row in rows:
            parent_id = str(row["parent_id"]) if row["parent_id"] is not None else None
            children[parent_id].append(dict(row))

        cursor_by_depth: dict[int, int] = defaultdict(int)
        positions: dict[str, tuple[int, int]] = {}

        def assign(parent_id: str | None, depth: int) -> None:
            for row in children.get(parent_id, []):
                x = 120 + depth * 340
                y = 120 + cursor_by_depth[depth] * 240
                positions[str(row["id"])] = (x, y)
                cursor_by_depth[depth] += 1
                assign(str(row["id"]), depth + 1)

        assign(None, 0)
        for unit_id, (canvas_x, canvas_y) in positions.items():
            connection.execute(
                sa.text(
                    "UPDATE org_unit SET canvas_x = :canvas_x, canvas_y = :canvas_y WHERE id = :unit_id"
                ),
                {"unit_id": unit_id, "canvas_x": canvas_x, "canvas_y": canvas_y},
            )

    op.alter_column("org_unit", "canvas_x", server_default=None)
    op.alter_column("org_unit", "canvas_y", server_default=None)


def downgrade() -> None:
    op.drop_column("org_unit", "canvas_y")
    op.drop_column("org_unit", "canvas_x")
