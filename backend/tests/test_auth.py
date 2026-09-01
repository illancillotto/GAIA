from collections.abc import Generator
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_action_token,
    decode_action_token,
    hash_password,
    verify_password,
)
from app.db.base import Base
from app.main import app
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.models.application_user_password_reset import ApplicationUserPasswordResetToken
from app.models.network import NetworkVpnDevice, NetworkVpnSession
from app.models.section_permission import Section
from app.models.user_presence import UserPresence
from app.modules.accessi.routes import auth as auth_routes

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


def create_super_admin_user() -> ApplicationUser:
    db = TestingSessionLocal()
    user = ApplicationUser(
        username="superadmin",
        email="superadmin@example.local",
        password_hash=hash_password("secret123"),
        role=ApplicationUserRole.SUPER_ADMIN.value,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def create_inactive_user() -> ApplicationUser:
    db = TestingSessionLocal()
    user = ApplicationUser(
        username="inactive",
        email="inactive@example.local",
        password_hash=hash_password("secret123"),
        role=ApplicationUserRole.VIEWER.value,
        is_active=False,
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


def enable_password_reset_email(monkeypatch: pytest.MonkeyPatch, deliveries: list[dict[str, str]]) -> None:
    monkeypatch.setattr(settings, "smtp_enabled", True)
    monkeypatch.setattr(settings, "smtp_username", "smtp-user")
    monkeypatch.setattr(settings, "smtp_password", "smtp-password")
    monkeypatch.setattr(settings, "smtp_from_email", "gaia@example.local")
    monkeypatch.setattr(settings, "password_reset_expire_minutes", 60)
    monkeypatch.setattr(settings, "password_reset_min_interval_minutes", 5)

    def fake_send_email(*, to_email: str, subject: str, text_body: str, html_body: str | None = None) -> None:
        deliveries.append(
            {
                "to_email": to_email,
                "subject": subject,
                "text_body": text_body,
                "html_body": html_body or "",
            }
        )

    monkeypatch.setattr("app.modules.accessi.routes.auth.send_email", fake_send_email)


def extract_reset_token(delivery: dict[str, str]) -> str:
    marker = "/auth/reset-password/"
    assert marker in delivery["text_body"]
    return delivery["text_body"].split(marker, maxsplit=1)[1].split()[0]


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


def test_login_registers_and_reuses_vpn_device() -> None:
    create_user()

    first = client.post(
        "/auth/login",
        json={"username": "admin", "password": "secret123", "device_id": "device-a", "device_label": "Windows"},
        headers={"user-agent": "pytest-browser", "x-forwarded-for": "10.250.10.20"},
    )
    second = client.post(
        "/auth/login",
        json={"username": "admin", "password": "secret123", "device_id": "device-a", "device_label": "Windows"},
        headers={"user-agent": "pytest-browser", "x-forwarded-for": "10.250.10.21"},
    )

    assert first.status_code == 200
    assert second.status_code == 200

    db = TestingSessionLocal()
    devices = db.query(NetworkVpnDevice).all()
    sessions = db.query(NetworkVpnSession).order_by(NetworkVpnSession.id).all()
    assert len(devices) == 1
    assert devices[0].client_device_id == "device-a"
    assert devices[0].display_name == "Windows"
    assert devices[0].last_client_ip == "10.250.10.21"
    assert [session.event_type for session in sessions] == ["login_allowed", "login_allowed"]
    db.close()


def test_login_blocks_eighth_active_vpn_device_for_admin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_user()
    monkeypatch.setattr(settings, "network_vpn_device_enforcement_enabled", True)
    monkeypatch.setattr(settings, "network_vpn_max_active_devices_per_user", 4)

    for index in range(7):
        response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "secret123", "device_id": f"device-{index}"},
            headers={"user-agent": f"pytest-browser-{index}"},
        )
        assert response.status_code == 200

    blocked = client.post(
        "/auth/login",
        json={"username": "admin", "password": "secret123", "device_id": "device-8"},
        headers={"user-agent": "pytest-browser-8"},
    )

    assert blocked.status_code == 403
    assert "Limite dispositivi raggiunto" in blocked.json()["detail"]

    db = TestingSessionLocal()
    assert db.query(NetworkVpnDevice).count() == 7
    blocked_session = db.query(NetworkVpnSession).order_by(NetworkVpnSession.id.desc()).first()
    assert blocked_session is not None
    assert blocked_session.event_type == "login_blocked"
    assert blocked_session.blocked_reason == "max_active_devices:7"
    db.close()


