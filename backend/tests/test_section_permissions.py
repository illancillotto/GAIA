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
from app.models.application_user import ApplicationUser

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
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


def create_user(username: str, role: str) -> ApplicationUser:
    db = TestingSessionLocal()
    user = ApplicationUser(
        username=username,
        email=f"{username}@example.local",
        password_hash=hash_password("secret123"),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def login(username: str) -> str:
    resp = client.post("/auth/login", json={"username": username, "password": "secret123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_super_admin_and_viewer_permission_resolution_sources() -> None:
    create_user("root", "super_admin")
    create_user("bob", "viewer")
    admin_token = login("root")
    viewer_token = login("bob")

    create_section_resp = client.post(
        "/sections",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"module": "accessi", "key": "accessi.dashboard", "label": "Dash", "min_role": "viewer"},
    )
    assert create_section_resp.status_code == 201

    mine_admin = client.get("/auth/my-permissions", headers={"Authorization": f"Bearer {admin_token}"})
    assert mine_admin.status_code == 200
    assert mine_admin.json()["sections"][0]["source"] == "super_admin"

    mine_viewer = client.get("/auth/my-permissions", headers={"Authorization": f"Bearer {viewer_token}"})
    assert mine_viewer.status_code == 200
    assert mine_viewer.json()["sections"][0]["source"] in {"role_default", "min_role"}


def test_super_admin_receives_ruolo_sections_in_my_permissions() -> None:
    create_user("root", "super_admin")
    admin_token = login("root")

    create_section_resp = client.post(
        "/sections",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"module": "ruolo", "key": "ruolo.dashboard", "label": "Ruolo dashboard", "min_role": "viewer"},
    )
    assert create_section_resp.status_code == 201

    mine_admin = client.get("/auth/my-permissions", headers={"Authorization": f"Bearer {admin_token}"})
    assert mine_admin.status_code == 200
    assert "ruolo.dashboard" in mine_admin.json()["granted_keys"]
