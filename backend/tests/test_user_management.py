from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.operazioni.models.wc_operator import WCOperator
from app.modules.accessi.routes.admin_users import _build_gate_mobile_console_map
from app.repositories.application_user import (
    delete_application_user,
    get_application_user_by_login_identifier,
    list_application_users,
    update_application_user,
)
from app.schemas.users import ApplicationUserCreate, ApplicationUserUpdate

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


def super_admin_modules() -> list[str]:
    return ["accessi", "rete", "inventario", "gis", "catasto", "utenze", "operazioni", "riordino", "ruolo", "presenze", "organigramma"]


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
            "full_name": "Alice Example",
            "office_location": "Ufficio protocollo",
            "phone_extension": "245",
            "password": "secret123",
            "role": "viewer",
            "is_active": True,
            "module_accessi": True,
            "module_rete": True,
            "module_inventario": False,
            "module_gis": True,
            "module_catasto": True,
            "module_utenze": True,
            "module_ruolo": False,
            "module_presenze": True,
        },
    )
    assert create_resp.status_code == 201
    assert create_resp.json()["full_name"] == "Alice Example"
    assert create_resp.json()["phone_extension"] == "245"
    assert create_resp.json()["module_gis"] is True
    assert create_resp.json()["module_presenze"] is True
    assert create_resp.json()["enabled_modules"] == ["accessi", "rete", "gis", "catasto", "utenze", "presenze"]

    list_resp = client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 2

    patch_resp = client.patch(
        f"/admin/users/{create_resp.json()['id']}/modules?module_accessi=false&module_rete=false&module_inventario=true&module_gis=false&module_catasto=true&module_utenze=true&module_operazioni=false&module_riordino=false&module_ruolo=true&module_presenze=true",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["module_gis"] is False
    assert patch_resp.json()["module_presenze"] is True
    assert patch_resp.json()["enabled_modules"] == ["inventario", "catasto", "utenze", "ruolo", "presenze"]

    update_resp = client.put(
        f"/admin/users/{create_resp.json()['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "full_name": "Alice Esempio",
            "office_location": "CED",
            "phone_extension": "301",
        },
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["full_name"] == "Alice Esempio"
    assert update_resp.json()["office_location"] == "CED"
    assert update_resp.json()["phone_extension"] == "301"

    login("alice")
    list_after_login = client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert list_after_login.status_code == 200
    alice = next(item for item in list_after_login.json()["items"] if item["username"] == "alice")
    assert alice["login_count"] == 1
    assert alice["last_login_at"] is not None
    assert alice["last_login_ip"]
    assert "gate_mobile_console" not in alice


def test_admin_users_list_exposes_readonly_gate_mobile_console_summary() -> None:
    create_user("root", "super_admin")
    token = login("root")

    create_resp = client.post(
        "/admin/users",
        headers={"Authorization": f"Bearer {token}"},
        json={
          "username": "operatore",
          "email": "operatore@example.local",
          "password": "secret123",
          "role": "viewer",
          "is_active": True,
          "module_accessi": True,
          "module_operazioni": True,
        },
    )
    assert create_resp.status_code == 201
    user_id = create_resp.json()["id"]

    db = TestingSessionLocal()
    operator = WCOperator(
        wc_id=501,
        first_name="Mario",
        last_name="Rossi",
        enabled=True,
        gate_mobile_console_enabled=True,
        gate_mobile_console_role="device_manager",
        gaia_user_id=user_id,
    )
    db.add(operator)
    db.commit()
    db.refresh(operator)
    db.close()

    list_resp = client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert list_resp.status_code == 200

    operatore = next(item for item in list_resp.json()["items"] if item["id"] == user_id)
    assert operatore["gate_mobile_console"] == {
        "operator_id": str(operator.id),
        "enabled": True,
        "role": "device_manager",
    }

    get_resp = client.get(f"/admin/users/{user_id}", headers={"Authorization": f"Bearer {token}"})
    assert get_resp.status_code == 200
    assert get_resp.json()["gate_mobile_console"] == {
        "operator_id": str(operator.id),
        "enabled": True,
        "role": "device_manager",
    }


def test_gate_mobile_console_map_returns_empty_for_empty_user_list() -> None:
    db = TestingSessionLocal()
    try:
        assert _build_gate_mobile_console_map(db, user_ids=[]) == {}
    finally:
        db.close()


def test_application_user_enabled_modules_include_gis_and_late_modules() -> None:
    user = ApplicationUser(
        username="module-rich",
        email="module-rich@example.local",
        password_hash=hash_password("secret123"),
        role="viewer",
        is_active=True,
        module_gis=True,
        module_riordino=True,
        module_organigramma=True,
    )

    assert user.enabled_modules == ["gis", "riordino", "organigramma"]
    user.role = ApplicationUserRole.SUPER_ADMIN.value
    assert user.enabled_modules == super_admin_modules()


def test_user_schema_validators_reject_invalid_input_and_accept_optional_update_email() -> None:
    with pytest.raises(ValueError):
        ApplicationUserCreate(username="bad-email", email="not-valid", password="secret123")
    with pytest.raises(ValueError):
        ApplicationUserCreate(username="short-password", email="short@example.local", password="short")
    with pytest.raises(ValueError):
        ApplicationUserUpdate(password="short")

    assert ApplicationUserUpdate(email=None).email is None
    assert ApplicationUserUpdate(email="UPPER@example.local").email == "upper@example.local"


def test_application_user_repository_filters_password_and_delete_paths() -> None:
    db = TestingSessionLocal()
    try:
        active = ApplicationUser(
            username="active-admin",
            email="active-admin@example.local",
            password_hash=hash_password("secret123"),
            role="admin",
            is_active=True,
        )
        inactive = ApplicationUser(
            username="inactive-viewer",
            email="inactive-viewer@example.local",
            password_hash=hash_password("secret123"),
            role="viewer",
            is_active=False,
        )
        db.add_all([active, inactive])
        db.commit()
        db.refresh(active)
        db.refresh(inactive)

        assert get_application_user_by_login_identifier(db, "   ") is None
        assert get_application_user_by_login_identifier(db, "ACTIVE-ADMIN@example.local").id == active.id

        admins, admin_total = list_application_users(db, role="admin")
        assert [user.username for user in admins] == ["active-admin"]
        assert admin_total == 1

        inactive_users, inactive_total = list_application_users(db, is_active=False)
        assert [user.username for user in inactive_users] == ["inactive-viewer"]
        assert inactive_total == 1

        old_hash = active.password_hash
        updated = update_application_user(db, active, ApplicationUserUpdate(password="new-secret", module_presenze=True))
        assert updated.password_hash != old_hash
        assert updated.module_presenze is True

        delete_application_user(db, inactive)
        remaining, total = list_application_users(db)
        assert total == 1
        assert [user.username for user in remaining] == ["active-admin"]
    finally:
        db.close()


def test_admin_user_error_paths() -> None:
    create_user("root", "super_admin")
    create_user("plain-admin", "admin")
    token = login("root")
    admin_token = login("plain-admin")

    conflict_username = client.post(
        "/admin/users",
        headers={"Authorization": f"Bearer {token}"},
        json={"username": "root", "email": "other@example.local", "password": "secret123", "role": "viewer"},
    )
    assert conflict_username.status_code == 409

    conflict_email = client.post(
        "/admin/users",
        headers={"Authorization": f"Bearer {token}"},
        json={"username": "other", "email": "root@example.local", "password": "secret123", "role": "viewer"},
    )
    assert conflict_email.status_code == 409

    denied_super_admin_create = client.post(
        "/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"username": "new-root", "email": "new-root@example.local", "password": "secret123", "role": "super_admin"},
    )
    assert denied_super_admin_create.status_code == 403

    assert client.post("/admin/users/999/send-invite", headers={"Authorization": f"Bearer {token}"}).status_code == 404
    assert client.get("/admin/users/999", headers={"Authorization": f"Bearer {token}"}).status_code == 404
    assert client.put("/admin/users/999", headers={"Authorization": f"Bearer {token}"}, json={"email": "missing@example.local"}).status_code == 404
    assert client.put("/admin/users/1", headers={"Authorization": f"Bearer {admin_token}"}, json={"email": "root2@example.local"}).status_code == 403
    assert client.delete("/admin/users/1", headers={"Authorization": f"Bearer {token}"}).status_code == 400
    assert client.delete("/admin/users/999", headers={"Authorization": f"Bearer {token}"}).status_code == 404
    removable = client.post(
        "/admin/users",
        headers={"Authorization": f"Bearer {token}"},
        json={"username": "remove-me", "email": "remove-me@example.local", "password": "secret123", "role": "viewer"},
    )
    assert removable.status_code == 201
    assert client.delete(f"/admin/users/{removable.json()['id']}", headers={"Authorization": f"Bearer {token}"}).status_code == 204
    patch_missing = client.patch(
        "/admin/users/999/modules?module_accessi=false&module_rete=false&module_inventario=false&module_gis=false&module_catasto=false&module_utenze=false&module_operazioni=false&module_riordino=false&module_ruolo=false&module_presenze=false",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patch_missing.status_code == 404


def test_viewer_cannot_access_admin_users() -> None:
    create_user("viewer", ApplicationUserRole.VIEWER.value)
    token = login("viewer")
    resp = client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_admin_without_accessi_module_cannot_access_admin_users() -> None:
    db = TestingSessionLocal()
    user = ApplicationUser(
        username="catasto_admin",
        email="catasto_admin@example.local",
        password_hash=hash_password("secret123"),
        role=ApplicationUserRole.ADMIN.value,
        is_active=True,
        module_accessi=False,
        module_catasto=True,
        module_utenze=True,
    )
    db.add(user)
    db.commit()
    db.close()

    token = login("catasto_admin")
    resp = client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_utenze_module_route_requires_module_flag() -> None:
    create_user("root", "super_admin")
    token = login("root")

    allowed = client.get("/utenze", headers={"Authorization": f"Bearer {token}"})
    assert allowed.status_code == 200
    assert allowed.json()["module"] == "utenze"

    db = TestingSessionLocal()
    user = ApplicationUser(
        username="viewer_no_anagrafica",
        email="viewer_no_anagrafica@example.local",
        password_hash=hash_password("secret123"),
        role=ApplicationUserRole.VIEWER.value,
        is_active=True,
        module_accessi=True,
        module_utenze=False,
    )
    db.add(user)
    db.commit()
    db.close()

    denied_token = login("viewer_no_anagrafica")
    denied = client.get("/utenze", headers={"Authorization": f"Bearer {denied_token}"})
    assert denied.status_code == 403


def test_user_invite_activation_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    create_user("root", "super_admin")
    token = login("root")
    deliveries: list[dict[str, str]] = []

    def fake_send_email(*, to_email: str, subject: str, text_body: str, html_body: str | None = None) -> None:
        deliveries.append(
            {
                "to_email": to_email,
                "subject": subject,
                "text_body": text_body,
                "html_body": html_body or "",
            }
        )

    monkeypatch.setattr("app.modules.accessi.routes.admin_users.send_email", fake_send_email)

    create_resp = client.post(
        "/admin/users",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "username": "invitee",
            "email": "invitee@example.local",
            "role": "viewer",
            "is_active": True,
            "module_accessi": True,
            "module_rete": False,
            "module_inventario": False,
            "module_gis": False,
            "module_catasto": False,
            "module_utenze": False,
            "module_operazioni": False,
            "module_riordino": False,
            "module_ruolo": False,
            "module_presenze": False,
        },
    )
    assert create_resp.status_code == 201
    assert create_resp.json()["is_active"] is False
    assert create_resp.json()["module_gis"] is False
    assert create_resp.json()["module_presenze"] is False
    assert create_resp.json()["module_presenze"] is False

    invite_resp = client.post(
        f"/admin/users/{create_resp.json()['id']}/send-invite",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert invite_resp.status_code == 200
    assert len(deliveries) == 1
    assert deliveries[0]["to_email"] == "invitee@example.local"
    assert invite_resp.json()["activation_url"].startswith(settings.frontend_public_url.rstrip("/"))

    activation_path = invite_resp.json()["activation_url_path"]
    activation_token = activation_path.rsplit("/", maxsplit=1)[-1]

    info_resp = client.get(f"/auth/user-invite/{activation_token}")
    assert info_resp.status_code == 200
    assert info_resp.json()["username"] == "invitee"
    assert info_resp.json()["already_activated"] is False

    activate_resp = client.post(
        f"/auth/user-invite/{activation_token}/activate",
        json={"password": "secret123"},
    )
    assert activate_resp.status_code == 200

    invitee_login = client.post(
        "/auth/login",
        json={"username": "invitee@example.local", "password": "secret123"},
    )
    assert invitee_login.status_code == 200


def test_user_invite_uses_configured_public_frontend_url_even_with_internal_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_user("root", "super_admin")
    token = login("root")
    deliveries: list[dict[str, str]] = []

    def fake_send_email(*, to_email: str, subject: str, text_body: str, html_body: str | None = None) -> None:
        deliveries.append(
            {
                "to_email": to_email,
                "subject": subject,
                "text_body": text_body,
                "html_body": html_body or "",
            }
        )

    monkeypatch.setattr("app.modules.accessi.routes.admin_users.send_email", fake_send_email)

    create_resp = client.post(
        "/admin/users",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "username": "invitee2",
            "email": "invitee2@example.local",
            "role": "viewer",
            "is_active": True,
            "module_accessi": True,
            "module_rete": False,
            "module_inventario": False,
            "module_gis": False,
            "module_catasto": False,
            "module_utenze": False,
            "module_operazioni": False,
            "module_riordino": False,
            "module_ruolo": False,
            "module_presenze": False,
        },
    )
    assert create_resp.status_code == 201

    invite_resp = client.post(
        f"/admin/users/{create_resp.json()['id']}/send-invite",
        headers={
            "Authorization": f"Bearer {token}",
            "Origin": "http://gaia-internal.docker:8080",
            "Referer": "http://gaia-internal.docker:8080/gaia/users",
        },
    )
    assert invite_resp.status_code == 200
    assert len(deliveries) == 1

    expected_base = settings.frontend_public_url.rstrip("/")
    assert invite_resp.json()["activation_url"].startswith(expected_base)
    assert "gaia-internal.docker" not in invite_resp.json()["activation_url"]
    assert expected_base in deliveries[0]["text_body"]
    assert expected_base in deliveries[0]["html_body"]
    assert "gaia-internal.docker" not in deliveries[0]["text_body"]
    assert "gaia-internal.docker" not in deliveries[0]["html_body"]
