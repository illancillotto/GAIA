from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path
import sys
import types

from cryptography.fernet import Fernet
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.db.base import Base
from app.models.application_user import ApplicationUser
from app.models.catasto import CatastoBatch, CatastoComune, CatastoDocument, CatastoParcel, CatastoVisuraRequest, CatastoVisuraRequestStatus
from app.models.elaborazioni import ElaborazioneCredential
from app.modules.catasto.services.ade_status_scan import ADE_SCAN_PURPOSE, create_ade_status_scan_batch
from app.modules.ruolo.models import RuoloAvviso, RuoloImportJob, RuoloParticella, RuoloPartita
from app.services.catasto_credentials import get_credential_fernet
from app.services.elaborazioni_batches import BatchConflictError, expire_stale_pending_batches, retry_failed_batch, validate_visure_records


WORKER_ROOT = Path(__file__).resolve().parents[2] / "modules" / "elaborazioni" / "worker"
if str(WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKER_ROOT))

if "playwright.async_api" not in sys.modules:
    playwright_module = types.ModuleType("playwright")
    playwright_async_api_module = types.ModuleType("playwright.async_api")
    for name in ("Browser", "BrowserContext", "Download", "Page", "Playwright"):
        setattr(playwright_async_api_module, name, type(name, (), {}))
    playwright_async_api_module.TimeoutError = TimeoutError
    playwright_async_api_module.async_playwright = lambda: None
    sys.modules["playwright"] = playwright_module
    sys.modules["playwright.async_api"] = playwright_async_api_module

if "browser_session" not in sys.modules:
    browser_session_module = types.ModuleType("browser_session")
    browser_session_module.BrowserSession = type("BrowserSession", (), {})
    browser_session_module.BrowserSessionConfig = type("BrowserSessionConfig", (), {})
    sys.modules["browser_session"] = browser_session_module

if "captcha_solver" not in sys.modules:
    captcha_solver_module = types.ModuleType("captcha_solver")
    captcha_solver_module.CaptchaSolver = type("CaptchaSolver", (), {})
    sys.modules["captcha_solver"] = captcha_solver_module

import worker as worker_module


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
    db.add(CatastoComune(nome="Arborea", codice_sister="A357#ARBOREA#3#0", ufficio="ORISTANO Territorio"))
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


def test_retry_failed_batch_requeues_old_failed_batches_without_stale_expiration() -> None:
    db = TestingSessionLocal()
    try:
        user = db.query(ApplicationUser).filter(ApplicationUser.username == "worker").one()
        original_started_at = datetime.now(UTC) - timedelta(hours=3)
        batch = CatastoBatch(
            user_id=user.id,
            name="Batch retry stale guard",
            status="failed",
            total_items=1,
            failed_items=1,
            created_at=datetime.now(UTC) - timedelta(hours=4),
            started_at=original_started_at,
            completed_at=datetime.now(UTC) - timedelta(hours=2),
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
                status=CatastoVisuraRequestStatus.FAILED.value,
                current_operation="Errore precedente",
                error_message="Errore test",
            )
        )
        db.commit()

        retry_failed_batch(db, user.id, batch.id)
        expired = expire_stale_pending_batches(db, user.id)

        db.refresh(batch)
        request = db.query(CatastoVisuraRequest).filter(CatastoVisuraRequest.batch_id == batch.id).one()
        assert expired == 0
        assert batch.status == "pending"
        assert batch.current_operation == "Retry queued"
        assert batch.started_at is not None
        assert batch.started_at > original_started_at
        assert batch.completed_at is None
        assert request.status == CatastoVisuraRequestStatus.PENDING.value
        assert request.current_operation == "Queued for retry"
        assert request.error_message is None
    finally:
        db.close()


