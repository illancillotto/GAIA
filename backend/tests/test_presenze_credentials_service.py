from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.presenze.models import PresenzeCredential
from app.modules.presenze.schemas import PresenzeCredentialCreate, PresenzeCredentialUpdate
from app.modules.presenze.services import credentials as credentials_service


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class _FakeFernet:
    def encrypt(self, value: bytes) -> bytes:
        return b"enc:" + value

    def decrypt(self, value: bytes) -> bytes:
        prefix = b"enc:"
        if not value.startswith(prefix):
            raise ValueError("invalid ciphertext")
        return value[len(prefix):]


@pytest.fixture(autouse=True)
def setup_database(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(credentials_service, "get_credential_fernet", lambda: _FakeFernet())
    yield
    Base.metadata.drop_all(bind=engine)


def _create_user(username: str, *, is_super_admin: bool = False) -> ApplicationUser:
    db = TestingSessionLocal()
    try:
        user = ApplicationUser(
            username=username,
            email=f"{username}@example.local",
            password_hash=hash_password("secret123"),
            role=ApplicationUserRole.SUPER_ADMIN.value if is_super_admin else ApplicationUserRole.ADMIN.value,
            is_active=True,
            module_accessi=True,
            module_presenze=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def _create_credential(
    db: Session,
    user: ApplicationUser,
    *,
    label: str = "Main",
    username: str = "user.inaz",
    password: str = "secret",
    active: bool = True,
    consecutive_failures: int = 0,
) -> PresenzeCredential:
    credential = PresenzeCredential(
        application_user_id=user.id,
        label=label,
        username=username,
        password_encrypted=credentials_service._encrypt(password),
        active=active,
        consecutive_failures=consecutive_failures,
    )
    db.add(credential)
    db.commit()
    db.refresh(credential)
    return credential


def test_encrypt_and_decrypt_round_trip() -> None:
    encrypted = credentials_service._encrypt("secret")
    assert encrypted == "enc:secret"
    assert credentials_service._decrypt(encrypted) == "secret"


def test_create_list_get_update_and_delete_credential() -> None:
    owner = _create_user("cred_owner")
    outsider = _create_user("cred_outsider")
    super_admin = _create_user("cred_super", is_super_admin=True)
    db = TestingSessionLocal()
    try:
        created = credentials_service.create_credential(
            db,
            owner.id,
            PresenzeCredentialCreate(label="  Ufficio  ", username="  office.inaz ", password="pw1", active=True),
        )
        stored = db.get(PresenzeCredential, created.id)
        assert stored is not None
        assert stored.label == "Ufficio"
        assert stored.username == "office.inaz"
        assert stored.password_encrypted == "enc:pw1"

        owner_rows = credentials_service.list_credentials(db, owner)
        outsider_rows = credentials_service.list_credentials(db, outsider)
        super_rows = credentials_service.list_credentials(db, super_admin)
        assert [item.id for item in owner_rows] == [created.id]
        assert outsider_rows == []
        assert [item.id for item in super_rows] == [created.id]

        assert credentials_service.user_can_access_credential(owner, stored) is True
        assert credentials_service.user_can_access_credential(super_admin, stored) is True
        assert credentials_service.user_can_access_credential(outsider, stored) is False
        assert credentials_service.get_credential(db, created.id, owner) is not None
        assert credentials_service.get_credential(db, created.id, outsider) is None

        updated = credentials_service.update_credential(
            db,
            created.id,
            owner,
            PresenzeCredentialUpdate(label=" Updated ", username=" upd.inaz ", password="pw2", active=True),
        )
        assert updated is not None
        db.refresh(stored)
        assert stored.label == "Updated"
        assert stored.username == "upd.inaz"
        assert stored.password_encrypted == "enc:pw2"
        assert stored.consecutive_failures == 0

        missing_update = credentials_service.update_credential(
            db,
            created.id,
            outsider,
            PresenzeCredentialUpdate(label="forbidden"),
        )
        assert missing_update is None

        assert credentials_service.delete_credential(db, created.id, outsider) is False
        assert credentials_service.delete_credential(db, created.id, owner) is True
        assert db.get(PresenzeCredential, created.id) is None
    finally:
        db.close()


def test_pick_credential_supports_explicit_id_and_default_active_lookup() -> None:
    owner = _create_user("pick_owner")
    outsider = _create_user("pick_outsider")
    db = TestingSessionLocal()
    try:
        inactive = _create_credential(db, owner, label="Inactive", username="inactive", active=False)
        active = _create_credential(db, owner, label="Active", username="active", password="pw-active", active=True)

        picked, decrypted = credentials_service.pick_credential(db, owner, active.id)
        assert picked.id == active.id
        assert decrypted == "pw-active"

        with pytest.raises(RuntimeError, match="non attiva"):
            credentials_service.pick_credential(db, owner, inactive.id)
        with pytest.raises(RuntimeError, match="non trovata"):
            credentials_service.pick_credential(db, outsider, active.id)

        default_credential, default_password = credentials_service.pick_credential(db, owner)
        assert default_credential.id == active.id
        assert default_password == "pw-active"

        active.active = False
        db.add(active)
        db.commit()
        with pytest.raises(RuntimeError, match="Nessuna credenziale Presenze attiva disponibile"):
            credentials_service.pick_credential(db, owner)
    finally:
        db.close()


def test_mark_credential_used_and_error_update_runtime_metadata(caplog: pytest.LogCaptureFixture) -> None:
    owner = _create_user("mark_owner")
    db = TestingSessionLocal()
    try:
        credential = _create_credential(db, owner, active=False, consecutive_failures=4)

        credentials_service.mark_credential_used(db, credential.id, "https://presenze/auth")
        db.refresh(credential)
        assert credential.active is True
        assert credential.last_used_at is not None
        assert credential.last_authenticated_url == "https://presenze/auth"
        assert credential.last_error is None
        assert credential.consecutive_failures == 0

        long_error = "x" * 700
        with caplog.at_level("WARNING"):
            credentials_service.mark_credential_error(db, credential.id, long_error)
        db.refresh(credential)
        assert credential.last_error == long_error[:500]
        assert credential.consecutive_failures == 1
        assert credential.active is True

        credentials_service.mark_credential_error(db, credential.id, "Login INAZ non riuscito: credenziali non valide")
        db.refresh(credential)
        assert credential.active is False

        credential.consecutive_failures = 4
        credential.active = True
        db.add(credential)
        db.commit()
        with caplog.at_level("WARNING"):
            credentials_service.mark_credential_error(db, credential.id, "boom")
        db.refresh(credential)
        assert credential.consecutive_failures == 5
        assert credential.active is False
        assert "disabilitata dopo 5 fallimenti consecutivi" in caplog.text

        credentials_service.mark_credential_used(db, 9999, "https://unused")
        credentials_service.mark_credential_error(db, 9999, "ignored")
    finally:
        db.close()


@pytest.mark.anyio
async def test_test_credential_reports_success_and_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    owner = _create_user("test_owner")
    outsider = _create_user("test_outsider")
    db = TestingSessionLocal()
    try:
        credential = _create_credential(db, owner, username="owner.inaz", password="pw-test")

        async def fake_success(**kwargs):
            assert kwargs == {"username": "owner.inaz", "password": "pw-test"}
            return {"authenticated_url": "https://presenze/home", "cookies": "SESSION"}

        monkeypatch.setattr(credentials_service, "test_login_with_credentials", fake_success)
        ok_result = await credentials_service.test_credential(db, owner, credential.id)
        db.refresh(credential)
        assert ok_result.ok is True
        assert ok_result.authenticated_url == "https://presenze/home"
        assert ok_result.cookies == "SESSION"
        assert credential.last_error is None
        assert credential.last_authenticated_url == "https://presenze/home"

        not_found = await credentials_service.test_credential(db, outsider, credential.id)
        assert not_found.ok is False
        assert not_found.error == "Credenziale non trovata"

        async def fake_failure(**kwargs):
            raise RuntimeError("login failed")

        monkeypatch.setattr(credentials_service, "test_login_with_credentials", fake_failure)
        failed = await credentials_service.test_credential(db, owner, credential.id)
        db.refresh(credential)
        assert failed.ok is False
        assert failed.error == "login failed"
        assert credential.last_error == "login failed"
        assert credential.consecutive_failures == 1
    finally:
        db.close()
