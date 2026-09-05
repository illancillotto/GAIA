from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_active_user, require_module
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.utenze.anpr.models import AnprCheckLog
from app.modules.utenze.models import AnagraficaDocType, AnagraficaDocument, AnagraficaSubject
from app.modules.utenze.routes import bonifica, documents, imports, reporting, subjects
from app.modules.utenze.routes.subject_detail import _build_subject_detail as _build_subject_detail
from app.modules.utenze.routes.support import _utenze_stats_timezone, _visible_document_condition
from app.modules.utenze.schemas import AnagraficaStatsResponse
from app.services.nas_connector import get_nas_client as _get_nas_client

get_nas_client = _get_nas_client
get_anagrafica_import_service = imports.get_anagrafica_import_service

router = APIRouter(tags=["utenze"])
for subrouter in (imports.router, bonifica.router, subjects.router, documents.router):
    router.routes.extend(subrouter.routes)

RequireUtenzeModule = Depends(require_module("utenze"))


# Preserve the legacy stats callable while retaining its public import.
# fmt: off
@router.get("/stats", response_model=AnagraficaStatsResponse)
def get_stats(
    _: Annotated[ApplicationUser, Depends(require_active_user)],
    __: Annotated[ApplicationUser, RequireUtenzeModule],
    db: Annotated[Session, Depends(get_db)],
) -> AnagraficaStatsResponse:
    now_utc = datetime.now(timezone.utc)  # noqa: UP017 - Preserve legacy AST for baseline matching.
    local_tz = _utenze_stats_timezone()
    now_local = now_utc.astimezone(local_tz)
    month_start_utc = now_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)  # noqa: UP017 - Preserve legacy AST for baseline matching.
    year_start_utc = now_local.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)  # noqa: UP017 - Preserve legacy AST for baseline matching.
    visible_document_condition = _visible_document_condition()
    total_subjects = db.scalar(select(func.count()).select_from(AnagraficaSubject)) or 0
    total_persons = db.scalar(select(func.count()).select_from(AnagraficaSubject).where(AnagraficaSubject.subject_type == "person")) or 0
    total_companies = db.scalar(select(func.count()).select_from(AnagraficaSubject).where(AnagraficaSubject.subject_type == "company")) or 0
    total_unknown = db.scalar(select(func.count()).select_from(AnagraficaSubject).where(AnagraficaSubject.subject_type == "unknown")) or 0
    total_documents = db.scalar(select(func.count()).select_from(AnagraficaDocument).where(visible_document_condition)) or 0
    requires_review = db.scalar(select(func.count()).select_from(AnagraficaSubject).where(AnagraficaSubject.requires_review.is_(True))) or 0
    active_subjects = db.scalar(select(func.count()).select_from(AnagraficaSubject).where(AnagraficaSubject.status == "active")) or 0
    inactive_subjects = db.scalar(select(func.count()).select_from(AnagraficaSubject).where(AnagraficaSubject.status == "inactive")) or 0
    documents_unclassified = db.scalar(select(func.count()).select_from(AnagraficaDocument).where(AnagraficaDocument.doc_type == AnagraficaDocType.ALTRO.value, visible_document_condition)) or 0
    deceased_updates_last_24h = db.scalar(select(func.count(func.distinct(AnprCheckLog.subject_id))).where(AnprCheckLog.call_type == "C004", AnprCheckLog.esito == "deceased", AnprCheckLog.created_at >= now_utc - timedelta(hours=24))) or 0
    deceased_updates_current_month = db.scalar(select(func.count(func.distinct(AnprCheckLog.subject_id))).where(AnprCheckLog.call_type == "C004", AnprCheckLog.esito == "deceased", AnprCheckLog.created_at >= month_start_utc)) or 0
    deceased_updates_current_year = db.scalar(select(func.count(func.distinct(AnprCheckLog.subject_id))).where(AnprCheckLog.call_type == "C004", AnprCheckLog.esito == "deceased", AnprCheckLog.created_at >= year_start_utc)) or 0
    letter_rows = db.execute(select(AnagraficaSubject.nas_folder_letter, func.count()).group_by(AnagraficaSubject.nas_folder_letter).order_by(AnagraficaSubject.nas_folder_letter.asc())).all()
    by_letter = {letter or "?": total for letter, total in letter_rows}
    return AnagraficaStatsResponse(total_subjects=total_subjects, total_persons=total_persons, total_companies=total_companies, total_unknown=total_unknown, total_documents=total_documents, requires_review=requires_review, active_subjects=active_subjects, inactive_subjects=inactive_subjects, documents_unclassified=documents_unclassified, deceased_updates_last_24h=deceased_updates_last_24h, deceased_updates_current_month=deceased_updates_current_month, deceased_updates_current_year=deceased_updates_current_year, by_letter=by_letter)
# fmt: on

router.routes.extend(reporting.router.routes)
