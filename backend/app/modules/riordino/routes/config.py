"""Configuration routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_module, require_section
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.riordino.models import (
    RiordinoDocumentTypeConfig,
    RiordinoIssueTypeConfig,
    RiordinoPractice,
    RiordinoStepTemplate,
)
from app.modules.riordino.schemas import (
    DocumentTypeConfigCreate,
    DocumentTypeConfigResponse,
    DocumentTypeConfigUpdate,
    IssueTypeConfigCreate,
    IssueTypeConfigResponse,
    IssueTypeConfigUpdate,
    StepTemplateResponse,
    StepTemplateUpdate,
)
from app.modules.riordino.services.common import require_admin_like

router = APIRouter(dependencies=[Depends(require_module("riordino")), Depends(require_section("riordino.config"))])


@router.get("/step-templates", response_model=list[StepTemplateResponse])
def list_step_templates_endpoint(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    items = list(db.scalars(select(RiordinoStepTemplate).order_by(RiordinoStepTemplate.phase_code, RiordinoStepTemplate.sequence_no)))
    return [StepTemplateResponse.model_validate(item) for item in items]


@router.patch("/step-templates/{template_id}", response_model=StepTemplateResponse)
def update_step_template_endpoint(
    template_id: UUID,
    payload: StepTemplateUpdate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    require_admin_like(current_user)
    template = db.get(RiordinoStepTemplate, template_id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(template, key, value)
    db.commit()
    db.refresh(template)
    return template


@router.get("/document-types", response_model=list[DocumentTypeConfigResponse])
def list_document_types_endpoint(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    items = list(
        db.scalars(
            select(RiordinoDocumentTypeConfig)
            .order_by(RiordinoDocumentTypeConfig.sort_order.asc(), RiordinoDocumentTypeConfig.label.asc())
        )
    )
    return [DocumentTypeConfigResponse.model_validate(item) for item in items]


@router.post("/document-types", response_model=DocumentTypeConfigResponse)
def create_document_type_endpoint(
    payload: DocumentTypeConfigCreate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    require_admin_like(current_user)
    item = RiordinoDocumentTypeConfig(**payload.model_dump())
    db.add(item)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Document type code already exists") from exc
    db.refresh(item)
    return item


@router.patch("/document-types/{config_id}", response_model=DocumentTypeConfigResponse)
def update_document_type_endpoint(
    config_id: UUID,
    payload: DocumentTypeConfigUpdate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    require_admin_like(current_user)
    item = db.get(RiordinoDocumentTypeConfig, config_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document type config not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Document type code already exists") from exc
    db.refresh(item)
    return item


@router.delete("/document-types/{config_id}", response_model=DocumentTypeConfigResponse)
def delete_document_type_endpoint(
    config_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    require_admin_like(current_user)
    item = db.get(RiordinoDocumentTypeConfig, config_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document type config not found")
    response = DocumentTypeConfigResponse.model_validate(item)
    db.delete(item)
    db.commit()
    return response


@router.get("/issue-types", response_model=list[IssueTypeConfigResponse])
def list_issue_types_endpoint(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    items = list(
        db.scalars(
            select(RiordinoIssueTypeConfig)
            .order_by(RiordinoIssueTypeConfig.sort_order.asc(), RiordinoIssueTypeConfig.label.asc())
        )
    )
    return [IssueTypeConfigResponse.model_validate(item) for item in items]


@router.post("/issue-types", response_model=IssueTypeConfigResponse)
def create_issue_type_endpoint(
    payload: IssueTypeConfigCreate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    require_admin_like(current_user)
    item = RiordinoIssueTypeConfig(**payload.model_dump())
    db.add(item)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Issue type code already exists") from exc
    db.refresh(item)
    return item


@router.patch("/issue-types/{config_id}", response_model=IssueTypeConfigResponse)
def update_issue_type_endpoint(
    config_id: UUID,
    payload: IssueTypeConfigUpdate,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    require_admin_like(current_user)
    item = db.get(RiordinoIssueTypeConfig, config_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue type config not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Issue type code already exists") from exc
    db.refresh(item)
    return item


@router.delete("/issue-types/{config_id}", response_model=IssueTypeConfigResponse)
def delete_issue_type_endpoint(
    config_id: UUID,
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    require_admin_like(current_user)
    item = db.get(RiordinoIssueTypeConfig, config_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue type config not found")
    response = IssueTypeConfigResponse.model_validate(item)
    db.delete(item)
    db.commit()
    return response


@router.get("/municipalities", response_model=list[str])
def list_municipalities_endpoint(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    rows = list(
        db.execute(
            select(RiordinoPractice.municipality)
            .where(RiordinoPractice.deleted_at.is_(None))
            .distinct()
            .order_by(RiordinoPractice.municipality.asc())
        )
    )
    return [row[0] for row in rows]
