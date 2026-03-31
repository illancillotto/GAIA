from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import mimetypes
import os
from pathlib import Path, PurePosixPath
import re
import shlex
from typing import Protocol
import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models.application_user import ApplicationUser
from app.modules.anagrafica.models import (
    AnagraficaAuditLog,
    AnagraficaCompany,
    AnagraficaDocument,
    AnagraficaImportJob,
    AnagraficaImportJobItem,
    AnagraficaImportJobItemStatus,
    AnagraficaImportJobStatus,
    AnagraficaPerson,
    AnagraficaStorageType,
    AnagraficaSubject,
    AnagraficaSubjectStatus,
)
from app.modules.anagrafica.services.classify_service import classify_filename
from app.modules.anagrafica.services.parser_service import parse_folder_name
from app.services.nas_connector import NasConnectorError, get_nas_client


class NasCommandRunner(Protocol):
    def run_command(self, command: str) -> str:
        ...

    def download_file(self, path: str) -> bytes:
        ...

    def ensure_directory(self, path: str) -> None:
        ...

    def path_exists(self, path: str) -> bool:
        ...

    def upload_file(self, path: str, content: bytes) -> None:
        ...


@dataclass(slots=True)
class AnagraficaNASWarning:
    code: str
    message: str
    path: str | None = None


@dataclass(slots=True)
class AnagraficaPreviewDocument:
    filename: str
    relative_path: str
    nas_path: str
    extension: str | None
    is_pdf: bool
    doc_type: str
    classification_source: str
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class AnagraficaPreviewSubject:
    folder_name: str
    letter: str
    nas_folder_path: str
    source_name_raw: str
    subject_type: str
    requires_review: bool
    confidence: float
    cognome: str | None = None
    nome: str | None = None
    codice_fiscale: str | None = None
    ragione_sociale: str | None = None
    partita_iva: str | None = None
    warnings: list[str] = field(default_factory=list)
    documents: list[AnagraficaPreviewDocument] = field(default_factory=list)


@dataclass(slots=True)
class DiscoveredSubjectFolder:
    folder_name: str
    letter: str | None
    nas_folder_path: str


@dataclass(slots=True)
class ImportPreviewResult:
    letter: str
    archive_root: str
    generated_at: datetime
    total_folders: int
    parsed_subjects: int
    subjects_requiring_review: int
    total_documents: int
    non_pdf_documents: int
    warnings: list[AnagraficaNASWarning] = field(default_factory=list)
    errors: list[AnagraficaNASWarning] = field(default_factory=list)
    subjects: list[AnagraficaPreviewSubject] = field(default_factory=list)


@dataclass(slots=True)
class ImportRunResult:
    job_id: uuid.UUID
    letter: str
    status: str
    total_folders: int
    imported_ok: int
    imported_errors: int
    warning_count: int
    created_subjects: int
    updated_subjects: int
    created_documents: int
    updated_documents: int
    generated_at: datetime
    completed_at: datetime
    log_json: dict[str, object] | list[object] | None = None


@dataclass(slots=True)
class SubjectImportRunResult:
    subject_id: uuid.UUID
    matched_folder_path: str
    matched_folder_name: str
    warning_count: int
    created_documents: int
    updated_documents: int
    imported_at: datetime


@dataclass(slots=True)
class ResetAnagraficaResult:
    cleared_subject_links: int
    deleted_documents: int
    deleted_audit_logs: int
    deleted_import_jobs: int
    deleted_import_job_items: int
    deleted_storage_files: int


@dataclass(slots=True)
class SubjectFolderCandidate:
    folder_name: str
    letter: str | None
    nas_folder_path: str
    score: int
    subject_type: str
    confidence: float
    requires_review: bool
    codice_fiscale: str | None = None
    partita_iva: str | None = None
    ragione_sociale: str | None = None
    cognome: str | None = None
    nome: str | None = None


@dataclass(slots=True)
class SubjectNasImportStatus:
    can_import_from_nas: bool
    missing_in_nas: bool
    matched_folder_path: str | None
    matched_folder_name: str | None
    total_files_in_nas: int
    pending_files_in_nas: int
    message: str


