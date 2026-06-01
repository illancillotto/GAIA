from __future__ import annotations

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser


def get_accessi_dashboard_summary_read_model(db: Session, current_user: ApplicationUser) -> dict[str, object]:
    from app.services.audit import get_audit_dashboard_summary

    return get_audit_dashboard_summary(db)


def get_nas_user_read_model(db: Session, current_user: ApplicationUser, username: str) -> dict[str, object] | None:
    from app.services.audit import get_nas_users

    user = next((item for item in get_nas_users(db) if item.username.lower() == username.lower()), None)
    if user is None:
        return None
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "email_domain": user.email.split("@", 1)[1] if user.email and "@" in user.email else None,
        "is_active": user.is_active,
        "last_seen_snapshot_id": user.last_seen_snapshot_id,
    }


def get_share_read_model(db: Session, current_user: ApplicationUser, share_name: str) -> dict[str, object] | None:
    from app.services.audit import get_shares
    from app.models.effective_permission import EffectivePermission
    from app.models.review import Review

    share = next(
        (item for item in get_shares(db) if item.name.lower() == share_name.lower() or item.path.lower().endswith(f"/{share_name.lower()}")),
        None,
    )
    if share is None:
        return None
    permission_row = db.execute(
        select(
            func.count().label("total_permissions"),
            func.coalesce(func.sum(case((EffectivePermission.can_read == True, 1), else_=0)), 0).label("read_count"),
            func.coalesce(func.sum(case((EffectivePermission.can_write == True, 1), else_=0)), 0).label("write_count"),
        ).where(EffectivePermission.share_id == share.id)
    ).one()
    pending_reviews = db.scalar(
        select(func.count()).select_from(Review).where(Review.share_id == share.id, Review.decision == "pending")
    ) or 0
    return {
        "id": share.id,
        "name": share.name,
        "path": share.path,
        "sector": share.sector,
        "last_seen_snapshot_id": share.last_seen_snapshot_id,
        "total_permissions": int(permission_row.total_permissions or 0),
        "read_count": int(permission_row.read_count or 0),
        "write_count": int(permission_row.write_count or 0),
        "pending_reviews": int(pending_reviews),
    }