def test_login_blocks_twenty_first_active_vpn_device_for_super_admin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_super_admin_user()
    monkeypatch.setattr(settings, "network_vpn_device_enforcement_enabled", True)

    for index in range(20):
        response = client.post(
            "/auth/login",
            json={
                "username": "superadmin",
                "password": "secret123",
                "device_id": f"superadmin-device-{index}",
            },
        )
        assert response.status_code == 200

    blocked = client.post(
        "/auth/login",
        json={
            "username": "superadmin",
            "password": "secret123",
            "device_id": "superadmin-device-20",
        },
    )

    assert blocked.status_code == 403
    assert "massimo 20 dispositivi attivi" in blocked.json()["detail"]

    db = TestingSessionLocal()
    assert db.query(NetworkVpnDevice).count() == 20
    blocked_session = db.query(NetworkVpnSession).order_by(NetworkVpnSession.id.desc()).first()
    assert blocked_session is not None
    assert blocked_session.blocked_reason == "max_active_devices:20"
    db.close()


def test_login_keeps_four_device_limit_for_non_admin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_viewer_user()
    monkeypatch.setattr(settings, "network_vpn_device_enforcement_enabled", True)
    monkeypatch.setattr(settings, "network_vpn_max_active_devices_per_user", 4)

    for index in range(4):
        response = client.post(
            "/auth/login",
            json={
                "username": "viewer",
                "password": "secret123",
                "device_id": f"viewer-device-{index}",
            },
        )
        assert response.status_code == 200

    blocked = client.post(
        "/auth/login",
        json={
            "username": "viewer",
            "password": "secret123",
            "device_id": "viewer-device-5",
        },
    )

    assert blocked.status_code == 403
    assert "massimo 4 dispositivi attivi" in blocked.json()["detail"]


def test_login_blocks_revoked_vpn_device() -> None:
    create_user()
    first = client.post(
        "/auth/login",
        json={"username": "admin", "password": "secret123", "device_id": "revoked-device"},
    )
    assert first.status_code == 200

    db = TestingSessionLocal()
    device = db.query(NetworkVpnDevice).filter(NetworkVpnDevice.client_device_id == "revoked-device").one()
    device.status = "revoked"
    db.add(device)
    db.commit()
    db.close()

    blocked = client.post(
        "/auth/login",
        json={"username": "admin", "password": "secret123", "device_id": "revoked-device"},
    )

    assert blocked.status_code == 403
    assert "Dispositivo non autorizzato" in blocked.json()["detail"]


def test_login_allows_fifth_device_when_vpn_enforcement_is_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    create_user()
    monkeypatch.setattr(settings, "network_vpn_device_enforcement_enabled", False)
    monkeypatch.setattr(settings, "network_vpn_max_active_devices_per_user", 4)

    for index in range(5):
        response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "secret123", "device_id": f"soft-device-{index}"},
        )
        assert response.status_code == 200

    db = TestingSessionLocal()
    assert db.query(NetworkVpnDevice).count() == 5
    db.close()


def test_login_without_device_id_falls_back_to_user_agent() -> None:
    create_user()

    response = client.post(
        "/auth/login",
        json={"username": "admin", "password": "secret123"},
        headers={"user-agent": ""},
    )

    assert response.status_code == 200
    db = TestingSessionLocal()
    device = db.query(NetworkVpnDevice).one()
    assert device.client_device_id is None
    assert device.user_agent_hash is None
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


