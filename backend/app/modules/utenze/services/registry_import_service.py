from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.utenze.models import (
    AnagraficaDocument,
    AnagraficaImportJob,
    AnagraficaImportJobStatus,
    AnagraficaStorageType,
    AnagraficaSubject,
)


class RegistrySubjectPreview(Protocol):
    letter: str
    requires_review: bool
    documents: list[Any]


class RegistryMatchedFolder(Protocol):
    nas_folder_path: str


@dataclass(slots=True)
class RegistryDocumentPersistence:
    db: Session
    subject: AnagraficaSubject
    subject_preview: RegistrySubjectPreview
    matched_folder: RegistryMatchedFolder
    job: AnagraficaImportJob
    upsert_documents: Callable[..., dict[str, int]]
    create_audit_log: Callable[..., None]


def is_scheduled_registry_job(job: AnagraficaImportJob) -> bool:
    return isinstance(job.log_json, dict) and job.log_json.get("trigger") == "worker_schedule"


def registry_job_has_valid_actor(db: Session, job: AnagraficaImportJob) -> bool:
    if job.requested_by_user_id is None:
        return is_scheduled_registry_job(job)
    return db.get(ApplicationUser, job.requested_by_user_id) is not None


def registry_job_metadata(job: AnagraficaImportJob) -> dict[str, object]:
    job_log = job.log_json if isinstance(job.log_json, dict) else {}
    return {
        key: job_log[key]
        for key in ("mode", "trigger", "scheduled_at")
        if job_log.get(key) is not None
    }


def persist_registry_subject_documents(context: RegistryDocumentPersistence) -> dict[str, int]:
    documents = context.subject_preview.documents
    if is_scheduled_registry_job(context.job):
        existing_paths = set(
            context.db.scalars(
                select(AnagraficaDocument.nas_path).where(
                    AnagraficaDocument.subject_id == context.subject.id
                )
            ).all()
        )
        documents = [document for document in documents if document.nas_path not in existing_paths]
    if not documents:
        return {"created": 0, "updated": 0}

    imported_at = context.job.started_at or datetime.now(UTC)
    context.subject.nas_folder_path = context.matched_folder.nas_folder_path
    context.subject.nas_folder_letter = context.subject_preview.letter
    context.subject.requires_review = context.subject_preview.requires_review
    context.subject.imported_at = imported_at
    context.db.add(context.subject)
    document_stats = context.upsert_documents(
        db=context.db,
        connector=None,
        subject_id=context.subject.id,
        documents=documents,
        storage_mode=AnagraficaStorageType.NAS_LINK.value,
        imported_at=imported_at,
    )
    context.create_audit_log(
        db=context.db,
        subject_id=context.subject.id,
        changed_by_user_id=context.job.requested_by_user_id,
        action="bulk_import_from_registry",
        diff_json={
            "job_id": str(context.job.id),
            "trigger": "worker_schedule" if is_scheduled_registry_job(context.job) else "manual",
            "matched_folder_path": context.matched_folder.nas_folder_path,
            "created_documents": document_stats["created"],
            "updated_documents": document_stats["updated"],
        },
    )
    return document_stats


def ensure_scheduled_registry_bulk_import_job(
    db: Session,
    schedule_time: time,
    schedule_timezone: ZoneInfo,
    *,
    now: datetime | None = None,
) -> uuid.UUID | None:
    active_job_id = db.scalar(
        select(AnagraficaImportJob.id)
        .where(
            AnagraficaImportJob.letter == "REGISTRY",
            AnagraficaImportJob.status.in_(
                [AnagraficaImportJobStatus.PENDING.value, AnagraficaImportJobStatus.RUNNING.value]
            ),
        )
        .limit(1)
    )
    if active_job_id is not None:
        return None

    current_time = _as_aware_utc(now or datetime.now(UTC))
    local_time = current_time.astimezone(schedule_timezone)
    scheduled_time = datetime.combine(local_time.date(), schedule_time, tzinfo=schedule_timezone)
    if local_time < scheduled_time:
        return None

    latest_scheduled_job = db.scalar(
        select(AnagraficaImportJob)
        .where(
            AnagraficaImportJob.letter == "REGISTRY",
            AnagraficaImportJob.requested_by_user_id.is_(None),
        )
        .order_by(AnagraficaImportJob.created_at.desc())
        .limit(1)
    )
    if (
        latest_scheduled_job is not None
        and _scheduled_registry_job_date(
            latest_scheduled_job,
            schedule_timezone,
        )
        >= local_time.date()
    ):
        return None

    total_subjects = int(db.scalar(select(func.count()).select_from(AnagraficaSubject)) or 0)
    job = AnagraficaImportJob(
        requested_by_user_id=None,
        letter="REGISTRY",
        status=AnagraficaImportJobStatus.PENDING.value,
        total_folders=total_subjects,
        imported_ok=0,
        imported_errors=0,
        warning_count=0,
        log_json={
            "mode": "registry_import",
            "trigger": "worker_schedule",
            "scheduled_at": current_time.isoformat(),
            "warnings": [],
            "errors": [],
            "items": [],
        },
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job.id


def claim_next_registry_import_job(
    db: Session,
    *,
    auto_import_enabled: bool,
    schedule_time: time,
    schedule_timezone: ZoneInfo,
) -> uuid.UUID | None:
    if auto_import_enabled:
        ensure_scheduled_registry_bulk_import_job(db, schedule_time, schedule_timezone)
    job = db.scalar(
        select(AnagraficaImportJob)
        .where(
            AnagraficaImportJob.letter == "REGISTRY",
            AnagraficaImportJob.status == AnagraficaImportJobStatus.PENDING.value,
        )
        .order_by(AnagraficaImportJob.created_at.asc())
        .with_for_update(skip_locked=True)
    )
    if job is None:
        return None
    job.status = AnagraficaImportJobStatus.RUNNING.value
    job.started_at = datetime.now(UTC)
    db.commit()
    return job.id


def _scheduled_registry_job_date(job: AnagraficaImportJob, schedule_timezone: ZoneInfo) -> date:
    job_log = job.log_json if isinstance(job.log_json, dict) else {}
    scheduled_at = job_log.get("scheduled_at")
    reference_time = (
        datetime.fromisoformat(scheduled_at) if isinstance(scheduled_at, str) else job.created_at
    )
    return _as_aware_utc(reference_time).astimezone(schedule_timezone).date()


def _as_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
