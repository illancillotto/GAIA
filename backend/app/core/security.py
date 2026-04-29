from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings

PASSWORD_SCHEME = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 390000
UTC = timezone.utc


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )
    return (
        f"{PASSWORD_SCHEME}${PASSWORD_ITERATIONS}$"
        f"{base64.b64encode(salt).decode('utf-8')}$"
        f"{base64.b64encode(derived_key).decode('utf-8')}"
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        scheme, iterations, encoded_salt, encoded_hash = password_hash.split("$", maxsplit=3)
    except ValueError:
        return False

    if scheme != PASSWORD_SCHEME:
        return False

    salt = base64.b64decode(encoded_salt.encode("utf-8"))
    expected_hash = base64.b64decode(encoded_hash.encode("utf-8"))
    computed_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        int(iterations),
    )
    return hmac.compare_digest(computed_hash, expected_hash)


def create_access_token(user_id: str, role: str, modules: list[str], expires_minutes: int | None = None) -> str:
    expire_delta = timedelta(minutes=expires_minutes or settings.jwt_expire_minutes)
    payload = {
        "sub": user_id,
        "role": role,
        "modules": modules,
        "exp": datetime.now(UTC) + expire_delta,
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