def test_password_reset_request_sends_email_and_confirms_once(monkeypatch: pytest.MonkeyPatch) -> None:
    create_user()
    deliveries: list[dict[str, str]] = []
    enable_password_reset_email(monkeypatch, deliveries)

    response = client.post(
        "/auth/password-reset/request",
        json={"identifier": "admin@example.local"},
        headers={"x-forwarded-for": "10.0.0.5, 10.0.0.6", "user-agent": "pytest-agent"},
    )

    assert response.status_code == 200
    assert "Se l'account esiste" in response.json()["message"]
    assert len(deliveries) == 1
    assert deliveries[0]["to_email"] == "admin@example.local"
    assert deliveries[0]["subject"] == "GAIA - Ripristino password"
    reset_token = extract_reset_token(deliveries[0])

    db = TestingSessionLocal()
    stored_token = db.query(ApplicationUserPasswordResetToken).one()
    assert stored_token.token_hash != reset_token
    assert len(stored_token.token_hash) == 64
    assert stored_token.requested_identifier == "admin@example.local"
    assert stored_token.requested_ip == "10.0.0.5"
    assert stored_token.requested_user_agent == "pytest-agent"
    db.close()

    info_response = client.get(f"/auth/password-reset/{reset_token}")
    assert info_response.status_code == 200
    assert info_response.json()["username"] == "admin"
    assert info_response.json()["email"] == "admin@example.local"
    assert info_response.json()["expires_at"].endswith("+00:00")

    short_password_response = client.post(
        f"/auth/password-reset/{reset_token}/confirm",
        json={"password": "short"},
    )
    assert short_password_response.status_code == 422

    confirm_response = client.post(
        f"/auth/password-reset/{reset_token}/confirm",
        json={"password": "new-secret123"},
    )
    assert confirm_response.status_code == 200
    assert confirm_response.json()["username"] == "admin"

    assert client.post("/auth/login", json={"username": "admin", "password": "secret123"}).status_code == 401
    assert client.post("/auth/login", json={"username": "admin", "password": "new-secret123"}).status_code == 200
    assert client.get(f"/auth/password-reset/{reset_token}").status_code == 404
    assert client.post(f"/auth/password-reset/{reset_token}/confirm", json={"password": "another-secret"}).status_code == 404

    db = TestingSessionLocal()
    user = db.query(ApplicationUser).filter(ApplicationUser.username == "admin").one()
    stored_token = db.query(ApplicationUserPasswordResetToken).one()
    assert verify_password("new-secret123", user.password_hash)
    assert stored_token.used_at is not None
    assert stored_token.invalidated_at is not None
    db.close()


def test_password_reset_request_is_generic_for_unknown_or_inactive_user(monkeypatch: pytest.MonkeyPatch) -> None:
    create_inactive_user()
    deliveries: list[dict[str, str]] = []
    enable_password_reset_email(monkeypatch, deliveries)

    unknown_response = client.post("/auth/password-reset/request", json={"identifier": "missing@example.local"})
    inactive_response = client.post("/auth/password-reset/request", json={"identifier": "inactive@example.local"})

    assert unknown_response.status_code == 200
    assert inactive_response.status_code == 200
    assert unknown_response.json() == inactive_response.json()
    assert deliveries == []

    db = TestingSessionLocal()
    assert db.query(ApplicationUserPasswordResetToken).count() == 0
    db.close()


def test_password_reset_request_requires_smtp_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    create_user()
    monkeypatch.setattr(settings, "smtp_enabled", False)

    response = client.post("/auth/password-reset/request", json={"identifier": "admin@example.local"})

    assert response.status_code == 503
    assert response.json()["detail"] == "Servizio ripristino password non configurato"


