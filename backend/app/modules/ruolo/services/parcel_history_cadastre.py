"""Documentary cadastral evidence, scoped to existing links and document permissions."""

from sqlalchemy import or_, select

from app.models.catasto import (
    CatastoDocument,
    CatastoSisterExtraction,
    CatastoSisterHistoryEvent,
    CatastoSisterOwner,
    CatastoSisterParcel,
)


def source_documents(db, rows, user_id):
    parcel_ids = {parcel.cat_particella_id for parcel, _, _ in rows if parcel.cat_particella_id}
    document_ids = {
        parcel.ade_scan_document_id for parcel, _, _ in rows if parcel.ade_scan_document_id
    }
    linked = (
        select(CatastoSisterExtraction.document_id)
        .join(CatastoSisterParcel, CatastoSisterParcel.extraction_id == CatastoSisterExtraction.id)
        .where(CatastoSisterParcel.cat_particella_id.in_(parcel_ids))
    )
    return db.execute(
        select(CatastoDocument, CatastoSisterExtraction)
        .outerjoin(
            CatastoSisterExtraction, CatastoSisterExtraction.document_id == CatastoDocument.id
        )
        .where(
            CatastoDocument.user_id == user_id,
            or_(CatastoDocument.id.in_(document_ids), CatastoDocument.id.in_(linked)),
        )
        .order_by(CatastoDocument.created_at, CatastoDocument.id)
    ).all()


def owner_view(owner):
    return {
        "name": owner.denominazione,
        "tax_code": owner.codice_fiscale,
        "right": owner.diritto,
        "share": owner.quota,
    }


def extraction_evidence(db, extraction, document_id):
    parcels = db.scalars(
        select(CatastoSisterParcel).where(CatastoSisterParcel.extraction_id == extraction.id)
    ).all()
    # The current parser assigns history to an extraction, not to individual parcels.
    # Never attribute a multi-property history to one parcel automatically.
    if len(parcels) != 1:
        return {"owners": [], "events": [], "ambiguous": True}
    owners = db.scalars(
        select(CatastoSisterOwner)
        .where(CatastoSisterOwner.sister_parcel_id == parcels[0].id)
        .order_by(CatastoSisterOwner.id)
    ).all()
    events = db.scalars(
        select(CatastoSisterHistoryEvent)
        .where(CatastoSisterHistoryEvent.extraction_id == extraction.id)
        .order_by(CatastoSisterHistoryEvent.from_date, CatastoSisterHistoryEvent.id)
    ).all()
    return {
        "owners": [owner_view(owner) for owner in owners],
        "events": [
            {
                **owner_view(event),
                "id": str(event.id),
                "from_date": event.from_date,
                "act_date": event.act_date,
                "act": event.act_description,
                "document_id": str(document_id),
            }
            for event in events
        ],
        "ambiguous": False,
    }


def cadastral_history(db, rows, user_id):
    documents = []
    events = []
    for document, extraction in source_documents(db, rows, user_id):
        evidence = {"owners": [], "events": [], "ambiguous": False}
        if extraction is not None and extraction.status == "completed":
            evidence = extraction_evidence(db, extraction, document.id)
        events.extend(evidence["events"])
        documents.append(
            {
                "id": str(document.id),
                "filename": document.filename,
                "observed_at": extraction.observed_at if extraction else None,
                "recorded_at": document.created_at,
                "type": document.tipo_visura,
                "extraction_status": extraction.status if extraction else "not_available",
                "owners": evidence["owners"],
                "ambiguous": evidence["ambiguous"],
                "suppressed": document.parcel_classification == "suppressed"
                and not evidence["ambiguous"],
                "suppressed_at": document.parcel_suppressed_at,
            }
        )
    return {
        "documents": documents,
        "events": sorted(
            events, key=lambda event: (str(event["from_date"] or "9999"), event["id"])
        ),
        "completeness": "not_certified",
        "cessation": "documented_suppression"
        if any(d["suppressed"] for d in documents)
        else "not_documented",
    }
