from __future__ import annotations

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.catasto import CatastoCaptchaLog
from app.models.elaborazioni import ElaborazioneRichiesta, ElaborazioneRichiestaStatus


class ElaborazioneCaptchaRequestNotFoundError(Exception):
    pass


class ElaborazioneCaptchaConflictError(Exception):
    pass


def get_captcha_request_for_user(db: Session, user_id: int, request_id) -> ElaborazioneRichiesta:
    request = db.scalar(
        select(ElaborazioneRichiesta).where(
            ElaborazioneRichiesta.id == request_id,
            ElaborazioneRichiesta.user_id == user_id,
        ),
    )
    if request is None:
        raise ElaborazioneCaptchaRequestNotFoundError(f"Captcha request {request_id} not found")
    return request


def list_pending_captcha_requests(db: Session, user_id: int) -> list[ElaborazioneRichiesta]:
    statement = (
        select(ElaborazioneRichiesta)
        .where(
            ElaborazioneRichiesta.user_id == user_id,
            ElaborazioneRichiesta.status == ElaborazioneRichiestaStatus.AWAITING_CAPTCHA.value,
        )
        .order_by(ElaborazioneRichiesta.captcha_requested_at.asc(), ElaborazioneRichiesta.created_at.asc())
    )
    return list(db.scalars(statement).all())


def get_manual_captcha_summary_for_user(db: Session, user_id: int) -> dict[str, int]:
    statement = select(
        func.count(CatastoCaptchaLog.id).label("processed"),
        func.coalesce(func.sum(case((CatastoCaptchaLog.is_correct.is_(True), 1), else_=0)), 0).label("correct"),
        func.coalesce(func.sum(case((CatastoCaptchaLog.is_correct.is_(False), 1), else_=0)), 0).label("wrong"),
    ).join(
        ElaborazioneRichiesta,
        ElaborazioneRichiesta.id == CatastoCaptchaLog.request_id,
    ).where(
        ElaborazioneRichiesta.user_id == user_id,
        CatastoCaptchaLog.method == "manual",
    )
    row = db.execute(statement).one()
    return {
        "processed": int(row.processed or 0),
        "correct": int(row.correct or 0),
        "wrong": int(row.wrong or 0),
    }


def submit_manual_captcha_solution(db: Session, user_id: int, request_id, text: str) -> ElaborazioneRichiesta:
    request = get_captcha_request_for_user(db, user_id, request_id)
    if request.status != ElaborazioneRichiestaStatus.AWAITING_CAPTCHA.value:
        raise ElaborazioneCaptchaConflictError("Request is not waiting for manual CAPTCHA input")

    request.captcha_manual_solution = text.strip()
    request.captcha_skip_requested = False
    request.current_operation = "Manual CAPTCHA submitted"
    db.commit()
    db.refresh(request)
    return request


def skip_captcha_request(db: Session, user_id: int, request_id) -> ElaborazioneRichiesta:
    request = get_captcha_request_for_user(db, user_id, request_id)
    if request.status != ElaborazioneRichiestaStatus.AWAITING_CAPTCHA.value:
        raise ElaborazioneCaptchaConflictError("Request is not waiting for manual CAPTCHA input")

    request.captcha_skip_requested = True
    request.captcha_manual_solution = None
    request.current_operation = "Skip requested by user"
    db.commit()
    db.refresh(request)
    return request
