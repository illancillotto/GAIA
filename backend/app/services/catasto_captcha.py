from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catasto import CatastoVisuraRequest, CatastoVisuraRequestStatus


class CatastoCaptchaRequestNotFoundError(Exception):
    pass


class CatastoCaptchaConflictError(Exception):
    pass


def get_captcha_request_for_user(db: Session, user_id: int, request_id) -> CatastoVisuraRequest:
    request = db.scalar(
        select(CatastoVisuraRequest).where(
            CatastoVisuraRequest.id == request_id,
            CatastoVisuraRequest.user_id == user_id,
        ),
    )
    if request is None:
        raise CatastoCaptchaRequestNotFoundError(f"Captcha request {request_id} not found")
    return request


def list_pending_captcha_requests(db: Session, user_id: int) -> list[CatastoVisuraRequest]:
    statement = (
        select(CatastoVisuraRequest)
        .where(
            CatastoVisuraRequest.user_id == user_id,
            CatastoVisuraRequest.status == CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value,
        )
        .order_by(CatastoVisuraRequest.captcha_requested_at.asc(), CatastoVisuraRequest.created_at.asc())
    )
    return list(db.scalars(statement).all())


def submit_manual_captcha_solution(db: Session, user_id: int, request_id, text: str) -> CatastoVisuraRequest:
    request = get_captcha_request_for_user(db, user_id, request_id)
    if request.status != CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value:
        raise CatastoCaptchaConflictError("Request is not waiting for manual CAPTCHA input")

    request.captcha_manual_solution = text.strip()
    request.captcha_skip_requested = False
    request.current_operation = "Manual CAPTCHA submitted"
    db.commit()
    db.refresh(request)
    return request


def skip_captcha_request(db: Session, user_id: int, request_id) -> CatastoVisuraRequest:
    request = get_captcha_request_for_user(db, user_id, request_id)
    if request.status != CatastoVisuraRequestStatus.AWAITING_CAPTCHA.value:
        raise CatastoCaptchaConflictError("Request is not waiting for manual CAPTCHA input")

    request.captcha_skip_requested = True
    request.captcha_manual_solution = None
    request.current_operation = "Skip requested by user"
    db.commit()
    db.refresh(request)
    return request
