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

    db = TestingSessionLocal()
    db.add(
        ApplicationUser(
            username="syncadmin",
            email="syncadmin@example.local",
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
    login_response = client.post(
        "/auth/login",
        json={"username": "syncadmin", "password": "secret123"},
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_sync_capabilities_requires_authentication() -> None:
    response = client.get("/sync/capabilities")
    assert response.status_code == 401


def test_sync_capabilities_returns_configured_connector_info() -> None:
    response = client.get("/sync/capabilities", headers=auth_headers())

    assert response.status_code == 200
    assert response.json()["ssh_configured"] is True
    assert response.json()["supports_live_sync"] is False
    assert response.json()["host"] == "nas.internal.local"


def test_sync_preview_parses_inline_samples() -> None:
    payload = {
        "passwd_text": "mrossi:x:1001:100:Mario Rossi:/var/services/homes/mrossi:/sbin/nologin\n",
        "group_text": "amministrazione:x:2001:mrossi\n",
        "shares_text": "contabilita\n",
        "acl_texts": ["allow: group:amministrazione:read,write\ndeny: user:ospite:read\n"],
    }

    response = client.post("/sync/preview", json=payload, headers=auth_headers())

    assert response.status_code == 200
    body = response.json()
    assert body["users"][0]["username"] == "mrossi"
    assert body["groups"][0]["name"] == "amministrazione"
    assert body["shares"][0]["name"] == "contabilita"
    assert body["acl_entries"][1]["effect"] == "deny"
