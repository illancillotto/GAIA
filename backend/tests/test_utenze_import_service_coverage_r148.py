"""Behavioural coverage of the utenze NAS import service (R148).

Every test drives a public or worker-facing entry point of
``app.modules.utenze.services.import_service`` against an in-memory database
and a fake NAS connector, and asserts the returned values, error messages and
persisted rows.
"""

import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.core.database as core_database
from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.utenze.models import (
    AnagraficaAuditLog,
    AnagraficaCompany,
    AnagraficaDocument,
    AnagraficaImportJob,
    AnagraficaImportJobItem,
    AnagraficaPerson,
    AnagraficaSubject,
)
from app.modules.utenze.services import import_service
from app.modules.utenze.services.import_service import (
    AnagraficaImportPreviewService,
    create_import_snapshot,
    create_manual_document,
    delete_registry_import_job,
    finalize_stuck_registry_import_job,
    import_existing_registry_subjects,
    import_subject_from_existing_registry,
    prepare_registry_import_jobs_for_recovery,
    process_import_job,
    process_import_job_async,
    process_registry_bulk_import_job,
    queue_resume_registry_bulk_import_job,
    reset_anagrafica_data,
    run_import,
    run_registry_bulk_import_job_by_id,
)
from app.services.nas_connector import NasConnectorError

ROOT = "/archive"


def dirs_cmd(path: str) -> str:
    return f"find '{path}' -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort"


def files_cmd(path: str) -> str:
    return f"find '{path}' -type f 2>/dev/null | sort"


class FakeNasConnector:
    def __init__(
        self,
        outputs: dict[str, str] | None = None,
        failing_commands: set[str] | None = None,
    ) -> None:
        self.outputs = outputs or {}
        self.failing_commands = failing_commands or set()
        self.closed = 0

    def run_command(self, command: str) -> str:
        if command in self.failing_commands:
            raise NasConnectorError(f"command failed: {command}")
        return self.outputs.get(command, "")

    def close(self) -> None:
        self.closed += 1


class UploadConnector:
    """NAS connector without ``close`` that records uploads."""

    def __init__(self, existing_paths: set[str]) -> None:
        self.existing_paths = existing_paths
        self.ensured: list[str] = []
        self.checked: list[str] = []
        self.uploads: dict[str, bytes] = {}

    def ensure_directory(self, path: str) -> None:
        self.ensured.append(path)

    def path_exists(self, path: str) -> bool:
        self.checked.append(path)
        return path in self.existing_paths

    def upload_file(self, path: str, content: bytes) -> None:
        self.uploads[path] = content


