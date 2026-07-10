import pytest
from fastapi import HTTPException

from app.api import deps
from app.models.application_user import ApplicationUser, ApplicationUserRole


def _make_user(
    *,
    role: str = ApplicationUserRole.VIEWER.value,
    is_active: bool = True,
    module_presenze: bool = False,
    module_operazioni: bool = False,
) -> ApplicationUser:
    return ApplicationUser(
        username=f"{role}-user",
        email=f"{role}@example.local",
        password_hash="hash",
        role=role,
        is_active=is_active,
        module_presenze=module_presenze,
        module_operazioni=module_operazioni,
    )


def test_get_current_user_uses_token_service(monkeypatch) -> None:
    expected_user = _make_user()

    def fake_get_current_user_from_token(db, token: str) -> ApplicationUser:
        assert db == "db-session"
        assert token == "jwt-token"
        return expected_user

    monkeypatch.setattr(deps, "get_current_user_from_token", fake_get_current_user_from_token)

    assert deps.get_current_user("db-session", "jwt-token") is expected_user


def test_require_active_user_returns_active_user() -> None:
    user = _make_user(is_active=True)

    assert deps.require_active_user(user) is user


def test_require_active_user_rejects_inactive_user() -> None:
    user = _make_user(is_active=False)

    with pytest.raises(HTTPException) as exc:
        deps.require_active_user(user)

    assert exc.value.status_code == 403
    assert exc.value.detail == "Inactive user"


def test_require_role_returns_user_when_role_is_allowed() -> None:
    user = _make_user(role=ApplicationUserRole.ADMIN.value)

    assert deps.require_role("super_admin", "admin")(user) is user


def test_require_role_rejects_user_when_role_is_not_allowed() -> None:
    user = _make_user(role=ApplicationUserRole.VIEWER.value)

    with pytest.raises(HTTPException) as exc:
        deps.require_role("super_admin", "admin")(user)

    assert exc.value.status_code == 403
    assert exc.value.detail == "Insufficient role"


def test_require_module_returns_super_admin_without_module_flag() -> None:
    user = _make_user(role=ApplicationUserRole.SUPER_ADMIN.value)

    assert deps.require_module("operazioni")(user) is user


def test_require_module_accepts_presenze_for_inaz() -> None:
    user = _make_user(module_presenze=True)

    assert deps.require_module("inaz")(user) is user


def test_require_module_rejects_user_without_enabled_module() -> None:
    user = _make_user(module_operazioni=False)

    with pytest.raises(HTTPException) as exc:
        deps.require_module("operazioni")(user)

    assert exc.value.status_code == 403
    assert exc.value.detail == "Module access denied"


def test_require_section_returns_user_when_permission_resolver_allows(monkeypatch) -> None:
    user = _make_user()

    def fake_can_access_section(db, current_user: ApplicationUser, section_key: str) -> bool:
        assert db == "db-session"
        assert current_user is user
        assert section_key == "dashboard"
        return True

    monkeypatch.setattr(deps, "can_access_section", fake_can_access_section)

    assert deps.require_section("dashboard")("db-session", user) is user


def test_require_section_rejects_user_when_permission_resolver_denies(monkeypatch) -> None:
    user = _make_user()
    monkeypatch.setattr(deps, "can_access_section", lambda db, current_user, section_key: False)

    with pytest.raises(HTTPException) as exc:
        deps.require_section("dashboard")("db-session", user)

    assert exc.value.status_code == 403
    assert exc.value.detail == "Section access denied"


def test_require_admin_user_returns_same_user() -> None:
    user = _make_user(role=ApplicationUserRole.ADMIN.value)

    assert deps.require_admin_user(user) is user


def test_require_super_admin_user_returns_same_user() -> None:
    user = _make_user(role=ApplicationUserRole.SUPER_ADMIN.value)

    assert deps.require_super_admin_user(user) is user


def test_require_not_operator_returns_non_operator_user() -> None:
    user = _make_user(role=ApplicationUserRole.ADMIN.value)

    assert deps.require_not_operator(user) is user


def test_require_not_operator_rejects_operator_user() -> None:
    user = _make_user(role=ApplicationUserRole.OPERATOR.value)

    with pytest.raises(HTTPException) as exc:
        deps.require_not_operator(user)

    assert exc.value.status_code == 403
    assert exc.value.detail == "Operators cannot access this resource"


def test_require_mobile_connector_returns_token_when_valid(monkeypatch) -> None:
    monkeypatch.setattr(deps.settings, "mobile_connector_token", "primary-token")
    monkeypatch.setattr(deps.settings, "gate_mobile_connector_token", "fallback-token")

    assert deps.require_mobile_connector("primary-token") == "primary-token"


def test_require_mobile_connector_rejects_missing_configuration(monkeypatch) -> None:
    monkeypatch.setattr(deps.settings, "mobile_connector_token", "")
    monkeypatch.setattr(deps.settings, "gate_mobile_connector_token", "")

    with pytest.raises(HTTPException) as exc:
        deps.require_mobile_connector("any-token")

    assert exc.value.status_code == 503
    assert exc.value.detail == "Mobile connector auth not configured"


def test_require_mobile_connector_rejects_invalid_token(monkeypatch) -> None:
    monkeypatch.setattr(deps.settings, "mobile_connector_token", "")
    monkeypatch.setattr(deps.settings, "gate_mobile_connector_token", "fallback-token")

    with pytest.raises(HTTPException) as exc:
        deps.require_mobile_connector("wrong-token")

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid connector token"