class AnagraficaImportPreviewService:
    def __init__(self, connector: NasCommandRunner, archive_root: str | None = None) -> None:
        self.connector = connector
        self.archive_root = (archive_root or settings.anagrafica_nas_archive_root).rstrip("/")

    def preview_letter(self, letter: str) -> ImportPreviewResult:
        normalized_letter = self._normalize_letter(letter)
        return self._preview_folders(normalized_letter, self.discover_subject_folders(normalized_letter))

    def preview_archive(self, letter: str | None = None) -> ImportPreviewResult:
        if letter:
            return self.preview_letter(letter)
        return self._preview_folders("ALL", self.discover_subject_folders())

    def discover_subject_folders(self, letter: str | None = None) -> list[DiscoveredSubjectFolder]:
        errors: list[AnagraficaNASWarning] = []

        try:
            if letter:
                normalized_letter = self._normalize_letter(letter)
                archive_entries = self._list_directories(f"{self.archive_root}/{normalized_letter}")
                return [
                    DiscoveredSubjectFolder(
                        folder_name=os.path.basename(path.rstrip("/")),
                        letter=normalized_letter,
                        nas_folder_path=path,
                    )
                    for path in archive_entries
                ]

            archive_entries = self._list_directories(self.archive_root)
        except NasConnectorError as exc:
            raise NasConnectorError(str(exc)) from exc

        discovered: list[DiscoveredSubjectFolder] = []

        for entry_path in archive_entries:
            folder_name = os.path.basename(entry_path.rstrip("/"))
            normalized_name = folder_name.strip().upper()
            if len(normalized_name) == 1 and normalized_name.isalpha():
                for subject_path in self._list_directories(entry_path):
                    discovered.append(
                        DiscoveredSubjectFolder(
                            folder_name=os.path.basename(subject_path.rstrip("/")),
                            letter=normalized_name,
                            nas_folder_path=subject_path,
                        )
                    )
                continue

            discovered.append(
                DiscoveredSubjectFolder(
                    folder_name=folder_name,
                    letter=self._derive_subject_letter(folder_name),
                    nas_folder_path=entry_path,
                )
            )

        return sorted(discovered, key=lambda item: ((item.letter or ""), item.folder_name.lower(), item.nas_folder_path))

    def preview_subject_folder(
        self,
        subject_folder: DiscoveredSubjectFolder,
        errors: list[AnagraficaNASWarning] | None = None,
        warnings: list[AnagraficaNASWarning] | None = None,
        strict: bool = False,
    ) -> AnagraficaPreviewSubject:
        resolved_errors = errors if errors is not None else []
        resolved_warnings = warnings if warnings is not None else []
        parse_result = parse_folder_name(subject_folder.folder_name)
        document_paths = self._safe_list_files(subject_folder.nas_folder_path, resolved_errors, raise_on_error=strict)
        documents = self._build_documents(subject_folder.nas_folder_path, document_paths, resolved_warnings)
        subject_warnings = list(parse_result.warnings)
        has_nested_directories = any("/" in document.relative_path for document in documents)
        has_non_pdf_documents = any(not document.is_pdf for document in documents)
        if has_nested_directories:
            subject_warnings.append("nested_directories_detected")
        if has_non_pdf_documents:
            subject_warnings.append("non_pdf_files_present")

        return AnagraficaPreviewSubject(
            folder_name=subject_folder.folder_name,
            letter=subject_folder.letter or self._derive_subject_letter(subject_folder.folder_name) or "?",
            nas_folder_path=subject_folder.nas_folder_path,
            source_name_raw=parse_result.source_name_raw,
            subject_type=parse_result.subject_type,
            requires_review=(parse_result.requires_review or has_non_pdf_documents),
            confidence=parse_result.confidence,
            cognome=parse_result.cognome,
            nome=parse_result.nome,
            codice_fiscale=parse_result.codice_fiscale,
            ragione_sociale=parse_result.ragione_sociale,
            partita_iva=parse_result.partita_iva,
            warnings=subject_warnings,
            documents=documents,
        )

    def match_existing_subject_folder(self, db: Session, subject: AnagraficaSubject) -> DiscoveredSubjectFolder:
        if subject.nas_folder_path and _path_matches_primary_identifier(db, subject, subject.nas_folder_path):
            return DiscoveredSubjectFolder(
                folder_name=os.path.basename(subject.nas_folder_path.rstrip("/")),
                letter=subject.nas_folder_letter or self._derive_subject_letter(subject.source_name_raw),
                nas_folder_path=subject.nas_folder_path,
            )

        letter = _derive_existing_subject_letter(db, subject)
        if not letter:
            raise ValueError("Impossibile derivare la lettera archivio del soggetto")

        candidates = self.discover_subject_folders(letter)
        if not candidates:
            raise ValueError(f"Nessuna cartella NAS trovata per la lettera {letter}")

        strict_candidates = _filter_candidates_by_primary_identifier(db, subject, candidates)
        if strict_candidates:
            return sorted(strict_candidates, key=lambda item: (item.folder_name.lower(), item.nas_folder_path))[0]

        if _subject_has_primary_identifiers(db, subject):
            raise ValueError(f"Nessuna cartella NAS compatibile trovata per il soggetto {subject.id}")

        scored_candidates = [
            (candidate, _score_subject_folder_candidate(db, subject, candidate.folder_name))
            for candidate in candidates
        ]
        scored_candidates = [item for item in scored_candidates if item[1] > 0]
        if not scored_candidates:
            raise ValueError(f"Nessuna cartella NAS compatibile trovata per il soggetto {subject.id}")

        scored_candidates.sort(key=lambda item: (-item[1], item[0].folder_name.lower(), item[0].nas_folder_path))
        return scored_candidates[0][0]

    def list_existing_subject_folder_candidates(
        self,
        db: Session,
        subject: AnagraficaSubject,
        limit: int = 20,
    ) -> list[SubjectFolderCandidate]:
        letter = _derive_existing_subject_letter(db, subject)
        if not letter:
            return []

        candidates = self.discover_subject_folders(letter)
        strict_candidates = _filter_candidates_by_primary_identifier(db, subject, candidates)
        if strict_candidates:
            candidates = strict_candidates
        elif _subject_has_primary_identifiers(db, subject):
            return []

        scored_candidates: list[SubjectFolderCandidate] = []
        for candidate in candidates:
            score = _score_subject_folder_candidate(db, subject, candidate.folder_name)
            if score <= 0:
                continue
            parsed = parse_folder_name(candidate.folder_name)
            scored_candidates.append(
                SubjectFolderCandidate(
                    folder_name=candidate.folder_name,
                    letter=candidate.letter,
                    nas_folder_path=candidate.nas_folder_path,
                    score=score,
                    subject_type=parsed.subject_type,
                    confidence=parsed.confidence,
                    requires_review=parsed.requires_review,
                    codice_fiscale=parsed.codice_fiscale,
                    partita_iva=parsed.partita_iva,
                    ragione_sociale=parsed.ragione_sociale,
                    cognome=parsed.cognome,
                    nome=parsed.nome,
                )
            )

        scored_candidates.sort(key=lambda item: (-item.score, item.folder_name.lower(), item.nas_folder_path))
        return scored_candidates[:limit]

    def get_subject_import_status(self, db: Session, subject: AnagraficaSubject) -> SubjectNasImportStatus:
        try:
            matched_folder = self.match_existing_subject_folder(db, subject)
        except ValueError as exc:
            return SubjectNasImportStatus(
                can_import_from_nas=False,
                missing_in_nas=True,
                matched_folder_path=None,
                matched_folder_name=None,
                total_files_in_nas=0,
                pending_files_in_nas=0,
                message=str(exc),
            )

        preview = self.preview_subject_folder(matched_folder, strict=True)
        existing_nas_paths = set(
            db.scalars(select(AnagraficaDocument.nas_path).where(AnagraficaDocument.subject_id == subject.id)).all()
        )
        total_files = len(preview.documents)
        pending_files = sum(1 for document in preview.documents if document.nas_path not in existing_nas_paths)

        if total_files == 0:
            return SubjectNasImportStatus(
                can_import_from_nas=False,
                missing_in_nas=False,
                matched_folder_path=matched_folder.nas_folder_path,
                matched_folder_name=matched_folder.folder_name,
                total_files_in_nas=0,
                pending_files_in_nas=0,
                message="Cartella NAS trovata ma senza file importabili.",
            )

        if pending_files == 0:
            return SubjectNasImportStatus(
                can_import_from_nas=False,
                missing_in_nas=False,
                matched_folder_path=matched_folder.nas_folder_path,
                matched_folder_name=matched_folder.folder_name,
                total_files_in_nas=total_files,
                pending_files_in_nas=0,
                message="Tutti i file NAS disponibili risultano gia importati.",
            )

        return SubjectNasImportStatus(
            can_import_from_nas=True,
            missing_in_nas=False,
            matched_folder_path=matched_folder.nas_folder_path,
            matched_folder_name=matched_folder.folder_name,
            total_files_in_nas=total_files,
            pending_files_in_nas=pending_files,
            message=f"Trovati {pending_files} file NAS ancora da importare.",
        )

    def _preview_folders(self, scope: str, subject_folders: list[DiscoveredSubjectFolder]) -> ImportPreviewResult:
        errors: list[AnagraficaNASWarning] = []
        warnings: list[AnagraficaNASWarning] = []
        subjects: list[AnagraficaPreviewSubject] = []
        for subject_folder in subject_folders:
            subjects.append(self.preview_subject_folder(subject_folder, errors=errors, warnings=warnings))

        total_documents = sum(len(subject.documents) for subject in subjects)
        non_pdf_documents = sum(1 for subject in subjects for document in subject.documents if not document.is_pdf)
        subjects_requiring_review = sum(1 for subject in subjects if subject.requires_review)

        return ImportPreviewResult(
            letter=scope,
            archive_root=self.archive_root,
            generated_at=datetime.now(UTC),
            total_folders=len(subject_folders),
            parsed_subjects=len(subjects),
            subjects_requiring_review=subjects_requiring_review,
            total_documents=total_documents,
            non_pdf_documents=non_pdf_documents,
            warnings=warnings,
            errors=errors,
            subjects=subjects,
        )

    @staticmethod
    def _derive_subject_letter(folder_name: str) -> str | None:
        for char in folder_name.strip():
            if char.isalpha():
                return char.upper()
        return None

    def _normalize_letter(self, letter: str) -> str:
        normalized_letter = (letter or "").strip().upper()
        if len(normalized_letter) != 1 or not normalized_letter.isalpha():
            raise ValueError("letter must be a single alphabetical character")
        return normalized_letter

    def _list_directories(self, root_path: str) -> list[str]:
        command = (
            f"find {self._quote_path(root_path)} "
            "-mindepth 1 -maxdepth 1 -type d "
            "2>/dev/null | sort"
        )
        return self._split_command_output(self.connector.run_command(command))

    def _safe_list_files(
        self,
        folder_path: str,
        errors: list[AnagraficaNASWarning],
        raise_on_error: bool = False,
    ) -> list[str]:
        command = f"find {self._quote_path(folder_path)} -type f 2>/dev/null | sort"
        try:
            return [
                path
                for path in self._split_command_output(self.connector.run_command(command))
                if _is_supported_nas_document_path(path)
            ]
        except NasConnectorError as exc:
            if raise_on_error:
                raise
            errors.append(
                AnagraficaNASWarning(
                    code="folder_scan_failed",
                    message=str(exc),
                    path=folder_path,
                )
            )
            return []

    def _build_documents(
        self,
        folder_path: str,
        document_paths: list[str],
        warnings: list[AnagraficaNASWarning],
    ) -> list[AnagraficaPreviewDocument]:
        documents: list[AnagraficaPreviewDocument] = []
        for document_path in document_paths:
            filename = os.path.basename(document_path)
            relative_path = os.path.relpath(document_path, folder_path)
            extension = os.path.splitext(filename)[1].lower() or None
            doc_type, classification_source = classify_filename(filename)
            is_pdf = extension == ".pdf"
            document_warnings: list[str] = []
            if not is_pdf:
                document_warnings.append("unsupported_preview_extension")
                warnings.append(
                    AnagraficaNASWarning(
                        code="non_pdf_document_detected",
                        message=f"File non-PDF rilevato: {relative_path}",
                        path=document_path,
                    )
                )
            documents.append(
                AnagraficaPreviewDocument(
                    filename=filename,
                    relative_path=relative_path,
                    nas_path=document_path,
                    extension=extension,
                    is_pdf=is_pdf,
                    doc_type=doc_type,
                    classification_source=classification_source,
                    warnings=document_warnings,
                )
            )
        return documents

    @staticmethod
    def _split_command_output(output: str) -> list[str]:
        return [line.strip() for line in output.splitlines() if line.strip()]

    @staticmethod
    def _quote_path(path: str) -> str:
        return shlex.quote(path) if any(char.isspace() for char in path) else f"'{path}'"


