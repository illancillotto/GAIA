from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, decode_access_token, verify_password
from app.models.application_user import ApplicationUser
from app.repositories.application_user import (
    get_application_user_by_id,
    get_application_user_by_username,
)


def authenticate_user(db: Session, username: str, password: str) -> ApplicationUser:
    user = get_application_user_by_username(db, username)
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return user


def issue_access_token(user: ApplicationUser) -> str:
    return create_access_token(str(user.id))


def get_current_user_from_token(db: Session, token: str) -> ApplicationUser:
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except Exception as exc:  # pragma: no cover - normalized into HTTP response
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        ) from exc

    user = get_application_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )
    return user
