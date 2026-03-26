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
from app.models.effective_permission import EffectivePermission
from app.models.nas_user import NasUser
from app.models.share import Share
from app.models.snapshot import Snapshot


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

    db = TestingSessionLocal()
    db.add(
        ApplicationUser(
            username="permadmin",
            email="permadmin@example.local",
            password_hash=hash_password("secret123"),
            role=ApplicationUserRole.ADMIN.value,
            is_active=True,
        )
    )
    db.commit()
    db.close()

    yield

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def auth_headers() -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"username": "permadmin", "password": "secret123"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_calculate_preview_requires_authentication() -> None:
    response = client.post("/permissions/calculate-preview", json={"users": [], "permission_entries": []})
    assert response.status_code == 401


def test_calculate_preview_returns_effective_permissions() -> None:
    payload = {
        "users": [{"username": "mrossi", "groups": ["amministrazione"]}],
        "permission_entries": [
            {
                "share_name": "contabilita",
                "subject_type": "group",
                "subject_name": "amministrazione",
                "permission_level": "write",
                "is_deny": False,
            }
        ],
    }

    response = client.post(
        "/permissions/calculate-preview",
        json=payload,
        headers=auth_headers(),
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "username": "mrossi",
            "share_name": "contabilita",
            "can_read": True,
            "can_write": True,
            "is_denied": False,
            "source_summary": "group:amministrazione:write:allow",
        }
    ]


def test_effective_permissions_lists_persisted_records() -> None:
    db = TestingSessionLocal()
    nas_user = NasUser(username="mrossi", is_active=True)
    share = Share(name="contabilita", path="/volume1/contabilita")
    db.add_all([nas_user, share])
    db.commit()
    db.refresh(nas_user)
    db.refresh(share)
    db.add(
        EffectivePermission(
            snapshot_id=None,
            nas_user_id=nas_user.id,
            share_id=share.id,
            can_read=True,
            can_write=False,
            is_denied=False,
            source_summary="seeded",
            details_json=None,
        )
    )
    db.commit()
    db.close()

    response = client.get("/effective-permissions", headers=auth_headers())

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "snapshot_id": None,
            "nas_user_id": 1,
            "share_id": 1,
            "can_read": True,
            "can_write": False,
            "is_denied": False,
            "source_summary": "seeded",
        }
    ]


def test_effective_permissions_returns_only_latest_snapshot_records() -> None:
    db = TestingSessionLocal()
    snapshot_1 = Snapshot(status="completed", checksum="snap-1")
    snapshot_2 = Snapshot(status="completed", checksum="snap-2")
    nas_user = NasUser(username="mrossi", is_active=True)
    share = Share(name="contabilita", path="/volume1/contabilita")
    db.add_all([snapshot_1, snapshot_2, nas_user, share])
    db.commit()
    db.refresh(snapshot_1)
    db.refresh(snapshot_2)
    db.refresh(nas_user)
    db.refresh(share)
    snapshot_2_id = snapshot_2.id
    db.add_all(
        [
            EffectivePermission(
                snapshot_id=snapshot_1.id,
                nas_user_id=nas_user.id,
                share_id=share.id,
                can_read=True,
                can_write=False,
                is_denied=False,
                source_summary="old-snapshot",
                details_json=None,
            ),
            EffectivePermission(
                snapshot_id=snapshot_2.id,
                nas_user_id=nas_user.id,
                share_id=share.id,
                can_read=True,
                can_write=True,
                is_denied=False,
                source_summary="latest-snapshot",
                details_json=None,
            ),
        ]
    )
    db.commit()
    db.close()

    response = client.get("/effective-permissions", headers=auth_headers())

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["snapshot_id"] == snapshot_2_id
    assert response.json()[0]["source_summary"] == "latest-snapshot"
