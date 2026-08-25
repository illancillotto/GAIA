from collections.abc import Generator
from types import SimpleNamespace
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.application_user import ApplicationUser
from app.schemas.elaborazioni import (
    ElaborazioneCredentialCreateRequest,
    ElaborazioneCredentialTestRequest,
    ElaborazioneCredentialUpdateRequest,
)
from app.services.catasto_credentials import get_credential_fernet
from app.services.elaborazioni_credentials import (
    ElaborazioneConnectionTestNotFoundError,
    ElaborazioneCredentialConfigurationError,
    ElaborazioneCredentialNotFoundError,
    create_credential,
    decrypt_credentials_password,
    decrypt_encrypted_secret,
    delete_credential,
    get_connection_test_for_user,
    get_credential_for_user,
    get_default_credential_for_user,
    get_runnable_credential_for_user,
    list_credentials_for_user,
    queue_credentials_connection_test,
    require_credentials_for_user,
    update_credential,
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

        schedule = {
            "timezone": "Europe/Rome",
            "weekly": {"0": [{"start": "18:00", "end": "08:00"}]},
        }
        scheduled = update_credential(
            db,
            user.id,
            second.id,
            ElaborazioneCredentialUpdateRequest(schedule_enabled=True, availability_schedule=schedule),
        )
        assert scheduled.schedule_enabled is True
        assert scheduled.availability_schedule == schedule

        non_default = update_credential(
            db,
            user.id,
            second.id,
            ElaborazioneCredentialUpdateRequest(is_default=False),
        )
        assert non_default.is_default is False

        disabled = update_credential(
            db,
            user.id,
            second.id,
            ElaborazioneCredentialUpdateRequest(schedule_enabled=False, availability_schedule=None),
        )
        assert disabled.schedule_enabled is False
        assert disabled.availability_schedule is None
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


def test_credential_service_covers_crud_fallbacks_and_secret_failures() -> None:
    db = TestingSessionLocal()
    try:
        user = db.query(ApplicationUser).filter(ApplicationUser.username == "worker").one()
        inactive = create_credential(
            db,
            user.id,
            ElaborazioneCredentialCreateRequest(
                label="",
                sister_username="inactive-user",
                sister_password="secret-1",
                active=False,
            ),
        )
        inactive.is_default = False
        db.commit()
        assert get_default_credential_for_user(db, user.id) == inactive
        assert get_credential_for_user(db, user.id + 1, inactive.id) is None
        assert get_runnable_credential_for_user(db, user.id) is None
        with pytest.raises(ElaborazioneCredentialNotFoundError, match="Active SISTER"):
            require_credentials_for_user(db, user.id)

        active = create_credential(
            db,
            user.id,
            ElaborazioneCredentialCreateRequest(
                sister_username="active-user",
                sister_password="secret-2",
            ),
        )
        active.is_default = False
        db.commit()
        assert get_runnable_credential_for_user(db, user.id) == active
        inactive.label = ""
        updated = update_credential(
            db,
            user.id,
            inactive.id,
            ElaborazioneCredentialUpdateRequest(
                sister_username=" renamed ",
                sister_password="new-secret",
                convenzione=" ",
                codice_richiesta=" code ",
                ufficio_provinciale=" CAGLIARI Territorio ",
                active=True,
                is_default=False,
            ),
        )
        assert updated.label == "renamed"
        assert updated.convenzione is None
        assert updated.codice_richiesta == "code"
        assert updated.ufficio_provinciale == "CAGLIARI Territorio"
        assert decrypt_credentials_password(updated) == "new-secret"

        relabeled = update_credential(
            db,
            user.id,
            updated.id,
            ElaborazioneCredentialUpdateRequest(label=" Etichetta ", sister_username="user-final"),
        )
        assert relabeled.label == "Etichetta"

        with pytest.raises(ElaborazioneCredentialNotFoundError):
            update_credential(db, user.id, uuid4(), ElaborazioneCredentialUpdateRequest(active=True))
        with pytest.raises(ElaborazioneCredentialConfigurationError, match="schedule is required"):
            update_credential(
                db,
                user.id,
                active.id,
                ElaborazioneCredentialUpdateRequest(schedule_enabled=True, availability_schedule=None),
            )
        db.rollback()

        with pytest.raises(ElaborazioneCredentialConfigurationError, match="cannot be decrypted"):
            decrypt_credentials_password(SimpleNamespace(sister_password_encrypted=b"invalid"))
        with pytest.raises(ElaborazioneCredentialConfigurationError, match="cannot be decrypted"):
            decrypt_encrypted_secret(b"invalid")

        active.active = False
        active.is_default = False
        relabeled.active = False
        relabeled.is_default = False
        db.commit()
        update_credential(
            db,
            user.id,
            active.id,
            ElaborazioneCredentialUpdateRequest(is_default=False),
        )
        assert delete_credential(db, user.id, uuid4()) is False
        assert delete_credential(db, user.id, active.id) is True
        assert delete_credential(db, user.id, relabeled.id) is True
        assert get_default_credential_for_user(db, user.id) is None
    finally:
        db.close()


def test_credential_service_covers_connection_test_variants_and_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    db = TestingSessionLocal()
    try:
        user = db.query(ApplicationUser).filter(ApplicationUser.username == "worker").one()
        saved = create_credential(
            db,
            user.id,
            ElaborazioneCredentialCreateRequest(sister_username="saved", sister_password="secret"),
        )
        default_test = queue_credentials_connection_test(db, user.id)
        assert default_test.credential_id == saved.id

        transient = queue_credentials_connection_test(
            db,
            user.id,
            ElaborazioneCredentialTestRequest(
                sister_username=" transient ",
                sister_password=" transient-secret ",
                ufficio_provinciale=" CAGLIARI Territorio ",
            ),
        )
        assert transient.credential_id is None
        assert transient.sister_username == "transient"
        assert transient.ufficio_provinciale == "CAGLIARI Territorio"
        assert get_connection_test_for_user(db, user.id, transient.id) == transient
        with pytest.raises(ElaborazioneConnectionTestNotFoundError):
            get_connection_test_for_user(db, user.id, uuid4())
        with pytest.raises(ElaborazioneCredentialNotFoundError):
            queue_credentials_connection_test(
                db,
                user.id,
                ElaborazioneCredentialTestRequest(credential_id=uuid4()),
            )
    finally:
        db.close()

    monkeypatch.setattr("app.services.elaborazioni_credentials.settings.credential_master_key", "")
    get_credential_fernet.cache_clear()
    with pytest.raises(ElaborazioneCredentialConfigurationError, match="not configured"):
        get_credential_fernet()
    monkeypatch.setattr("app.services.elaborazioni_credentials.settings.credential_master_key", "invalid")
    get_credential_fernet.cache_clear()
    with pytest.raises(ElaborazioneCredentialConfigurationError, match="invalid for Fernet"):
        get_credential_fernet()
