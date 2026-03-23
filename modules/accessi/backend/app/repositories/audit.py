from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.nas_group import NasGroup
from app.models.nas_user import NasUser
from app.models.review import Review
from app.models.share import Share
from app.models.snapshot import Snapshot
from app.models.sync_run import SyncRun


def get_dashboard_summary(db: Session) -> dict[str, int]:
    return {
        "nas_users": db.scalar(select(func.count(NasUser.id))) or 0,
        "nas_groups": db.scalar(select(func.count(NasGroup.id))) or 0,
        "shares": db.scalar(select(func.count(Share.id))) or 0,
        "reviews": db.scalar(select(func.count(Review.id))) or 0,
        "snapshots": db.scalar(select(func.count(Snapshot.id))) or 0,
        "sync_runs": db.scalar(select(func.count(SyncRun.id))) or 0,
    }


def list_nas_users(db: Session) -> list[NasUser]:
    statement = select(NasUser).order_by(NasUser.username.asc())
    return list(db.execute(statement).scalars().all())


def list_nas_groups(db: Session) -> list[NasGroup]:
    statement = select(NasGroup).order_by(NasGroup.name.asc())
    return list(db.execute(statement).scalars().all())


def list_shares(db: Session) -> list[Share]:
    statement = select(Share).order_by(Share.name.asc())
    return list(db.execute(statement).scalars().all())


def list_reviews(db: Session) -> list[Review]:
    statement = select(Review).order_by(Review.reviewed_at.desc(), Review.id.desc())
    return list(db.execute(statement).scalars().all())


def list_sync_runs(db: Session) -> list[SyncRun]:
    statement = select(SyncRun).order_by(SyncRun.completed_at.desc(), SyncRun.id.desc())
    return list(db.execute(statement).scalars().all())