@pytest.fixture
def session_factory() -> Iterator[sessionmaker]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    try:
        yield factory
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def db_session(session_factory: sessionmaker) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def create_user(db: Session) -> ApplicationUser:
    user = ApplicationUser(
        username="r148_admin",
        email="r148_admin@example.local",
        password_hash=hash_password("secret123"),
        role=ApplicationUserRole.ADMIN.value,
        is_active=True,
        module_accessi=True,
        module_utenze=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def add_subject(db: Session, source_name_raw: str, **fields: object) -> AnagraficaSubject:
    subject = AnagraficaSubject(source_name_raw=source_name_raw, **fields)
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject


def add_person(
    db: Session,
    source_name_raw: str,
    cognome: str,
    nome: str,
    codice_fiscale: str,
    **fields: object,
) -> AnagraficaSubject:
    subject = add_subject(db, source_name_raw, **fields)
    db.add(
        AnagraficaPerson(
            subject_id=subject.id, cognome=cognome, nome=nome, codice_fiscale=codice_fiscale
        )
    )
    db.commit()
    return subject


def add_company(
    db: Session,
    source_name_raw: str,
    ragione_sociale: str,
    partita_iva: str,
    codice_fiscale: str | None,
) -> AnagraficaSubject:
    subject = add_subject(db, source_name_raw)
    db.add(
        AnagraficaCompany(
            subject_id=subject.id,
            ragione_sociale=ragione_sociale,
            partita_iva=partita_iva,
            codice_fiscale=codice_fiscale,
        )
    )
    db.commit()
    return subject


def add_registry_job(
    db: Session,
    *,
    requested_by_user_id: int | None,
    status: str = "pending",
    letter: str = "REGISTRY",
    log_json: object = None,
    total_folders: int = 0,
) -> AnagraficaImportJob:
    job = AnagraficaImportJob(
        requested_by_user_id=requested_by_user_id,
        letter=letter,
        status=status,
        total_folders=total_folders,
        log_json=log_json,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def add_item(
    db: Session,
    job: AnagraficaImportJob,
    status: str,
    *,
    subject_id: uuid.UUID | None = None,
    folder_name: str = "folder",
) -> AnagraficaImportJobItem:
    item = AnagraficaImportJobItem(
        job_id=job.id,
        subject_id=subject_id,
        letter="A",
        folder_name=folder_name,
        nas_folder_path=f"/archive/A/{folder_name}",
        status=status,
        last_error="old error",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


# --- folder discovery -------------------------------------------------------


def test_discover_full_archive_reraises_root_listing_failure() -> None:
    connector = FakeNasConnector(failing_commands={dirs_cmd(ROOT)})
    service = AnagraficaImportPreviewService(connector, archive_root=ROOT)

    with pytest.raises(NasConnectorError, match="command failed: find '/archive'"):
        service.discover_subject_folders()


def test_discover_full_archive_derives_letter_for_root_level_named_folder() -> None:
    connector = FakeNasConnector(
        {
            dirs_cmd(ROOT): "/archive/zedda_Srl_12345678901\n/archive/__1__",
            files_cmd("/archive/zedda_Srl_12345678901"): "/archive/zedda_Srl_12345678901/a.pdf",
        }
    )
    service = AnagraficaImportPreviewService(connector, archive_root=ROOT)

    folders = service.discover_subject_folders()
    preview = service.preview_archive()

    assert [(item.folder_name, item.letter) for item in folders] == [
        ("__1__", None),
        ("zedda_Srl_12345678901", "Z"),
    ]
    assert [(item.folder_name, item.letter) for item in preview.subjects] == [
        ("__1__", "?"),
        ("zedda_Srl_12345678901", "Z"),
    ]


def test_preview_skips_synology_stream_files_outside_eadir() -> None:
    folder = "/archive/A/Atzori_Mario_TZRMRA80A01H501Z"
    connector = FakeNasConnector(
        {
            dirs_cmd("/archive/A"): folder,
            files_cmd(folder): f"{folder}/doc.pdf@SynoEAStream\n{folder}/doc.pdf",
        }
    )

    result = AnagraficaImportPreviewService(connector, archive_root=ROOT).preview_letter("A")

    assert [document.nas_path for document in result.subjects[0].documents] == [f"{folder}/doc.pdf"]


# --- matching existing subjects ----------------------------------------------


def test_match_without_derivable_letter_raises_and_status_reports_missing(
    db_session: Session,
) -> None:
    subject = add_subject(db_session, "1234 - 99")
    service = AnagraficaImportPreviewService(FakeNasConnector(), archive_root=ROOT)

    with pytest.raises(ValueError, match="Impossibile derivare la lettera archivio del soggetto"):
        service.match_existing_subject_folder(db_session, subject)

    status = service.get_subject_import_status(db_session, subject)
    assert status.can_import_from_nas is False
    assert status.missing_in_nas is True
    assert status.matched_folder_path is None
    assert status.message == "Impossibile derivare la lettera archivio del soggetto"
    assert service.list_existing_subject_folder_candidates(db_session, subject) == []


def test_match_without_identifiers_and_without_positive_score_raises(db_session: Session) -> None:
    subject = add_subject(db_session, "Rossi Mario")
    connector = FakeNasConnector({dirs_cmd("/archive/R"): "/archive/R/Verdi_Luca"})
    service = AnagraficaImportPreviewService(connector, archive_root=ROOT)

    with pytest.raises(ValueError) as exc_info:
        service.match_existing_subject_folder(db_session, subject)

    assert (
        str(exc_info.value)
        == f"Nessuna cartella NAS compatibile trovata per il soggetto {subject.id}"
    )
    assert service.list_existing_subject_folder_candidates(db_session, subject) == []


def test_candidates_are_empty_when_primary_identifier_matches_no_folder(
    db_session: Session,
) -> None:
    subject = add_person(db_session, "Rossi Mario", "Rossi", "Mario", "RSSMRA80A01H501U")
    connector = FakeNasConnector(
        {dirs_cmd("/archive/R"): "/archive/R/Rossi_Mario_XXXXXX00X00X000X"}
    )
    service = AnagraficaImportPreviewService(connector, archive_root=ROOT)

    assert service.list_existing_subject_folder_candidates(db_session, subject) == []


def test_company_primary_identifiers_select_strict_candidates(db_session: Session) -> None:
    full = add_company(db_session, "Olati Srl", "Olati Srl", "14542661005", "97000000001")
    vat_only = add_company(db_session, "Olati Due Srl", "Olati Due Srl", "22222222222", None)
    tax_code_only = add_company(db_session, "Olati Tre Srl", "Olati Tre Srl", "", "33333333333")
    connector = FakeNasConnector(
        {
            dirs_cmd("/archive/O"): "\n".join(
                [
                    "/archive/O/Olati_Srl_14542661005",
                    "/archive/O/Olati_Srl_97000000001",
                    "/archive/O/Olati_Due_Srl_22222222222",
                    "/archive/O/Olati_Tre_Srl_33333333333",
                ]
            )
        }
    )
    service = AnagraficaImportPreviewService(connector, archive_root=ROOT)

    full_candidates = service.list_existing_subject_folder_candidates(db_session, full)
    assert [(item.folder_name, item.score) for item in full_candidates] == [
        ("Olati_Srl_14542661005", 770),
        ("Olati_Srl_97000000001", 520),
    ]
    assert full_candidates[0].subject_type == "company"
    assert full_candidates[0].partita_iva == "14542661005"
    assert full_candidates[0].ragione_sociale == "Olati Srl"

    assert service.match_existing_subject_folder(db_session, vat_only).folder_name == (
        "Olati_Due_Srl_22222222222"
    )
    assert service.match_existing_subject_folder(db_session, tax_code_only).folder_name == (
        "Olati_Tre_Srl_33333333333"
    )


def test_status_reports_folder_without_importable_files(db_session: Session) -> None:
    folder = "/archive/Z/Zeta_Vuota"
    subject = add_subject(db_session, "Zeta Vuota", nas_folder_path=folder)
    service = AnagraficaImportPreviewService(FakeNasConnector(), archive_root=ROOT)

    matched = service.match_existing_subject_folder(db_session, subject)
    status = service.get_subject_import_status(db_session, subject)

    assert (matched.folder_name, matched.letter, matched.nas_folder_path) == (
        "Zeta_Vuota",
        "Z",
        folder,
    )
    assert status.can_import_from_nas is False
    assert status.missing_in_nas is False
    assert status.matched_folder_path == folder
    assert status.matched_folder_name == "Zeta_Vuota"
    assert status.total_files_in_nas == 0
    assert status.pending_files_in_nas == 0
    assert status.message == "Cartella NAS trovata ma senza file importabili."


def test_status_counts_pending_and_already_imported_files(db_session: Session) -> None:
    folder = "/archive/R/Rossi_Mario_RSSMRA80A01H501U"
    subject = add_person(
        db_session,
        "Rossi Mario",
        "Rossi",
        "Mario",
        "RSSMRA80A01H501U",
        nas_folder_path=folder,
        nas_folder_letter="R",
    )
    connector = FakeNasConnector({files_cmd(folder): f"{folder}/a.pdf\n{folder}/b.pdf"})
    service = AnagraficaImportPreviewService(connector, archive_root=ROOT)
    db_session.add(
        AnagraficaDocument(
            subject_id=subject.id,
            doc_type="altro",
            filename="a.pdf",
            nas_path=f"{folder}/a.pdf",
            classification_source="auto",
            storage_type="nas_link",
        )
    )
    db_session.commit()

    pending = service.get_subject_import_status(db_session, subject)
    assert pending.can_import_from_nas is True
    assert pending.total_files_in_nas == 2
    assert pending.pending_files_in_nas == 1
    assert pending.message == "Trovati 1 file NAS ancora da importare."

    db_session.add(
        AnagraficaDocument(
            subject_id=subject.id,
            doc_type="altro",
            filename="b.pdf",
            nas_path=f"{folder}/b.pdf",
            classification_source="auto",
            storage_type="nas_link",
        )
    )
    db_session.commit()

    imported = service.get_subject_import_status(db_session, subject)
    assert imported.can_import_from_nas is False
    assert imported.total_files_in_nas == 2
    assert imported.pending_files_in_nas == 0
    assert imported.message == "Tutti i file NAS disponibili risultano gia importati."


def test_import_subject_from_registry_rejects_unknown_subject_and_closes_connector(
    db_session: Session,
) -> None:
    connector = FakeNasConnector()
    user = create_user(db_session)

    with pytest.raises(ValueError, match="Subject not found"):
        import_subject_from_existing_registry(
            db_session,
            user,
            uuid.uuid4(),
            service=AnagraficaImportPreviewService(connector, archive_root=ROOT),
        )

    assert connector.closed == 1


# --- snapshot -----------------------------------------------------------------


def test_create_import_snapshot_serializes_preview_warnings_and_errors(db_session: Session) -> None:
    good = "/archive/O/Olati_Srl_14542661005"
    bad = "/archive/O/Orru_Anna_RRONNA80A41H501X"
    connector = FakeNasConnector(
        {dirs_cmd("/archive/O"): f"{good}\n{bad}", files_cmd(good): f"{good}/foto.png"},
        failing_commands={files_cmd(bad)},
    )
    user = create_user(db_session)

    result = create_import_snapshot(
        db_session, user, "o", service=AnagraficaImportPreviewService(connector, archive_root=ROOT)
    )

    assert result.letter == "O"
    assert result.imported_errors == 1
    assert result.log_json["warnings"] == [
        {
            "code": "non_pdf_document_detected",
            "message": "File non-PDF rilevato: foto.png",
            "path": f"{good}/foto.png",
        }
    ]
    assert result.log_json["errors"] == [
        {"code": "folder_scan_failed", "message": f"command failed: {files_cmd(bad)}", "path": bad}
    ]
    assert connector.closed == 1


# --- letter import jobs -------------------------------------------------------


def test_run_import_sets_document_mime_types_by_extension(db_session: Session) -> None:
    folder = "/archive/O/Olati_Srl_14542661005"
    names = ["a.pdf", "b.gif", "c.png", "d.jpg", "e.jpeg", "f.txt", "g"]
    connector = FakeNasConnector(
        {
            dirs_cmd("/archive/O"): folder,
            files_cmd(folder): "\n".join(f"{folder}/{name}" for name in names),
        }
    )
    user = create_user(db_session)

    run_import(
        db_session, user, "O", service=AnagraficaImportPreviewService(connector, archive_root=ROOT)
    )

    documents = {doc.filename: doc for doc in db_session.scalars(select(AnagraficaDocument)).all()}
    assert {name: documents[name].mime_type for name in names} == {
        "a.pdf": "application/pdf",
        "b.gif": "image/gif",
        "c.png": "image/png",
        "d.jpg": "image/jpeg",
        "e.jpeg": "image/jpeg",
        "f.txt": None,
        "g": None,
    }
    assert documents["a.pdf"].notes is None
    assert documents["c.png"].notes == "unsupported_preview_extension"


def test_run_import_replaces_company_details_with_person_details(db_session: Session) -> None:
    folder = "/archive/R/Rossi_Mario_RSSMRA80A01H501U"
    subject = add_company(db_session, "Rossi Srl", "Rossi Srl", "12345678901", None)
    subject.nas_folder_path = folder
    db_session.commit()
    connector = FakeNasConnector({dirs_cmd("/archive/R"): folder})
    user = create_user(db_session)

    result = run_import(
        db_session, user, "R", service=AnagraficaImportPreviewService(connector, archive_root=ROOT)
    )

    assert (result.created_subjects, result.updated_subjects) == (0, 1)
    assert db_session.get(AnagraficaCompany, subject.id) is None
    person = db_session.get(AnagraficaPerson, subject.id)
    assert (person.cognome, person.nome, person.codice_fiscale) == (
        "Rossi",
        "Mario",
        "RSSMRA80A01H501U",
    )
    assert db_session.get(AnagraficaSubject, subject.id).subject_type == "person"


def test_run_import_replaces_person_details_with_company_details(db_session: Session) -> None:
    folder = "/archive/O/Olati_Srl_14542661005"
    subject = add_person(
        db_session, "Olati", "Olati", "Ugo", "LTOUGO80A01H501U", nas_folder_path=folder
    )
    connector = FakeNasConnector({dirs_cmd("/archive/O"): folder})
    user = create_user(db_session)

    run_import(
        db_session, user, "O", service=AnagraficaImportPreviewService(connector, archive_root=ROOT)
    )

    assert db_session.get(AnagraficaPerson, subject.id) is None
    company = db_session.get(AnagraficaCompany, subject.id)
    assert (company.ragione_sociale, company.partita_iva) == ("Olati Srl", "14542661005")


def test_run_import_unknown_folder_drops_person_and_company_details(db_session: Session) -> None:
    folder = "/archive/T/TELERILEVAMENTO"
    subject = add_person(
        db_session, "Tele", "Tele", "Rilevamento", "TLERLV80A01H501U", nas_folder_path=folder
    )
    db_session.add(
        AnagraficaCompany(
            subject_id=subject.id, ragione_sociale="Tele Srl", partita_iva="12345678901"
        )
    )
    db_session.commit()
    connector = FakeNasConnector({dirs_cmd("/archive/T"): folder})
    user = create_user(db_session)

    result = run_import(
        db_session, user, "T", service=AnagraficaImportPreviewService(connector, archive_root=ROOT)
    )

    assert result.status == "completed"
    assert db_session.get(AnagraficaPerson, subject.id) is None
    assert db_session.get(AnagraficaCompany, subject.id) is None
    refreshed = db_session.get(AnagraficaSubject, subject.id)
    assert (refreshed.subject_type, refreshed.requires_review) == ("unknown", True)


def test_run_import_creates_unknown_subject_without_details(db_session: Session) -> None:
    folder = "/archive/T/TELERILEVAMENTO"
    connector = FakeNasConnector({dirs_cmd("/archive/T"): folder})
    user = create_user(db_session)

    result = run_import(
        db_session, user, "T", service=AnagraficaImportPreviewService(connector, archive_root=ROOT)
    )

    assert (result.created_subjects, result.updated_subjects) == (1, 0)
    subject = db_session.scalars(select(AnagraficaSubject)).one()
    assert (subject.subject_type, subject.nas_folder_path) == ("unknown", folder)
    assert db_session.get(AnagraficaPerson, subject.id) is None
    assert db_session.get(AnagraficaCompany, subject.id) is None


def test_process_import_job_rejects_unknown_job(db_session: Session) -> None:
    user = create_user(db_session)
    connector = FakeNasConnector()

    with pytest.raises(ValueError, match="Import job not found"):
        process_import_job(
            db_session,
            user,
            uuid.uuid4(),
            None,
            service=AnagraficaImportPreviewService(connector, archive_root=ROOT),
        )


def test_process_import_job_async_runs_job_for_existing_user(
    session_factory: sessionmaker, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = "/archive/O/Olati_Srl_14542661005"
    connector = FakeNasConnector(
        {dirs_cmd("/archive/O"): folder, files_cmd(folder): f"{folder}/a.pdf"}
    )
    monkeypatch.setattr(import_service, "get_nas_client", lambda: connector)
    monkeypatch.setattr(settings, "utenze_nas_archive_root", ROOT)
    setup = session_factory()
    user = create_user(setup)
    job = import_service.enqueue_import(
        setup,
        user,
        "O",
        service=AnagraficaImportPreviewService(
            FakeNasConnector(connector.outputs), archive_root=ROOT
        ),
    )
    job_id, user_id = job.id, user.id
    setup.close()

    process_import_job_async(job_id, user_id, "O", session_factory)

    check = session_factory()
    try:
        stored = check.get(AnagraficaImportJob, job_id)
        assert (stored.status, stored.imported_ok, stored.imported_errors) == ("completed", 1, 0)
        assert check.scalars(select(AnagraficaDocument.nas_path)).all() == [f"{folder}/a.pdf"]
    finally:
        check.close()
    assert connector.closed == 1


def test_process_import_job_async_ignores_missing_user(
    session_factory: sessionmaker, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_nas_client() -> None:
        raise AssertionError("NAS must not be contacted for a missing user")

    monkeypatch.setattr(import_service, "get_nas_client", fail_nas_client)
    setup = session_factory()
    job = add_registry_job(setup, requested_by_user_id=None, letter="O", status="pending")
    job_id = job.id
    setup.close()

    assert process_import_job_async(job_id, 4242, "O", session_factory) is None

    check = session_factory()
    try:
        assert check.get(AnagraficaImportJob, job_id).status == "pending"
    finally:
        check.close()


# --- registry jobs --------------------------------------------------------------


def test_queue_resume_ignores_missing_and_non_registry_jobs(db_session: Session) -> None:
    letter_job = add_registry_job(
        db_session, requested_by_user_id=None, letter="A", status="failed"
    )

    assert queue_resume_registry_bulk_import_job(db_session, uuid.uuid4()) is None
    assert queue_resume_registry_bulk_import_job(db_session, letter_job.id) is None
    db_session.refresh(letter_job)
    assert letter_job.status == "failed"


def test_queue_resume_requeues_processing_items_and_keeps_log(db_session: Session) -> None:
    job = add_registry_job(
        db_session,
        requested_by_user_id=None,
        status="failed",
        log_json={"mode": "registry_import", "errors": ["x"]},
    )
    processing = add_item(db_session, job, "processing", folder_name="p")
    completed = add_item(db_session, job, "completed", folder_name="c")

    result = queue_resume_registry_bulk_import_job(db_session, job.id)

    assert result is not None
    assert (result.status, result.started_at, result.completed_at) == ("pending", None, None)
    assert result.log_json["mode"] == "registry_import_resume"
    assert result.log_json["errors"] == ["x"]
    assert "queued_at" in result.log_json
    db_session.refresh(processing)
    db_session.refresh(completed)
    assert (processing.status, processing.last_error) == ("pending", None)
    assert (completed.status, completed.last_error) == ("completed", "old error")


def test_queue_resume_replaces_non_dict_log(db_session: Session) -> None:
    job = add_registry_job(
        db_session, requested_by_user_id=None, status="failed", log_json=["legacy"]
    )

    result = queue_resume_registry_bulk_import_job(db_session, job.id)

    assert set(result.log_json) == {"mode", "queued_at"}


def test_prepare_recovery_resets_running_registry_jobs(db_session: Session) -> None:
    running = add_registry_job(
        db_session,
        requested_by_user_id=None,
        status="running",
        log_json={"trigger": "worker_schedule"},
    )
    legacy = add_registry_job(
        db_session, requested_by_user_id=None, status="running", log_json=None
    )
    add_registry_job(db_session, requested_by_user_id=None, status="completed")
    processing = add_item(db_session, running, "processing", folder_name="p")
    completed = add_item(db_session, running, "completed", folder_name="c")

    recovered = prepare_registry_import_jobs_for_recovery(db_session)
    db_session.commit()

    assert set(recovered) == {running.id, legacy.id}
    db_session.refresh(running)
    db_session.refresh(legacy)
    assert running.status == "pending"
    assert running.log_json["trigger"] == "worker_schedule"
    assert running.log_json["mode"] == "registry_import_resume"
    assert "recovered_at" in running.log_json
    assert set(legacy.log_json) == {"mode", "recovered_at"}
    db_session.refresh(processing)
    db_session.refresh(completed)
    assert (processing.status, completed.status) == ("pending", "completed")


def test_prepare_recovery_without_running_jobs_returns_empty(db_session: Session) -> None:
    add_registry_job(db_session, requested_by_user_id=None, status="pending")

    assert prepare_registry_import_jobs_for_recovery(db_session) == []


def test_process_registry_job_ignores_missing_and_non_registry_jobs(db_session: Session) -> None:
    letter_job = add_registry_job(
        db_session, requested_by_user_id=None, letter="A", status="pending"
    )

    assert process_registry_bulk_import_job(db_session, uuid.uuid4()) is None
    assert process_registry_bulk_import_job(db_session, letter_job.id) is None
    db_session.refresh(letter_job)
    assert letter_job.status == "pending"


@pytest.mark.parametrize(
    ("log_json", "expected_errors"),
    [
        ({"errors": [{"message": "previous"}]}, [{"message": "previous"}]),
        ({"errors": "not-a-list"}, []),
        (None, []),
    ],
)
def test_process_registry_job_without_valid_actor_fails(
    db_session: Session, log_json: object, expected_errors: list[dict[str, str]]
) -> None:
    job = add_registry_job(db_session, requested_by_user_id=None, log_json=log_json)

    process_registry_bulk_import_job(db_session, job.id)

    db_session.refresh(job)
    assert job.status == "failed"
    assert job.completed_at is not None
    assert job.log_json["errors"] == [
        *expected_errors,
        {"message": "Utente richiedente non disponibile: impossibile eseguire il job REGISTRY."},
    ]


def test_run_registry_job_by_id_uses_worker_session(
    session_factory: sessionmaker, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(core_database, "SessionLocal", session_factory)
    setup = session_factory()
    job_id = add_registry_job(setup, requested_by_user_id=None).id
    setup.close()

    run_registry_bulk_import_job_by_id(job_id)

    check = session_factory()
    try:
        assert check.get(AnagraficaImportJob, job_id).status == "failed"
    finally:
        check.close()


def _person_with_folder(
    db: Session, cognome: str, nome: str, cf: str
) -> tuple[AnagraficaSubject, str]:
    folder = f"/archive/{cognome[0]}/{cognome}_{nome}_{cf}"
    subject = add_person(
        db,
        f"{cognome} {nome}",
        cognome,
        nome,
        cf,
        nas_folder_path=folder,
        nas_folder_letter=cognome[0],
    )
    return subject, folder


def test_process_registry_job_resume_skips_completed_subjects(db_session: Session) -> None:
    user = create_user(db_session)
    done, done_folder = _person_with_folder(db_session, "Atzori", "Mario", "TZRMRA80A01H501Z")
    todo, todo_folder = _person_with_folder(db_session, "Bianchi", "Luca", "BNCLCU80A01H501Z")
    job = add_registry_job(
        db_session,
        requested_by_user_id=user.id,
        log_json={"mode": "registry_import_resume"},
        total_folders=0,
    )
    add_item(db_session, job, "completed", subject_id=done.id, folder_name="done")
    add_item(db_session, job, "failed", subject_id=todo.id, folder_name="todo")
    connector = FakeNasConnector(
        {
            files_cmd(done_folder): f"{done_folder}/x.pdf",
            files_cmd(todo_folder): f"{todo_folder}/y.pdf",
        }
    )

    process_registry_bulk_import_job(
        db_session, job.id, service=AnagraficaImportPreviewService(connector, archive_root=ROOT)
    )

    db_session.refresh(job)
    assert job.total_folders == 2
    assert (job.status, job.imported_ok, job.imported_errors) == ("completed", 2, 0)
    items = db_session.scalars(
        select(AnagraficaImportJobItem).where(AnagraficaImportJobItem.job_id == job.id)
    ).all()
    assert sorted((item.folder_name, item.status) for item in items) == [
        ("Bianchi_Luca_BNCLCU80A01H501Z", "completed"),
        ("done", "completed"),
    ]
    assert db_session.scalars(select(AnagraficaDocument.nas_path)).all() == [f"{todo_folder}/y.pdf"]
    assert connector.closed == 1


def test_finalize_stuck_registry_job(db_session: Session) -> None:
    letter_job = add_registry_job(
        db_session, requested_by_user_id=None, letter="A", status="running"
    )
    assert finalize_stuck_registry_import_job(db_session, uuid.uuid4()) is None
    assert finalize_stuck_registry_import_job(db_session, letter_job.id) is None

    job = add_registry_job(db_session, requested_by_user_id=None, status="running")
    stuck = add_item(db_session, job, "processing", folder_name="stuck")
    ok = add_item(db_session, job, "completed", folder_name="ok")

    not_refreshed = finalize_stuck_registry_import_job(
        db_session, job.id, refresh=False, message="stop"
    )
    assert not_refreshed.status == "running"
    db_session.refresh(stuck)
    assert (stuck.status, stuck.last_error) == ("failed", "stop")
    assert stuck.completed_at is not None

    finalized = finalize_stuck_registry_import_job(db_session, job.id)
    assert (finalized.status, finalized.imported_ok, finalized.imported_errors) == ("failed", 1, 1)
    assert finalized.completed_at is not None
    assert finalized.log_json["errors"] == [
        {"folder_name": "stuck", "path": "/archive/A/stuck", "message": "stop"}
    ]
    db_session.refresh(ok)
    assert ok.status == "completed"


def test_delete_registry_job(db_session: Session) -> None:
    letter_job = add_registry_job(db_session, requested_by_user_id=None, letter="A")
    job = add_registry_job(db_session, requested_by_user_id=None)
    add_item(db_session, job, "completed")
    add_item(db_session, letter_job, "completed")

    assert delete_registry_import_job(db_session, uuid.uuid4()) is False
    assert delete_registry_import_job(db_session, letter_job.id) is False
    assert delete_registry_import_job(db_session, job.id) is True

    assert db_session.scalars(select(AnagraficaImportJob.id)).all() == [letter_job.id]
    assert db_session.scalars(select(AnagraficaImportJobItem.job_id)).all() == [letter_job.id]


def test_import_existing_registry_subjects_summarizes_items(db_session: Session) -> None:
    user = create_user(db_session)
    subject, folder = _person_with_folder(db_session, "Atzori", "Mario", "TZRMRA80A01H501Z")
    connector = FakeNasConnector({files_cmd(folder): f"{folder}/a.pdf\n{folder}/b.png"})

    result = import_existing_registry_subjects(
        db_session, user, service=AnagraficaImportPreviewService(connector, archive_root=ROOT)
    )

    assert result.letter == "REGISTRY"
    assert result.status == "completed"
    assert (result.total_folders, result.imported_ok, result.imported_errors) == (1, 1, 0)
    assert (result.created_subjects, result.updated_subjects) == (0, 1)
    assert (result.created_documents, result.updated_documents) == (2, 0)
    assert result.warning_count == 2
    assert result.log_json["created_documents"] == 2
    audit = db_session.scalars(select(AnagraficaAuditLog)).all()
    assert [(entry.subject_id, entry.action) for entry in audit] == [
        (subject.id, "bulk_import_from_registry")
    ]


# --- manual documents and reset -----------------------------------------------------


def test_create_manual_document_rejects_unknown_subject(
    db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "utenze_document_storage_path", str(tmp_path))
    user = create_user(db_session)

    with pytest.raises(ValueError, match="Subject not found"):
        create_manual_document(db_session, user, uuid.uuid4(), "a.pdf", b"x", "altro")

    assert list(tmp_path.iterdir()) == []


FOLDER_R = "/archive/R/Rossi_Mario_RSSMRA80A01H501U"


@pytest.mark.parametrize(
    ("existing", "expected_name"),
    [
        (set(), "doc.pdf"),
        ({"doc.pdf", "doc (1).pdf"}, "doc (2).pdf"),
    ],
)
def test_create_manual_document_picks_first_free_nas_name(
    db_session: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    existing: set[str],
    expected_name: str,
) -> None:
    folder = FOLDER_R
    connector = UploadConnector({f"{folder}/{name}" for name in existing})
    monkeypatch.setattr(settings, "utenze_document_storage_path", str(tmp_path))
    monkeypatch.setattr(import_service, "get_nas_client", lambda: connector)
    user = create_user(db_session)
    subject = add_subject(db_session, "Rossi Mario", nas_folder_path=folder)

    document = create_manual_document(db_session, user, subject.id, "doc.pdf", b"payload", "altro")

    expected_path = f"{folder}/{expected_name}"
    assert document.nas_path == expected_path
    assert document.mime_type == "application/pdf"
    assert connector.ensured == [folder]
    assert (
        connector.checked
        == [f"{folder}/{name}" for name in ["doc.pdf", "doc (1).pdf", "doc (2).pdf"]][
            : len(existing) + 1
        ]
    )
    assert connector.uploads == {expected_path: b"payload"}
    assert Path(document.local_path).read_bytes() == b"payload"
    audit = db_session.scalars(select(AnagraficaAuditLog)).one()
    assert audit.action == "document_manual_uploaded"
    assert audit.diff_json["nas_synced"] is True


def test_reset_anagrafica_data_clears_nested_local_storage(
    db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = tmp_path / "storage"
    (storage / "s1" / "manual").mkdir(parents=True)
    (storage / "s1" / "manual" / "a.pdf").write_bytes(b"a")
    (storage / "s2").mkdir()
    (storage / "s2" / "b.pdf").write_bytes(b"b")
    monkeypatch.setattr(settings, "utenze_document_storage_path", str(storage))
    add_subject(db_session, "Rossi", nas_folder_path="/archive/R/Rossi", nas_folder_letter="R")

    result = reset_anagrafica_data(db_session)

    assert result.deleted_storage_files == 2
    assert result.cleared_subject_links == 1
    assert storage.is_dir()
    assert list(storage.iterdir()) == []
    subject = db_session.scalars(select(AnagraficaSubject)).one()
    assert (subject.nas_folder_path, subject.nas_folder_letter) == (None, None)
