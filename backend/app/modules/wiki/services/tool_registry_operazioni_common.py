from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.wiki.schemas import WikiChatResponse
from app.modules.wiki.services.response_composer import build_live_data_response
from app.modules.wiki.services.tool_registry_common import contains_any, has_uuid, parse_uuid, score_terms


def contains_operazioni_specific_entity(question: str) -> bool:
    return contains_any(
        question,
        "assegnazione",
        "assegnazioni",
        "assignment",
        "manutenzione",
        "manutenzioni",
        "maintenance",
        "sessione",
        "sessioni",
        "usage session",
        "attivita",
        "attività",
        "activity",
        "approvazione",
        "approvazioni",
        "approval",
        "review",
        "autodoc",
        "sync",
        "fuel log",
        "rifornimento",
        "rifornimenti",
        "carburante",
        "transazione non risolta",
        "transazioni non risolte",
        "unresolved",
        "anomalia",
        "anomalie",
    )


def match_vehicle(question: str) -> int:
    if not has_uuid(question):
        return 0
    if contains_operazioni_specific_entity(question):
        return 0
    return 10 + score_terms(question, "mezzo", "veicolo", "vehicle", "operazioni")


def find_vehicle_by_id(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    from app.modules.operazioni.routes.vehicles import get_vehicle_endpoint
    from app.modules.operazioni.schemas.vehicles import VehicleResponse

    vehicle_id = parse_uuid(question)
    if vehicle_id is None:
        return build_live_data_response(
            answer="Per cercare un mezzo Operazioni devo ricevere un UUID valido.",
            tool_name="find_vehicle_by_id",
            evidence_label="Lookup mezzo non eseguito",
            source_key="operazioni.vehicles.lookup",
            excerpt="UUID mezzo non presente nella domanda.",
        )

    response = VehicleResponse.model_validate(
        get_vehicle_endpoint(vehicle_id=vehicle_id, current_user=current_user, db=db)
    )
    payload = response.model_dump(mode="json")
    answer = (
        "Lookup mezzo Operazioni: "
        f"{response.code} {response.name}, targa {response.plate_number or 'n/d'}, "
        f"stato {response.current_status}, tipo {response.vehicle_type}, "
        f"GPS {'sì' if response.has_gps_device else 'no'}, attivo {'sì' if response.is_active else 'no'}."
    )
    excerpt = (
        f"Mezzo {response.code}, nome {response.name}, targa {response.plate_number or 'n/d'}, "
        f"stato {response.current_status}."
    )
    return build_live_data_response(
        answer=answer,
        tool_name="find_vehicle_by_id",
        evidence_label="Dettaglio mezzo Operazioni",
        source_key=f"operazioni.vehicles.{response.id}",
        excerpt=excerpt,
        payload=payload,
    )
