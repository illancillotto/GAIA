"""Workflow services."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.riordino.enums import EventType, PHASE_1, PHASE_2, PhaseStatus, PracticeStatus, StepStatus
from app.modules.riordino.models import RiordinoAppeal
from app.modules.riordino.repositories import AppealRepository, PracticeRepository, WorkflowRepository
from app.modules.riordino.services.common import create_event, require_admin_like, utcnow


def advance_step(
    db: Session,
    practice_id: UUID,
    step_id: UUID,
    current_user,
    *,
    outcome_code: str | None = None,
    outcome_notes: str | None = None,
):
    repo = WorkflowRepository(db)
    step = repo.get_step(practice_id, step_id)
    if not step:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Step not found")
    if step.status not in {StepStatus.todo.value, StepStatus.in_progress.value}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Step cannot be advanced")
    if step.is_decision and not outcome_code:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Outcome code is required")
    if step.requires_document and not repo.has_documents_for_step(step.id):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Document required")
    if repo.open_blocking_issues_for_step(step.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Blocking issues must be closed")
    if repo.blocking_checklist_for_step(step.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Blocking checklist items must be checked")

    now = utcnow()
    practice = step.practice
    if practice.status == PracticeStatus.draft.value:
        practice.status = PracticeStatus.open.value
        practice.opened_at = now
    if step.phase.status == PhaseStatus.not_started.value:
        step.phase.status = PhaseStatus.in_progress.value
        step.phase.started_at = step.phase.started_at or now
        create_event(db, practice_id=practice_id, phase_id=step.phase_id, created_by=current_user.id, event_type=EventType.phase_started)

    step.status = StepStatus.done.value
    step.started_at = step.started_at or now
    step.completed_at = now
    step.outcome_code = outcome_code
    step.outcome_notes = outcome_notes
    step.version += 1

    if step.code == "F2_VERIFICA" and outcome_code == "conforme":
        skipped = repo.auto_skip_branch(practice_id, "anomalia", "Verifica conforme - skip automatico")
        for branch_step in skipped:
            create_event(
                db,
                practice_id=practice_id,
                phase_id=branch_step.phase_id,
                step_id=branch_step.id,
                created_by=current_user.id,
                event_type=EventType.step_skipped,
                payload_json={"reason": branch_step.skip_reason},
            )

    create_event(
        db,
        practice_id=practice_id,
        phase_id=step.phase_id,
        step_id=step.id,
        created_by=current_user.id,
        event_type=EventType.step_completed,
        payload_json={"outcome_code": outcome_code},
    )
    db.flush()
    return step


def skip_step(db: Session, practice_id: UUID, step_id: UUID, current_user, skip_reason: str):
    require_admin_like(current_user)
    step = WorkflowRepository(db).get_step(practice_id, step_id)
    if not step:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Step not found")
    if not skip_reason.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Skip reason is required")
    step.status = StepStatus.skipped.value
    step.skip_reason = skip_reason
    step.version += 1
    create_event(
        db,
        practice_id=practice_id,
        phase_id=step.phase_id,
        step_id=step.id,
        created_by=current_user.id,
        event_type=EventType.step_skipped,
        payload_json={"reason": skip_reason},
    )
    db.flush()
    return step


def reopen_step(db: Session, practice_id: UUID, step_id: UUID, current_user):
    require_admin_like(current_user)
    step = WorkflowRepository(db).get_step(practice_id, step_id)
    if not step:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Step not found")
    if step.status != StepStatus.done.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only completed steps can be reopened")
    step.status = StepStatus.in_progress.value
    step.completed_at = None
    step.outcome_code = None
    step.outcome_notes = None
    step.version += 1
    create_event(db, practice_id=practice_id, phase_id=step.phase_id, step_id=step.id, created_by=current_user.id, event_type=EventType.step_reopened)
    db.flush()
    return step


def start_phase(db: Session, practice_id: UUID, phase_id: UUID, current_user):
    require_admin_like(current_user)
    repo = WorkflowRepository(db)
    phase = repo.get_phase(practice_id, phase_id)
    if not phase:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phase not found")
    practice = PracticeRepository(db).get(practice_id)
    if phase.phase_code == PHASE_2:
        phase_1 = next((item for item in practice.phases if item.phase_code == PHASE_1), None)
        if not phase_1 or phase_1.status != PhaseStatus.completed.value:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Phase 1 must be completed")
        practice.current_phase = PHASE_2
    if practice.status == PracticeStatus.draft.value:
        practice.status = PracticeStatus.open.value
        practice.opened_at = practice.opened_at or utcnow()
    phase.status = PhaseStatus.in_progress.value
    phase.started_at = phase.started_at or utcnow()
    create_event(db, practice_id=practice_id, phase_id=phase.id, created_by=current_user.id, event_type=EventType.phase_started)
    db.flush()
    return phase


def complete_phase(db: Session, practice_id: UUID, phase_id: UUID, current_user, notes: str | None = None):
    require_admin_like(current_user)
    repo = WorkflowRepository(db)
    phase = repo.get_phase(practice_id, phase_id)
    if not phase:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phase not found")
    steps = repo.phase_steps(phase_id)
    incomplete = [step.code for step in steps if step.is_required and step.status not in {StepStatus.done.value, StepStatus.skipped.value}]
    if incomplete:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Required steps incomplete: {', '.join(incomplete)}")
    if phase.phase_code == PHASE_1:
        open_appeals = list(
            db.scalars(
                select(RiordinoAppeal).where(
                    RiordinoAppeal.practice_id == practice_id,
                    RiordinoAppeal.status.in_(["open", "under_review"]),
                )
            )
        )
        if open_appeals:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Open appeals block phase completion")
    if repo.open_blocking_issues_for_phase(phase_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Blocking issues must be closed")
    phase.status = PhaseStatus.completed.value
    phase.completed_at = utcnow()
    phase.approved_by = current_user.id
    phase.notes = notes

    practice = PracticeRepository(db).get(practice_id)
    if phase.phase_code == PHASE_1:
        practice.current_phase = PHASE_2
        practice.status = PracticeStatus.in_review.value

    create_event(db, practice_id=practice_id, phase_id=phase.id, created_by=current_user.id, event_type=EventType.phase_completed)
    db.flush()
    return phase