def preview_import(letter: str | None = None, service: AnagraficaImportPreviewService | None = None) -> ImportPreviewResult:
    resolved_service = service or AnagraficaImportPreviewService(get_nas_client())
    try:
        return resolved_service.preview_archive(letter)
    finally:
        _close_connector(resolved_service.connector)


def create_import_snapshot(
    db: Session,
    current_user: ApplicationUser,
    letter: str | None,
    service: AnagraficaImportPreviewService | None = None,
) -> ImportRunResult:
    resolved_service = service or AnagraficaImportPreviewService(get_nas_client())
    generated_at = datetime.now(UTC)

    try:
        preview = resolved_service.preview_archive(letter)
        warning_count = len(preview.warnings) + sum(
            len(subject.warnings) + sum(len(document.warnings) for document in subject.documents)
            for subject in preview.subjects
        )
        job = AnagraficaImportJob(
            requested_by_user_id=current_user.id,
            letter=preview.letter,
            status=AnagraficaImportJobStatus.COMPLETED.value,
            total_folders=preview.total_folders,
            imported_ok=preview.parsed_subjects,
            imported_errors=len(preview.errors),
            warning_count=warning_count,
            log_json={
                "archive_root": preview.archive_root,
                "generated_at": preview.generated_at.isoformat(),
                "warnings": [_warning_to_dict(item) for item in preview.warnings],
                "errors": [_warning_to_dict(item) for item in preview.errors],
                "summary": {
                    "parsed_subjects": preview.parsed_subjects,
                    "subjects_requiring_review": preview.subjects_requiring_review,
                    "total_documents": preview.total_documents,
                    "non_pdf_documents": preview.non_pdf_documents,
                },
            },
            started_at=generated_at,
            completed_at=generated_at,
        )
        db.add(job)
        db.flush()

        for subject in preview.subjects:
            db.add(
                AnagraficaImportJobItem(
                    job_id=job.id,
                    letter=subject.letter,
                    folder_name=subject.folder_name,
                    nas_folder_path=subject.nas_folder_path,
                    status=AnagraficaImportJobItemStatus.COMPLETED.value,
                    attempt_count=1,
                    warning_count=len(subject.warnings) + sum(len(document.warnings) for document in subject.documents),
                    documents_created=len(subject.documents),
                    documents_updated=0,
                    payload_json={
                        "folder_name": subject.folder_name,
                        "letter": subject.letter,
                        "nas_folder_path": subject.nas_folder_path,
                        "source_name_raw": subject.source_name_raw,
                        "subject_type": subject.subject_type,
                        "requires_review": subject.requires_review,
                        "confidence": subject.confidence,
                        "cognome": subject.cognome,
                        "nome": subject.nome,
                        "codice_fiscale": subject.codice_fiscale,
                        "ragione_sociale": subject.ragione_sociale,
                        "partita_iva": subject.partita_iva,
                        "warnings": list(subject.warnings),
                        "documents": [
                            {
                                "filename": document.filename,
                                "relative_path": document.relative_path,
                                "nas_path": document.nas_path,
                                "extension": document.extension,
                                "is_pdf": document.is_pdf,
                                "doc_type": document.doc_type,
                                "classification_source": document.classification_source,
                                "warnings": list(document.warnings),
                            }
                            for document in subject.documents
                        ],
                    },
                    started_at=generated_at,
                    completed_at=generated_at,
                )
            )

        db.commit()
        db.refresh(job)

        return ImportRunResult(
            job_id=job.id,
            letter=preview.letter,
            status=job.status,
            total_folders=job.total_folders,
            imported_ok=job.imported_ok,
            imported_errors=job.imported_errors,
            warning_count=job.warning_count,
            created_subjects=0,
            updated_subjects=0,
            created_documents=0,
            updated_documents=0,
            generated_at=job.created_at,
            completed_at=job.completed_at or generated_at,
            log_json=job.log_json,
        )
    finally:
        _close_connector(resolved_service.connector)


