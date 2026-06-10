from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
import mimetypes
from pathlib import Path, PurePosixPath
import re
from typing import Protocol

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.datetime_compat import UTC
from app.models.application_user import ApplicationUser
from app.models.catasto import CatastoDocument
from app.modules.utenze.models import (
    AnagraficaAuditLog,
    AnagraficaClassificationSource,
    AnagraficaCompany,
    AnagraficaDocType,
    AnagraficaDocument,
    AnagraficaStorageType,
    AnagraficaSubject,
    AnagraficaVisuraRoutingAnomaly,
    AnagraficaPerson,
)
from app.modules.utenze.services.nas_path_service import canonical_subject_nas_folder_path

logger = logging.getLogger(__name__)
_SUPPORTED_VISURE_EXTENSIONS = {".pdf", ".xls", ".xlsx"}

_SUBJECT_VISURA_RE = re.compile(
    r"^(?P<identifier>[A-Z0-9]{11,16})_(?P<date>\d{4}-\d{2}-\d{2})_(?P<time>\d{2}-\d{2}-\d{2})(?P<suffix>\.[^.]+)?$",
    re.IGNORECASE,
)
_IMMOBILE_VISURA_RE = re.compile(
    r"^visure-immobili-(?P<identifier>[A-Z0-9]{11,16})-(?P<date>\d{4}-\d{2}-\d{2})(?P<suffix>\.[^.]+)?$",
    re.IGNORECASE,
)
_NON_ALNUM_RE = re.compile(r"[^A-Z0-9]+")


class NasVisureConnector(Protocol):
    def list_files(self, path: str) -> list[str]: ...
    def path_exists(self, path: str) -> bool: ...
    def ensure_directory(self, path: str) -> None: ...
    def move_file(self, source_path: str, destination_path: str) -> None: ...


@dataclass(slots=True)
class ParsedVisuraFilename:
    filename: str
    identifier: str
    identifier_kind: str
    visura_kind: str


@dataclass(slots=True)
class VisureRoutingResult:
    scanned_files: int = 0
    ignored_files: int = 0
    moved_files: int = 0
    created_documents: int = 0
    updated_documents: int = 0
    created_anomalies: int = 0
    updated_anomalies: int = 0


def parse_visura_filename(filename: str) -> ParsedVisuraFilename | None:
    basename = Path(filename).name.strip()
    for pattern, visura_kind in (
        (_SUBJECT_VISURA_RE, "soggetto"),
        (_IMMOBILE_VISURA_RE, "immobile"),
    ):
        match = pattern.match(basename)
        if match is None:
            continue
        identifier = match.group("identifier").upper()
        identifier_kind = "company" if len(identifier) == 11 else "person"
        return ParsedVisuraFilename(
            filename=basename,
            identifier=identifier,
            identifier_kind=identifier_kind,
            visura_kind=visura_kind,
        )
    return None


