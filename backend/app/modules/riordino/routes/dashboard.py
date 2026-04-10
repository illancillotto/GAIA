"""Dashboard routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_module, require_section
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.riordino.schemas import DashboardResponse
from app.modules.riordino.services import get_summary

router = APIRouter(dependencies=[Depends(require_module("riordino")), Depends(require_section("riordino.dashboard"))])


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard_endpoint(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    db: Annotated[Session, Depends(get_db)],
):
    return DashboardResponse.model_validate(get_summary(db))
