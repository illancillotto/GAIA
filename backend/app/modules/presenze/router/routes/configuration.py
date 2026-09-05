from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.presenze.models import (
    PresenzeCollaboratorScheduleAssignment,
    PresenzeHoliday,
    PresenzeScheduleRule,
    PresenzeScheduleTemplate,
)
from app.modules.presenze.router.common import RequirePresenzeAdmin, RequirePresenzeModule
from app.modules.presenze.router.helpers.daily_records import _get_collaborator_or_404
from app.modules.presenze.router.helpers.schedules import (
    _build_schedule_bootstrap_preview,
    _preset_by_template_code,
    _serialize_schedule_assignment,
    _serialize_schedule_template,
    _upsert_template_rules,
    ensure_system_schedule_templates,
)
from app.modules.presenze.schemas import (
    PresenzeCollaboratorScheduleAssignmentCreate,
    PresenzeCollaboratorScheduleAssignmentResponse,
    PresenzeCredentialCreate,
    PresenzeCredentialResponse,
    PresenzeCredentialTestResult,
    PresenzeCredentialUpdate,
    PresenzeHolidayBootstrapResponse,
    PresenzeHolidayCreate,
    PresenzeHolidayResponse,
    PresenzeHolidayUpdate,
    PresenzeScheduleBootstrapApplyRequest,
    PresenzeScheduleBootstrapApplyResponse,
    PresenzeScheduleBootstrapPreviewResponse,
    PresenzeScheduleRuleCreate,
    PresenzeScheduleRuleResponse,
    PresenzeScheduleRuleUpdate,
    PresenzeScheduleTemplateCreate,
    PresenzeScheduleTemplateResponse,
    PresenzeScheduleTemplateUpdate,
)
from app.modules.presenze.services.credentials import (
    create_credential,
    delete_credential,
    get_credential,
    list_credentials,
    test_credential,
    update_credential,
)
from app.modules.presenze.services.schedule_engine import (
    seed_holidays_for_year,
)

# Keep extracted callable formatting stable for complexity-baseline matching.
# fmt: off

router = APIRouter(prefix="/presenze")

@router.get("/holidays", response_model=list[PresenzeHolidayResponse])
def list_presenze_holidays(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
    year: int | None = Query(default=None, ge=2000, le=2100),
) -> list[PresenzeHolidayResponse]:
    stmt = select(PresenzeHoliday)
    if year is not None:
        stmt = stmt.where(
            PresenzeHoliday.holiday_date >= date(year, 1, 1),
            PresenzeHoliday.holiday_date <= date(year, 12, 31),
        )
    items = db.execute(
        stmt.order_by(PresenzeHoliday.holiday_date.asc(), PresenzeHoliday.company_code.asc())
    ).scalars().all()
    return [PresenzeHolidayResponse.model_validate(item) for item in items]

@router.post("/holidays/bootstrap", response_model=PresenzeHolidayBootstrapResponse)
def bootstrap_presenze_holidays(
    year: int = Query(..., ge=2000, le=2100),
    db: Annotated[Session, Depends(get_db)] = ...,
    _: Annotated[ApplicationUser, RequirePresenzeAdmin] = ...,
    __: Annotated[ApplicationUser, RequirePresenzeModule] = ...,
) -> PresenzeHolidayBootstrapResponse:
    items = seed_holidays_for_year(db, year)
    db.commit()
    return PresenzeHolidayBootstrapResponse(
        year=year,
        created=len(items),
        items=[PresenzeHolidayResponse.model_validate(item) for item in items],
    )

