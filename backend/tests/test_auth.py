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


def create_user() -> ApplicationUser:
    db = TestingSessionLocal()
    user = ApplicationUser(
        username="admin",
        email="admin@example.local",
        password_hash=hash_password("secret123"),
        role=ApplicationUserRole.ADMIN.value,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def test_login_returns_bearer_token() -> None:
    create_user()

    response = client.post(
        "/auth/login",
        json={"username": "admin", "password": "secret123"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]


def test_login_rejects_invalid_credentials() -> None:
    create_user()

    response = client.post(
        "/auth/login",
        json={"username": "admin", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_me_returns_current_user() -> None:
    create_user()
    login_response = client.post(
        "/auth/login",
        json={"username": "admin", "password": "secret123"},
    )
    token = login_response.json()["access_token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == 1
    assert body["username"] == "admin"
    assert body["email"] == "admin@example.local"
    assert body["role"] == "admin"
    assert body["is_active"] is True
    assert body["module_accessi"] is True
    assert body["module_rete"] is False
    assert body["module_inventario"] is False
    assert body["module_catasto"] is False
    assert body["module_anagrafica"] is False
    assert body["enabled_modules"] == ["accessi"]


def test_me_requires_authentication() -> None:
    response = client.get("/auth/me")

    assert response.status_code == 401
