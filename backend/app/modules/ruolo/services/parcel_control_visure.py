from copy import deepcopy
from uuid import UUID, uuid4

from sqlalchemy import select

from app.models.catasto import (
    CatastoBatch,
    CatastoDocument,
    CatastoSisterExtraction,
    CatastoVisuraRequest,
)
from app.modules.ruolo.parcel_control_models import ParcelControlIndex
from app.modules.ruolo.services.parcel_control_identity import digest, token
from app.services.elaborazioni_batches import validate_visure_records


def queue_visura(db, case, data, actor_id):
    if not data.get("scope"):
        raise ValueError("Specificare l'ambito effettivo della ricerca")
    payload = deepcopy(data.get("request", {}))
    if payload.get("search_mode") == "soggetto":
        matches = [
            match
            for match in case.matches
            if match["id"] == data.get("match_id") and match["status"] == "confirmed"
        ]
        if not matches:
            raise ValueError("La visura per soggetto richiede un'identità confermata")
        payload.update(subject_id=matches[0]["tax_code"], subject_kind=matches[0]["subject_kind"])
    rows = validate_visure_records(db, [payload])
    row = rows[0]
    if row.status == "skipped":
        raise ValueError("Identificativo non utilizzabile per SISTER")
    key = digest([payload, data["scope"]])
    previous = [entry for entry in case.evidence if entry.get("request_key") == key]
    if previous:
        return
    batch = CatastoBatch(
        user_id=actor_id,
        name=f"Controllo particelle {case.id}",
        batch_kind="manual_single",
        total_items=1,
        status="pending",
    )
    db.add(batch)
    db.flush()
    fields = (
        "search_mode",
        "comune",
        "comune_codice",
        "catasto",
        "sezione",
        "foglio",
        "particella",
        "subalterno",
        "tipo_visura",
        "subject_kind",
        "subject_id",
        "request_type",
        "intestazione",
    )
    request = CatastoVisuraRequest(
        batch_id=batch.id,
        user_id=actor_id,
        row_index=1,
        **{field: getattr(row, field) for field in fields},
    )
    db.add(request)
    db.flush()
    case.evidence = [
        *case.evidence,
        {
            "id": str(uuid4()),
            "kind": "visura",
            "actor_id": actor_id,
            "request_id": str(request.id),
            "request_key": key,
            "scope": data["scope"],
            "batch_id": str(batch.id),
        },
    ]


def recover_parcel(db, case, data):
    evidence, _request, document, extraction = subject_extraction(db, case, data)
    payload = extraction.payload_json
    parcel = payload.get("parcel") or {}
    if not all(parcel.get(field) for field in ("foglio", "particella")) or not payload.get(
        "comune_codice"
    ):
        raise ValueError("Identificativo estratto incompleto: approfondimento manuale necessario")
    reference = {
        "namespace": "sister",
        "comune_codice": token(payload["comune_codice"]),
        "comune_nome": payload.get("comune_nome", ""),
        "catasto": document.catasto,
        "sezione": payload.get("sezione"),
        "foglio": token(parcel["foglio"]),
        "particella": token(parcel["particella"]),
        "subalterno": token(parcel.get("subalterno")),
    }
    item = recovered_index(db, reference)
    if not any(entry["id"] == str(item.id) for entry in case.parcels):
        case.parcels = [
            *case.parcels,
            {
                "id": str(item.id),
                "reference": reference,
                "evidence_id": evidence["id"],
                "territorial_status": "verification_required",
                "status": "investigating",
                "owners": payload.get("owners", []),
                "role_match_status": "verification_required",
                "extraction_scope": "single_parsed_reference",
            },
        ]


def subject_extraction(db, case, data):
    evidence = [
        entry
        for entry in case.evidence
        if entry["id"] == data.get("evidence_id") and entry["kind"] == "visura"
    ]
    if not evidence:
        raise ValueError("Selezionare una visura collegata alla pratica")
    request = db.get(CatastoVisuraRequest, UUID(evidence[0]["request_id"]))
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
    if request.search_mode != "soggetto" or request.status != "completed" or extraction is None:
        raise ValueError("Occorre una visura per soggetto completata con estrazione disponibile")
    return evidence[0], request, document, extraction


def recovered_index(db, reference):
    key = digest(reference)
    item = db.scalar(select(ParcelControlIndex).where(ParcelControlIndex.identity_key == key))
    if item is None:
        item = ParcelControlIndex(
            identity_key=key,
            label=f"{reference['comune_nome']} · Fg.{reference['foglio']} Part.{reference['particella']}",
            active=False,
            original={"reference": reference, "incomplete": False, "occurrences": []},
        )
        db.add(item)
        db.flush()
    return item