def test_password_reset_rate_limit_and_new_request_invalidate_previous(monkeypatch: pytest.MonkeyPatch) -> None:
    create_user()
    deliveries: list[dict[str, str]] = []
    enable_password_reset_email(monkeypatch, deliveries)

    first_response = client.post("/auth/password-reset/request", json={"identifier": "admin"})
    second_response = client.post("/auth/password-reset/request", json={"identifier": "admin"})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert len(deliveries) == 1
    first_token = extract_reset_token(deliveries[0])

    monkeypatch.setattr(settings, "password_reset_min_interval_minutes", 0)
    third_response = client.post("/auth/password-reset/request", json={"identifier": "admin"})

    assert third_response.status_code == 200
    assert len(deliveries) == 2
    second_token = extract_reset_token(deliveries[1])
    assert second_token != first_token
    assert client.get(f"/auth/password-reset/{first_token}").status_code == 404
    assert client.get(f"/auth/password-reset/{second_token}").status_code == 200

    db = TestingSessionLocal()
    stored_tokens = db.query(ApplicationUserPasswordResetToken).order_by(ApplicationUserPasswordResetToken.id).all()
    assert len(stored_tokens) == 2
    assert stored_tokens[0].invalidated_at is not None
    assert stored_tokens[1].invalidated_at is None
    db.close()


def test_password_reset_rejects_expired_token(monkeypatch: pytest.MonkeyPatch) -> None:
    create_user()
    deliveries: list[dict[str, str]] = []
    enable_password_reset_email(monkeypatch, deliveries)
    monkeypatch.setattr(settings, "password_reset_expire_minutes", -10)

    response = client.post("/auth/password-reset/request", json={"identifier": "admin"})

    assert response.status_code == 200
    reset_token = extract_reset_token(deliveries[0])
    assert client.get(f"/auth/password-reset/{reset_token}").status_code == 200

    db = TestingSessionLocal()
    stored_token = db.query(ApplicationUserPasswordResetToken).one()
    stored_token.expires_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
    db.add(stored_token)
    db.commit()
    db.close()

    assert client.get(f"/auth/password-reset/{reset_token}").status_code == 404


def test_password_reset_rejects_missing_or_user_invalid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    user = create_user()
    deliveries: list[dict[str, str]] = []
    enable_password_reset_email(monkeypatch, deliveries)

    assert client.get("/auth/password-reset/missing-token").status_code == 404

    response = client.post("/auth/password-reset/request", json={"identifier": "admin"})
    assert response.status_code == 200
    reset_token = extract_reset_token(deliveries[0])

    db = TestingSessionLocal()
    stored_user = db.get(ApplicationUser, user.id)
    assert stored_user is not None
    stored_user.is_active = False
    db.add(stored_user)
    db.commit()
    db.close()

    assert client.get(f"/auth/password-reset/{reset_token}").status_code == 404


def test_auth_internal_datetime_and_redirect_helpers() -> None:
    aware_value = datetime.now(timezone.utc)

    assert auth_routes._as_utc(aware_value) == aware_value
    assert auth_routes._build_frontend_login_redirect().endswith("/login")


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
    assert body["module_gis"] is False
    assert body["module_catasto"] is False
    assert body["module_utenze"] is False
    assert body["module_operazioni"] is False
    assert body["module_riordino"] is False
    assert body["module_ruolo"] is False
    assert body["module_presenze"] is False
    assert "module_gis" in body
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

    state = create_action_token(
        "google-oauth",
        "google_oauth_state",
        expires_minutes=15,
        extra_claims={"device_id": "google-device-1", "device_label": "Chrome Linux"},
    )
    response = client.get(
        f"/auth/google/callback?code=google-code&state={state}",
        follow_redirects=False,
    )

    assert response.status_code == 302
    location = response.headers["location"]
    assert "provider=google" in location
    assert "access_token=" in location
    db = TestingSessionLocal()
    try:
        device = db.query(NetworkVpnDevice).filter(NetworkVpnDevice.client_device_id == "google-device-1").one()
        assert device.display_name == "Chrome Linux"
    finally:
        db.close()


