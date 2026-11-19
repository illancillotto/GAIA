"""Allow dated Adduttore shift assignments."""

import sqlalchemy as sa

from alembic import op

revision = "20261119_1600"
down_revision = "20261119_1200"
branch_labels = None
depends_on = None


def _set_types(types):
    with op.batch_alter_table("presenze_shift_assignments") as batch:
        batch.drop_constraint("ck_shift_assignment_type", type_="check")
        batch.create_check_constraint("ck_shift_assignment_type", f"shift_worker_type IN ({types})")


def upgrade():
    _set_types("'none', 'acquaiolo', 'adduttore', 'telecontrollo', 'tecnico_turnista'")


def downgrade():
    exists = op.get_bind().scalar(
        sa.text(
            "SELECT 1 FROM presenze_shift_assignments WHERE shift_worker_type = 'adduttore' LIMIT 1"
        )
    )
    if exists:
        raise RuntimeError("Reconcile Adduttore shift assignments before downgrade")
    _set_types("'none', 'acquaiolo', 'telecontrollo', 'tecnico_turnista'")
