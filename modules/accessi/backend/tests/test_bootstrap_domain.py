from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.models.effective_permission import EffectivePermission
from app.models.nas_group import NasGroup
from app.models.nas_user import NasUser
from app.models.permission_entry import PermissionEntry
from app.models.review import Review
from app.models.share import Share
from app.models.snapshot import Snapshot
from app.services.bootstrap_domain import SEED_SNAPSHOT_CHECKSUM, ensure_bootstrap_domain


def test_ensure_bootstrap_domain_creates_seed_once() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        reviewer = ApplicationUser(
            username="reviewer",
            email="reviewer@example.local",
            password_hash=hash_password("secret123"),
            role=ApplicationUserRole.REVIEWER.value,
            is_active=True,
        )
        db.add(reviewer)
        db.commit()
        db.refresh(reviewer)

        first_result = ensure_bootstrap_domain(db, reviewer_user_id=reviewer.id)
        second_result = ensure_bootstrap_domain(db, reviewer_user_id=reviewer.id)

        snapshot = db.scalar(select(Snapshot).where(Snapshot.checksum == SEED_SNAPSHOT_CHECKSUM))
        nas_user_count = db.scalar(select(func.count(NasUser.id)))
        nas_group_count = db.scalar(select(func.count(NasGroup.id)))
        share_count = db.scalar(select(func.count(Share.id)))
        permission_entry_count = db.scalar(select(func.count(PermissionEntry.id)))
        effective_permission_count = db.scalar(select(func.count(EffectivePermission.id)))
        review_count = db.scalar(select(func.count(Review.id)))
    finally:
        db.close()

    assert first_result["snapshot_created"] is True
    assert second_result["snapshot_created"] is False
    assert first_result["snapshot_id"] == second_result["snapshot_id"]
    assert snapshot is not None
    assert nas_user_count == 3
    assert nas_group_count == 3
    assert share_count == 3
    assert permission_entry_count == 5
    assert effective_permission_count == 4
    assert review_count == 2
