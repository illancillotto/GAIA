"""Practice services."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.riordino.enums import EventType, PHASE_1, PHASE_2, PhaseStatus, PracticeStatus, StepStatus
from app.modules.riordino.models import RiordinoPhase, RiordinoPractice, RiordinoStep, RiordinoStepTemplate
from app.modules.riordino.repositories import PracticeRepository
from app.modules.riordino.services.common import create_event, require_admin_like, utcnow


def create_practice(db: Session, data: dict, created_by_user_id: int) -> RiordinoPractice:
    repo = PracticeRepository(db)
    code = repo.next_code(datetime.now().year)
    practice = RiordinoPractice(
        code=code,
        title=data["title"],
        description=data.get("description"),
        municipality=data["municipality"],
        grid_code=data["grid_code"],
        lot_code=data["lot_code"],
        owner_user_id=data["owner_user_id"],
        created_by=created_by_user_id,
        current_phase=PHASE_1,
        status=PracticeStatus.draft.value,
    )
    repo.add(practice)

    phase_1 = RiordinoPhase(practice_id=practice.id, phase_code=PHASE_1, status=PhaseStatus.not_started.value)
    phase_2 = RiordinoPhase(practice_id=practice.id, phase_code=PHASE_2, status=PhaseStatus.not_started.value)
    db.add_all([phase_1, phase_2])
    db.flush()

    templates = list(db.scalars(select(RiordinoStepTemplate).where(RiordinoStepTemplate.is_active.is_(True)).order_by(RiordinoStepTemplate.phase_code, RiordinoStepTemplate.sequence_no)))
    steps: list[RiordinoStep] = []
    for template in templates:
        phase_id = phase_1.id if template.phase_code == PHASE_1 else phase_2.id
        steps.append(
            RiordinoStep(
                practice_id=practice.id,
                phase_id=phase_id,
                template_id=template.id,
                code=template.code,
                title=template.title,
                sequence_no=template.sequence_no,
                status=StepStatus.todo.value,
                is_required=template.is_required,
                branch=template.branch,
                is_decision=template.is_decision,
                requires_document=template.requires_document,
            )
        )
    db.add_all(steps)
    create_event(
        db,
        practice_id=practice.id,
        created_by=created_by_user_id,
        event_type=EventType.practice_created,
        payload_json={"code": practice.code},
    )
    db.flush()
    return practice


def list_practices(
    db: Session,
    *,
    status_filter: str | None,
    municipality: str | None,
    phase: str | None,
    owner: int | None,
    page: int,
    per_page: int,
) -> tuple[list[RiordinoPractice], int]:
    return PracticeRepository(db).list(
        status=status_filter,
        municipality=municipality,
        phase=phase,
        owner=owner,
        page=page,
        per_page=per_page,
    )


def get_practice_detail(db: Session, practice_id: UUID) -> tuple[RiordinoPractice, tuple[int, int, int]]:
    repo = PracticeRepository(db)
    practice = repo.get(practice_id)
    if not practice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practice not found")
    return practice, repo.detail_counts(practice_id)


def update_practice(db: Session, practice_id: UUID, data: dict, updated_by_user_id: int) -> RiordinoPractice:
    practice = PracticeRepository(db).get(practice_id)
    if not practice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practice not found")
    if practice.version != data["version"]:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Version conflict")
    for field in ("title", "description", "municipality", "grid_code", "lot_code", "owner_user_id"):
        if field in data and data[field] is not None:
            setattr(practice, field, data[field])
    practice.version += 1
    create_event(
        db,
        practice_id=practice.id,
        created_by=updated_by_user_id,
        event_type=EventType.practice_updated,
        payload_json={"version": practice.version},
    )
    db.flush()
    return practice


def delete_practice(db: Session, practice_id: UUID, current_user) -> RiordinoPractice:
    require_admin_like(current_user)
    practice = PracticeRepository(db).get(practice_id)
    if not practice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practice not found")
    if practice.status != PracticeStatus.draft.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only draft practices can be deleted")
    practice.deleted_at = utcnow()
    create_event(db, practice_id=practice.id, created_by=current_user.id, event_type=EventType.practice_deleted)
    db.flush()
    return practice


def archive_practice(db: Session, practice_id: UUID, current_user) -> RiordinoPractice:
    require_admin_like(current_user)
    practice = PracticeRepository(db).get(practice_id)
    if not practice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practice not found")
    if practice.status != PracticeStatus.completed.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only completed practices can be archived")
    practice.status = PracticeStatus.archived.value
    practice.archived_at = utcnow()
    create_event(db, practice_id=practice.id, created_by=current_user.id, event_type=EventType.practice_archived)
    db.flush()
    return practice


def complete_practice(db: Session, practice_id: UUID, current_user) -> RiordinoPractice:
    require_admin_like(current_user)
    practice = PracticeRepository(db).get(practice_id)
    if not practice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practice not found")
    phase_2 = next((phase for phase in practice.phases if phase.phase_code == PHASE_2), None)
    if not phase_2 or phase_2.status != PhaseStatus.completed.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Phase 2 must be completed")
    open_issues = [issue for issue in practice.issues if issue.status != "closed"]
    if open_issues:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Practice has open issues")
    open_appeals = [appeal for appeal in practice.appeals if appeal.status in {"open", "under_review"}]
    if open_appeals:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Practice has open appeals")
    practice.status = PracticeStatus.completed.value
    practice.completed_at = utcnow()
    create_event(db, practice_id=practice.id, created_by=current_user.id, event_type=EventType.status_changed, payload_json={"status": practice.status})
    db.flush()
    return practice