def run_import(
    db: Session,
    current_user: ApplicationUser,
    letter: str | None,
    service: AnagraficaImportPreviewService | None = None,
) -> ImportRunResult:
    job = enqueue_import(db, current_user=current_user, letter=letter, service=service)
    return process_import_job(db, current_user=current_user, job_id=job.id, letter=letter, service=service)


def import_subject_from_existing_registry(
    db: Session,
    current_user: ApplicationUser,
    subject_id: uuid.UUID,
    service: AnagraficaImportPreviewService | None = None,
) -> SubjectImportRunResult:
    resolved_service = service or AnagraficaImportPreviewService(get_nas_client())
    imported_at = datetime.now(UTC)

    try:
        subject = db.get(AnagraficaSubject, subject_id)
        if subject is None:
            raise ValueError("Subject not found")

        matched_folder = resolved_service.match_existing_subject_folder(db, subject)
        subject_preview = resolved_service.preview_subject_folder(matched_folder, strict=True)

        with db.begin_nested():
            subject.nas_folder_path = matched_folder.nas_folder_path
            subject.nas_folder_letter = subject_preview.letter
            subject.requires_review = subject_preview.requires_review
            subject.imported_at = imported_at
            db.add(subject)
            document_stats = _upsert_documents(
                db=db,
                connector=resolved_service.connector,
                subject_id=subject.id,
                documents=subject_preview.documents,
                storage_mode=AnagraficaStorageType.LOCAL_UPLOAD.value,
                imported_at=imported_at,
            )
            _create_audit_log(
                db=db,
                subject_id=subject.id,
                changed_by_user_id=current_user.id,
                action="import_from_registry",
                diff_json={
                    "matched_folder_path": matched_folder.nas_folder_path,
                    "matched_folder_name": matched_folder.folder_name,
                    "created_documents": document_stats["created"],
                    "updated_documents": document_stats["updated"],
                    "warning_count": len(subject_preview.warnings)
                    + sum(len(document.warnings) for document in subject_preview.documents),
                },
            )
        db.commit()

        return SubjectImportRunResult(
            subject_id=subject.id,
            matched_folder_path=matched_folder.nas_folder_path,
            matched_folder_name=matched_folder.folder_name,
            warning_count=len(subject_preview.warnings)
            + sum(len(document.warnings) for document in subject_preview.documents),
            created_documents=document_stats["created"],
            updated_documents=document_stats["updated"],
            imported_at=imported_at,
        )
    finally:
        _close_connector(resolved_service.connector)


def import_existing_registry_subjects(
    db: Session,
    current_user: ApplicationUser,
    service: AnagraficaImportPreviewService | None = None,
) -> ImportRunResult:
    resolved_service = service or AnagraficaImportPreviewService(get_nas_client())
    started_at = datetime.now(UTC)

    try:
        subjects = db.scalars(
            select(AnagraficaSubject).order_by(AnagraficaSubject.nas_folder_letter.asc(), AnagraficaSubject.created_at.asc())
        ).all()
        job = AnagraficaImportJob(
            requested_by_user_id=current_user.id,
            letter="REGISTRY",
            status=AnagraficaImportJobStatus.RUNNING.value,
            total_folders=len(subjects),
            imported_ok=0,
            imported_errors=0,
            warning_count=0,
            log_json={"mode": "registry_import", "warnings": [], "errors": [], "items": []},
            started_at=started_at,
        )
        db.add(job)
        db.flush()

        created_subjects = 0
        updated_subjects = 0
        created_documents = 0
        updated_documents = 0
        warning_count = 0

        for subject in subjects:
            folder_name = _subject_display_name(db, subject)
            job_item = AnagraficaImportJobItem(
                job_id=job.id,
                subject_id=subject.id,
                letter=_derive_existing_subject_letter(db, subject),
                folder_name=folder_name,
                nas_folder_path=f"subject:{subject.id}",
                status=AnagraficaImportJobItemStatus.PROCESSING.value,
                attempt_count=1,
                started_at=datetime.now(UTC),
            )
            db.add(job_item)
            db.flush()

            try:
                matched_folder = resolved_service.match_existing_subject_folder(db, subject)
                subject_preview = resolved_service.preview_subject_folder(matched_folder, strict=True)
                with db.begin_nested():
                    subject.nas_folder_path = matched_folder.nas_folder_path
                    subject.nas_folder_letter = subject_preview.letter
                    subject.requires_review = subject_preview.requires_review
                    subject.imported_at = started_at
                    db.add(subject)
                    document_stats = _upsert_documents(
                        db=db,
                        connector=resolved_service.connector,
                        subject_id=subject.id,
                        documents=subject_preview.documents,
                        storage_mode=AnagraficaStorageType.LOCAL_UPLOAD.value,
                        imported_at=started_at,
                    )
                    _create_audit_log(
                        db=db,
                        subject_id=subject.id,
                        changed_by_user_id=current_user.id,
                        action="bulk_import_from_registry",
                        diff_json={
                            "job_id": str(job.id),
                            "matched_folder_path": matched_folder.nas_folder_path,
                            "created_documents": document_stats["created"],
                            "updated_documents": document_stats["updated"],
                        },
                    )

                updated_subjects += 1
                created_documents += document_stats["created"]
                updated_documents += document_stats["updated"]
                item_warning_count = len(subject_preview.warnings) + sum(len(document.warnings) for document in subject_preview.documents)
                warning_count += item_warning_count

                job_item.letter = subject_preview.letter
                job_item.folder_name = matched_folder.folder_name
                job_item.nas_folder_path = matched_folder.nas_folder_path
                job_item.status = AnagraficaImportJobItemStatus.COMPLETED.value
                job_item.warning_count = item_warning_count
                job_item.documents_created = document_stats["created"]
                job_item.documents_updated = document_stats["updated"]
                job_item.payload_json = {
                    "mode": "registry_import",
                    "matched_folder_path": matched_folder.nas_folder_path,
                    "matched_folder_name": matched_folder.folder_name,
                }
                job_item.completed_at = datetime.now(UTC)
                db.add(job_item)
                db.commit()
            except Exception as exc:  # pragma: no cover - defensive path
                job_item.status = AnagraficaImportJobItemStatus.FAILED.value
                job_item.last_error = str(exc)
                job_item.completed_at = datetime.now(UTC)
                db.add(job_item)
                db.commit()

        _refresh_import_job_status(db, job.id)
        db.refresh(job)
        job.warning_count = warning_count
        db.add(job)
        db.commit()
        db.refresh(job)

        return ImportRunResult(
            job_id=job.id,
            letter="REGISTRY",
            status=job.status,
            total_folders=job.total_folders,
            imported_ok=job.imported_ok,
            imported_errors=job.imported_errors,
            warning_count=job.warning_count,
            created_subjects=created_subjects,
            updated_subjects=updated_subjects,
            created_documents=created_documents,
            updated_documents=updated_documents,
            generated_at=started_at,
            completed_at=job.completed_at or datetime.now(UTC),
            log_json=job.log_json,
        )
    finally:
        _close_connector(resolved_service.connector)