def test_persist_flow_result_uses_subject_specific_message_for_not_found() -> None:
    db = TestingSessionLocal()
    try:
        user = db.query(ApplicationUser).filter(ApplicationUser.username == "worker").one()
        batch = CatastoBatch(
            user_id=user.id,
            name="Batch not found subject",
            status="processing",
            total_items=1,
        )
        db.add(batch)
        db.flush()
        request = CatastoVisuraRequest(
            batch_id=batch.id,
            user_id=user.id,
            row_index=1,
            search_mode="soggetto",
            subject_kind="PF",
            subject_id="CNCFTN98A02B314E",
            request_type="ATTUALITA",
            tipo_visura="Sintetica",
            status=CatastoVisuraRequestStatus.PROCESSING.value,
        )
        db.add(request)
        db.commit()
        batch_id = batch.id
        request_id = request.id
    finally:
        db.close()

    worker = worker_module.CatastoWorker.__new__(worker_module.CatastoWorker)
    worker._persist_flow_result(
        batch_id,
        request_id,
        "SISTERUSER",
        worker_module.VisuraFlowResult(
            status="not_found",
            error_message="Nessuna corrispondenza catastale per PF 'CNCFTN98A02B314E'",
        ),
    )

    db = TestingSessionLocal()
    try:
        request = db.get(CatastoVisuraRequest, request_id)
        batch = db.get(CatastoBatch, batch_id)
        assert request is not None
        assert batch is not None
        assert request.status == CatastoVisuraRequestStatus.NOT_FOUND.value
        assert request.current_operation == "Utente non è titolare di terreni o immobili"
        assert batch.current_operation == "Utente senza titolarità catastale riga 1"
    finally:
        db.close()


def test_expire_stale_pending_batch_marks_batch_and_requests_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.elaborazioni_batches.settings.elaborazioni_pending_start_timeout_minutes", 25)

    db = TestingSessionLocal()
    try:
        user = db.query(ApplicationUser).filter(ApplicationUser.username == "worker").one()
        batch = CatastoBatch(
            user_id=user.id,
            name="Batch pending stale",
            status="pending",
            total_items=1,
            current_operation="Awaiting start",
            created_at=datetime.now(UTC) - timedelta(hours=2),
        )
        db.add(batch)
        db.flush()
        request = CatastoVisuraRequest(
            batch_id=batch.id,
            user_id=user.id,
            row_index=1,
            search_mode="soggetto",
            subject_kind="PNF",
            subject_id="00042370957",
            request_type="ATTUALITA",
            tipo_visura="Sintetica",
            status=CatastoVisuraRequestStatus.PENDING.value,
            current_operation="Pending",
        )
        db.add(request)
        db.commit()

        expired = expire_stale_pending_batches(db, user.id)
        assert expired == 1

        db.refresh(batch)
        db.refresh(request)
        assert batch.status == "failed"
        assert batch.current_operation == "Batch scaduto prima dell'avvio (25 min)"
        assert batch.completed_at is not None
        assert batch.failed_items == 1
        assert request.status == CatastoVisuraRequestStatus.FAILED.value
        assert request.current_operation == "Scaduta prima dell'avvio"
        assert "25 minuti" in (request.error_message or "")
        assert request.processed_at is not None
    finally:
        db.close()


