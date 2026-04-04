from collections.abc import Generator

from cryptography.fernet import Fernet
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.application_user import ApplicationUser
from app.services.catasto_credentials import get_credential_fernet
from app.services.elaborazioni_credentials import (
    create_credential,
    get_default_credential_for_user,
    list_credentials_for_user,
    queue_credentials_connection_test,
    require_credentials_for_user,
    update_credential,
)
from app.schemas.elaborazioni import (
    ElaborazioneCredentialCreateRequest,
    ElaborazioneCredentialTestRequest,
    ElaborazioneCredentialUpdateRequest,
)


SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def setup_database(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    generated_key = Fernet.generate_key().decode("utf-8")
    monkeypatch.setattr("app.services.catasto_credentials.settings.credential_master_key", generated_key)
    monkeypatch.setattr("app.core.config.settings.credential_master_key", generated_key)
    get_credential_fernet.cache_clear()

    db = TestingSessionLocal()
    db.add(ApplicationUser(username="worker", email="worker@example.local", password_hash="hash", role="admin", is_active=True))
    db.commit()
    db.close()

    yield

    Base.metadata.drop_all(bind=engine)


def test_create_multiple_credentials_and_switch_default() -> None:
    db = TestingSessionLocal()
    try:
        user = db.query(ApplicationUser).filter(ApplicationUser.username == "worker").one()
        first = create_credential(
            db,
            user.id,
            ElaborazioneCredentialCreateRequest(
                label="Profilo A",
                sister_username="RSSMRA80A01H501U",
                sister_password="secret-1",
                is_default=True,
            ),
        )
        second = create_credential(
            db,
            user.id,
            ElaborazioneCredentialCreateRequest(
                label="Profilo B",
                sister_username="01234567890",
                sister_password="secret-2",
            ),
        )

        assert first.is_default is True
        assert second.is_default is False
        assert len(list_credentials_for_user(db, user.id)) == 2

        update_credential(
            db,
            user.id,
            second.id,
            ElaborazioneCredentialUpdateRequest(is_default=True, active=True),
        )
        default_credential = get_default_credential_for_user(db, user.id)
        runnable_credential = require_credentials_for_user(db, user.id)

        assert default_credential is not None
        assert default_credential.id == second.id
        assert runnable_credential.id == second.id
    finally:
        db.close()


def test_queue_connection_test_for_specific_saved_credential() -> None:
    db = TestingSessionLocal()
    try:
        user = db.query(ApplicationUser).filter(ApplicationUser.username == "worker").one()
        first = create_credential(
            db,
            user.id,
            ElaborazioneCredentialCreateRequest(
                label="Profilo A",
                sister_username="RSSMRA80A01H501U",
                sister_password="secret-1",
                is_default=True,
            ),
        )
        second = create_credential(
            db,
            user.id,
            ElaborazioneCredentialCreateRequest(
                label="Profilo B",
                sister_username="01234567890",
                sister_password="secret-2",
            ),
        )

        connection_test = queue_credentials_connection_test(
            db,
            user.id,
            ElaborazioneCredentialTestRequest(credential_id=second.id),
        )

        assert connection_test.credential_id == second.id
        assert connection_test.sister_username == second.sister_username
        assert connection_test.persist_verification is True
        assert connection_test.credential_id != first.id
    finally:
        db.close()
