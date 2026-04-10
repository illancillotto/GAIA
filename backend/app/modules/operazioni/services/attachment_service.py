"""Attachment and storage services."""

from __future__ import annotations

import hashlib
import logging
import os
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import BinaryIO

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.operazioni.models.attachments import (
    Attachment,
    StorageQuotaAlert,
    StorageQuotaMetric,
)

logger = logging.getLogger(__name__)

QUOTA_BYTES = 50 * 1024 * 1024 * 1024  # 50 GB
ALERT_THRESHOLDS = [
    ("warning_70", Decimal("70.00")),
    ("warning_85", Decimal("85.00")),
    ("critical_95", Decimal("95.00")),
]

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "audio/mpeg",
    "audio/wav",
    "audio/ogg",
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB per file


def get_storage_base_path() -> Path:
    return Path(
        os.environ.get("OPERAZIONI_STORAGE_PATH", "/storage/operazioni/attachments")
    )


def build_storage_path(filename: str) -> Path:
    now = datetime.now()
    unique_name = f"{uuid.uuid4()}_{filename}"
    return get_storage_base_path() / str(now.year) / f"{now.month:02d}" / unique_name


def compute_checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def get_attachment_type(mime_type: str) -> str:
    if mime_type.startswith("image/"):
        return "image"
    if mime_type.startswith("audio/"):
        return "audio"
    if mime_type.startswith("video/"):
        return "video"
    return "document"


def get_file_extension(filename: str) -> str | None:
    if "." in filename:
        return filename.rsplit(".", 1)[-1].lower()
    return None


def check_quota(db: Session) -> dict:
    total_used = (
        db.scalar(
            select(func.sum(Attachment.file_size_bytes)).where(
                Attachment.is_deleted == False
            )
        )
        or 0
    )
    percentage = (
        (Decimal(total_used) / Decimal(QUOTA_BYTES) * 100).quantize(Decimal("0.01"))
        if QUOTA_BYTES > 0
        else Decimal(0)
    )
    return {
        "total_bytes_used": total_used,
        "quota_bytes": QUOTA_BYTES,
        "percentage_used": float(percentage),
    }


def check_and_create_alerts(
    db: Session, metric: StorageQuotaMetric
) -> list[StorageQuotaAlert]:
    alerts = []
    for level, threshold in ALERT_THRESHOLDS:
        if metric.percentage_used >= threshold:
            existing = db.scalar(
                select(StorageQuotaAlert).where(
                    StorageQuotaAlert.alert_level == level,
                    StorageQuotaAlert.resolved_at.is_(None),
                )
            )
            if not existing:
                alert = StorageQuotaAlert(
                    alert_level=level,
                    threshold_percentage=threshold,
                    triggered_at=datetime.now(),
                    metric_id=metric.id,
                )
                db.add(alert)
                alerts.append(alert)
                logger.warning(
                    "Storage alert triggered: %s at %.2f%%",
                    level,
                    metric.percentage_used,
                )
    return alerts


def create_quota_metric(db: Session) -> StorageQuotaMetric:
    quota = check_quota(db)
    metric = StorageQuotaMetric(
        measured_at=datetime.now(),
        total_bytes_used=quota["total_bytes_used"],
        quota_bytes=quota["quota_bytes"],
        percentage_used=Decimal(str(quota["percentage_used"])),
    )
    db.add(metric)
    db.flush()
    check_and_create_alerts(db, metric)
    return metric


def create_attachment_record(
    db: Session,
    storage_path: str,
    filename: str,
    mime_type: str,
    file_size: int,
    source_context: str,
    source_entity_id: uuid.UUID | None = None,
    uploaded_by_user_id: int | None = None,
    checksum: str | None = None,
) -> Attachment:
    if mime_type not in ALLOWED_MIME_TYPES:
        raise ValueError(f"MIME type not allowed: {mime_type}")
    if file_size > MAX_FILE_SIZE:
        raise ValueError(f"File too large: {file_size} bytes (max {MAX_FILE_SIZE})")

    attachment = Attachment(
        storage_path=storage_path,
        original_filename=filename,
        mime_type=mime_type,
        extension=get_file_extension(filename),
        attachment_type=get_attachment_type(mime_type),
        file_size_bytes=file_size,
        checksum_sha256=checksum,
        source_context=source_context,
        source_entity_id=source_entity_id,
        uploaded_by_user_id=uploaded_by_user_id,
    )
    db.add(attachment)
    db.flush()
    return attachment


def soft_delete_attachment(db: Session, attachment_id: uuid.UUID) -> Attachment:
    attachment = db.get(Attachment, attachment_id)
    if not attachment:
        raise ValueError("Attachment not found")
    attachment.is_deleted = True
    attachment.deleted_at = datetime.now()
    db.flush()
    return attachment


def get_active_alerts(db: Session) -> list[StorageQuotaAlert]:
    return db.scalars(
        select(StorageQuotaAlert)
        .where(StorageQuotaAlert.resolved_at.is_(None))
        .order_by(StorageQuotaAlert.triggered_at.desc())
    ).all()


def get_latest_metric(db: Session) -> StorageQuotaMetric | None:
    return db.scalar(
        select(StorageQuotaMetric)
        .order_by(StorageQuotaMetric.measured_at.desc())
        .limit(1)
    )
