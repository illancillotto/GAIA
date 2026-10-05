"""Manual shift assignment from GAIA's daily record view."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.core.datetime_compat import UTC
from app.models.application_user import ApplicationUser
from app.modules.presenze.router.common import RequirePresenzeModule
from app.modules.presenze.router.helpers.access import (
    _can_edit_daily_record,
    _can_view_all_inaz_data,
)
from app.modules.presenze.router.helpers.daily_records import (
    _get_daily_record_or_404,
    _serialize_daily_record,
)
from app.modules.presenze.schemas import PresenzeDailyRecordResponse
from app.modules.presenze.services.dashboard_snapshot_store import (
    invalidate_all_dashboard_snapshots,
)
from app.modules.presenze.services.shift_assignments import (
    ShiftAssignmentConflict,
    ShiftAssignmentOrigin,
    record_shift_assignment,
)
from app.modules.presenze.shift_worker_schemas import ShiftWorkerAssignmentRequest

router = APIRouter(prefix="/presenze")


@router.post("/giornaliere/{record_id}/turnista", response_model=PresenzeDailyRecordResponse)
def assign_shift_worker(
    record_id: uuid.UUID,
    payload: ShiftWorkerAssignmentRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
    _: Annotated[ApplicationUser, RequirePresenzeModule],
):
    record = _get_daily_record_or_404(db, record_id, current_user)
    if not _can_view_all_inaz_data(current_user) or not _can_edit_daily_record(
        current_user, record
    ):
        raise HTTPException(
            status_code=403, detail="Edit privileges required for this daily record"
        )
    try:
        record_shift_assignment(
            db,
            record,
            payload,
            origin=ShiftAssignmentOrigin(
                current_user.id, "gaia", datetime.now(UTC), str(uuid.uuid4())
            ),
        )
    except ShiftAssignmentConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    invalidate_all_dashboard_snapshots(db)
    db.commit()
    return _serialize_daily_record(db, record)
