from collections.abc import Generator

from cryptography.fernet import Fernet
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.db.base import Base
from app.models.application_user import ApplicationUser
from app.models.catasto import CatastoBatch, CatastoComune, CatastoVisuraRequest, CatastoVisuraRequestStatus
from app.services.catasto_credentials import get_credential_fernet
from app.services.elaborazioni_batches import BatchConflictError, retry_failed_batch, validate_visure_records


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
    db.add(CatastoComune(nome="Oristano", codice_sister="G113#ORISTANO#5#5", ufficio="ORISTANO Territorio"))
    db.commit()
    db.close()

    yield

    Base.metadata.drop_all(bind=engine)


def test_validate_visure_records_supports_subject_pf_and_pnf() -> None:
    db = TestingSessionLocal()
    try:
        rows = validate_visure_records(
            db,
            [
                {"subject_id": "RSSMRA80A01H501U", "request_type": "storica", "tipo_visura": "completa"},
                {"subject_id": "01234567890", "tipo_visura": "sintetica"},
            ],
        )
    finally:
        db.close()

    assert rows[0].search_mode == "soggetto"
    assert rows[0].subject_kind == "PF"
    assert rows[0].request_type == "STORICA"
    assert rows[1].subject_kind == "PNF"
    assert rows[1].request_type == "ATTUALITA"


def test_validate_visure_records_keeps_immobile_flow() -> None:
    db = TestingSessionLocal()
    try:
        rows = validate_visure_records(
            db,
            [
                {
                    "comune": "Oristano",
                    "catasto": "Terreni e Fabbricati",
                    "foglio": "5",
                    "particella": "120",
                    "subalterno": "3",
                    "tipo_visura": "Completa",
                }
            ],
        )
    finally:
        db.close()

    assert rows[0].search_mode == "immobile"
    assert rows[0].comune == "Oristano"
    assert rows[0].foglio == "5"
    assert rows[0].particella == "120"


def test_retry_failed_batch_does_not_retry_not_found_requests() -> None:
    db = TestingSessionLocal()
    try:
        user = db.query(ApplicationUser).filter(ApplicationUser.username == "worker").one()
        batch = CatastoBatch(
            user_id=user.id,
            name="Batch not found",
            status="failed",
            total_items=1,
            not_found_items=1,
        )
        db.add(batch)
        db.flush()
        db.add(
            CatastoVisuraRequest(
                batch_id=batch.id,
                user_id=user.id,
                row_index=1,
                search_mode="soggetto",
                subject_kind="PF",
                subject_id="RSSMRA80A01H501U",
                request_type="ATTUALITA",
                tipo_visura="Sintetica",
                status=CatastoVisuraRequestStatus.NOT_FOUND.value,
                current_operation="Nessuna corrispondenza",
                error_message="Nessuna corrispondenza catastale",
            )
        )
        db.commit()

        with pytest.raises(BatchConflictError, match="No failed requests available for retry"):
            retry_failed_batch(db, user.id, batch.id)
    finally:
        db.close()
