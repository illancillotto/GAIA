"""Operational notice workspace; every external action remains a persistent worker job."""

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.api.deps import require_module, require_section
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.ruolo.routes.poste_dispatch_routes import _command
from app.modules.ruolo.services import poste_dispatch_views, poste_preparation, solleciti_generation
from app.modules.ruolo.services.solleciti_workspace import workspace

router = APIRouter(
    prefix="/tributi/solleciti/workspace",
    tags=["ruolo-tributi"],
    dependencies=[Depends(require_module("ruolo")), Depends(require_section("ruolo.tributi.view"))],
)
MANAGE = "ruolo.tributi.manage_status"


class Generation(BaseModel):
    year: int = Field(ge=2021, le=date.today().year)
    tax_code: str = Field(pattern=r"^(?:[0-9]{11}|[A-Z0-9]{16})$")

    @field_validator("tax_code", mode="before")
    @classmethod
    def normalize(cls, value):
        return value.strip().upper() if isinstance(value, str) else value


class Preparation(BaseModel):
    item_ids: list[UUID] = Field(min_length=1, max_length=50)
    credential_id: int = Field(ge=1)


class AccountRefresh(BaseModel):
    credential_id: int = Field(ge=1)
    year: int | None = Field(default=None, ge=2021, le=date.today().year)


class WorkspaceQuery(BaseModel):
    q: str = Field(default="", max_length=120)
    year: int | None = None
    account: str = Field(default="all", pattern=r"^(all|none|legacy|conflict|[1-9][0-9]*)$")
    stage: Literal["all", "available", "sent", "draft", "review", "processing", "conflict"] = "all"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


@router.get("")
def get_workspace(filters: Annotated[WorkspaceQuery, Query()], db: Session = Depends(get_db)):
    return workspace(db, filters.model_dump())


@router.post("/generate")
def generate(
    body: Generation,
    db: Session = Depends(get_db),
    actor: ApplicationUser = Depends(require_section(MANAGE)),
):
    return _command(
        db,
        lambda: solleciti_generation.generate(
            db, year=body.year, tax_code=body.tax_code, actor_id=actor.id
        ),
    )


@router.post("/prepare")
def prepare(
    body: Preparation,
    db: Session = Depends(get_db),
    actor: ApplicationUser = Depends(require_section(MANAGE)),
):
    lot = _command(
        db,
        lambda: poste_preparation.prepare(
            db, item_ids=body.item_ids, credential_id=body.credential_id, actor_id=actor.id
        ),
    )
    return poste_dispatch_views.lot_detail(db, lot.id)


@router.post("/reconcile")
def reconcile(
    body: AccountRefresh,
    db: Session = Depends(get_db),
    actor: ApplicationUser = Depends(require_section(MANAGE)),
):
    return _command(
        db,
        lambda: poste_preparation.reconcile_account(
            db, credential_id=body.credential_id, year=body.year, actor_id=actor.id
        ),
    )
