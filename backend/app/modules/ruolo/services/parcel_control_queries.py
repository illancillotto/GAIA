from uuid import UUID

from sqlalchemy import String, func, or_, select

from app.models.catasto import CatastoDocument, CatastoSisterExtraction, CatastoVisuraRequest
from app.modules.ruolo.models import RuoloAvviso
from app.modules.ruolo.parcel_control_models import (
    ParcelControlAudit,
    ParcelControlCase,
    ParcelControlIndex,
    ParcelControlProposal,
    ParcelControlState,
)
from app.modules.ruolo.services.parcel_control_identity import YEARS, annual_presence
from app.modules.ruolo.services.parcel_control_index import source_stamp
from app.modules.ruolo.services.parcel_control_notices import notice_case_index


def index_view(item, state, case=None):
    present_years = sorted({row["year"] for row in item.original["occurrences"]})
    coverage = state.coverage if state else {}
    signatures = state.signatures if state else {}
    years = {
        str(year): annual_presence(
            year in present_years,
            all(
                (
                    not item.original["incomplete"],
                    str(year) in coverage,
                    coverage.get(str(year), {}).get("signature") == signatures.get(str(year)),
                )
            ),
        )
        for year in YEARS
    }
    return {
        "id": str(item.id),
        "label": item.label,
        "reference": item.original["reference"],
        "years": years,
        "first_year": min(present_years, default=None),
        "last_year": max(present_years, default=None),
        "current_presence": years["2025"],
        "cf_anomaly": item.cf_anomaly,
        "identity_incomplete": item.original["incomplete"],
        "territorial_status": "verification_required",
        "occurrences": item.original["occurrences"],
        "case_id": str(case.id) if case else None,
        "case_status": case.status if case else None,
    }


def list_index(db, filters):
    state = db.get(ParcelControlState, 1)
    stale = bool(state and state.signatures.get("_stamp") != source_stamp(db))
    query = select(ParcelControlIndex, ParcelControlCase).outerjoin(
        ParcelControlCase, ParcelControlCase.parcel_id == ParcelControlIndex.id
    )
    query = query.where(ParcelControlIndex.active.is_(True))
    if filters.search:
        escaped = filters.search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(ParcelControlIndex.label.ilike(f"%{escaped}%", escape="\\"))
    if filters.view == "missing":
        query = query.where(ParcelControlIndex.current_present.is_(False))
    if filters.view == "cf":
        query = query.where(ParcelControlIndex.cf_anomaly.is_(True))
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.execute(
        query.order_by(ParcelControlIndex.label, ParcelControlIndex.id)
        .offset((filters.page - 1) * filters.page_size)
        .limit(filters.page_size)
    )
    return {
        "items": [index_view(item, None if stale else state, case) for item, case in rows],
        "total": total,
        "current_year": 2025,
        "coverage": state.coverage if state else {},
        "refreshed_at": state.refreshed_at if state else None,
        "sources_changed": stale,
    }


def visura_view(db, request_id):
    request = db.get(CatastoVisuraRequest, request_id)
    if request is None:
        raise ValueError("Visura non trovata")
    document = db.scalar(select(CatastoDocument).where(CatastoDocument.request_id == request.id))
    extraction = (
        db.scalar(
            select(CatastoSisterExtraction).where(
                CatastoSisterExtraction.document_id == document.id
            )
        )
        if document
        else None
    )
    return {
        "id": str(request.id),
        "status": request.status,
        "search_mode": request.search_mode,
        "error": request.error_message,
        "subject_id": request.subject_id,
        "document_id": str(document.id) if document else None,
        "extraction_status": extraction.status if extraction else None,
        "extraction": extraction.payload_json if extraction else None,
        "batch_id": str(request.batch_id),
    }


def case_index(db, case):
    return db.get(ParcelControlIndex, case.parcel_id) if case.parcel_id else notice_case_index(case)


def current_state(db):
    state = db.get(ParcelControlState, 1)
    if state and state.signatures.get("_stamp") != source_stamp(db):
        return None
    return state


def list_cases(db, filters):
    query = select(ParcelControlCase).outerjoin(
        ParcelControlIndex, ParcelControlIndex.id == ParcelControlCase.parcel_id
    )
    query = query.outerjoin(RuoloAvviso, RuoloAvviso.id == ParcelControlCase.notice_id)
    if filters.view in {"cases", "closed"}:
        query = query.where(
            ParcelControlCase.status.in_(
                ["closed", "excluded"] if filters.view == "closed" else ["open", "investigating"]
            )
        )
    if filters.view == "visure":
        query = query.where(ParcelControlCase.evidence.cast(String).contains('"request_id"'))
    if filters.view == "recovered":
        query = query.where(ParcelControlCase.parcels.cast(String).contains('"evidence_id"'))
    if filters.search:
        escaped = filters.search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(
            or_(
                ParcelControlIndex.label.ilike(f"%{escaped}%", escape="\\"),
                RuoloAvviso.codice_cnc.ilike(f"%{escaped}%", escape="\\"),
            )
        )
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(
        query.order_by(ParcelControlCase.created_at, ParcelControlCase.id)
        .offset((filters.page - 1) * filters.page_size)
        .limit(filters.page_size)
    ).all()
    state = db.get(ParcelControlState, 1)
    verified_state = current_state(db)
    values = [index_view(case_index(db, case), verified_state, case) for case in rows]
    return {
        "items": values,
        "total": total,
        "current_year": 2025,
        "coverage": state.coverage if state else {},
        "refreshed_at": state.refreshed_at if state else None,
    }


def case_view(db, case):
    item = case_index(db, case)
    audit = db.scalars(
        select(ParcelControlAudit)
        .where(ParcelControlAudit.case_id == case.id)
        .order_by(ParcelControlAudit.created_at, ParcelControlAudit.id)
    ).all()
    proposals = db.scalars(
        select(ParcelControlProposal).where(ParcelControlProposal.case_id == case.id)
    ).all()
    linked = [evidence for evidence in case.evidence if evidence["kind"] == "visura"]
    return {
        "id": str(case.id),
        "parcel_id": str(case.parcel_id) if case.parcel_id else None,
        "status": case.status,
        "version": case.version,
        "responsible_id": case.responsible_id,
        "original": case.original,
        "evidence": case.evidence,
        "matches": case.matches,
        "parcels": case.parcels,
        "current": index_view(item, current_state(db), case),
        "visure": [visura_view(db, UUID(evidence["request_id"])) for evidence in linked],
        "proposals": [
            {"id": str(proposal.id), "status": proposal.status, **proposal.payload}
            for proposal in proposals
        ],
        "audit": [
            {
                "action": event.action,
                "reason": event.reason,
                "actor_id": event.actor_id,
                "created_at": event.created_at,
                "payload": event.payload,
            }
            for event in audit
        ],
    }


def proposal_queue(db, filters):
    query = select(ParcelControlProposal).order_by(ParcelControlProposal.id)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(query.offset((filters.page - 1) * filters.page_size).limit(filters.page_size))
    return {
        "items": [
            {"id": str(row.id), "case_id": str(row.case_id), "status": row.status, **row.payload}
            for row in rows
        ],
        "total": total,
    }
