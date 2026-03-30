from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.anagrafica.models import (
    AnagraficaAuditLog,
    AnagraficaDocument,
    AnagraficaImportJob,
    AnagraficaPerson,
    AnagraficaSubject,
)
from app.modules.anagrafica.services.import_service import AnagraficaImportPreviewService
from app.modules.anagrafica.services.import_service import run_import
from app.services.nas_connector import NasConnectorError


class FakeNasConnector:
    def __init__(self, outputs: dict[str, str], failing_commands: set[str] | None = None) -> None:
        self.outputs = outputs
        self.failing_commands = failing_commands or set()

    def run_command(self, command: str) -> str:
        if command in self.failing_commands:
            raise NasConnectorError(f"command failed: {command}")
        return self.outputs.get(command, "")


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def create_user(db_session: Session) -> ApplicationUser:
    user = ApplicationUser(
        username="anagrafica_admin",
        email="anagrafica_admin@example.local",
        password_hash=hash_password("secret123"),
        role=ApplicationUserRole.ADMIN.value,
        is_active=True,
        module_accessi=True,
        module_anagrafica=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_preview_letter_builds_subjects_and_documents() -> None:
    root = "/volume1/settore catasto/ARCHIVIO"
    connector = FakeNasConnector(
        outputs={
            f"find '{root}/O' -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort": "\n".join(
                [
                    f"{root}/O/Obinu_Santina_BNOSTN34L64I743F",
                    f"{root}/O/Olati_Srl_14542661005",
                ]
            ),
            (
                f"find '{root}/O/Obinu_Santina_BNOSTN34L64I743F' -type f 2>/dev/null | sort"
            ): "\n".join(
                [
                    f"{root}/O/Obinu_Santina_BNOSTN34L64I743F/INGIUNZIONE-2024.pdf",
                    f"{root}/O/Obinu_Santina_BNOSTN34L64I743F/sotto/Relata_notifica_messo.pdf",
                ]
            ),
            (
                f"find '{root}/O/Olati_Srl_14542661005' -type f 2>/dev/null | sort"
            ): f"{root}/O/Olati_Srl_14542661005/documento.gif",
        }
    )

    result = AnagraficaImportPreviewService(connector, archive_root=root).preview_letter("o")

    assert result.letter == "O"
    assert result.total_folders == 2
    assert result.parsed_subjects == 2
    assert result.total_documents == 3
    assert result.non_pdf_documents == 1
    assert result.subjects_requiring_review == 1

    person = result.subjects[0]
    assert person.subject_type == "person"
    assert person.codice_fiscale == "BNOSTN34L64I743F"
    assert "nested_directories_detected" in person.warnings
    assert person.documents[0].doc_type == "ingiunzione"
    assert person.documents[1].doc_type == "notifica"
    assert person.documents[1].relative_path == "sotto/Relata_notifica_messo.pdf"

    company = result.subjects[1]
    assert company.subject_type == "company"
    assert company.ragione_sociale == "Olati Srl"
    assert company.requires_review is True
    assert "non_pdf_files_present" in company.warnings
    assert company.documents[0].is_pdf is False

    assert any(warning.code == "non_pdf_document_detected" for warning in result.warnings)


def test_preview_letter_ignores_synology_metadata_streams() -> None:
    root = "/volume1/Settore Catasto/ARCHIVIO"
    connector = FakeNasConnector(
        outputs={
            f"find '{root}/A' -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort": (
                f"{root}/A/Atzori_Antonello_TZRNNL66A05E972H"
            ),
            (
                f"find '{root}/A/Atzori_Antonello_TZRNNL66A05E972H' -type f 2>/dev/null | sort"
            ): "\n".join(
                [
                    (
                        f"{root}/A/Atzori_Antonello_TZRNNL66A05E972H/"
                        "Verifica_DUI_2024/@eaDir/P_U_8209_24_Rif31-Verifica_domanda_utenza_irrigua_2024.pdf@SynoEAStream"
                    ),
                    (
                        f"{root}/A/Atzori_Antonello_TZRNNL66A05E972H/"
                        "Verifica_DUI_2024/P_U_8209_24_Rif31-Verifica_domanda_utenza_irrigua_2024.pdf"
                    ),
                ]
            ),
        }
    )

    result = AnagraficaImportPreviewService(connector, archive_root=root).preview_letter("A")

    assert result.total_folders == 1
    assert result.total_documents == 1
    assert result.subjects[0].documents[0].filename == "P_U_8209_24_Rif31-Verifica_domanda_utenza_irrigua_2024.pdf"
    assert "@eaDir" not in result.subjects[0].documents[0].nas_path


def test_preview_letter_collects_folder_scan_errors() -> None:
    root = "/archive"
    failing_command = "find '/archive/T/TELERILEVAMENTO' -type f 2>/dev/null | sort"
    connector = FakeNasConnector(
        outputs={
            "find '/archive/T' -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort": "/archive/T/TELERILEVAMENTO",
        },
        failing_commands={failing_command},
    )

    result = AnagraficaImportPreviewService(connector, archive_root=root).preview_letter("T")

    assert result.total_folders == 1
    assert result.total_documents == 0
    assert result.subjects[0].subject_type == "unknown"
    assert "special_folder_candidate" in result.subjects[0].warnings
    assert result.errors[0].code == "folder_scan_failed"
    assert result.errors[0].path == "/archive/T/TELERILEVAMENTO"


def test_preview_archive_aggregates_all_letters() -> None:
    root = "/archive"
    connector = FakeNasConnector(
        outputs={
            "find '/archive' -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort": "\n".join(
                ["/archive/O", "/archive/R"]
            ),
            "find '/archive/O' -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort": "/archive/O/Olati_Srl_14542661005",
            "find '/archive/R' -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort": "/archive/R/Rossi_Mario_RSSMRA80A01H501Z",
            "find '/archive/O/Olati_Srl_14542661005' -type f 2>/dev/null | sort": "/archive/O/Olati_Srl_14542661005/documento.pdf",
            "find '/archive/R/Rossi_Mario_RSSMRA80A01H501Z' -type f 2>/dev/null | sort": "/archive/R/Rossi_Mario_RSSMRA80A01H501Z/notifica.pdf",
        }
    )

    result = AnagraficaImportPreviewService(connector, archive_root=root).preview_archive()

    assert result.letter == "ALL"
    assert result.total_folders == 2
    assert result.parsed_subjects == 2
    assert {item.letter for item in result.subjects} == {"O", "R"}


def test_preview_archive_includes_root_level_subject_folders() -> None:
    root = "/archive"
    connector = FakeNasConnector(
        outputs={
            "find '/archive' -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort": "\n".join(
                ["/archive/00710430950", "/archive/A"]
            ),
            "find '/archive/A' -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort": "/archive/A/Atzori_Mario_TZRMRA80A01H501Z",
            "find '/archive/00710430950' -type f 2>/dev/null | sort": "/archive/00710430950/documento.pdf",
            "find '/archive/A/Atzori_Mario_TZRMRA80A01H501Z' -type f 2>/dev/null | sort": "/archive/A/Atzori_Mario_TZRMRA80A01H501Z/documento.pdf",
        }
    )

    result = AnagraficaImportPreviewService(connector, archive_root=root).preview_archive()

    assert result.total_folders == 2
    assert result.parsed_subjects == 2
    assert any(item.folder_name == "00710430950" for item in result.subjects)


def test_preview_letter_rejects_invalid_letter() -> None:
    connector = FakeNasConnector(outputs={})

    try:
        AnagraficaImportPreviewService(connector, archive_root="/archive").preview_letter("12")
    except ValueError as exc:
        assert str(exc) == "letter must be a single alphabetical character"
    else:  # pragma: no cover
        raise AssertionError("Expected ValueError for invalid letter")


def test_run_import_persists_subject_documents_job_and_audit(db_session: Session) -> None:
    root = "/volume1/settore catasto/ARCHIVIO"
    connector = FakeNasConnector(
        outputs={
            f"find '{root}/O' -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort": (
                f"{root}/O/Obinu_Santina_BNOSTN34L64I743F"
            ),
            (
                f"find '{root}/O/Obinu_Santina_BNOSTN34L64I743F' -type f 2>/dev/null | sort"
            ): "\n".join(
                [
                    f"{root}/O/Obinu_Santina_BNOSTN34L64I743F/INGIUNZIONE-2024.pdf",
                    f"{root}/O/Obinu_Santina_BNOSTN34L64I743F/foto.gif",
                ]
            ),
        }
    )
    user = create_user(db_session)

    result = run_import(
        db_session,
        current_user=user,
        letter="O",
        service=AnagraficaImportPreviewService(connector, archive_root=root),
    )

    assert result.status == "completed"
    assert result.total_folders == 1
    assert result.imported_ok == 1
    assert result.imported_errors == 0
    assert result.created_subjects == 1
    assert result.updated_subjects == 0
    assert result.created_documents == 2
    assert result.updated_documents == 0
    assert result.warning_count >= 2

    subjects = db_session.scalars(select(AnagraficaSubject)).all()
    assert len(subjects) == 1
    assert subjects[0].subject_type == "person"
    assert subjects[0].requires_review is True
    assert subjects[0].imported_at is not None

    person = db_session.get(AnagraficaPerson, subjects[0].id)
    assert person is not None
    assert person.codice_fiscale == "BNOSTN34L64I743F"

    documents = db_session.scalars(select(AnagraficaDocument)).all()
    assert len(documents) == 2
    assert {document.filename for document in documents} == {"INGIUNZIONE-2024.pdf", "foto.gif"}

    jobs = db_session.scalars(select(AnagraficaImportJob)).all()
    assert len(jobs) == 1
    assert jobs[0].requested_by_user_id == user.id
    assert jobs[0].imported_ok == 1
    assert jobs[0].completed_at is not None

    audit_entries = db_session.scalars(select(AnagraficaAuditLog)).all()
    assert len(audit_entries) == 1
    assert audit_entries[0].action == "import_created"


def test_run_import_is_idempotent_for_subjects_and_documents(db_session: Session) -> None:
    root = "/archive"
    connector = FakeNasConnector(
        outputs={
            "find '/archive/O' -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort": (
                "/archive/O/Olati_Srl_14542661005"
            ),
            (
                "find '/archive/O/Olati_Srl_14542661005' -type f 2>/dev/null | sort"
            ): "/archive/O/Olati_Srl_14542661005/documento.pdf",
        }
    )
    user = create_user(db_session)
    service = AnagraficaImportPreviewService(connector, archive_root=root)

    first = run_import(db_session, current_user=user, letter="O", service=service)
    second = run_import(db_session, current_user=user, letter="O", service=service)

    assert first.created_subjects == 1
    assert second.created_subjects == 0
    assert second.updated_subjects == 1
    assert first.created_documents == 1
    assert second.created_documents == 0
    assert second.updated_documents == 1

    assert len(db_session.scalars(select(AnagraficaSubject)).all()) == 1
    assert len(db_session.scalars(select(AnagraficaDocument)).all()) == 1
    assert len(db_session.scalars(select(AnagraficaImportJob)).all()) == 2


def test_run_import_tracks_preview_errors_in_job(db_session: Session) -> None:
    root = "/archive"
    connector = FakeNasConnector(
        outputs={
            "find '/archive/T' -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort": "/archive/T/TELERILEVAMENTO",
        },
        failing_commands={"find '/archive/T/TELERILEVAMENTO' -type f 2>/dev/null | sort"},
    )
    user = create_user(db_session)

    result = run_import(
        db_session,
        current_user=user,
        letter="T",
        service=AnagraficaImportPreviewService(connector, archive_root=root),
    )

    assert result.status == "failed"
    assert result.imported_ok == 0
    assert result.imported_errors == 1
    assert result.log_json is not None
    assert "TELERILEVAMENTO" in result.log_json["errors"][0]["message"]


def test_run_import_without_letter_scans_full_archive(db_session: Session) -> None:
    root = "/archive"
    connector = FakeNasConnector(
        outputs={
            "find '/archive' -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort": "/archive/O",
            "find '/archive/O' -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort": "/archive/O/Olati_Srl_14542661005",
            "find '/archive/O/Olati_Srl_14542661005' -type f 2>/dev/null | sort": "/archive/O/Olati_Srl_14542661005/documento.pdf",
        }
    )
    user = create_user(db_session)

    result = run_import(
        db_session,
        current_user=user,
        letter=None,
        service=AnagraficaImportPreviewService(connector, archive_root=root),
    )

    assert result.letter == "ALL"
    assert result.imported_ok == 1


def test_run_import_resumes_failed_items_only(db_session: Session) -> None:
    root = "/archive"
    outputs = {
        "find '/archive' -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort": "\n".join(
            ["/archive/A", "/archive/B"]
        ),
        "find '/archive/A' -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort": "/archive/A/Atzori_Mario_TZRMRA80A01H501Z",
        "find '/archive/B' -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort": "/archive/B/Bianchi_Luca_BNCLCU80A01H501Z",
        "find '/archive/A/Atzori_Mario_TZRMRA80A01H501Z' -type f 2>/dev/null | sort": "/archive/A/Atzori_Mario_TZRMRA80A01H501Z/documento.pdf",
        "find '/archive/B/Bianchi_Luca_BNCLCU80A01H501Z' -type f 2>/dev/null | sort": "/archive/B/Bianchi_Luca_BNCLCU80A01H501Z/documento.pdf",
    }
    user = create_user(db_session)
    first_service = AnagraficaImportPreviewService(
        FakeNasConnector(outputs, failing_commands={"find '/archive/B/Bianchi_Luca_BNCLCU80A01H501Z' -type f 2>/dev/null | sort"}),
        archive_root=root,
    )
    first = run_import(db_session, current_user=user, letter=None, service=first_service)
    assert first.imported_ok == 1
    assert first.imported_errors == 1

    second = run_import(
        db_session,
        current_user=user,
        letter=None,
        service=AnagraficaImportPreviewService(FakeNasConnector(outputs), archive_root=root),
    )
    assert second.job_id == first.job_id
    assert second.imported_ok == 2
    assert second.imported_errors == 0
