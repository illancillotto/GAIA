from __future__ import annotations

import uuid

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.application_user import ApplicationUser
from app.models.catasto import CatastoDocument
from app.modules.utenze.models import (
    AnagraficaCompany,
    AnagraficaDocument,
    AnagraficaPerson,
    AnagraficaSubject,
    AnagraficaVisuraRoutingAnomaly,
)
from app.modules.utenze.services.visure_routing_service import (
    parse_visura_filename,
    route_public_visure_files,
)


SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class FakeNasConnector:
    def __init__(self, files: dict[str, bytes]) -> None:
        self.files = dict(files)
        self.directories: set[str] = set()

    def list_files(self, path: str) -> list[str]:
        prefix = path.rstrip("/") + "/"
        return sorted(
            filepath
            for filepath in self.files
            if filepath.startswith(prefix) and "/" not in filepath[len(prefix):]
        )

    def path_exists(self, path: str) -> bool:
        return path in self.files or path in self.directories

    def ensure_directory(self, path: str) -> None:
        self.directories.add(path)

    def move_file(self, source_path: str, destination_path: str) -> None:
        self.files[destination_path] = self.files.pop(source_path)
        self.directories.add(destination_path.rsplit("/", 1)[0])


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def teardown_function() -> None:
    Base.metadata.drop_all(bind=engine)


def test_parse_visura_filename_supports_both_patterns() -> None:
    subject = parse_visura_filename("RSSMRA80A01H501U_2026-06-08_09-03-35.pdf")
    immobile = parse_visura_filename("visure-immobili-01234567890-2026-06-06.pdf")

    assert subject is not None
    assert subject.identifier == "RSSMRA80A01H501U"
    assert subject.identifier_kind == "person"
    assert subject.visura_kind == "soggetto"

    assert immobile is not None
    assert immobile.identifier == "01234567890"
    assert immobile.identifier_kind == "company"
    assert immobile.visura_kind == "immobile"


def test_route_public_visure_files_moves_file_into_subject_visure_folder(monkeypatch) -> None:
    monkeypatch.setattr("app.core.config.settings.visure_nas_inbox_path", "/volume1/pubblica condivisa/GAIA/Visure")
    monkeypatch.setattr("app.core.config.settings.utenze_nas_archive_root", "/volume1/Settore Catasto/ARCHIVIO")
    monkeypatch.setattr("app.core.config.settings.anagrafica_nas_archive_root", "/volume1/Settore Catasto/ARCHIVIO")

    db = TestingSessionLocal()
    try:
        user = ApplicationUser(
            username="admin",
            email="admin@example.local",
            password_hash="hash",
            role="admin",
            is_active=True,
        )
        db.add(user)
        db.flush()

        subject = AnagraficaSubject(
            subject_type="person",
            source_system="gaia",
            source_name_raw="Rossi Mario",
            nas_folder_path=None,
            nas_folder_letter=None,
        )
        db.add(subject)
        db.flush()
        db.add(
            AnagraficaPerson(
                subject_id=subject.id,
                cognome="Rossi",
                nome="Mario",
                codice_fiscale="RSSMRA80A01H501U",
            )
        )
        db.add(
            CatastoDocument(
                user_id=user.id,
                request_id=uuid.uuid4(),
                search_mode="soggetto",
                tipo_visura="Sintetica",
                subject_kind="PF",
                subject_id="RSSMRA80A01H501U",
                filename="RSSMRA80A01H501U_2026-06-08_09-03-35.pdf",
                filepath="/data/catasto/documents/batch-1/RSSMRA80A01H501U_2026-06-08_09-03-35.pdf",
                file_size=1234,
                codice_fiscale="RSSMRA80A01H501U",
            )
        )
        db.commit()

        connector = FakeNasConnector(
            {
                "/volume1/pubblica condivisa/GAIA/Visure/RSSMRA80A01H501U_2026-06-08_09-03-35.pdf": b"%PDF",
            }
        )

        result = route_public_visure_files(db, connector)

        subject = db.get(AnagraficaSubject, subject.id)
        target_path = "/volume1/Settore Catasto/ARCHIVIO/R/ROSSI_MARIO_RSSMRA80A01H501U/visure/RSSMRA80A01H501U_2026-06-08_09-03-35.pdf"
        routed_document = db.scalar(select(AnagraficaDocument).where(AnagraficaDocument.nas_path == target_path))

        assert result.scanned_files == 1
        assert result.moved_files == 1
        assert result.created_documents == 1
        assert subject is not None
        assert subject.nas_folder_path == "/volume1/Settore Catasto/ARCHIVIO/R/ROSSI_MARIO_RSSMRA80A01H501U"
        assert routed_document is not None
        assert routed_document.doc_type == "visura"
        assert routed_document.local_path == "/data/catasto/documents/batch-1/RSSMRA80A01H501U_2026-06-08_09-03-35.pdf"
        assert "/volume1/pubblica condivisa/GAIA/Visure/RSSMRA80A01H501U_2026-06-08_09-03-35.pdf" not in connector.files
        assert target_path in connector.files
    finally:
        db.close()


def test_route_public_visure_files_creates_anomaly_when_subject_is_missing(monkeypatch) -> None:
    monkeypatch.setattr("app.core.config.settings.visure_nas_inbox_path", "/volume1/pubblica condivisa/GAIA/Visure")

    db = TestingSessionLocal()
    try:
        connector = FakeNasConnector(
            {
                "/volume1/pubblica condivisa/GAIA/Visure/visure-immobili-01234567890-2026-06-06.pdf": b"%PDF",
            }
        )

        result = route_public_visure_files(db, connector)
        anomaly = db.scalar(select(AnagraficaVisuraRoutingAnomaly))

        assert result.scanned_files == 1
        assert result.moved_files == 0
        assert result.created_anomalies == 1
        assert anomaly is not None
        assert anomaly.reason == "subject_not_found"
        assert anomaly.identifier == "01234567890"
        assert "/volume1/pubblica condivisa/GAIA/Visure/visure-immobili-01234567890-2026-06-06.pdf" in connector.files
    finally:
        db.close()


def test_route_public_visure_files_ignores_unsupported_extensions(monkeypatch) -> None:
    monkeypatch.setattr("app.core.config.settings.visure_nas_inbox_path", "/volume1/pubblica condivisa/GAIA/Visure")

    db = TestingSessionLocal()
    try:
        connector = FakeNasConnector(
            {
                "/volume1/pubblica condivisa/GAIA/Visure/RSSMRA80A01H501U_2026-06-08_09-03-35.dat": b"raw",
                "/volume1/pubblica condivisa/GAIA/Visure/README.txt": b"text",
            }
        )

        result = route_public_visure_files(db, connector)
        anomaly = db.scalar(select(AnagraficaVisuraRoutingAnomaly))

        assert result.scanned_files == 2
        assert result.ignored_files == 2
        assert result.moved_files == 0
        assert result.created_anomalies == 0
        assert anomaly is None
        assert "/volume1/pubblica condivisa/GAIA/Visure/RSSMRA80A01H501U_2026-06-08_09-03-35.dat" in connector.files
    finally:
        db.close()
