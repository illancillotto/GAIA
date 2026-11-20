"""Add the administrative area on the deployed Presenze revision.

This migration can be applied independently of the Adduttore shift rollout.
"""

import sqlalchemy as sa

from alembic import op

revision = "20261120_1200"
down_revision = "20261119_1200"
branch_labels = ("amministrativa_personnel",)
depends_on = None

CONSTRAINTS = (
    ("wc_operator", "ck_wc_operator_personnel_area", True),
    ("organization_teams", "ck_organization_teams_personnel_area", False),
    ("presenze_personnel_profiles", "ck_personnel_profile_area", False),
)


def _replace(areas):
    for table, constraint, nullable in CONSTRAINTS:
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(constraint, type_="check")
            condition = f"personnel_area IN ({areas})"
            if nullable:
                condition = "personnel_area IS NULL OR " + condition
            batch.create_check_constraint(constraint, condition)


def upgrade():
    _replace("'AGRARIO', 'IMPIANTI', 'CATASTO', 'AMMINISTRATIVA'")


def downgrade():
    for table, _, _ in CONSTRAINTS:
        if (
            op.get_bind()
            .execute(
                sa.text(f"SELECT count(*) FROM {table} WHERE personnel_area = 'AMMINISTRATIVA'")
            )
            .scalar_one()
        ):
            raise RuntimeError("Reconcile Amministrativa personnel areas before downgrade")
    _replace("'AGRARIO', 'IMPIANTI', 'CATASTO'")