def reset_anagrafica_data(db: Session) -> ResetAnagraficaResult:
    linked_subjects = db.query(AnagraficaSubject).filter(
        (AnagraficaSubject.nas_folder_path.is_not(None))
        | (AnagraficaSubject.nas_folder_letter.is_not(None))
        | (AnagraficaSubject.imported_at.is_not(None))
    ).count()
    deleted_documents = db.query(AnagraficaDocument).count()
    deleted_audit_logs = db.query(AnagraficaAuditLog).filter(
        AnagraficaAuditLog.action.in_(
            [
                "import_created",
                "import_updated",
                "import_from_registry",
                "bulk_import_from_registry",
                "document_updated",
                "document_deleted",
            ]
        )
    ).count()
    deleted_import_jobs = db.query(AnagraficaImportJob).count()
    deleted_import_job_items = db.query(AnagraficaImportJobItem).count()
    deleted_storage_files = _clear_local_storage(Path(settings.anagrafica_document_storage_path))

    db.execute(delete(AnagraficaImportJobItem))
    db.execute(delete(AnagraficaImportJob))
    db.execute(
        delete(AnagraficaAuditLog).where(
            AnagraficaAuditLog.action.in_(
                [
                    "import_created",
                    "import_updated",
                    "import_from_registry",
                    "bulk_import_from_registry",
                    "document_updated",
                    "document_deleted",
                ]
            )
        )
    )
    db.execute(delete(AnagraficaDocument))
    subjects = db.scalars(select(AnagraficaSubject)).all()
    for subject in subjects:
        subject.nas_folder_path = None
        subject.nas_folder_letter = None
        subject.imported_at = None
        db.add(subject)
    db.commit()

    return ResetAnagraficaResult(
        cleared_subject_links=linked_subjects,
        deleted_documents=deleted_documents,
        deleted_audit_logs=deleted_audit_logs,
        deleted_import_jobs=deleted_import_jobs,
        deleted_import_job_items=deleted_import_job_items,
        deleted_storage_files=deleted_storage_files,
    )


def enqueue_import(
    db: Session,
    current_user: ApplicationUser,
    letter: str | None,
    service: AnagraficaImportPreviewService | None = None,
) -> AnagraficaImportJob:
    resolved_service = service or AnagraficaImportPreviewService(get_nas_client())
    scope = resolved_service._normalize_letter(letter) if letter else "ALL"

    try:
        job = _get_resumable_job(db, current_user=current_user, scope=scope)
        if job is None:
            subject_folders = resolved_service.discover_subject_folders(letter)
            now = datetime.now(UTC)
            job = AnagraficaImportJob(
                requested_by_user_id=current_user.id,
                letter=scope,
                status=AnagraficaImportJobStatus.RUNNING.value,
                total_folders=len(subject_folders),
                imported_ok=0,
                imported_errors=0,
                warning_count=0,
                log_json={"warnings": [], "errors": [], "items": []},
                started_at=now,
            )
            db.add(job)
            db.flush()

            for folder in subject_folders:
                db.add(
                    AnagraficaImportJobItem(
                        job_id=job.id,
                        letter=folder.letter,
                        folder_name=folder.folder_name,
                        nas_folder_path=folder.nas_folder_path,
                        status=AnagraficaImportJobItemStatus.PENDING.value,
                    )
                )
            db.commit()
            db.refresh(job)
        else:
            job.status = AnagraficaImportJobStatus.PENDING.value
            job.completed_at = None
            db.add(job)
            db.commit()
            db.refresh(job)
        return job
    finally:
        _close_connector(resolved_service.connector)


