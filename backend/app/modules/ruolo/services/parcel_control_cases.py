from copy import deepcopy
from uuid import UUID, uuid4

from sqlalchemy import select

from app.models.catasto import CatastoVisuraRequest
from app.modules.ruolo.parcel_control_models import (
    ParcelControlAudit,
    ParcelControlCase,
    ParcelControlIndex,
)
from app.modules.ruolo.services.parcel_control_identity import digest, tax_code_check


def require_case(db, case_id):
    case = db.scalar(
        select(ParcelControlCase)
        .where(ParcelControlCase.id == case_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if case is None:
        raise LookupError("Pratica non trovata")
    return case


def replay(db, case_id, actor_id, action, command):
    event = db.scalar(
        select(ParcelControlAudit).where(ParcelControlAudit.command_id == command.command_id)
    )
    if event is None:
        return False
    expected = digest(command.model_dump(mode="json"))
    if (event.actor_id, event.action, event.case_id, event.payload["digest"]) != (
        actor_id,
        action,
        case_id,
        expected,
    ):
        raise ValueError("Chiave di idempotenza già usata con un altro comando")
    return True


def audit_command(db, case_id, actor_id, action, command):
    db.add(
        ParcelControlAudit(
            command_id=command.command_id,
            case_id=case_id,
            actor_id=actor_id,
            action=action,
            reason=command.reason,
            payload={"digest": digest(command.model_dump(mode="json")), "data": command.data},
        )
    )


def open_case(db, parcel_id, actor_id, command):
    item = db.get(ParcelControlIndex, parcel_id)
    if item is None:
        raise LookupError("Particella non trovata: aggiornare l'analisi")
    case = db.scalar(select(ParcelControlCase).where(ParcelControlCase.parcel_id == parcel_id))
    if case is None:
        case = ParcelControlCase(
            parcel_id=parcel_id,
            responsible_id=actor_id,
            original=deepcopy(item.original),
            evidence=[],
            matches=[],
            parcels=[],
        )
        db.add(case)
        db.flush()
    if not replay(db, case.id, actor_id, "open", command):
        audit_command(db, case.id, actor_id, "open", command)
    return case


def record_evidence(db, case, data, actor_id):
    kind = data.get("kind")
    if kind not in {"document", "territory", "cadastre", "historical_title", "role_check"}:
        raise ValueError("Tipo evidenza non valido")
    if not all(
        str(data.get(field, "")).strip() for field in ("source", "reference", "observed_at")
    ):
        raise ValueError("Fonte, riferimento documentale e data sono obbligatori")
    if kind == "territory" and not all(data.get(field) for field in ("version", "scope", "result")):
        raise ValueError("Evidenza territoriale: versione, ambito ed esito obbligatori")
    parcel_id = data.get("parcel_id") or (str(case.parcel_id) if case.parcel_id else None)
    if parcel_id not in {
        str(case.parcel_id) if case.parcel_id else None,
        *(entry["id"] for entry in case.parcels),
    }:
        raise ValueError("Particella non appartenente alla pratica")
    evidence = {**deepcopy(data), "id": str(uuid4()), "actor_id": actor_id, "parcel_id": parcel_id}
    case.evidence = [*case.evidence, evidence]


def record_match(case, data, actor_id):
    check = tax_code_check(data.get("tax_code"))
    if check["anomaly"]:
        raise ValueError("Codice fiscale formalmente non valido")
    evidence_ids = data.get("evidence_ids", [])
    available = {entry["id"] for entry in case.evidence}
    if not evidence_ids or not set(evidence_ids).issubset(available):
        raise ValueError("Il matching richiede evidenze presenti nella pratica")
    if data.get("status") not in {"proposed", "confirmed"}:
        raise ValueError("Stato matching non valido")
    if not all(data.get(field) for field in ("subject_kind", "name", "right", "share", "period")):
        raise ValueError("Specificare tipo soggetto, intestatario, diritto, quota e periodo")
    if data["subject_kind"] not in {"PF", "PNF"}:
        raise ValueError("Tipo soggetto non valido")
    case.matches = [
        *case.matches,
        {
            **deepcopy(data),
            "id": str(uuid4()),
            "tax_code": check["normalized"],
            "actor_id": actor_id,
        },
    ]


def link_visura(db, case, data, actor_id):
    request = db.get(CatastoVisuraRequest, UUID(data["request_id"]))
    if request is None or request.user_id != actor_id:
        raise ValueError("Visura non disponibile per l'operatore")
    if not data.get("scope"):
        raise ValueError("Specificare l'ambito effettivo della ricerca")
    if any(entry.get("request_id") == str(request.id) for entry in case.evidence):
        return
    case.evidence = [
        *case.evidence,
        {
            "id": str(uuid4()),
            "kind": "visura",
            "request_id": str(request.id),
            "scope": data["scope"],
            "actor_id": actor_id,
        },
    ]


def update_case(db, case, action, data, actor_id):
    handlers = {
        "evidence": lambda: record_evidence(db, case, data, actor_id),
        "match": lambda: record_match(case, data, actor_id),
        "link_visura": lambda: link_visura(db, case, data, actor_id),
        "parcel_status": lambda: update_parcel_status(case, data),
    }
    if action in handlers:
        handlers[action]()
    elif action == "status":
        if data.get("status") not in {"open", "investigating", "closed", "excluded"}:
            raise ValueError("Stato pratica non valido")
        case.status = data["status"]
    else:
        raise ValueError("Azione non supportata")


def update_parcel_status(case, data):
    if data.get("status") not in {"investigating", "verified", "excluded"}:
        raise ValueError("Esito particella non valido")
    parcels = deepcopy(case.parcels)
    selected = [parcel for parcel in parcels if parcel["id"] == data.get("parcel_id")]
    if not selected:
        raise ValueError("Particella non appartenente alla pratica")
    selected[0]["status"] = data["status"]
    case.parcels = parcels
