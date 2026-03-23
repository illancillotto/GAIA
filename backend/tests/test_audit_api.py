from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.models.nas_group import NasGroup
from app.models.nas_user import NasUser
from app.models.review import Review
from app.models.share import Share
from app.models.snapshot import Snapshot
from app.models.sync_run import SyncRun


SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database() -> Generator[None, None, None]:
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def seed_audit_domain() -> str:
    db = TestingSessionLocal()

    app_user = ApplicationUser(
        username="reviewer",
        email="reviewer@example.local",
        password_hash=hash_password("secret123"),
        role=ApplicationUserRole.REVIEWER.value,
        is_active=True,
    )
    snapshot = Snapshot(status="completed", checksum="snap-001")
    nas_user = NasUser(
        username="mrossi",
        full_name="Mario Rossi",
        email="mrossi@example.local",
        source_uid="1001",
        is_active=True,
    )
    nas_group = NasGroup(name="amministrazione", description="Settore amministrativo")
    share = Share(
        name="contabilita",
        path="/volume1/contabilita",
        sector="Amministrazione",
        description="Documenti contabilita",
    )

    db.add_all([app_user, snapshot, nas_user, nas_group, share])
    db.commit()
    db.refresh(app_user)
    db.refresh(snapshot)
    db.refresh(nas_user)
    db.refresh(share)

    review = Review(
        snapshot_id=snapshot.id,
        nas_user_id=nas_user.id,
        share_id=share.id,
        reviewer_user_id=app_user.id,
        decision="approved",
        note="Accesso coerente con il ruolo",
    )
    db.add(review)
    db.add(
        SyncRun(
            snapshot_id=snapshot.id,
            mode="payload",
            trigger_type="api",
            status="succeeded",
            attempts_used=1,
            duration_ms=25,
            initiated_by="reviewer",
            source_label="api:payload",
            error_detail=None,
        )
    )
    db.commit()
    db.close()

    login_response = client.post(
        "/auth/login",
        json={"username": "reviewer", "password": "secret123"},
    )
    return login_response.json()["access_token"]


def test_dashboard_summary_requires_authentication() -> None:
    response = client.get("/dashboard/summary")
    assert response.status_code == 401


def test_dashboard_summary_returns_domain_counts() -> None:
    token = seed_audit_domain()
    response = client.get("/dashboard/summary", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {
        "nas_users": 1,
        "nas_groups": 1,
        "shares": 1,
        "reviews": 1,
        "snapshots": 1,
        "sync_runs": 1,
    }


def test_nas_users_endpoint_returns_ordered_items() -> None:
    token = seed_audit_domain()
    response = client.get("/nas-users", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "username": "mrossi",
            "full_name": "Mario Rossi",
            "email": "mrossi@example.local",
            "source_uid": "1001",
            "is_active": True,
            "last_seen_snapshot_id": None,
        }
    ]


def test_nas_groups_and_shares_endpoints_return_domain_entities() -> None:
    token = seed_audit_domain()

    groups_response = client.get("/nas-groups", headers={"Authorization": f"Bearer {token}"})
    shares_response = client.get("/shares", headers={"Authorization": f"Bearer {token}"})

    assert groups_response.status_code == 200
    assert shares_response.status_code == 200
    assert groups_response.json()[0]["name"] == "amministrazione"
    assert shares_response.json()[0]["name"] == "contabilita"
    assert shares_response.json()[0]["path"] == "/volume1/contabilita"


def test_reviews_endpoint_returns_review_records() -> None:
    token = seed_audit_domain()
    response = client.get("/reviews", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()[0]["decision"] == "approved"
    assert response.json()[0]["reviewer_user_id"] == 1


def test_sync_runs_endpoint_returns_audit_records() -> None:
    token = seed_audit_domain()
    response = client.get("/sync-runs", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()[0]["mode"] == "payload"
    assert response.json()[0]["status"] == "succeeded"
    assert response.json()[0]["duration_ms"] == 25
    assert response.json()[0]["initiated_by"] == "reviewer"
    assert response.json()[0]["source_label"] == "api:payload"
