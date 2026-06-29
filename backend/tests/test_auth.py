from datetime import datetime, timezone
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import create_action_token, hash_password
from app.db.base import Base
from app.main import app
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.models.section_permission import Section
from app.models.user_presence import UserPresence


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


def create_viewer_user() -> ApplicationUser:
    db = TestingSessionLocal()
    user = ApplicationUser(
        username="viewer",
        email="viewer@example.local",
        password_hash=hash_password("secret123"),
        role=ApplicationUserRole.VIEWER.value,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def create_accessi_users_section() -> None:
    db = TestingSessionLocal()
    db.add(
        Section(
            module="accessi",
            key="accessi.users",
            label="Utenti GAIA",
            min_role=ApplicationUserRole.ADMIN.value,
            is_active=True,
            sort_order=10,
        )
    )
    db.commit()
    db.close()


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


def test_login_records_access_metadata() -> None:
    create_user()

    response = client.post(
        "/auth/login",
        json={"username": "admin", "password": "secret123"},
    )

    assert response.status_code == 200

    db = TestingSessionLocal()
    user = db.query(ApplicationUser).filter(ApplicationUser.username == "admin").one()
    assert user.login_count == 1
    assert user.last_login_at is not None
    assert user.last_login_ip
    db.close()


def test_login_rejects_invalid_credentials() -> None:
    create_user()

    response = client.post(
        "/auth/login",
        json={"username": "admin", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_login_accepts_email_identifier() -> None:
    create_user()

    response = client.post(
        "/auth/login",
        json={"username": "admin@example.local", "password": "secret123"},
    )

    assert response.status_code == 200
    assert response.json()["access_token"]


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
    assert body["module_utenze"] is False
    assert body["module_operazioni"] is False
    assert body["module_riordino"] is False
    assert body["module_ruolo"] is False
    assert body["module_presenze"] is False
    assert "module_presenze" in body
    assert body["enabled_modules"] == ["accessi"]


def test_me_requires_authentication() -> None:
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_google_callback_issues_token_for_existing_active_user(monkeypatch: pytest.MonkeyPatch) -> None:
    create_user()

    class FakeProfile:
        email = "admin@example.local"
        email_verified = True

    async def fake_exchange_code_for_profile(*, code: str):
        assert code == "google-code"
        return FakeProfile()

    monkeypatch.setattr(
        "app.modules.accessi.routes.auth.exchange_code_for_profile",
        fake_exchange_code_for_profile,
    )

    state = create_action_token("google-oauth", "google_oauth_state", expires_minutes=15)
    response = client.get(
        f"/auth/google/callback?code=google-code&state={state}",
        follow_redirects=False,
    )

    assert response.status_code == 302
    location = response.headers["location"]
    assert "provider=google" in location
    assert "access_token=" in location


def test_presence_heartbeat_upserts_last_route() -> None:
    create_user()
    token = client.post("/auth/login", json={"username": "admin", "password": "secret123"}).json()["access_token"]

    response = client.post(
        "/auth/presence/heartbeat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "path": "/operazioni/attivita",
            "route_label": "Operazioni / Attivita",
            "module_key": "operazioni",
            "action_label": "Apertura lista attivita operative",
            "visible": True,
        },
    )

    assert response.status_code == 200
    db = TestingSessionLocal()
    presence = db.get(UserPresence, 1)
    assert presence is not None
    assert presence.last_path == "/operazioni/attivita"
    assert presence.last_route_label == "Operazioni / Attivita"
    assert presence.last_module_key == "operazioni"
    assert presence.last_action_label == "Apertura lista attivita operative"
    assert presence.last_visible is True
    assert "Operazioni / Attivita" in presence.recent_routes_json
    assert "Apertura lista attivita operative" in presence.recent_actions_json
    db.close()


def test_presence_summary_returns_recent_users_only() -> None:
    create_user()
    create_accessi_users_section()
    token = client.post("/auth/login", json={"username": "admin", "password": "secret123"}).json()["access_token"]

    viewer = create_viewer_user()
    db = TestingSessionLocal()
    db.add(
        UserPresence(
            user_id=1,
            first_seen_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
            last_path="/",
            last_route_label="Home",
            last_module_key="home",
            last_visible=True,
        )
    )
    db.add(
        UserPresence(
            user_id=viewer.id,
            first_seen_at=datetime.now(timezone.utc),
            last_seen_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            last_path="/network",
            last_route_label="Rete",
            last_module_key="rete",
            last_visible=False,
        )
    )
    db.commit()
    db.close()

    response = client.get("/auth/presence/summary?window_minutes=15", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["window_minutes"] == 15
    assert body["active_users"] == 1
    assert body["visible_users"] == 1
    assert [item["username"] for item in body["items"]] == ["admin"]
    assert body["by_module"] == [{"module_key": "home", "count": 1}]


def test_presence_summary_requires_admin_role() -> None:
    create_accessi_users_section()
    create_viewer_user()
    token = client.post("/auth/login", json={"username": "viewer", "password": "secret123"}).json()["access_token"]

    response = client.get("/auth/presence/summary", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