def test_auth_providers_and_google_start(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "google_oauth_enabled", True)
    monkeypatch.setattr(settings, "google_oauth_client_id", "client-id")
    monkeypatch.setattr(settings, "google_oauth_client_secret", "client-secret")
    monkeypatch.setattr(settings, "google_oauth_redirect_uri", "http://backend/auth/google/callback")
    providers_response = client.get("/auth/providers")
    captured_state: dict[str, str] = {}

    def fake_google_authorization_url(*, state: str) -> str:
        captured_state["state"] = state
        return f"https://google.example/auth?state={state}"

    monkeypatch.setattr(
        "app.modules.accessi.routes.auth.build_google_authorization_url",
        fake_google_authorization_url,
    )

    start_response = client.get(
        "/auth/google/start?device_id=browser-1&device_label=Linux%20Chrome",
        follow_redirects=False,
    )

    assert providers_response.status_code == 200
    assert providers_response.json() == {"password": True, "google": True}
    assert start_response.status_code == 302
    assert start_response.headers["location"].startswith("https://google.example/auth?state=")
    state_payload = decode_action_token(captured_state["state"], expected_purpose="google_oauth_state")
    assert state_payload["device_id"] == "browser-1"
    assert state_payload["device_label"] == "Linux Chrome"


def test_google_callback_error_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    denied_response = client.get("/auth/google/callback?error=access_denied", follow_redirects=False)
    missing_response = client.get("/auth/google/callback", follow_redirects=False)
    invalid_state_response = client.get("/auth/google/callback?code=google-code&state=bad-state", follow_redirects=False)

    assert denied_response.status_code == 307
    assert "Google%20access%20denied" in denied_response.headers["location"]
    assert missing_response.status_code == 307
    assert "Risposta%20Google%20non%20valida" in missing_response.headers["location"]
    assert invalid_state_response.status_code == 302
    assert "Sessione%20Google%20non%20valida" in invalid_state_response.headers["location"]

    state = create_action_token("google-oauth", "google_oauth_state", expires_minutes=15)

    class UnverifiedProfile:
        email = "admin@example.local"
        email_verified = False

    async def unverified_profile(*, code: str):
        return UnverifiedProfile()

    monkeypatch.setattr("app.modules.accessi.routes.auth.exchange_code_for_profile", unverified_profile)
    unverified_response = client.get(f"/auth/google/callback?code=google-code&state={state}", follow_redirects=False)
    assert "Google%20email%20is%20not%20verified" in unverified_response.headers["location"]

    class ActiveProfile:
        email = "missing@example.local"
        email_verified = True

    async def missing_profile(*, code: str):
        return ActiveProfile()

    monkeypatch.setattr("app.modules.accessi.routes.auth.exchange_code_for_profile", missing_profile)
    missing_user_response = client.get(f"/auth/google/callback?code=google-code&state={state}", follow_redirects=False)
    assert "Nessun%20account%20GAIA%20attivo" in missing_user_response.headers["location"]

    async def exploding_profile(*, code: str):
        raise RuntimeError("google boom")

    monkeypatch.setattr("app.modules.accessi.routes.auth.exchange_code_for_profile", exploding_profile)
    generic_error_response = client.get(f"/auth/google/callback?code=google-code&state={state}", follow_redirects=False)
    assert "Errore%20durante%20accesso%20Google" in generic_error_response.headers["location"]


def test_user_activation_token_branches() -> None:
    user = create_user()
    token = create_action_token(
        str(user.id),
        "application_user_activation",
        expires_minutes=10,
        extra_claims={
            "email": user.email,
            "pwdv": auth_routes._password_fingerprint(user.password_hash),
        },
    )

    info_response = client.get(f"/auth/user-invite/{token}")
    short_password_response = client.post(f"/auth/user-invite/{token}/activate", json={"password": "short"})
    activate_response = client.post(f"/auth/user-invite/{token}/activate", json={"password": "new-secret123"})
    already_response = client.post(f"/auth/user-invite/{token}/activate", json={"password": "another-secret"})

    assert info_response.status_code == 200
    assert info_response.json()["already_activated"] is False
    assert short_password_response.status_code == 422
    assert activate_response.status_code == 200
    assert already_response.status_code == 409

    invalid_response = client.get("/auth/user-invite/not-a-token")
    assert invalid_response.status_code == 404

    mismatch_token = create_action_token(
        str(user.id),
        "application_user_activation",
        expires_minutes=10,
        extra_claims={"email": "other@example.local", "pwdv": "v"},
    )
    assert client.get(f"/auth/user-invite/{mismatch_token}").status_code == 404


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
