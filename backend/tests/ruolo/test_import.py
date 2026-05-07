import asyncio
from collections.abc import Generator
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.ruolo.models import RuoloAvviso
from app.modules.ruolo.services import import_service as import_service_module
from app.modules.ruolo.services.import_service import (
    check_anno_already_imported,
    create_import_job,
)
from app.modules.ruolo.services.parser import ParsedPartitaCNC
from app.modules.utenze.models import AnagraficaPerson, AnagraficaSubject


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
    monkeypatch.setattr(import_service_module, "SessionLocal", TestingSessionLocal)

    db = TestingSessionLocal()
    db.add(
        ApplicationUser(
            username="ruolo-import-admin",
            email="ruolo-import@example.local",
            password_hash=hash_password("secret123"),
            role=ApplicationUserRole.ADMIN.value,
            is_active=True,
            module_ruolo=True,
        )
    )
    db.commit()
    db.close()

    yield

    Base.metadata.drop_all(bind=engine)


def _build_partita_cnc(codice_cnc: str, codice_fiscale_raw: str, nominativo_raw: str) -> ParsedPartitaCNC:
    return ParsedPartitaCNC(
        codice_cnc=codice_cnc,
        codice_fiscale_raw=codice_fiscale_raw,
        n2_extra_raw="00000000 00 N",
        nominativo_raw=nominativo_raw,
        domicilio_raw="VIA TEST 1",
        residenza_raw="VIA TEST 1",
        codice_utenza="025000001",
        importo_totale_0648=Decimal("10.00"),
        importo_totale_0985=Decimal("5.00"),
        importo_totale_0668=None,
        importo_totale_euro=Decimal("15.00"),
        importo_totale_lire=None,
        n4_campo_sconosciuto="100.000",
        partite=[],
    )


def test_run_import_job_records_skipped_subject_not_found_and_report_preview(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = TestingSessionLocal()
    job = create_import_job(
        db,
        anno_tributario=2025,
        filename="R2025.14215.00002.dmp",
        triggered_by=1,
    )
    db.commit()
    job_id = job.id
    db.close()

    payload = [_build_partita_cnc("01.02025000000101", "MCCPLA69E23F272E", "MACCIONI PAOLO")]
    monkeypatch.setattr(import_service_module, "extract_text_from_content", lambda *_args, **_kwargs: "RAW")
    monkeypatch.setattr(import_service_module, "parse_ruolo_file", lambda _text: payload)

    asyncio.run(import_service_module.run_import_job(job_id, b"raw", 2025, filename="R2025.14215.00002.dmp"))

    db = TestingSessionLocal()
    saved_job = db.get(import_service_module.RuoloImportJob, job_id)
    assert saved_job is not None
    assert saved_job.status == "completed"
    assert saved_job.records_imported == 0
    assert saved_job.records_skipped == 1
    assert saved_job.records_errors == 0
    assert saved_job.total_partite == 1
    assert saved_job.params_json is not None
    assert saved_job.params_json["report_summary"]["records_skipped"] == 1
    skipped_items = saved_job.params_json["report_preview"]["skipped_items"]
    assert len(skipped_items) == 1
    assert skipped_items[0]["codice_cnc"] == "01.02025000000101"
    assert skipped_items[0]["reason_code"] == "subject_not_found"
    assert skipped_items[0]["reason_label"] == "Soggetto non trovato in Anagrafica"
    assert check_anno_already_imported(db, 2025) == 1
    db.close()


def test_run_import_job_records_imported_when_subject_is_resolved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = TestingSessionLocal()
    subject = AnagraficaSubject(
        source_name_raw="MACCIONI PAOLO",
        subject_type="person",
        source_system="gaia",
    )
    db.add(subject)
    db.flush()
    subject_id = subject.id
    db.add(
        AnagraficaPerson(
            subject_id=subject.id,
            cognome="MACCIONI",
            nome="PAOLO",
            codice_fiscale="MCCPLA69E23F272E",
        )
    )
    job = create_import_job(
        db,
        anno_tributario=2025,
        filename="R2025.14215.00002.dmp",
        triggered_by=1,
    )
    db.commit()
    job_id = job.id
    db.close()

    payload = [_build_partita_cnc("01.02025000000101", "MCCPLA69E23F272E", "MACCIONI PAOLO")]
    monkeypatch.setattr(import_service_module, "extract_text_from_content", lambda *_args, **_kwargs: "RAW")
    monkeypatch.setattr(import_service_module, "parse_ruolo_file", lambda _text: payload)

    asyncio.run(import_service_module.run_import_job(job_id, b"raw", 2025, filename="R2025.14215.00002.dmp"))

    db = TestingSessionLocal()
    saved_job = db.get(import_service_module.RuoloImportJob, job_id)
    avvisi = db.query(RuoloAvviso).all()
    assert saved_job is not None
    assert saved_job.records_imported == 1
    assert saved_job.records_skipped == 0
    assert saved_job.records_errors == 0
    assert saved_job.params_json is not None
    assert saved_job.params_json["report_preview"]["skipped_items"] == []
    assert len(avvisi) == 1
    assert avvisi[0].subject_id == subject_id
    db.close()


def test_run_import_job_records_error_preview_when_partita_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = TestingSessionLocal()
    job = create_import_job(
        db,
        anno_tributario=2025,
        filename="R2025.14215.00002.dmp",
        triggered_by=1,
    )
    db.commit()
    job_id = job.id
    db.close()

    payload = [_build_partita_cnc("01.02025000000999", "RSSMRA80A01H501U", "ROSSI MARIA")]
    monkeypatch.setattr(import_service_module, "extract_text_from_content", lambda *_args, **_kwargs: "RAW")
    monkeypatch.setattr(import_service_module, "parse_ruolo_file", lambda _text: payload)
    monkeypatch.setattr(
        import_service_module,
        "_upsert_partite",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("errore test particelle")),
    )

    asyncio.run(import_service_module.run_import_job(job_id, b"raw", 2025, filename="R2025.14215.00002.dmp"))

    db = TestingSessionLocal()
    saved_job = db.get(import_service_module.RuoloImportJob, job_id)
    assert saved_job is not None
    assert saved_job.records_imported == 0
    assert saved_job.records_skipped == 0
    assert saved_job.records_errors == 1
    assert saved_job.error_detail is not None
    assert "CNC 01.02025000000999" in saved_job.error_detail
    error_items = saved_job.params_json["report_preview"]["error_items"]
    assert len(error_items) == 1
    assert error_items[0]["codice_cnc"] == "01.02025000000999"
    assert error_items[0]["reason_code"] == "import_error"
    assert "errore test particelle" in error_items[0]["reason_label"]
    db.close()
