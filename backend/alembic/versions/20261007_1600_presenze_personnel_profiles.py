"""Persist dated personnel attestations independently of INAZ imports."""

from alembic import op

from app.modules.presenze.personnel_profile_models import PresenzePersonnelProfile

revision = "20261007_1600"
down_revision = "20261006_1200"
branch_labels = None
depends_on = None


def upgrade():
    PresenzePersonnelProfile.__table__.create(op.get_bind(), checkfirst=True)
    with op.batch_alter_table("presenze_shift_assignments") as batch:
        batch.drop_constraint("ck_shift_assignment_type", type_="check")
        batch.create_check_constraint("ck_shift_assignment_type", "shift_worker_type IN ('none', 'acquaiolo', 'telecontrollo', 'tecnico_turnista')")


def downgrade():
    from sqlalchemy import text
    if op.get_bind().execute(text("SELECT count(*) FROM presenze_shift_assignments WHERE shift_worker_type = 'tecnico_turnista'")).scalar_one():
        raise RuntimeError("Reconcile technician shift assignments before downgrade")
    with op.batch_alter_table("presenze_shift_assignments") as batch:
        batch.drop_constraint("ck_shift_assignment_type", type_="check")
        batch.create_check_constraint("ck_shift_assignment_type", "shift_worker_type IN ('none', 'acquaiolo', 'telecontrollo')")
    PresenzePersonnelProfile.__table__.drop(op.get_bind())
