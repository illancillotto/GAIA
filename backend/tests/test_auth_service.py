from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models.application_user import ApplicationUser
from app.services import auth


def _user(*, active: bool = True) -> ApplicationUser:
    user = ApplicationUser()
    user.id = 7
    user.username = "admin"
    user.email = "admin@example.local"
    user.password_hash = "hashed"
    user.role = "admin"
    user.is_active = active
    user.module_accessi = True
    return user


def test_authenticate_user_returns_active_user() -> None:
    db = MagicMock()
    user = _user()

    with (
        patch("app.services.auth.get_application_user_by_login_identifier", return_value=user),
        patch("app.services.auth.verify_password", return_value=True),
    ):
        assert auth.authenticate_user(db, "admin", "secret") is user


def test_authenticate_user_rejects_invalid_credentials() -> None:
    db = MagicMock()

    with patch("app.services.auth.get_application_user_by_login_identifier", return_value=None):
        with pytest.raises(HTTPException, match="Invalid credentials") as exc_info:
            auth.authenticate_user(db, "admin", "secret")

    assert exc_info.value.status_code == 401


def test_authenticate_user_rejects_inactive_user() -> None:
    db = MagicMock()
    user = _user(active=False)

    with (
        patch("app.services.auth.get_application_user_by_login_identifier", return_value=user),
        patch("app.services.auth.verify_password", return_value=True),
    ):
        with pytest.raises(HTTPException, match="Inactive user") as exc_info:
            auth.authenticate_user(db, "admin", "secret")

    assert exc_info.value.status_code == 403


def test_issue_access_token_delegates_to_security() -> None:
    user = _user()

    with patch("app.services.auth.create_access_token", return_value="token-123") as mocked_create:
        assert auth.issue_access_token(user) == "token-123"

    mocked_create.assert_called_once_with("7", "admin", ["accessi"])


def test_get_current_user_from_token_rejects_invalid_token() -> None:
    db = MagicMock()

    with patch("app.services.auth.decode_access_token", side_effect=ValueError("bad token")):
        with pytest.raises(HTTPException) as exc_info:
            auth.get_current_user_from_token(db, "invalid")

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Sessione scaduta o non valida. Effettua di nuovo l'accesso."


def test_get_current_user_from_token_rejects_missing_user() -> None:
    db = MagicMock()

    with (
        patch("app.services.auth.decode_access_token", return_value={"sub": "9"}),
        patch("app.services.auth.get_application_user_by_id", return_value=None),
    ):
        with pytest.raises(HTTPException) as exc_info:
            auth.get_current_user_from_token(db, "token")

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Sessione scaduta o non valida. Effettua di nuovo l'accesso."


def test_get_current_user_from_token_returns_active_user() -> None:
    db = MagicMock()
    user = _user()

    with (
        patch("app.services.auth.decode_access_token", return_value={"sub": "7"}),
        patch("app.services.auth.get_application_user_by_id", return_value=user),
    ):
        assert auth.get_current_user_from_token(db, "token") is user
