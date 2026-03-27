from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import os
import shlex
from typing import Protocol
import uuid

from sqlalchemy import select
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
            return self._split_command_output(self.connector.run_command(command))
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
                        subject_id=persisted_subject.id,
                        documents=subject_preview.documents,
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
    subject_id: uuid.UUID,
    documents: list[AnagraficaPreviewDocument],
) -> dict[str, int]:
    created = 0
    updated = 0
    for document_preview in documents:
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
                storage_type=AnagraficaStorageType.NAS_LINK.value,
                mime_type=_guess_mime_type(document_preview.extension),
                notes=_document_notes(document_preview),
            )
            db.add(document)
            created += 1
        else:
            document.subject_id = subject_id
            document.doc_type = document_preview.doc_type
            document.filename = document_preview.filename
            document.classification_source = document_preview.classification_source
            document.storage_type = AnagraficaStorageType.NAS_LINK.value
            document.mime_type = _guess_mime_type(document_preview.extension)
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


def _warning_to_dict(warning: AnagraficaNASWarning) -> dict[str, str | None]:
    return {
        "code": warning.code,
        "message": warning.message,
        "path": warning.path,
    }