def route_public_visure_files(
    db: Session,
    connector: NasVisureConnector,
    *,
    source_path: str | None = None,
) -> VisureRoutingResult:
    inbox_path = (source_path or settings.visure_nas_inbox_path or "").strip()
    if not inbox_path:
        raise ValueError("VISURE_NAS_INBOX_PATH is not configured")

    result = VisureRoutingResult()
    now = datetime.now(UTC)
    source_files = connector.list_files(inbox_path)

    for source_file in source_files:
        result.scanned_files += 1
        filename = PurePosixPath(source_file).name
        if Path(filename).suffix.lower() not in _SUPPORTED_VISURE_EXTENSIONS:
            result.ignored_files += 1
            continue
        parsed = parse_visura_filename(filename)
        if parsed is None:
            _upsert_anomaly(
                db,
                source_path=source_file,
                filename=filename,
                identifier=None,
                identifier_kind=None,
                reason="invalid_filename",
                details_json={"message": "Nome file non compatibile con i pattern visure attesi."},
                now=now,
                result=result,
            )
            continue

        catasto_document = _find_catasto_document(db, parsed)
        subject, person, company = _find_subject_bundle(db, parsed.identifier)
        if subject is None:
            _upsert_anomaly(
                db,
                source_path=source_file,
                filename=filename,
                identifier=parsed.identifier,
                identifier_kind=parsed.identifier_kind,
                reason="subject_not_found",
                details_json={
                    "visura_kind": parsed.visura_kind,
                    "catasto_document_id": str(catasto_document.id) if catasto_document is not None else None,
                },
                now=now,
                result=result,
            )
            continue

        if person is None and company is None:
            _upsert_anomaly(
                db,
                source_path=source_file,
                filename=filename,
                identifier=parsed.identifier,
                identifier_kind=parsed.identifier_kind,
                reason="subject_profile_missing",
                details_json={"subject_id": str(subject.id)},
                now=now,
                result=result,
            )
            continue

        if not subject.nas_folder_path:
            folder_letter = _derive_subject_folder_letter(subject, person, company)
            folder_slug = _build_subject_folder_slug(subject, person, company, parsed.identifier)
            subject.nas_folder_letter = folder_letter
            subject.nas_folder_path = canonical_subject_nas_folder_path(
                source_name_raw=folder_slug,
                nas_folder_letter=folder_letter,
            )

        if not subject.nas_folder_path:
            _upsert_anomaly(
                db,
                source_path=source_file,
                filename=filename,
                identifier=parsed.identifier,
                identifier_kind=parsed.identifier_kind,
                reason="subject_path_unresolved",
                details_json={"subject_id": str(subject.id)},
                now=now,
                result=result,
            )
            continue

        target_root = PurePosixPath(subject.nas_folder_path) / "visure"
        connector.ensure_directory(str(target_root))
        target_path = _resolve_unique_target_path(connector, target_root, filename)
        connector.move_file(source_file, target_path)

        created, updated = _upsert_anagrafica_document(
            db,
            subject=subject,
            filename=filename,
            target_path=target_path,
            catasto_document=catasto_document,
            source_file=source_file,
        )
        result.created_documents += created
        result.updated_documents += updated
        result.moved_files += 1

        anomaly = db.scalar(
            select(AnagraficaVisuraRoutingAnomaly).where(AnagraficaVisuraRoutingAnomaly.source_path == source_file)
        )
        if anomaly is not None:
            anomaly.resolved_at = now
            anomaly.details_json = {
                **(anomaly.details_json if isinstance(anomaly.details_json, dict) else {}),
                "resolved_target_path": target_path,
                "subject_id": str(subject.id),
            }

        db.add(
            AnagraficaAuditLog(
                subject_id=subject.id,
                changed_by_user_id=None,
                action="visura_routed_from_public_share",
                diff_json={
                    "filename": filename,
                    "source_path": source_file,
                    "target_path": target_path,
                    "catasto_document_id": str(catasto_document.id) if catasto_document is not None else None,
                },
            )
        )
        db.commit()

    return result


def _find_catasto_document(db: Session, parsed: ParsedVisuraFilename) -> CatastoDocument | None:
    statement = (
        select(CatastoDocument)
        .where(
            CatastoDocument.filename == parsed.filename,
            or_(
                CatastoDocument.subject_id == parsed.identifier,
                CatastoDocument.codice_fiscale == parsed.identifier,
            ),
        )
        .order_by(CatastoDocument.created_at.desc())
    )
    document = db.scalar(statement)
    if document is not None:
        return document
    return db.scalar(
        select(CatastoDocument)
        .where(CatastoDocument.filename == parsed.filename)
        .order_by(CatastoDocument.created_at.desc())
    )


def _find_subject_bundle(
    db: Session,
    identifier: str,
) -> tuple[AnagraficaSubject | None, AnagraficaPerson | None, AnagraficaCompany | None]:
    person = db.scalar(select(AnagraficaPerson).where(AnagraficaPerson.codice_fiscale == identifier))
    if person is not None:
        return db.get(AnagraficaSubject, person.subject_id), person, None

    company = db.scalar(
        select(AnagraficaCompany).where(
            or_(
                AnagraficaCompany.partita_iva == identifier,
                AnagraficaCompany.codice_fiscale == identifier,
            )
        )
    )
    if company is not None:
        return db.get(AnagraficaSubject, company.subject_id), None, company
    return None, None, None


def _normalize_folder_token(value: str | None) -> str:
    if not value:
        return ""
    normalized = _NON_ALNUM_RE.sub("_", value.strip().upper())
    return normalized.strip("_")


def _derive_subject_folder_letter(
    subject: AnagraficaSubject,
    person: AnagraficaPerson | None,
    company: AnagraficaCompany | None,
) -> str | None:
    if subject.nas_folder_letter and len(subject.nas_folder_letter.strip()) == 1:
        return subject.nas_folder_letter.strip().upper()
    candidates = [
        person.cognome if person is not None else None,
        company.ragione_sociale if company is not None else None,
        subject.source_name_raw,
    ]
    for candidate in candidates:
        if not candidate:
            continue
        for char in candidate.strip():
            if char.isalpha():
                return char.upper()
    return None


