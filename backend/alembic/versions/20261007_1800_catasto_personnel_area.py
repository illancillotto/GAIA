"""Allow attested Catasto personnel without altering existing grants."""

import sqlalchemy as sa

from alembic import op

revision = "20261007_1800"
down_revision = "20261007_1600"
branch_labels = None
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
    _replace("'AGRARIO', 'IMPIANTI', 'CATASTO'")


def downgrade():
    for table, _, _ in CONSTRAINTS:
        if (
            op.get_bind()
            .execute(sa.text(f"SELECT count(*) FROM {table} WHERE personnel_area = 'CATASTO'"))
            .scalar_one()
        ):
            raise RuntimeError("Reconcile Catasto personnel areas before downgrade")
    _replace("'AGRARIO', 'IMPIANTI'")