def test_create_ade_status_scan_batch_queues_unmatched_ruolo_particelle() -> None:
    db = TestingSessionLocal()
    try:
        user = db.query(ApplicationUser).filter(ApplicationUser.username == "worker").one()
        db.add(
            ElaborazioneCredential(
                user_id=user.id,
                label="SISTER test",
                sister_username="test-user",
                sister_password_encrypted=get_credential_fernet().encrypt(b"test-password"),
                ufficio_provinciale="ORISTANO Territorio",
                active=True,
                is_default=True,
            )
        )
        import_job = RuoloImportJob(anno_tributario=2025, filename="storico_ruolo_2025", status="completed")
        db.add(import_job)
        db.flush()
        avviso = RuoloAvviso(
            import_job_id=import_job.id,
            codice_cnc="CNC1",
            anno_tributario=2025,
        )
        db.add(avviso)
        db.flush()
        partita = RuoloPartita(
            avviso_id=avviso.id,
            codice_partita="0000000",
            comune_nome="ARBOREA",
            comune_codice="A357",
        )
        db.add(partita)
        parcel = CatastoParcel(
            comune_codice="A357",
            comune_nome="ARBOREA",
            foglio="25",
            particella="215",
            subalterno=None,
            valid_from=2025,
            source="ruolo_import",
        )
        db.add(parcel)
        db.flush()
        ruolo_particella = RuoloParticella(
            partita_id=partita.id,
            anno_tributario=2025,
            foglio="25",
            particella="215",
            subalterno=None,
            catasto_parcel_id=parcel.id,
            cat_particella_match_status="unmatched",
            cat_particella_match_reason="no_cat_particella_match",
        )
        db.add(ruolo_particella)
        db.commit()

        result = create_ade_status_scan_batch(db, user_id=user.id, limit=10)
        request = db.query(CatastoVisuraRequest).filter(CatastoVisuraRequest.purpose == ADE_SCAN_PURPOSE).one()
        db.refresh(ruolo_particella)

        assert result["created"] == 1
        assert request.target_ruolo_particella_id == ruolo_particella.id
        assert request.comune == "Arborea"
        assert request.sezione == "C"
        assert request.foglio == "25"
        assert request.particella == "215"
        assert request.request_type == "STORICA"
        assert request.tipo_visura == "Sintetica"
        assert ruolo_particella.ade_scan_status == "pending"
        assert ruolo_particella.ade_scan_request_id == request.id
    finally:
        db.close()


def test_create_ade_status_scan_batch_without_limit_queues_all_unmatched_ruolo_particelle() -> None:
    db = TestingSessionLocal()
    try:
        user = db.query(ApplicationUser).filter(ApplicationUser.username == "worker").one()
        db.add(
            ElaborazioneCredential(
                user_id=user.id,
                label="SISTER test",
                sister_username="test-user",
                sister_password_encrypted=get_credential_fernet().encrypt(b"test-password"),
                ufficio_provinciale="ORISTANO Territorio",
                active=True,
                is_default=True,
            )
        )
        import_job = RuoloImportJob(anno_tributario=2025, filename="storico_ruolo_2025", status="completed")
        db.add(import_job)
        db.flush()
        avviso = RuoloAvviso(import_job_id=import_job.id, codice_cnc="CNC1", anno_tributario=2025)
        db.add(avviso)
        db.flush()
        partita = RuoloPartita(
            avviso_id=avviso.id,
            codice_partita="0000000",
            comune_nome="ARBOREA",
            comune_codice="A357",
        )
        db.add(partita)
        parcel_one = CatastoParcel(
            comune_codice="A357",
            comune_nome="ARBOREA",
            foglio="25",
            particella="215",
            subalterno=None,
            valid_from=2025,
            source="ruolo_import",
        )
        parcel_two = CatastoParcel(
            comune_codice="A357",
            comune_nome="ARBOREA",
            foglio="25",
            particella="216",
            subalterno=None,
            valid_from=2025,
            source="ruolo_import",
        )
        db.add_all([parcel_one, parcel_two])
        db.flush()
        ruolo_particella_one = RuoloParticella(
            partita_id=partita.id,
            anno_tributario=2025,
            foglio="25",
            particella="215",
            subalterno=None,
            catasto_parcel_id=parcel_one.id,
            cat_particella_match_status="unmatched",
            cat_particella_match_reason="no_cat_particella_match",
        )
        ruolo_particella_two = RuoloParticella(
            partita_id=partita.id,
            anno_tributario=2025,
            foglio="25",
            particella="216",
            subalterno=None,
            catasto_parcel_id=parcel_two.id,
            cat_particella_match_status="unmatched",
            cat_particella_match_reason="no_cat_particella_match",
        )
        db.add_all([ruolo_particella_one, ruolo_particella_two])
        db.commit()

        result = create_ade_status_scan_batch(db, user_id=user.id)
        requests = (
            db.query(CatastoVisuraRequest)
            .filter(CatastoVisuraRequest.purpose == ADE_SCAN_PURPOSE)
            .order_by(CatastoVisuraRequest.row_index.asc())
            .all()
        )
        db.refresh(ruolo_particella_one)
        db.refresh(ruolo_particella_two)

        assert result["created"] == 2
        assert len(requests) == 2
        assert requests[0].target_ruolo_particella_id == ruolo_particella_one.id
        assert requests[1].target_ruolo_particella_id == ruolo_particella_two.id
        assert ruolo_particella_one.ade_scan_status == "pending"
        assert ruolo_particella_two.ade_scan_status == "pending"
    finally:
        db.close()


