from copy import deepcopy
from uuid import UUID

from sqlalchemy import select

from app.modules.ruolo.parcel_control_models import (
    ParcelControlCase,
    ParcelControlIndex,
    ParcelControlProposal,
    ParcelControlState,
)
from app.modules.ruolo.services.parcel_control_identity import EXCLUDED_DISTRICTS, YEARS, digest
from app.modules.ruolo.services.parcel_control_index import collect_index


def matching_evidence(case, evidence_ids):
    evidence = [entry for entry in case.evidence if entry["id"] in evidence_ids]
    if not evidence or len(evidence) != len(set(evidence_ids)):
        raise ValueError("Evidenze mancanti")
    return evidence


def verified_match(case, data):
    matches = [match for match in case.matches if match["id"] == data.get("match_id")]
    if not matches or matches[0]["status"] != "confirmed":
        raise ValueError("Confermare l'identità prima della proposta")
    return matches[0]


def proposal_parcel(db, case, data, evidence):
    parcel_id = UUID(data.get("parcel_id", str(case.parcel_id)))
    item = db.get(ParcelControlIndex, parcel_id)
    associated = [parcel for parcel in case.parcels if parcel["id"] == str(parcel_id)]
    if item is None or not any((parcel_id == case.parcel_id, associated)):
        raise ValueError("Particella non appartenente alla pratica")
    if data["kind"] == "insertion" and any(
        row["year"] == data["year"] for row in item.original["occurrences"]
    ):
        raise ValueError("Particella già a ruolo: valutare una rettifica")
    role_checks = [
        entry
        for entry in evidence
        if (entry["kind"], entry.get("parcel_id"), entry.get("result"))
        == ("role_check", str(parcel_id), "absent")
    ]
    if item.original["reference"].get("namespace") == "sister" and not any(
        data["year"] in entry.get("years", []) for entry in role_checks
    ):
        raise ValueError("Particella recuperata: confronto con lo storico ruolo da verificare")
    verify_historical_presence(item, evidence)
    return item


def verify_historical_presence(item, evidence):
    if any(row["year"] in YEARS for row in item.original["occurrences"]):
        return
    checks = [
        entry
        for entry in evidence
        if (entry["kind"], entry.get("parcel_id"), entry.get("result"))
        == ("role_check", str(item.id), "present")
    ]
    if not any(year in YEARS for entry in checks for year in entry.get("years", [])):
        raise ValueError("Documentare una presenza a ruolo nel 2011-2025 prima della proposta")


def create_proposal(db, case, data):
    year = data.get("year")
    if year not in YEARS:
        raise ValueError("Annualità non supportata")
    if data.get("kind") == "insertion" and year != 2025:
        raise ValueError("Per annualità pregresse usare una valutazione storica separata")
    match = verified_match(case, data)
    if not data.get("component") or data.get("kind") not in {
        "insertion",
        "rectification",
        "historical_review",
    }:
        raise ValueError("Specificare componente tributaria e tipo proposta")
    evidence = matching_evidence(case, data.get("evidence_ids", []))
    item = proposal_parcel(db, case, data, evidence)
    key = digest(
        [
            item.identity_key,
            year,
            match["tax_code"],
            match["right"],
            match["share"],
            data["component"],
            data["kind"],
        ]
    )
    existing = db.scalar(
        select(ParcelControlProposal).where(ParcelControlProposal.identity_key == key)
    )
    state = db.get(ParcelControlState, 1)
    proposal = ParcelControlProposal(
        identity_key=key,
        case_id=case.id,
        status="review_required",
        payload={
            **deepcopy(data),
            "parcel_id": str(item.id),
            "label": item.label,
            "verified_tax_code": match["tax_code"],
            "match": deepcopy(match),
            "evidence": deepcopy(evidence),
            "original": deepcopy(item.original),
            "source_signatures": deepcopy(state.signatures if state else {}),
            "destination": "gaia_review_queue",
            "residual_doubts": data.get("residual_doubts", ""),
        },
    )
    if existing:
        if existing.case_id != case.id or existing.status == "confirmed":
            raise ValueError("Proposta già presente: consultare la pratica di origine")
        existing.payload = proposal.payload
        existing.status = "review_required"
        return existing
    db.add(proposal)
    db.flush()
    return proposal


def decide_proposal(db, case, data):
    proposal = db.get(ParcelControlProposal, UUID(data["proposal_id"]))
    if proposal is None or proposal.case_id != case.id:
        raise ValueError("Proposta non appartenente alla pratica")
    decision = data.get("status")
    if decision not in {"confirmed", "excluded", "investigating"}:
        raise ValueError("Esito proposta non valido")
    if decision == "confirmed":
        validate_confirmation(db, proposal)
    proposal.status = decision


def validate_confirmation(db, proposal):
    payload = proposal.payload
    state = db.get(ParcelControlState, 1)
    _, signatures = collect_index(db)
    if state is None or payload["source_signatures"] != signatures:
        raise ValueError("Dati cambiati: rivalutare la proposta")
    evidence = [
        entry for entry in payload["evidence"] if entry.get("parcel_id") == payload["parcel_id"]
    ]
    case = db.get(ParcelControlCase, proposal.case_id)
    current_ids = {
        entry["id"] for entry in case.evidence if entry.get("parcel_id") == payload["parcel_id"]
    }
    if current_ids != {entry["id"] for entry in evidence}:
        raise ValueError("Nuove evidenze: preparare nuovamente la proposta prima della conferma")
    verify_historical_presence(db.get(ParcelControlIndex, UUID(payload["parcel_id"])), evidence)
    verify_territory(evidence)
    if not any(
        entry["kind"] == "cadastre" and entry.get("result") == "existing" for entry in evidence
    ):
        raise ValueError("Esistenza catastale da verificare")
    if payload["year"] < state.current_year:
        verify_historical_title(evidence, payload["year"])
    if not payload.get("eligibility_rule"):
        raise ValueError("Specificare la regola tributaria applicata")


def verify_territory(evidence):
    territorial = [entry for entry in evidence if entry["kind"] == "territory"]
    if not territorial or territorial[-1].get("result") != "inside_outside_town":
        raise ValueError("Verifica territoriale necessaria")
    if str(territorial[-1].get("district_code", "")).strip().upper() in EXCLUDED_DISTRICTS:
        raise ValueError("Distretto FD escluso dalle proposte di recupero")


def verify_historical_title(evidence, year):
    titles = [entry for entry in evidence if entry["kind"] == "historical_title"]
    if not any(year in entry.get("years", []) for entry in titles):
        raise ValueError("Titolarità storica da verificare")