@router.post("/holidays", response_model=PresenzeHolidayResponse, status_code=201)
def create_presenze_holiday(
    payload: PresenzeHolidayCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeHolidayResponse:
    item = PresenzeHoliday(**payload.to_model_payload())
    db.add(item)
    db.commit()
    db.refresh(item)
    return PresenzeHolidayResponse.model_validate(item)

@router.patch("/holidays/{holiday_id}", response_model=PresenzeHolidayResponse)
def update_presenze_holiday(
    holiday_id: int,
    payload: PresenzeHolidayUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeHolidayResponse:
    item = db.get(PresenzeHoliday, holiday_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Holiday not found")
    for field, value in payload.to_model_payload(current_kind=item.holiday_kind).items():
        setattr(item, field, value)
    db.add(item)
    db.commit()
    db.refresh(item)
    return PresenzeHolidayResponse.model_validate(item)

@router.delete("/holidays/{holiday_id}", status_code=204)
def delete_inaz_holiday(
    holiday_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> None:
    item = db.get(PresenzeHoliday, holiday_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Holiday not found")
    db.delete(item)
    db.commit()

@router.get("/schedule/templates", response_model=list[PresenzeScheduleTemplateResponse])
def list_schedule_templates(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> list[PresenzeScheduleTemplateResponse]:
    ensure_system_schedule_templates(db)
    templates = db.execute(
        select(PresenzeScheduleTemplate).order_by(PresenzeScheduleTemplate.code.asc())
    ).scalars().all()
    return [_serialize_schedule_template(db, item) for item in templates]

@router.post("/schedule/templates", response_model=PresenzeScheduleTemplateResponse, status_code=201)
def create_schedule_template(
    payload: PresenzeScheduleTemplateCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeScheduleTemplateResponse:
    item = PresenzeScheduleTemplate(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_schedule_template(db, item)

@router.patch("/schedule/templates/{template_id}", response_model=PresenzeScheduleTemplateResponse)
def update_schedule_template(
    template_id: int,
    payload: PresenzeScheduleTemplateUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeScheduleTemplateResponse:
    item = db.get(PresenzeScheduleTemplate, template_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Schedule template not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_schedule_template(db, item)

@router.delete("/schedule/templates/{template_id}", status_code=204)
def delete_schedule_template(
    template_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> None:
    item = db.get(PresenzeScheduleTemplate, template_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Schedule template not found")
    db.delete(item)
    db.commit()

@router.post("/schedule/templates/{template_id}/rules", response_model=PresenzeScheduleRuleResponse, status_code=201)
def create_schedule_rule(
    template_id: int,
    payload: PresenzeScheduleRuleCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeScheduleRuleResponse:
    if db.get(PresenzeScheduleTemplate, template_id) is None:
        raise HTTPException(status_code=404, detail="Schedule template not found")
    item = PresenzeScheduleRule(template_id=template_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return PresenzeScheduleRuleResponse.model_validate(item)

@router.patch("/schedule/rules/{rule_id}", response_model=PresenzeScheduleRuleResponse)
def update_schedule_rule(
    rule_id: int,
    payload: PresenzeScheduleRuleUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeScheduleRuleResponse:
    item = db.get(PresenzeScheduleRule, rule_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Schedule rule not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.add(item)
    db.commit()
    db.refresh(item)
    return PresenzeScheduleRuleResponse.model_validate(item)

@router.delete("/schedule/rules/{rule_id}", status_code=204)
def delete_schedule_rule(
    rule_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> None:
    item = db.get(PresenzeScheduleRule, rule_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Schedule rule not found")
    db.delete(item)
    db.commit()

@router.get(
    "/collaborators/{collaborator_id}/schedule-assignments",
    response_model=list[PresenzeCollaboratorScheduleAssignmentResponse],
)
def list_collaborator_schedule_assignments(
    collaborator_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> list[PresenzeCollaboratorScheduleAssignmentResponse]:
    _get_collaborator_or_404(db, collaborator_id)
    rows = db.execute(
        select(PresenzeCollaboratorScheduleAssignment)
        .where(PresenzeCollaboratorScheduleAssignment.collaborator_id == collaborator_id)
        .order_by(
            PresenzeCollaboratorScheduleAssignment.valid_from.desc(),
            PresenzeCollaboratorScheduleAssignment.id.desc(),
        )
    ).scalars().all()
    return [_serialize_schedule_assignment(db, row) for row in rows]

@router.post(
    "/collaborators/{collaborator_id}/schedule-assignments",
    response_model=PresenzeCollaboratorScheduleAssignmentResponse,
    status_code=201,
)
def create_collaborator_schedule_assignment(
    collaborator_id: uuid.UUID,
    payload: PresenzeCollaboratorScheduleAssignmentCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeCollaboratorScheduleAssignmentResponse:
    _get_collaborator_or_404(db, collaborator_id)
    if db.get(PresenzeScheduleTemplate, payload.template_id) is None:
        raise HTTPException(status_code=404, detail="Schedule template not found")
    duplicate_assignment = db.execute(
        select(PresenzeCollaboratorScheduleAssignment).where(
            PresenzeCollaboratorScheduleAssignment.collaborator_id == collaborator_id,
            PresenzeCollaboratorScheduleAssignment.template_id == payload.template_id,
            PresenzeCollaboratorScheduleAssignment.valid_from == payload.valid_from,
            PresenzeCollaboratorScheduleAssignment.valid_to == payload.valid_to,
        )
    ).scalar_one_or_none()
    if duplicate_assignment is not None:
        raise HTTPException(status_code=409, detail="Questo template e gia assegnato al collaboratore con la stessa validita")
    item = PresenzeCollaboratorScheduleAssignment(collaborator_id=collaborator_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serialize_schedule_assignment(db, item)

@router.delete("/schedule-assignments/{assignment_id}", status_code=204)
def delete_schedule_assignment(
    assignment_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> None:
    item = db.get(PresenzeCollaboratorScheduleAssignment, assignment_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Schedule assignment not found")
    db.delete(item)
    db.commit()

@router.get("/configuration/schedule-bootstrap-preview", response_model=PresenzeScheduleBootstrapPreviewResponse)
def get_schedule_bootstrap_preview(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeScheduleBootstrapPreviewResponse:
    return _build_schedule_bootstrap_preview(db)

@router.post("/configuration/schedule-bootstrap-apply", response_model=PresenzeScheduleBootstrapApplyResponse)
def apply_schedule_bootstrap(
    payload: PresenzeScheduleBootstrapApplyRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[ApplicationUser, RequirePresenzeAdmin],
    __: Annotated[ApplicationUser, RequirePresenzeModule],
) -> PresenzeScheduleBootstrapApplyResponse:
    preview = _build_schedule_bootstrap_preview(db)
    existing_templates = {
        item.code.strip().upper(): item for item in db.execute(select(PresenzeScheduleTemplate)).scalars().all()
    }
    created_templates = 0
    created_assignments = 0
    skipped_existing_templates = 0
    skipped_existing_assignments = 0
    template_codes: list[str] = []
    assigned_employee_codes: list[str] = []

    if payload.create_missing_templates:
        for preset in preview.presets:
            if preset.already_exists:
                skipped_existing_templates += 1
                continue
            preset_def = _preset_by_template_code(preset.template_code)
            if preset_def is None:
                continue
            template = PresenzeScheduleTemplate(
                code=preset_def.template_code,
                label=preset_def.template_label,
                company_code="53",
                is_active=True,
                notes=preset_def.template_notes,
            )
            db.add(template)
            db.flush()
            _upsert_template_rules(db, template, preset_def.rules)
            existing_templates[template.code.strip().upper()] = template
            created_templates += 1
            template_codes.append(template.code)

    if payload.assign_unassigned_collaborators:
        for suggestion in preview.collaborator_suggestions:
            if suggestion.suggested_template_code is None:
                continue
            if suggestion.suggestion_confidence != "high":
                skipped_existing_assignments += 1
                continue
            if suggestion.already_assigned:
                skipped_existing_assignments += 1
                continue
            template = existing_templates.get(suggestion.suggested_template_code.strip().upper())
            if template is None:
                skipped_existing_assignments += 1
                continue
            db.add(
                PresenzeCollaboratorScheduleAssignment(
                    collaborator_id=suggestion.collaborator_id,
                    template_id=template.id,
                    notes=f"Bootstrap automatico da schedule code INAZ: {', '.join(suggestion.schedule_codes)}",
                )
            )
            created_assignments += 1
            assigned_employee_codes.append(suggestion.employee_code)

    db.commit()
    return PresenzeScheduleBootstrapApplyResponse(
        created_templates=created_templates,
        created_assignments=created_assignments,
        skipped_existing_templates=skipped_existing_templates,
        skipped_existing_assignments=skipped_existing_assignments,
        template_codes=template_codes,
        assigned_employee_codes=assigned_employee_codes,
    )

@router.post("/credentials", response_model=PresenzeCredentialResponse, status_code=201)
def create_presenze_credential(
    payload: PresenzeCredentialCreate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> PresenzeCredentialResponse:
    return create_credential(db, current_user.id, payload)

@router.get("/credentials", response_model=list[PresenzeCredentialResponse])
def list_presenze_credentials(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> list[PresenzeCredentialResponse]:
    return list_credentials(db, current_user)

@router.get("/credentials/{credential_id}", response_model=PresenzeCredentialResponse)
def get_presenze_credential(
    credential_id: int,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> PresenzeCredentialResponse:
    credential = get_credential(db, credential_id, current_user)
    if credential is None:
        raise HTTPException(status_code=404, detail="Credenziale Presenze non trovata")
    return PresenzeCredentialResponse.model_validate(credential)

@router.patch("/credentials/{credential_id}", response_model=PresenzeCredentialResponse)
def update_presenze_credential(
    credential_id: int,
    payload: PresenzeCredentialUpdate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> PresenzeCredentialResponse:
    credential = update_credential(db, credential_id, current_user, payload)
    if credential is None:
        raise HTTPException(status_code=404, detail="Credenziale Presenze non trovata")
    return credential

@router.delete("/credentials/{credential_id}", status_code=204)
def delete_inaz_credential(
    credential_id: int,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    if not delete_credential(db, credential_id, current_user):
        raise HTTPException(status_code=404, detail="Credenziale Presenze non trovata")

@router.post("/credentials/{credential_id}/test", response_model=PresenzeCredentialTestResult)
async def test_presenze_credential(
    credential_id: int,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> PresenzeCredentialTestResult:
    result = await test_credential(db, current_user, credential_id)
    if not result.ok:
        raise HTTPException(status_code=502, detail=result.error)
    return result

# fmt: on
