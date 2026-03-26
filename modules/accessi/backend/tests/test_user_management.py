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


def create_user(username: str = "root", role: str = "super_admin") -> ApplicationUser:
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


def login(username: str, password: str = "secret123") -> str:
    resp = client.post("/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_admin_users_lifecycle_and_module_flags() -> None:
    create_user("root", "super_admin")
    token = login("root")

    create_resp = client.post(
        "/admin/users",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "username": "alice",
            "email": "alice@example.local",
            "password": "secret123",
            "role": "viewer",
            "is_active": True,
            "module_accessi": True,
            "module_rete": True,
            "module_inventario": False,
            "module_catasto": True,
        },
    )
    assert create_resp.status_code == 201
    assert create_resp.json()["enabled_modules"] == ["accessi", "rete", "catasto"]

    list_resp = client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 2

    patch_resp = client.patch(
        f"/admin/users/{create_resp.json()['id']}/modules?module_accessi=false&module_rete=false&module_inventario=true&module_catasto=true",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["enabled_modules"] == ["inventario", "catasto"]


def test_viewer_cannot_access_admin_users() -> None:
    create_user("viewer", ApplicationUserRole.VIEWER.value)
    token = login("viewer")
    resp = client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
