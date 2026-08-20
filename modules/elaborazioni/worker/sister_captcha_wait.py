from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catasto import (
    CatastoBatch,
    CatastoBatchStatus,
    CatastoVisuraRequest,
    CatastoVisuraRequestStatus,
)


SessionFactory = Callable[[], Session]


@dataclass(frozen=True, slots=True)
class SisterCaptchaClaim:
    batch_id: UUID
    request_id: UUID
    execution_token: UUID


@dataclass(frozen=True, slots=True)
class SisterCaptchaWaitState:
    active: bool
    solution: str | None = None
    skip_requested: bool = False


@dataclass(slots=True)
class SisterCaptchaWaitRepository:
    session_factory: SessionFactory

    def begin(
        self,
        batch_id: UUID,
        request_id: UUID,
        execution_token: UUID,
        image_path: Path,
        deadline: datetime,
    ) -> bool:
        with self.session_factory() as db:
            batch = db.scalar(select(CatastoBatch).where(CatastoBatch.id == batch_id).with_for_update())
            request = db.scalar(
                select(CatastoVisuraRequest).where(CatastoVisuraRequest.id == request_id).with_for_update()
            )
            if not _is_active_claim(batch, request, execution_token):
                return False
            assert batch is not None and request is not None
            request.status = CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value
            request.current_operation = "In attesa di CAPTCHA manuale"
            request.captcha_image_path = str(image_path)
            request.captcha_requested_at = datetime.now(timezone.utc)
            request.captcha_expires_at = deadline
            request.captcha_manual_solution = None
            request.captcha_skip_requested = False
            batch.current_operation = f"CAPTCHA richiesto per riga {request.row_index}"
            db.commit()
            return True

    def state(
        self,
        batch_id: UUID,
        request_id: UUID,
        execution_token: UUID,
    ) -> SisterCaptchaWaitState:
        with self.session_factory() as db:
            batch = db.get(CatastoBatch, batch_id)
            request = db.get(CatastoVisuraRequest, request_id)
            if not _is_active_claim(batch, request, execution_token):
                return SisterCaptchaWaitState(active=False)
            assert request is not None
            return SisterCaptchaWaitState(
                active=request.status == CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value,
                solution=request.captcha_manual_solution,
                skip_requested=request.captcha_skip_requested,
            )


def _is_active_claim(
    batch: CatastoBatch | None,
    request: CatastoVisuraRequest | None,
    execution_token: UUID,
) -> bool:
    return bool(
        batch is not None
        and request is not None
        and batch.status == CatastoBatchStatus.PROCESSING.value
        and request.status
        in {
            CatastoVisuraRequestStatus.PROCESSING.value,
            CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value,
        }
        and request.execution_token == execution_token
    )
