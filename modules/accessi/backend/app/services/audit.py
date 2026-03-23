from sqlalchemy.orm import Session

from app.repositories.audit import (
    get_dashboard_summary,
    list_nas_groups,
    list_nas_users,
    list_reviews,
    list_shares,
    list_sync_runs,
)


def get_audit_dashboard_summary(db: Session) -> dict[str, int]:
    return get_dashboard_summary(db)


def get_nas_users(db: Session):
    return list_nas_users(db)


def get_nas_groups(db: Session):
    return list_nas_groups(db)


def get_shares(db: Session):
    return list_shares(db)


def get_reviews(db: Session):
    return list_reviews(db)


def get_sync_runs(db: Session):
    return list_sync_runs(db)