def process_import_job(
    db: Session,
    current_user: ApplicationUser,
    job_id: uuid.UUID,
    letter: str | None,
    service: AnagraficaImportPreviewService | None = None,
) -> ImportRunResult:
    resolved_service = service or AnagraficaImportPreviewService(get_nas_client())
    generated_at = datetime.now(UTC)
    scope = resolved_service._normalize_letter(letter) if letter else "ALL"
    job = db.get(AnagraficaImportJob, job_id)
    if job is None:
        raise ValueError("Import job not found")

    try:
        job.status = AnagraficaImportJobStatus.RUNNING.value
        job.completed_at = None
        db.add(job)
        db.commit()
        db.refresh(job)

        created_subjects = 0
        updated_subjects = 0
        created_documents = 0
        updated_documents = 0
        items_query = (
            select(AnagraficaImportJobItem)
            .where(
                AnagraficaImportJobItem.job_id == job.id,
                AnagraficaImportJobItem.status.in_(
                    [
                        AnagraficaImportJobItemStatus.PENDING.value,
                        AnagraficaImportJobItemStatus.FAILED.value,
                    ]
                ),
            )
            .order_by(AnagraficaImportJobItem.letter.asc(), AnagraficaImportJobItem.folder_name.asc())
        )
        job_items = db.scalars(items_query).all()

        for job_item in job_items:
            item_started_at = datetime.now(UTC)
            job_item.status = AnagraficaImportJobItemStatus.PROCESSING.value
            job_item.attempt_count += 1
            job_item.started_at = item_started_at
            job_item.last_error = None
            db.add(job_item)
            db.commit()

            try:
                subject_preview = resolved_service.preview_subject_folder(
                    DiscoveredSubjectFolder(
                        folder_name=job_item.folder_name,
                        letter=job_item.letter,
                        nas_folder_path=job_item.nas_folder_path,
                    ),
                    strict=True,
                )
                with db.begin_nested():
                    persisted_subject, was_created = _upsert_subject(
                        db=db,
                        subject_preview=subject_preview,
                        imported_at=item_started_at,
                    )
                    document_stats = _upsert_documents(
                        db=db,
                        connector=None,
                        subject_id=persisted_subject.id,
                        documents=subject_preview.documents,
                        storage_mode=AnagraficaStorageType.NAS_LINK.value,
                    )
                    _create_audit_log(
                        db=db,
                        subject_id=persisted_subject.id,
                        changed_by_user_id=current_user.id,
                        action="import_created" if was_created else "import_updated",
                        diff_json={
                            "job_id": str(job.id),
                            "letter": scope,
                            "source_name_raw": subject_preview.source_name_raw,
                            "documents_created": document_stats["created"],
                            "documents_updated": document_stats["updated"],
                            "requires_review": subject_preview.requires_review,
                            "warnings": subject_preview.warnings,
                        },
                    )
                if was_created:
                    created_subjects += 1
                else:
                    updated_subjects += 1
                created_documents += document_stats["created"]
                updated_documents += document_stats["updated"]

                job_item.subject_id = persisted_subject.id
                job_item.status = AnagraficaImportJobItemStatus.COMPLETED.value
                job_item.warning_count = len(subject_preview.warnings) + sum(len(document.warnings) for document in subject_preview.documents)
                job_item.documents_created = document_stats["created"]
                job_item.documents_updated = document_stats["updated"]
                job_item.completed_at = datetime.now(UTC)
                db.add(job_item)
                db.commit()
            except Exception as exc:  # pragma: no cover - defensive path
                job_item.status = AnagraficaImportJobItemStatus.FAILED.value
                job_item.last_error = str(exc)
                job_item.completed_at = datetime.now(UTC)
                db.add(job_item)
                db.commit()

        _refresh_import_job_status(db, job.id)
        db.refresh(job)

        return ImportRunResult(
            job_id=job.id,
            letter=job.letter or (resolved_service._normalize_letter(letter) if letter else "ALL"),
            status=job.status,
            total_folders=job.total_folders,
            imported_ok=job.imported_ok,
            imported_errors=job.imported_errors,
            warning_count=job.warning_count,
            created_subjects=created_subjects,
            updated_subjects=updated_subjects,
            created_documents=created_documents,
            updated_documents=updated_documents,
            generated_at=generated_at,
            completed_at=job.completed_at or datetime.now(UTC),
            log_json=job.log_json,
        )
    finally:
        _close_connector(resolved_service.connector)


def process_import_job_async(
    job_id: uuid.UUID,
    current_user_id: int,
    letter: str | None,
    session_factory: sessionmaker,
) -> None:
    db = session_factory()
    try:
        user = db.get(ApplicationUser, current_user_id)
        if user is None:
            return
        process_import_job(
            db,
            current_user=user,
            job_id=job_id,
            letter=letter,
            service=AnagraficaImportPreviewService(get_nas_client()),
        )
    finally:
        db.close()


def _get_resumable_job(db: Session, current_user: ApplicationUser, scope: str) -> AnagraficaImportJob | None:
    return db.scalar(
        select(AnagraficaImportJob)
        .where(
            AnagraficaImportJob.requested_by_user_id == current_user.id,
            AnagraficaImportJob.letter == scope,
            AnagraficaImportJob.status.in_(
                [
                    AnagraficaImportJobStatus.RUNNING.value,
                    AnagraficaImportJobStatus.FAILED.value,
                ]
            ),
        )
        .order_by(AnagraficaImportJob.created_at.desc())
        .limit(1)
    )


def _refresh_import_job_status(db: Session, job_id: uuid.UUID) -> None:
    job = db.get(AnagraficaImportJob, job_id)
    if job is None:
        return

    items = db.scalars(select(AnagraficaImportJobItem).where(AnagraficaImportJobItem.job_id == job_id)).all()
    pending = [item for item in items if item.status in {AnagraficaImportJobItemStatus.PENDING.value, AnagraficaImportJobItemStatus.PROCESSING.value}]
    completed = [item for item in items if item.status == AnagraficaImportJobItemStatus.COMPLETED.value]
    failed = [item for item in items if item.status == AnagraficaImportJobItemStatus.FAILED.value]

    job.imported_ok = len(completed)
    job.imported_errors = len(failed)
    job.warning_count = sum(item.warning_count for item in items)
    job.completed_at = None if pending else datetime.now(UTC)
    job.status = (
        AnagraficaImportJobStatus.RUNNING.value
        if pending
        else AnagraficaImportJobStatus.FAILED.value if failed
        else AnagraficaImportJobStatus.COMPLETED.value
    )
    job.log_json = {
        "warnings": [],
        "errors": [
            {"folder_name": item.folder_name, "path": item.nas_folder_path, "message": item.last_error}
            for item in failed
        ],
        "items": [
            {
                "folder_name": item.folder_name,
                "subject_id": str(item.subject_id) if item.subject_id else None,
                "status": item.status,
                "documents_created": item.documents_created,
                "documents_updated": item.documents_updated,
                "warnings": item.warning_count,
                "error": item.last_error,
                "attempt_count": item.attempt_count,
            }
            for item in items
        ],
    }
    db.add(job)
    db.commit()


def _close_connector(connector: NasCommandRunner) -> None:
    close = getattr(connector, "close", None)
    if callable(close):
        close()


def _upsert_subject(
    db: Session,
    subject_preview: AnagraficaPreviewSubject,
    imported_at: datetime,
) -> tuple[AnagraficaSubject, bool]:
    subject = db.scalar(
        select(AnagraficaSubject).where(AnagraficaSubject.nas_folder_path == subject_preview.nas_folder_path)
    )
    was_created = subject is None
    if subject is None:
        subject = AnagraficaSubject(
            subject_type=subject_preview.subject_type,
            status=AnagraficaSubjectStatus.ACTIVE.value,
            source_name_raw=subject_preview.source_name_raw,
            nas_folder_path=subject_preview.nas_folder_path,
            nas_folder_letter=subject_preview.letter,
            requires_review=subject_preview.requires_review,
            imported_at=imported_at,
        )
        db.add(subject)
        db.flush()
    else:
        subject.subject_type = subject_preview.subject_type
        subject.status = AnagraficaSubjectStatus.ACTIVE.value
        subject.source_name_raw = subject_preview.source_name_raw
        subject.nas_folder_letter = subject_preview.letter
        subject.requires_review = subject_preview.requires_review
        subject.imported_at = imported_at
        db.add(subject)
        db.flush()

    _sync_subject_details(db, subject, subject_preview)
    return subject, was_created


