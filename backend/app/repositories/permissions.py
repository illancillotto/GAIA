from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.effective_permission import EffectivePermission


def list_effective_permissions(db: Session) -> list[EffectivePermission]:
    latest_snapshot_id = db.scalar(
        select(func.max(EffectivePermission.snapshot_id)).where(EffectivePermission.snapshot_id.is_not(None))
    )

    statement = select(EffectivePermission)
    if latest_snapshot_id is not None:
        statement = statement.where(EffectivePermission.snapshot_id == latest_snapshot_id)

    statement = statement.order_by(
        EffectivePermission.share_id.asc(),
        EffectivePermission.nas_user_id.asc(),
    )
    return list(db.execute(statement).scalars().all())