def _build_subject_folder_slug(
    subject: AnagraficaSubject,
    person: AnagraficaPerson | None,
    company: AnagraficaCompany | None,
    identifier: str,
) -> str:
    if person is not None:
        parts = [
            _normalize_folder_token(person.cognome),
            _normalize_folder_token(person.nome),
            _normalize_folder_token(person.codice_fiscale),
        ]
        return "_".join([part for part in parts if part])
    company_name = company.ragione_sociale if company is not None else subject.source_name_raw
    parts = [
        _normalize_folder_token(company_name),
        _normalize_folder_token(company.partita_iva if company is not None else None) or _normalize_folder_token(identifier),
    ]
    return "_".join([part for part in parts if part])


def _resolve_unique_target_path(connector: NasVisureConnector, target_root: PurePosixPath, filename: str) -> str:
    base_name = Path(filename).stem or "visura"
    suffix = Path(filename).suffix
    candidate = target_root / filename
    if not connector.path_exists(str(candidate)):
        return str(candidate)

    attempt = 1
    while True:
        candidate = target_root / f"{base_name} ({attempt}){suffix}"
        if not connector.path_exists(str(candidate)):
            return str(candidate)
        attempt += 1


def _upsert_anagrafica_document(
    db: Session,
    *,
    subject: AnagraficaSubject,
    filename: str,
    target_path: str,
    catasto_document: CatastoDocument | None,
    source_file: str,
) -> tuple[int, int]:
    existing = None
    if catasto_document is not None:
        existing = db.scalar(
            select(AnagraficaDocument).where(
                or_(
                    AnagraficaDocument.local_path == catasto_document.filepath,
                    AnagraficaDocument.nas_path == target_path,
                )
            )
        )
    if existing is None:
        existing = db.scalar(select(AnagraficaDocument).where(AnagraficaDocument.nas_path == target_path))

    note_parts = [f"Routed from {source_file}"]
    if catasto_document is not None:
        note_parts.append(f"catasto_document_id={catasto_document.id}")

    if existing is None:
        document = AnagraficaDocument(
            subject_id=subject.id,
            doc_type=AnagraficaDocType.VISURA.value,
            filename=filename,
            nas_path=target_path,
            file_size_bytes=catasto_document.file_size if catasto_document is not None else None,
            file_modified_at=datetime.now(UTC),
            classification_source=AnagraficaClassificationSource.AUTO.value,
            storage_type=AnagraficaStorageType.NAS_LINK.value,
            local_path=catasto_document.filepath if catasto_document is not None else None,
            mime_type=mimetypes.guess_type(filename)[0] or "application/pdf",
            notes="; ".join(note_parts),
        )
        db.add(document)
        db.flush()
        return 1, 0

    existing.subject_id = subject.id
    existing.doc_type = AnagraficaDocType.VISURA.value
    existing.filename = filename
    existing.nas_path = target_path
    existing.file_size_bytes = catasto_document.file_size if catasto_document is not None else existing.file_size_bytes
    existing.file_modified_at = datetime.now(UTC)
    existing.classification_source = AnagraficaClassificationSource.AUTO.value
    existing.storage_type = AnagraficaStorageType.NAS_LINK.value
    existing.local_path = catasto_document.filepath if catasto_document is not None else existing.local_path
    existing.mime_type = mimetypes.guess_type(filename)[0] or existing.mime_type or "application/pdf"
    existing.notes = "; ".join(note_parts)
    db.add(existing)
    db.flush()
    return 0, 1


def _upsert_anomaly(
    db: Session,
    *,
    source_path: str,
    filename: str,
    identifier: str | None,
    identifier_kind: str | None,
    reason: str,
    details_json: dict[str, object | None],
    now: datetime,
    result: VisureRoutingResult,
) -> None:
    anomaly = db.scalar(
        select(AnagraficaVisuraRoutingAnomaly).where(AnagraficaVisuraRoutingAnomaly.source_path == source_path)
    )
    if anomaly is None:
        db.add(
            AnagraficaVisuraRoutingAnomaly(
                source_path=source_path,
                filename=filename,
                identifier=identifier,
                identifier_kind=identifier_kind,
                reason=reason,
                details_json=details_json,
                occurrences=1,
            )
        )
        result.created_anomalies += 1
    else:
        anomaly.filename = filename
        anomaly.identifier = identifier
        anomaly.identifier_kind = identifier_kind
        anomaly.reason = reason
        anomaly.details_json = details_json
        anomaly.occurrences += 1
        anomaly.resolved_at = None
        anomaly.updated_at = now
        result.updated_anomalies += 1
    db.commit()