def _sync_subject_details(db: Session, subject: AnagraficaSubject, subject_preview: AnagraficaPreviewSubject) -> None:
    existing_person = db.get(AnagraficaPerson, subject.id)
    existing_company = db.get(AnagraficaCompany, subject.id)

    if subject_preview.subject_type == "person":
        codice_fiscale = subject_preview.codice_fiscale or f"MISSING-CF-{str(subject.id)[:8]}".upper()
        if existing_company is not None:
            db.delete(existing_company)
        person = existing_person or AnagraficaPerson(
            subject_id=subject.id,
            cognome=subject_preview.cognome or "",
            nome=subject_preview.nome or "",
            codice_fiscale=codice_fiscale,
        )
        person.cognome = subject_preview.cognome or subject.source_name_raw
        person.nome = subject_preview.nome or "-"
        person.codice_fiscale = codice_fiscale
        db.add(person)
        db.flush()
        return

    if subject_preview.subject_type == "company":
        partita_iva = subject_preview.partita_iva or f"MISSING-PI-{str(subject.id)[:8]}".upper()
        if existing_person is not None:
            db.delete(existing_person)
        company = existing_company or AnagraficaCompany(
            subject_id=subject.id,
            ragione_sociale=subject_preview.ragione_sociale or subject.source_name_raw,
            partita_iva=partita_iva,
        )
        company.ragione_sociale = subject_preview.ragione_sociale or subject.source_name_raw
        company.partita_iva = partita_iva
        db.add(company)
        db.flush()
        return

    if existing_person is not None:
        db.delete(existing_person)
    if existing_company is not None:
        db.delete(existing_company)
    db.flush()


def _upsert_documents(
    db: Session,
    connector: NasCommandRunner | None,
    subject_id: uuid.UUID,
    documents: list[AnagraficaPreviewDocument],
    storage_mode: str,
    imported_at: datetime | None = None,
) -> dict[str, int]:
    created = 0
    updated = 0
    for document_preview in documents:
        local_path = None
        if storage_mode == AnagraficaStorageType.LOCAL_UPLOAD.value:
            if connector is None:
                raise ValueError("NAS connector required for local document import")
            local_path = _store_document_locally(connector, subject_id, document_preview)
        document = db.scalar(
            select(AnagraficaDocument).where(AnagraficaDocument.nas_path == document_preview.nas_path)
        )
        if document is None:
            document = AnagraficaDocument(
                subject_id=subject_id,
                doc_type=document_preview.doc_type,
                filename=document_preview.filename,
                nas_path=document_preview.nas_path,
                classification_source=document_preview.classification_source,
                storage_type=storage_mode,
                local_path=local_path,
                mime_type=_guess_mime_type(document_preview.extension),
                uploaded_at=imported_at if storage_mode == AnagraficaStorageType.LOCAL_UPLOAD.value else None,
                notes=_document_notes(document_preview),
            )
            db.add(document)
            created += 1
        else:
            document.subject_id = subject_id
            document.doc_type = document_preview.doc_type
            document.filename = document_preview.filename
            document.classification_source = document_preview.classification_source
            document.storage_type = storage_mode
            document.local_path = local_path
            document.mime_type = _guess_mime_type(document_preview.extension)
            document.uploaded_at = imported_at if storage_mode == AnagraficaStorageType.LOCAL_UPLOAD.value else document.uploaded_at
            document.notes = _document_notes(document_preview)
            db.add(document)
            updated += 1
    db.flush()
    return {"created": created, "updated": updated}


def _create_audit_log(
    db: Session,
    subject_id: uuid.UUID,
    changed_by_user_id: int | None,
    action: str,
    diff_json: dict[str, object],
) -> None:
    db.add(
        AnagraficaAuditLog(
            subject_id=subject_id,
            changed_by_user_id=changed_by_user_id,
            action=action,
            diff_json=diff_json,
        )
    )
    db.flush()


def _guess_mime_type(extension: str | None) -> str | None:
    if extension == ".pdf":
        return "application/pdf"
    if extension in {".gif"}:
        return "image/gif"
    if extension in {".png"}:
        return "image/png"
    if extension in {".jpg", ".jpeg"}:
        return "image/jpeg"
    return None


def _document_notes(document_preview: AnagraficaPreviewDocument) -> str | None:
    if not document_preview.warnings:
        return None
    return ", ".join(document_preview.warnings)


def _normalize_match_value(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^A-Z0-9]+", "", value.upper())


def _subject_identifiers(db: Session, subject: AnagraficaSubject) -> list[str]:
    person = db.get(AnagraficaPerson, subject.id)
    company = db.get(AnagraficaCompany, subject.id)
    identifiers = [subject.source_name_raw]
    if person is not None:
        identifiers.extend([person.cognome, person.nome, person.codice_fiscale, f"{person.cognome}{person.nome}"])
    if company is not None:
        identifiers.extend([company.ragione_sociale, company.partita_iva, company.codice_fiscale])
    return [value for value in identifiers if value]


def _subject_primary_identifiers(db: Session, subject: AnagraficaSubject) -> list[str]:
    person = db.get(AnagraficaPerson, subject.id)
    company = db.get(AnagraficaCompany, subject.id)
    identifiers: list[str] = []
    if person is not None and person.codice_fiscale:
        identifiers.append(person.codice_fiscale)
    if company is not None:
        if company.partita_iva:
            identifiers.append(company.partita_iva)
        if company.codice_fiscale:
            identifiers.append(company.codice_fiscale)
    return [value for value in identifiers if value]


def _subject_display_name(db: Session, subject: AnagraficaSubject) -> str:
    person = db.get(AnagraficaPerson, subject.id)
    company = db.get(AnagraficaCompany, subject.id)
    if person is not None:
        return f"{person.cognome} {person.nome}".strip()
    if company is not None:
        return company.ragione_sociale
    return subject.source_name_raw


def _derive_existing_subject_letter(db: Session, subject: AnagraficaSubject) -> str | None:
    if subject.nas_folder_letter:
        return subject.nas_folder_letter.strip().upper()
    display_name = _subject_display_name(db, subject)
    for source_value in (display_name, subject.source_name_raw):
        for char in source_value.strip():
            if char.isalpha():
                return char.upper()
    return None