def test_worker_persists_ade_scan_document_and_parsed_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(worker_module, "SessionLocal", TestingSessionLocal)
    fixture_path = Path(__file__).resolve().parents[2] / "data-example" / "DOC_1998356604.pdf"

    db = TestingSessionLocal()
    try:
        user = db.query(ApplicationUser).filter(ApplicationUser.username == "worker").one()
        import_job = RuoloImportJob(anno_tributario=2025, filename="storico_ruolo_2025", status="completed")
        db.add(import_job)
        db.flush()
        avviso = RuoloAvviso(import_job_id=import_job.id, codice_cnc="CNC1", anno_tributario=2025)
        db.add(avviso)
        db.flush()
        partita = RuoloPartita(
            avviso_id=avviso.id,
            codice_partita="0000000",
            comune_nome="ARBOREA",
            comune_codice="A357",
        )
        db.add(partita)
        db.flush()
        ruolo_particella = RuoloParticella(
            partita_id=partita.id,
            anno_tributario=2025,
            foglio="25",
            particella="215",
            cat_particella_match_status="unmatched",
            cat_particella_match_reason="no_cat_particella_match",
        )
        db.add(ruolo_particella)
        batch = CatastoBatch(
            user_id=user.id,
            name="Visure storiche test",
            status="processing",
            total_items=1,
        )
        db.add(batch)
        db.flush()
        request = CatastoVisuraRequest(
            batch_id=batch.id,
            user_id=user.id,
            row_index=1,
            purpose=ADE_SCAN_PURPOSE,
            target_ruolo_particella_id=ruolo_particella.id,
            search_mode="immobile",
            comune="Arborea",
            comune_codice="A357#ARBOREA#3#0",
            catasto="Terreni",
            sezione="C",
            foglio="25",
            particella="215",
            tipo_visura="Sintetica",
            request_type="STORICA",
            status=CatastoVisuraRequestStatus.PROCESSING.value,
        )
        db.add(request)
        db.commit()
        batch_id = batch.id
        request_id = request.id
        ruolo_particella_id = ruolo_particella.id
    finally:
        db.close()

    worker = worker_module.CatastoWorker.__new__(worker_module.CatastoWorker)
    worker._persist_flow_result(
        batch_id,
        request_id,
        "SISTERUSER",
        worker_module.VisuraFlowResult(
            status="completed",
            file_path=fixture_path,
            file_size=fixture_path.stat().st_size,
        ),
    )

    db = TestingSessionLocal()
    try:
        request = db.get(CatastoVisuraRequest, request_id)
        ruolo_particella = db.get(RuoloParticella, ruolo_particella_id)
        document = db.query(CatastoDocument).filter(CatastoDocument.request_id == request_id).one()

        assert request is not None
        assert ruolo_particella is not None
        assert request.status == CatastoVisuraRequestStatus.COMPLETED.value
        assert request.document_id == document.id
        assert document.filename == "DOC_1998356604.pdf"
        assert document.request_type == "STORICA"
        assert document.tipo_visura == "Sintetica"
        assert ruolo_particella.ade_scan_status == "completed"
        assert ruolo_particella.ade_scan_classification == "suppressed"
        assert ruolo_particella.ade_scan_request_id == request_id
        assert ruolo_particella.ade_scan_document_id == document.id
        assert ruolo_particella.ade_scan_checked_at is not None
        assert ruolo_particella.ade_scan_payload_json["suppression"]["suppressed_from"] == "11/07/2019"
        assert ruolo_particella.ade_scan_payload_json["originated_or_varied_parcels"] == [
            {"foglio": "25", "particella": "243", "subalterno": None},
            {"foglio": "25", "particella": "244", "subalterno": None},
        ]
    finally:
        db.close()
