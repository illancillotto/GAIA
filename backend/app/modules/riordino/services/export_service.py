"""Export services for Riordino practice dossier and summary files."""

from __future__ import annotations

import csv
import json
import zipfile
from io import BytesIO, StringIO
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.riordino.models import RiordinoPractice
from app.modules.riordino.repositories import PracticeRepository


def _get_practice(db: Session, practice_id: UUID) -> RiordinoPractice:
    practice = PracticeRepository(db).get(practice_id)
    if not practice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practice not found")
    return practice


def build_practice_summary_rows(practice: RiordinoPractice) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for phase in practice.phases:
        for step in phase.steps:
            rows.append(
                {
                    "practice_code": practice.code,
                    "practice_title": practice.title,
                    "municipality": practice.municipality,
                    "grid_code": practice.grid_code,
                    "lot_code": practice.lot_code,
                    "practice_status": practice.status,
                    "phase_code": phase.phase_code,
                    "phase_status": phase.status,
                    "step_code": step.code,
                    "step_title": step.title,
                    "step_status": step.status,
                    "is_required": step.is_required,
                    "branch": step.branch or "",
                    "is_decision": step.is_decision,
                    "outcome_code": step.outcome_code or "",
                    "skip_reason": step.skip_reason or "",
                    "documents_count": len([document for document in step.documents if document.deleted_at is None]),
                    "checklist_total": len(step.checklist_items),
                    "checklist_checked": len([item for item in step.checklist_items if item.is_checked]),
                    "started_at": step.started_at.isoformat() if step.started_at else "",
                    "completed_at": step.completed_at.isoformat() if step.completed_at else "",
                }
            )
    return rows


def export_practice_summary_csv(db: Session, practice_id: UUID) -> tuple[bytes, str]:
    practice = _get_practice(db, practice_id)
    rows = build_practice_summary_rows(practice)
    fieldnames = list(rows[0].keys()) if rows else [
        "practice_code",
        "practice_title",
        "municipality",
        "grid_code",
        "lot_code",
        "practice_status",
        "phase_code",
        "phase_status",
        "step_code",
        "step_title",
        "step_status",
        "is_required",
        "branch",
        "is_decision",
        "outcome_code",
        "skip_reason",
        "documents_count",
        "checklist_total",
        "checklist_checked",
        "started_at",
        "completed_at",
    ]
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    filename = f"{practice.code.lower()}-summary.csv"
    return buffer.getvalue().encode("utf-8"), filename


def export_practice_dossier_zip(db: Session, practice_id: UUID) -> tuple[BytesIO, str]:
    practice = _get_practice(db, practice_id)
    summary_content, _ = export_practice_summary_csv(db, practice_id)

    archive_buffer = BytesIO()
    manifest = {
        "practice": {
            "id": str(practice.id),
            "code": practice.code,
            "title": practice.title,
            "municipality": practice.municipality,
            "grid_code": practice.grid_code,
            "lot_code": practice.lot_code,
            "status": practice.status,
            "current_phase": practice.current_phase,
        },
        "counts": {
            "phases": len(practice.phases),
            "steps": sum(len(phase.steps) for phase in practice.phases),
            "documents": len([document for document in practice.documents if document.deleted_at is None]),
            "issues": len(practice.issues),
            "appeals": len(practice.appeals),
        },
    }

    with zipfile.ZipFile(archive_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
        archive.writestr("summary/practice-summary.csv", summary_content)

        for phase in practice.phases:
            for step in phase.steps:
                for document in step.documents:
                    if document.deleted_at is not None:
                        continue
                    path = Path(document.storage_path)
                    if not path.exists():
                        continue
                    archive.write(path, arcname=f"documents/{phase.phase_code}/{step.code}/{document.original_filename}")

        for document in practice.documents:
            if document.deleted_at is not None or document.step_id is not None:
                continue
            path = Path(document.storage_path)
            if not path.exists():
                continue
            archive.write(path, arcname=f"documents/_general/{document.original_filename}")

    archive_buffer.seek(0)
    filename = f"{practice.code.lower()}-dossier.zip"
    return archive_buffer, filename