def _score_subject_folder_candidate(db: Session, subject: AnagraficaSubject, folder_name: str) -> int:
    normalized_folder = _normalize_match_value(folder_name)
    if not normalized_folder:
        return 0

    person = db.get(AnagraficaPerson, subject.id)
    company = db.get(AnagraficaCompany, subject.id)
    score = 0

    for identifier in _subject_identifiers(db, subject):
        normalized_identifier = _normalize_match_value(identifier)
        if normalized_identifier and normalized_identifier in normalized_folder:
            score += 30

    if person is not None:
        surname = _normalize_match_value(person.cognome)
        name = _normalize_match_value(person.nome)
        fiscal_code = _normalize_match_value(person.codice_fiscale)
        if fiscal_code and fiscal_code in normalized_folder:
            score += 500
        if surname and surname in normalized_folder:
            score += 150
        if name and name in normalized_folder:
            score += 80
    elif company is not None:
        company_name = _normalize_match_value(company.ragione_sociale)
        vat = _normalize_match_value(company.partita_iva)
        tax_code = _normalize_match_value(company.codice_fiscale)
        if vat and vat in normalized_folder:
            score += 500
        if tax_code and tax_code in normalized_folder:
            score += 250
        if company_name and company_name in normalized_folder:
            score += 180

    return score


def _filter_candidates_by_primary_identifier(
    db: Session,
    subject: AnagraficaSubject,
    candidates: list[DiscoveredSubjectFolder],
) -> list[DiscoveredSubjectFolder]:
    primary_identifiers = [_normalize_match_value(value) for value in _subject_primary_identifiers(db, subject)]
    primary_identifiers = [value for value in primary_identifiers if value]
    if not primary_identifiers:
        return []
    return [
        candidate
        for candidate in candidates
        if any(identifier in _normalize_match_value(candidate.folder_name) for identifier in primary_identifiers)
    ]


def _subject_has_primary_identifiers(db: Session, subject: AnagraficaSubject) -> bool:
    return any(_normalize_match_value(value) for value in _subject_primary_identifiers(db, subject))


def _path_matches_primary_identifier(db: Session, subject: AnagraficaSubject, path: str) -> bool:
    normalized_path = _normalize_match_value(path)
    primary_identifiers = [_normalize_match_value(value) for value in _subject_primary_identifiers(db, subject)]
    primary_identifiers = [value for value in primary_identifiers if value]
    if not primary_identifiers:
        return True
    return any(identifier in normalized_path for identifier in primary_identifiers)


def _is_supported_nas_document_path(path: str) -> bool:
    normalized_parts = [part.strip() for part in PurePosixPath(path).parts if part.strip()]
    if any(part.startswith("@eaDir") for part in normalized_parts):
        return False
    filename = normalized_parts[-1] if normalized_parts else ""
    if filename.endswith("@SynoEAStream"):
        return False
    return True


def _safe_relative_parts(relative_path: str) -> list[str]:
    parts = [part for part in PurePosixPath(relative_path).parts if part not in {"", ".", ".."}]
    return parts or ["document.bin"]


def _store_document_locally(
    connector: NasCommandRunner,
    subject_id: uuid.UUID,
    document_preview: AnagraficaPreviewDocument,
) -> str:
    storage_root = Path(settings.anagrafica_document_storage_path)
    target_path = storage_root / str(subject_id) / Path(*_safe_relative_parts(document_preview.relative_path))
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_bytes(connector.download_file(document_preview.nas_path))
    return str(target_path)


def store_uploaded_document(
    subject_id: uuid.UUID,
    filename: str,
    file_bytes: bytes,
) -> str:
    storage_root = Path(settings.anagrafica_document_storage_path)
    safe_name = Path(filename).name or "document.bin"
    target_path = storage_root / str(subject_id) / "manual" / f"{uuid.uuid4()}-{safe_name}"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_bytes(file_bytes)
    return str(target_path)


def create_manual_document(
    db: Session,
    current_user: ApplicationUser,
    subject_id: uuid.UUID,
    filename: str,
    file_bytes: bytes,
    doc_type: str,
    mime_type: str | None = None,
    notes: str | None = None,
) -> AnagraficaDocument:
    subject = db.get(AnagraficaSubject, subject_id)
    if subject is None:
        raise ValueError("Subject not found")

    local_path = store_uploaded_document(subject_id, filename, file_bytes)
    nas_target_path = None

    if subject.nas_folder_path:
        connector = get_nas_client()
        try:
            nas_target_path = _store_document_on_nas(connector, subject, filename, file_bytes)
        finally:
            close = getattr(connector, "close", None)
            if callable(close):
                close()

    document = AnagraficaDocument(
        subject_id=subject_id,
        doc_type=doc_type,
        filename=Path(filename).name or "document.bin",
        nas_path=nas_target_path,
        classification_source="manual",
        storage_type=AnagraficaStorageType.LOCAL_UPLOAD.value,
        local_path=local_path,
        mime_type=mime_type or mimetypes.guess_type(filename)[0],
        uploaded_at=datetime.now(UTC),
        notes=notes,
    )
    db.add(document)
    _create_audit_log(
        db,
        subject_id,
        current_user.id,
        "document_manual_uploaded",
        {
            "document_filename": document.filename,
            "doc_type": doc_type,
            "notes": notes,
            "nas_path": nas_target_path,
            "nas_synced": bool(nas_target_path),
        },
    )
    db.commit()
    db.refresh(document)
    return document


def _store_document_on_nas(
    connector: NasCommandRunner,
    subject: AnagraficaSubject,
    filename: str,
    file_bytes: bytes,
) -> str:
    if not subject.nas_folder_path:
        raise ValueError("Subject NAS folder path is not configured")

    safe_name = Path(filename).name or "document.bin"
    upload_root = PurePosixPath(subject.nas_folder_path)
    connector.ensure_directory(str(upload_root))

    target_path = _resolve_unique_nas_target_path(connector, upload_root, safe_name)
    connector.upload_file(str(target_path), file_bytes)
    return str(target_path)


def _resolve_unique_nas_target_path(
    connector: NasCommandRunner,
    upload_root: PurePosixPath,
    filename: str,
) -> PurePosixPath:
    base_name = Path(filename).stem or "document"
    suffix = Path(filename).suffix

    candidate = upload_root / filename
    if not connector.path_exists(str(candidate)):
        return candidate

    attempt = 1
    while True:
        candidate = upload_root / f"{base_name} ({attempt}){suffix}"
        if not connector.path_exists(str(candidate)):
            return candidate
        attempt += 1


def _clear_local_storage(storage_root: Path) -> int:
    if not storage_root.exists():
        return 0

    deleted_files = 0
    for file_path in sorted((path for path in storage_root.rglob("*") if path.is_file()), reverse=True):
        file_path.unlink(missing_ok=True)
        deleted_files += 1

    for directory in sorted((path for path in storage_root.rglob("*") if path.is_dir()), reverse=True):
        directory.rmdir()
    storage_root.mkdir(parents=True, exist_ok=True)
    return deleted_files


def _warning_to_dict(warning: AnagraficaNASWarning) -> dict[str, str | None]:
    return {
        "code": warning.code,
        "message": warning.message,
        "path": warning.path,
    }
