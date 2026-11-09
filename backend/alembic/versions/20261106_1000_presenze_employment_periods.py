"""Dated employment relationships without changing shift profiles or identities."""

from sqlalchemy import func, inspect, select

from alembic import op
from app.modules.presenze.employment_models import PresenzeEmploymentPeriod

revision = "20261106_1000"
down_revision = "20261104_1400"
branch_labels = None
depends_on = None


def upgrade():
    PresenzeEmploymentPeriod.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    bind = op.get_bind()
    table = PresenzeEmploymentPeriod.__table__
    if table.name in inspect(bind).get_table_names():
        if bind.scalar(select(func.count()).select_from(table)):
            raise RuntimeError("Reconcile employment periods before downgrade")
        table.drop(bind)
