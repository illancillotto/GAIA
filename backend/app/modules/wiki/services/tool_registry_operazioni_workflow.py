from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.wiki.schemas import WikiChatResponse
from app.modules.wiki.services.policy import WikiToolMeta
from app.modules.wiki.services.response_composer import build_live_data_response
from app.modules.wiki.services.system_logic import (
    explain_operazioni_activity_approval_decision,
    explain_operazioni_activity_status,
    explain_operazioni_assignment_status,
    explain_operazioni_case_status,
    explain_operazioni_fuel_log_status,
    explain_operazioni_maintenance_status,
    explain_operazioni_unresolved_transaction_reason,
    explain_operazioni_usage_session_status,
)
from app.modules.wiki.services.tool_registry_common import WikiToolDefinition, contains_any, has_uuid, parse_uuid, score_terms
from app.modules.wiki.services.tool_registry_operazioni_common import find_vehicle_by_id, match_vehicle


def _match_operazioni_case(question: str) -> int:
    if not has_uuid(question):
        return 0
    if not contains_any(question, "operazioni", "case", "pratica", "segnalazione"):
        return 0
    return 10 + score_terms(question, "operazioni", "case", "pratica", "segnalazione")


def _match_operazioni_case_logic(question: str) -> int:
    if not has_uuid(question):
        return 0
    if not contains_any(question, "operazioni", "case", "stato", "workflow"):
        return 0
    if not contains_any(question, "spiega", "perche", "perché", "significa", "stato"):
        return 0
    return 8 + score_terms(question, "operazioni", "case", "stato", "workflow")


def _match_operazioni_assignment(question: str) -> int:
    if not has_uuid(question):
        return 0
    if not contains_any(question, "assegnazione", "assegnazioni", "assignment"):
        return 0
    return 11 + score_terms(question, "assegnazione", "assegnazioni", "assignment", "mezzo", "veicolo", "operazioni")


def _match_operazioni_assignment_logic(question: str) -> int:
    if not has_uuid(question):
        return 0
    if not contains_any(question, "assegnazione", "assegnazioni", "assignment"):
        return 0
    if not contains_any(question, "spiega", "perche", "perché", "significa", "stato"):
        return 0
    return 9 + score_terms(question, "assegnazione", "assignment", "stato", "workflow", "mezzo", "veicolo")


def _match_operazioni_maintenance(question: str) -> int:
    if not has_uuid(question):
        return 0
    if not contains_any(question, "manutenzione", "manutenzioni", "maintenance", "tagliando", "intervento"):
        return 0
    return 11 + score_terms(question, "manutenzione", "manutenzioni", "maintenance", "tagliando", "intervento", "mezzo", "veicolo")


def _match_operazioni_maintenance_logic(question: str) -> int:
    if not has_uuid(question):
        return 0
    if not contains_any(question, "manutenzione", "manutenzioni", "maintenance", "tagliando", "intervento"):
        return 0
    if not contains_any(question, "spiega", "perche", "perché", "significa", "stato"):
        return 0
    return 9 + score_terms(question, "manutenzione", "maintenance", "tagliando", "intervento", "stato", "workflow")


def _match_operazioni_usage_session(question: str) -> int:
    if not has_uuid(question):
        return 0
    if not contains_any(question, "sessione", "sessioni", "uso", "utilizzo", "usage session", "guida", "trip"):
        return 0
    return 11 + score_terms(question, "sessione", "sessioni", "uso", "utilizzo", "usage session", "guida", "trip")


def _match_operazioni_usage_session_logic(question: str) -> int:
    if not has_uuid(question):
        return 0
    if not contains_any(question, "sessione", "sessioni", "uso", "utilizzo", "usage session", "guida", "trip"):
        return 0
    if not contains_any(question, "spiega", "perche", "perché", "significa", "stato", "validata", "aperta", "chiusa"):
        return 0
    return 9 + score_terms(question, "sessione", "usage session", "guida", "trip", "stato", "validata", "aperta", "chiusa")


def _match_operazioni_activity(question: str) -> int:
    if not has_uuid(question):
        return 0
    if not contains_any(question, "attivita", "attività", "activity", "task operativa"):
        return 0
    return 11 + score_terms(question, "attivita", "attività", "activity", "operazioni", "task")


def _match_operazioni_activity_logic(question: str) -> int:
    if not has_uuid(question):
        return 0
    if not contains_any(question, "attivita", "attività", "activity"):
        return 0
    if not contains_any(question, "spiega", "perche", "perché", "significa", "stato", "workflow"):
        return 0
    return 9 + score_terms(question, "attivita", "attività", "activity", "stato", "workflow")


def _match_operazioni_activity_approval(question: str) -> int:
    if not has_uuid(question):
        return 0
    if not contains_any(question, "approvazione", "approvazioni", "approval", "review"):
        return 0
    return 11 + score_terms(question, "approvazione", "approvazioni", "approval", "review", "attivita", "attività")


def _match_operazioni_activity_approval_logic(question: str) -> int:
    if not has_uuid(question):
        return 0
    if not contains_any(question, "approvazione", "approvazioni", "approval", "review"):
        return 0
    if not contains_any(question, "spiega", "perche", "perché", "significa", "decisione", "motivo"):
        return 0
    return 9 + score_terms(question, "approvazione", "approval", "review", "decisione", "motivo")


def _match_operazioni_fuel_log(question: str) -> int:
    if not has_uuid(question):
        return 0
    if not contains_any(question, "fuel log", "rifornimento", "rifornimenti", "carburante", "fuel"):
        return 0
    return 11 + score_terms(question, "fuel log", "rifornimento", "rifornimenti", "carburante", "fuel")


def _match_operazioni_fuel_log_logic(question: str) -> int:
    if not has_uuid(question):
        return 0
    if not contains_any(question, "fuel log", "rifornimento", "rifornimenti", "carburante", "fuel"):
        return 0
    if not contains_any(question, "spiega", "perche", "perché", "significa", "stato", "incompleto", "associato"):
        return 0
    return 9 + score_terms(question, "fuel log", "rifornimento", "carburante", "fuel", "stato", "incompleto", "associato")


def _match_operazioni_unresolved_transaction(question: str) -> int:
    if not has_uuid(question):
        return 0
    if not contains_any(question, "transazione non risolta", "transazioni non risolte", "unresolved", "mancato abbinamento"):
        return 0
    return 11 + score_terms(question, "transazione non risolta", "transazioni non risolte", "unresolved", "mancato abbinamento")


def _match_operazioni_unresolved_transaction_logic(question: str) -> int:
    if not has_uuid(question):
        return 0
    if not contains_any(question, "transazione non risolta", "transazioni non risolte", "unresolved", "mancato abbinamento"):
        return 0
    if not contains_any(question, "spiega", "perche", "perché", "significa", "motivo", "reason"):
        return 0
    return 9 + score_terms(question, "transazione non risolta", "unresolved", "motivo", "reason", "spiega")


def _operazioni_summary(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    from app.modules.operazioni.routes.dashboard import dashboard_summary

    payload = dashboard_summary(current_user=current_user, db=db)
    vehicles = payload["vehicles"]
    activities = payload["activities"]
    cases = payload["cases"]
    storage = payload["storage"]
    excerpt = (
        f"Mezzi totali {vehicles['total']}, disponibili {vehicles['available']}, "
        f"attivita in corso {activities['in_progress']}, pratiche aperte {cases['open']}."
    )
    answer = (
        "Dati live Operazioni: "
        f"{vehicles['total']} mezzi attivi, {vehicles['available']} disponibili, "
        f"{activities['today_total']} attivita oggi, {activities['in_progress']} in corso, "
        f"{cases['open']} pratiche aperte. Storage al {storage['percentage_used']:.1f}% "
        f"(livello {storage['alert_level']})."
    )
    return build_live_data_response(
        answer=answer,
        tool_name="get_operazioni_dashboard_summary",
        evidence_label="Dashboard Operazioni",
        source_key="operazioni.dashboard.summary",
        excerpt=excerpt,
        payload=payload,
    )


def _operazioni_pending_approvals(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    from app.modules.operazioni.routes.dashboard import pending_approvals

    items = pending_approvals(current_user=current_user, db=db)
    answer = (
        "Approvazioni attività Operazioni in coda: "
        f"{len(items)} elementi in review o inviati. "
        f"Ultimo elemento {items[0]['id'] if items else 'n/d'}, "
        f"stato {items[0]['status'] if items else 'n/d'}."
    )
    excerpt = f"Pending approvals {len(items)}, first_status {items[0]['status'] if items else 'n/d'}."
    return build_live_data_response(
        answer=answer,
        tool_name="get_operazioni_pending_approvals",
        evidence_label="Coda approvazioni Operazioni",
        source_key="operazioni.dashboard.pending-approvals",
        excerpt=excerpt,
        payload={"items": items, "count": len(items)},
    )


def _explain_operazioni_case_status(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    case_id = parse_uuid(question)
    if case_id is None:
        return build_live_data_response(
            answer="Per spiegare lo stato di un case Operazioni devo ricevere un UUID valido.",
            tool_name="explain_operazioni_case_status",
            evidence_label="Spiegazione case Operazioni non eseguita",
            source_key="operazioni.case.logic.lookup",
            excerpt="UUID case non presente nella domanda.",
        )
    return explain_operazioni_case_status(db, current_user, case_id)


def _explain_operazioni_assignment_status(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    assignment_id = parse_uuid(question)
    if assignment_id is None:
        return build_live_data_response(
            answer="Per spiegare lo stato di un'assegnazione mezzo Operazioni devo ricevere un UUID valido.",
            tool_name="explain_operazioni_assignment_status",
            evidence_label="Spiegazione assegnazione mezzo non eseguita",
            source_key="operazioni.assignment.logic.lookup",
            excerpt="UUID assegnazione non presente nella domanda.",
        )
    return explain_operazioni_assignment_status(db, current_user, assignment_id)


def _explain_operazioni_maintenance_status(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    maintenance_id = parse_uuid(question)
    if maintenance_id is None:
        return build_live_data_response(
            answer="Per spiegare lo stato di una manutenzione Operazioni devo ricevere un UUID valido.",
            tool_name="explain_operazioni_maintenance_status",
            evidence_label="Spiegazione manutenzione non eseguita",
            source_key="operazioni.maintenance.logic.lookup",
            excerpt="UUID manutenzione non presente nella domanda.",
        )
    return explain_operazioni_maintenance_status(db, current_user, maintenance_id)


def _explain_operazioni_usage_session_status(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    session_id = parse_uuid(question)
    if session_id is None:
        return build_live_data_response(
            answer="Per spiegare lo stato di una sessione d'uso Operazioni devo ricevere un UUID valido.",
            tool_name="explain_operazioni_usage_session_status",
            evidence_label="Spiegazione sessione d'uso non eseguita",
            source_key="operazioni.usage-session.logic.lookup",
            excerpt="UUID sessione non presente nella domanda.",
        )
    return explain_operazioni_usage_session_status(db, current_user, session_id)


def _explain_operazioni_activity_status(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    activity_id = parse_uuid(question)
    if activity_id is None:
        return build_live_data_response(
            answer="Per spiegare lo stato di un'attività Operazioni devo ricevere un UUID valido.",
            tool_name="explain_operazioni_activity_status",
            evidence_label="Spiegazione attività non eseguita",
            source_key="operazioni.activity.logic.lookup",
            excerpt="UUID attività non presente nella domanda.",
        )
    return explain_operazioni_activity_status(db, current_user, activity_id)


def _explain_operazioni_activity_approval_decision(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    approval_id = parse_uuid(question)
    if approval_id is None:
        return build_live_data_response(
            answer="Per spiegare un'approvazione attività Operazioni devo ricevere un UUID valido.",
            tool_name="explain_operazioni_activity_approval_decision",
            evidence_label="Spiegazione approvazione attività non eseguita",
            source_key="operazioni.activity-approval.logic.lookup",
            excerpt="UUID approvazione attività non presente nella domanda.",
        )
    return explain_operazioni_activity_approval_decision(db, current_user, approval_id)


def _explain_operazioni_fuel_log_status(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    fuel_log_id = parse_uuid(question)
    if fuel_log_id is None:
        return build_live_data_response(
            answer="Per spiegare lo stato di un fuel log Operazioni devo ricevere un UUID valido.",
            tool_name="explain_operazioni_fuel_log_status",
            evidence_label="Spiegazione fuel log non eseguita",
            source_key="operazioni.fuel-log.logic.lookup",
            excerpt="UUID fuel log non presente nella domanda.",
        )
    return explain_operazioni_fuel_log_status(db, current_user, fuel_log_id)


def _explain_operazioni_unresolved_transaction_reason(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    unresolved_id = parse_uuid(question)
    if unresolved_id is None:
        return build_live_data_response(
            answer="Per spiegare una transazione non risolta Operazioni devo ricevere un UUID valido.",
            tool_name="explain_operazioni_unresolved_transaction_reason",
            evidence_label="Spiegazione transazione non risolta non eseguita",
            source_key="operazioni.unresolved-transaction.logic.lookup",
            excerpt="UUID transazione non risolta non presente nella domanda.",
        )
    return explain_operazioni_unresolved_transaction_reason(db, current_user, unresolved_id)


def _find_operazioni_case_by_id(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    from app.modules.operazioni.routes.reports import get_case

    case_id = parse_uuid(question)
    if case_id is None:
        return build_live_data_response(
            answer="Per cercare un case Operazioni devo ricevere un UUID valido.",
            tool_name="find_operazioni_case_by_id",
            evidence_label="Lookup case Operazioni non eseguito",
            source_key="operazioni.cases.lookup",
            excerpt="UUID case non presente nella domanda.",
        )

    case = get_case(case_id=case_id, current_user=current_user, db=db)
    answer = (
        "Lookup case Operazioni: "
        f"{case['case_number']} {case['title']}, stato {case['status']}, "
        f"assegnato a utente {case['assigned_to_user_id'] or 'n/d'}, team {case['assigned_team_id'] or 'n/d'}, "
        f"eventi {len(case['events'])}."
    )
    excerpt = (
        f"Case {case['case_number']}, stato {case['status']}, "
        f"assigned_user {case['assigned_to_user_id']}, events {len(case['events'])}."
    )
    return build_live_data_response(
        answer=answer,
        tool_name="find_operazioni_case_by_id",
        evidence_label="Dettaglio case Operazioni",
        source_key=f"operazioni.cases.{case['id']}",
        excerpt=excerpt,
        payload=case,
    )


def _find_operazioni_assignment_by_id(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    from app.modules.operazioni.models.organizational import Team
    from app.modules.operazioni.models.vehicles import Vehicle, VehicleAssignment

    assignment_id = parse_uuid(question)
    if assignment_id is None:
        return build_live_data_response(
            answer="Per cercare un'assegnazione mezzo Operazioni devo ricevere un UUID valido.",
            tool_name="find_operazioni_assignment_by_id",
            evidence_label="Lookup assegnazione mezzo non eseguito",
            source_key="operazioni.assignments.lookup",
            excerpt="UUID assegnazione non presente nella domanda.",
        )

    assignment = db.get(VehicleAssignment, assignment_id)
    if assignment is None:
        return build_live_data_response(
            answer="Non ho trovato nessuna assegnazione mezzo Operazioni con questo identificativo.",
            tool_name="find_operazioni_assignment_by_id",
            evidence_label="Assegnazione mezzo non trovata",
            source_key=f"operazioni.assignments.{assignment_id}",
            excerpt=f"Assignment {assignment_id} non presente nel dominio Operazioni.",
        )

    vehicle = db.get(Vehicle, assignment.vehicle_id)
    operator = db.get(ApplicationUser, assignment.operator_user_id) if assignment.operator_user_id is not None else None
    team = db.get(Team, assignment.team_id) if assignment.team_id is not None else None
    payload = {
        "id": str(assignment.id),
        "vehicle_id": str(assignment.vehicle_id),
        "vehicle_code": vehicle.code if vehicle is not None else None,
        "vehicle_name": vehicle.name if vehicle is not None else None,
        "assignment_target_type": assignment.assignment_target_type,
        "operator_user_id": assignment.operator_user_id,
        "operator_username": operator.username if operator is not None else None,
        "team_id": str(assignment.team_id) if assignment.team_id is not None else None,
        "team_name": team.name if team is not None else None,
        "assigned_by_user_id": assignment.assigned_by_user_id,
        "start_at": assignment.start_at.isoformat(),
        "end_at": assignment.end_at.isoformat() if assignment.end_at is not None else None,
        "reason": assignment.reason,
        "notes": assignment.notes,
        "is_open": assignment.end_at is None,
    }
    target_label = operator.username if operator is not None else team.name if team is not None else "destinatario non risolto"
    answer = (
        "Lookup assegnazione mezzo Operazioni: "
        f"mezzo {vehicle.code if vehicle is not None else assignment.vehicle_id}, "
        f"target {'operatore' if assignment.assignment_target_type == 'operator' else 'team'} {target_label}, "
        f"stato {'aperta' if assignment.end_at is None else 'chiusa'}, "
        f"inizio {assignment.start_at.isoformat()}, fine {assignment.end_at.isoformat() if assignment.end_at is not None else 'n/d'}."
    )
    excerpt = (
        f"Assignment {assignment.id}, vehicle {vehicle.code if vehicle is not None else assignment.vehicle_id}, "
        f"target {assignment.assignment_target_type}, open {assignment.end_at is None}."
    )
    return build_live_data_response(
        answer=answer,
        tool_name="find_operazioni_assignment_by_id",
        evidence_label="Dettaglio assegnazione mezzo Operazioni",
        source_key=f"operazioni.assignments.{assignment.id}",
        excerpt=excerpt,
        payload=payload,
    )


def _find_operazioni_maintenance_by_id(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    from app.modules.operazioni.models.vehicles import Vehicle, VehicleMaintenance, VehicleMaintenanceType

    maintenance_id = parse_uuid(question)
    if maintenance_id is None:
        return build_live_data_response(
            answer="Per cercare una manutenzione Operazioni devo ricevere un UUID valido.",
            tool_name="find_operazioni_maintenance_by_id",
            evidence_label="Lookup manutenzione non eseguito",
            source_key="operazioni.maintenances.lookup",
            excerpt="UUID manutenzione non presente nella domanda.",
        )

    maintenance = db.get(VehicleMaintenance, maintenance_id)
    if maintenance is None:
        return build_live_data_response(
            answer="Non ho trovato nessuna manutenzione Operazioni con questo identificativo.",
            tool_name="find_operazioni_maintenance_by_id",
            evidence_label="Manutenzione non trovata",
            source_key=f"operazioni.maintenances.{maintenance_id}",
            excerpt=f"Maintenance {maintenance_id} non presente nel dominio Operazioni.",
        )

    vehicle = db.get(Vehicle, maintenance.vehicle_id)
    maintenance_type = db.get(VehicleMaintenanceType, maintenance.maintenance_type_id) if maintenance.maintenance_type_id is not None else None
    payload = {
        "id": str(maintenance.id),
        "vehicle_id": str(maintenance.vehicle_id),
        "vehicle_code": vehicle.code if vehicle is not None else None,
        "vehicle_name": vehicle.name if vehicle is not None else None,
        "maintenance_type_id": str(maintenance.maintenance_type_id) if maintenance.maintenance_type_id is not None else None,
        "maintenance_type_code": maintenance_type.code if maintenance_type is not None else None,
        "maintenance_type_name": maintenance_type.name if maintenance_type is not None else None,
        "title": maintenance.title,
        "description": maintenance.description,
        "status": maintenance.status,
        "opened_at": maintenance.opened_at.isoformat(),
        "scheduled_for": maintenance.scheduled_for.isoformat() if maintenance.scheduled_for is not None else None,
        "completed_at": maintenance.completed_at.isoformat() if maintenance.completed_at is not None else None,
        "odometer_km": float(maintenance.odometer_km) if maintenance.odometer_km is not None else None,
        "supplier_name": maintenance.supplier_name,
        "cost_amount": float(maintenance.cost_amount) if maintenance.cost_amount is not None else None,
        "notes": maintenance.notes,
    }
    answer = (
        "Lookup manutenzione Operazioni: "
        f"{maintenance.title}, mezzo {vehicle.code if vehicle is not None else maintenance.vehicle_id}, "
        f"stato {maintenance.status}, tipo {maintenance_type.name if maintenance_type is not None else 'n/d'}, "
        f"programmata {maintenance.scheduled_for.isoformat() if maintenance.scheduled_for is not None else 'n/d'}, "
        f"completata {maintenance.completed_at.isoformat() if maintenance.completed_at is not None else 'no'}."
    )
    excerpt = (
        f"Maintenance {maintenance.id}, vehicle {vehicle.code if vehicle is not None else maintenance.vehicle_id}, "
        f"status {maintenance.status}, type {maintenance_type.code if maintenance_type is not None else 'n/d'}."
    )
    return build_live_data_response(
        answer=answer,
        tool_name="find_operazioni_maintenance_by_id",
        evidence_label="Dettaglio manutenzione Operazioni",
        source_key=f"operazioni.maintenances.{maintenance.id}",
        excerpt=excerpt,
        payload=payload,
    )


def _find_operazioni_usage_session_by_id(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    from app.modules.operazioni.models.organizational import Team
    from app.modules.operazioni.models.vehicles import Vehicle, VehicleUsageSession

    session_id = parse_uuid(question)
    if session_id is None:
        return build_live_data_response(
            answer="Per cercare una sessione d'uso Operazioni devo ricevere un UUID valido.",
            tool_name="find_operazioni_usage_session_by_id",
            evidence_label="Lookup sessione d'uso non eseguito",
            source_key="operazioni.usage-sessions.lookup",
            excerpt="UUID sessione non presente nella domanda.",
        )

    session = db.get(VehicleUsageSession, session_id)
    if session is None:
        return build_live_data_response(
            answer="Non ho trovato nessuna sessione d'uso Operazioni con questo identificativo.",
            tool_name="find_operazioni_usage_session_by_id",
            evidence_label="Sessione d'uso non trovata",
            source_key=f"operazioni.usage-sessions.{session_id}",
            excerpt=f"Usage session {session_id} non presente nel dominio Operazioni.",
        )

    vehicle = db.get(Vehicle, session.vehicle_id)
    started_by = db.get(ApplicationUser, session.started_by_user_id)
    actual_driver = db.get(ApplicationUser, session.actual_driver_user_id) if session.actual_driver_user_id is not None else None
    team = db.get(Team, session.team_id) if session.team_id is not None else None
    payload = {
        "id": str(session.id),
        "vehicle_id": str(session.vehicle_id),
        "vehicle_code": vehicle.code if vehicle is not None else None,
        "vehicle_name": vehicle.name if vehicle is not None else None,
        "started_by_user_id": session.started_by_user_id,
        "started_by_username": started_by.username if started_by is not None else None,
        "actual_driver_user_id": session.actual_driver_user_id,
        "actual_driver_username": actual_driver.username if actual_driver is not None else None,
        "team_id": str(session.team_id) if session.team_id is not None else None,
        "team_name": team.name if team is not None else None,
        "related_assignment_id": str(session.related_assignment_id) if session.related_assignment_id is not None else None,
        "status": session.status,
        "started_at": session.started_at.isoformat(),
        "ended_at": session.ended_at.isoformat() if session.ended_at is not None else None,
        "start_odometer_km": float(session.start_odometer_km),
        "end_odometer_km": float(session.end_odometer_km) if session.end_odometer_km is not None else None,
        "route_distance_km": float(session.route_distance_km) if session.route_distance_km is not None else None,
        "engine_hours": float(session.engine_hours) if session.engine_hours is not None else None,
        "gps_source": session.gps_source,
        "notes": session.notes,
        "validated_at": session.validated_at.isoformat() if session.validated_at is not None else None,
    }
    answer = (
        "Lookup sessione d'uso Operazioni: "
        f"mezzo {vehicle.code if vehicle is not None else session.vehicle_id}, stato {session.status}, "
        f"driver {actual_driver.username if actual_driver is not None else started_by.username if started_by is not None else 'n/d'}, "
        f"avvio {session.started_at.isoformat()}, fine {session.ended_at.isoformat() if session.ended_at is not None else 'n/d'}."
    )
    excerpt = (
        f"Usage session {session.id}, vehicle {vehicle.code if vehicle is not None else session.vehicle_id}, "
        f"status {session.status}, driver {actual_driver.username if actual_driver is not None else 'n/d'}."
    )
    return build_live_data_response(
        answer=answer,
        tool_name="find_operazioni_usage_session_by_id",
        evidence_label="Dettaglio sessione d'uso Operazioni",
        source_key=f"operazioni.usage-sessions.{session.id}",
        excerpt=excerpt,
        payload=payload,
    )


def _find_operazioni_activity_by_id(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    from app.modules.operazioni.models.activities import ActivityCatalog, OperatorActivity
    from app.modules.operazioni.models.organizational import Team
    from app.modules.operazioni.models.vehicles import Vehicle

    activity_id = parse_uuid(question)
    if activity_id is None:
        return build_live_data_response(
            answer="Per cercare un'attività Operazioni devo ricevere un UUID valido.",
            tool_name="find_operazioni_activity_by_id",
            evidence_label="Lookup attività Operazioni non eseguito",
            source_key="operazioni.activities.lookup",
            excerpt="UUID attività non presente nella domanda.",
        )

    activity = db.get(OperatorActivity, activity_id)
    if activity is None:
        return build_live_data_response(
            answer="Non ho trovato nessuna attività Operazioni con questo identificativo.",
            tool_name="find_operazioni_activity_by_id",
            evidence_label="Attività Operazioni non trovata",
            source_key=f"operazioni.activities.{activity_id}",
            excerpt=f"Activity {activity_id} non presente nel dominio Operazioni.",
        )

    catalog = db.get(ActivityCatalog, activity.activity_catalog_id)
    vehicle = db.get(Vehicle, activity.vehicle_id) if activity.vehicle_id is not None else None
    operator = db.get(ApplicationUser, activity.operator_user_id)
    reviewer = db.get(ApplicationUser, activity.reviewed_by_user_id) if activity.reviewed_by_user_id is not None else None
    team = db.get(Team, activity.team_id) if activity.team_id is not None else None
    payload = {
        "id": str(activity.id),
        "activity_catalog_id": str(activity.activity_catalog_id),
        "activity_catalog_code": catalog.code if catalog is not None else None,
        "activity_catalog_name": catalog.name if catalog is not None else None,
        "activity_category": catalog.category if catalog is not None else None,
        "operator_user_id": activity.operator_user_id,
        "operator_username": operator.username if operator is not None else None,
        "team_id": str(activity.team_id) if activity.team_id is not None else None,
        "team_name": team.name if team is not None else None,
        "vehicle_id": str(activity.vehicle_id) if activity.vehicle_id is not None else None,
        "vehicle_code": vehicle.code if vehicle is not None else None,
        "vehicle_name": vehicle.name if vehicle is not None else None,
        "vehicle_usage_session_id": str(activity.vehicle_usage_session_id) if activity.vehicle_usage_session_id is not None else None,
        "status": activity.status,
        "started_at": activity.started_at.isoformat(),
        "ended_at": activity.ended_at.isoformat() if activity.ended_at is not None else None,
        "duration_minutes_declared": activity.duration_minutes_declared,
        "duration_minutes_calculated": activity.duration_minutes_calculated,
        "text_note": activity.text_note,
        "submitted_at": activity.submitted_at.isoformat() if activity.submitted_at is not None else None,
        "reviewed_by_user_id": activity.reviewed_by_user_id,
        "reviewed_by_username": reviewer.username if reviewer is not None else None,
        "reviewed_at": activity.reviewed_at.isoformat() if activity.reviewed_at is not None else None,
        "review_outcome": activity.review_outcome,
        "review_note": activity.review_note,
        "server_received_at": activity.server_received_at.isoformat() if activity.server_received_at is not None else None,
    }
    answer = (
        "Lookup attività Operazioni: "
        f"{catalog.name if catalog is not None else 'Attività'} "
        f"({catalog.code if catalog is not None else activity.activity_catalog_id}), "
        f"stato {activity.status}, operatore {operator.username if operator is not None else activity.operator_user_id}, "
        f"mezzo {vehicle.code if vehicle is not None else 'n/d'}, "
        f"review {activity.review_outcome or 'non presente'}."
    )
    excerpt = (
        f"Activity {activity.id}, catalog {catalog.code if catalog is not None else activity.activity_catalog_id}, "
        f"status {activity.status}, operator {operator.username if operator is not None else activity.operator_user_id}."
    )
    return build_live_data_response(
        answer=answer,
        tool_name="find_operazioni_activity_by_id",
        evidence_label="Dettaglio attività Operazioni",
        source_key=f"operazioni.activities.{activity.id}",
        excerpt=excerpt,
        payload=payload,
    )


def _find_operazioni_activity_approval_by_id(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    from app.modules.operazioni.models.activities import ActivityApproval, ActivityCatalog, OperatorActivity

    approval_id = parse_uuid(question)
    if approval_id is None:
        return build_live_data_response(
            answer="Per cercare un'approvazione attività Operazioni devo ricevere un UUID valido.",
            tool_name="find_operazioni_activity_approval_by_id",
            evidence_label="Lookup approvazione attività non eseguito",
            source_key="operazioni.activity-approvals.lookup",
            excerpt="UUID approvazione attività non presente nella domanda.",
        )

    approval = db.get(ActivityApproval, approval_id)
    if approval is None:
        return build_live_data_response(
            answer="Non ho trovato nessuna approvazione attività Operazioni con questo identificativo.",
            tool_name="find_operazioni_activity_approval_by_id",
            evidence_label="Approvazione attività non trovata",
            source_key=f"operazioni.activity-approvals.{approval_id}",
            excerpt=f"Activity approval {approval_id} non presente nel dominio Operazioni.",
        )

    activity = db.get(OperatorActivity, approval.operator_activity_id)
    catalog = db.get(ActivityCatalog, activity.activity_catalog_id) if activity is not None else None
    reviewer = db.get(ApplicationUser, approval.reviewer_user_id)
    operator = db.get(ApplicationUser, activity.operator_user_id) if activity is not None else None
    payload = {
        "id": str(approval.id),
        "operator_activity_id": str(approval.operator_activity_id),
        "activity_status": activity.status if activity is not None else None,
        "activity_catalog_code": catalog.code if catalog is not None else None,
        "activity_catalog_name": catalog.name if catalog is not None else None,
        "operator_user_id": activity.operator_user_id if activity is not None else None,
        "operator_username": operator.username if operator is not None else None,
        "reviewer_user_id": approval.reviewer_user_id,
        "reviewer_username": reviewer.username if reviewer is not None else None,
        "decision": approval.decision,
        "decision_at": approval.decision_at.isoformat(),
        "note": approval.note,
        "payload_json": approval.payload_json,
    }
    answer = (
        "Lookup approvazione attività Operazioni: "
        f"decisione {approval.decision}, reviewer {reviewer.username if reviewer is not None else approval.reviewer_user_id}, "
        f"attività {approval.operator_activity_id}, catalogo {catalog.code if catalog is not None else 'n/d'}."
    )
    excerpt = (
        f"Activity approval {approval.id}, decision {approval.decision}, "
        f"reviewer {reviewer.username if reviewer is not None else approval.reviewer_user_id}."
    )
    return build_live_data_response(
        answer=answer,
        tool_name="find_operazioni_activity_approval_by_id",
        evidence_label="Dettaglio approvazione attività Operazioni",
        source_key=f"operazioni.activity-approvals.{approval.id}",
        excerpt=excerpt,
        payload=payload,
    )


def _find_operazioni_fuel_log_by_id(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    from app.modules.operazioni.models.vehicles import Vehicle, VehicleFuelLog

    fuel_log_id = parse_uuid(question)
    if fuel_log_id is None:
        return build_live_data_response(
            answer="Per cercare un fuel log Operazioni devo ricevere un UUID valido.",
            tool_name="find_operazioni_fuel_log_by_id",
            evidence_label="Lookup fuel log non eseguito",
            source_key="operazioni.fuel-logs.lookup",
            excerpt="UUID fuel log non presente nella domanda.",
        )

    fuel_log = db.get(VehicleFuelLog, fuel_log_id)
    if fuel_log is None:
        return build_live_data_response(
            answer="Non ho trovato nessun fuel log Operazioni con questo identificativo.",
            tool_name="find_operazioni_fuel_log_by_id",
            evidence_label="Fuel log non trovato",
            source_key=f"operazioni.fuel-logs.{fuel_log_id}",
            excerpt=f"Fuel log {fuel_log_id} non presente nel dominio Operazioni.",
        )

    vehicle = db.get(Vehicle, fuel_log.vehicle_id)
    recorder = db.get(ApplicationUser, fuel_log.recorded_by_user_id)
    payload = {
        "id": str(fuel_log.id),
        "vehicle_id": str(fuel_log.vehicle_id),
        "vehicle_code": vehicle.code if vehicle is not None else None,
        "vehicle_name": vehicle.name if vehicle is not None else None,
        "usage_session_id": str(fuel_log.usage_session_id) if fuel_log.usage_session_id is not None else None,
        "recorded_by_user_id": fuel_log.recorded_by_user_id,
        "recorded_by_username": recorder.username if recorder is not None else None,
        "fueled_at": fuel_log.fueled_at.isoformat(),
        "liters": float(fuel_log.liters),
        "total_cost": float(fuel_log.total_cost) if fuel_log.total_cost is not None else None,
        "odometer_km": float(fuel_log.odometer_km) if fuel_log.odometer_km is not None else None,
        "station_name": fuel_log.station_name,
        "notes": fuel_log.notes,
    }
    answer = (
        "Lookup fuel log Operazioni: "
        f"mezzo {vehicle.code if vehicle is not None else fuel_log.vehicle_id}, "
        f"rifornimento {fuel_log.fueled_at.isoformat()}, litri {float(fuel_log.liters):.3f}, "
        f"costo {float(fuel_log.total_cost):.2f} euro, stazione {fuel_log.station_name or 'n/d'}."
        if fuel_log.total_cost is not None
        else
        "Lookup fuel log Operazioni: "
        f"mezzo {vehicle.code if vehicle is not None else fuel_log.vehicle_id}, "
        f"rifornimento {fuel_log.fueled_at.isoformat()}, litri {float(fuel_log.liters):.3f}, "
        f"costo non registrato, stazione {fuel_log.station_name or 'n/d'}."
    )
    excerpt = (
        f"Fuel log {fuel_log.id}, vehicle {vehicle.code if vehicle is not None else fuel_log.vehicle_id}, "
        f"liters {float(fuel_log.liters):.3f}, station {fuel_log.station_name or 'n/d'}."
    )
    return build_live_data_response(
        answer=answer,
        tool_name="find_operazioni_fuel_log_by_id",
        evidence_label="Dettaglio fuel log Operazioni",
        source_key=f"operazioni.fuel-logs.{fuel_log.id}",
        excerpt=excerpt,
        payload=payload,
    )


def _find_operazioni_unresolved_transaction_by_id(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    from app.modules.operazioni.models.vehicles import FleetUnresolvedTransaction

    unresolved_id = parse_uuid(question)
    if unresolved_id is None:
        return build_live_data_response(
            answer="Per cercare una transazione non risolta Operazioni devo ricevere un UUID valido.",
            tool_name="find_operazioni_unresolved_transaction_by_id",
            evidence_label="Lookup transazione non risolta non eseguito",
            source_key="operazioni.unresolved-transactions.lookup",
            excerpt="UUID transazione non risolta non presente nella domanda.",
        )

    row = db.get(FleetUnresolvedTransaction, unresolved_id)
    if row is None:
        return build_live_data_response(
            answer="Non ho trovato nessuna transazione non risolta Operazioni con questo identificativo.",
            tool_name="find_operazioni_unresolved_transaction_by_id",
            evidence_label="Transazione non risolta non trovata",
            source_key=f"operazioni.unresolved-transactions.{unresolved_id}",
            excerpt=f"Unresolved transaction {unresolved_id} non presente nel dominio Operazioni.",
        )

    payload = {
        "id": str(row.id),
        "import_ref": row.import_ref,
        "status": row.status,
        "row_index": row.row_index,
        "reason_type": row.reason_type,
        "reason_detail": row.reason_detail,
        "targa": row.targa,
        "identificativo": row.identificativo,
        "fueled_at_iso": row.fueled_at_iso,
        "liters": row.liters,
        "total_cost": row.total_cost,
        "odometer_km": row.odometer_km,
        "operator_name": row.operator_name,
        "wc_operator_id": row.wc_operator_id,
        "card_code": row.card_code,
        "station_name": row.station_name,
        "notes_extra": row.notes_extra,
        "resolved_vehicle_id": str(row.resolved_vehicle_id) if row.resolved_vehicle_id is not None else None,
        "resolved_by_user_id": row.resolved_by_user_id,
        "resolved_at": row.resolved_at.isoformat() if row.resolved_at is not None else None,
        "created_at": row.created_at.isoformat(),
    }
    answer = (
        "Lookup transazione non risolta Operazioni: "
        f"stato {row.status}, motivo {row.reason_type}, tessera {row.card_code or 'n/d'}, "
        f"operatore {row.operator_name or 'n/d'}, rifornimento {row.fueled_at_iso or 'n/d'}."
    )
    excerpt = (
        f"Unresolved {row.id}, status {row.status}, reason_type {row.reason_type}, "
        f"card {row.card_code or 'n/d'}, operator {row.operator_name or 'n/d'}."
    )
    return build_live_data_response(
        answer=answer,
        tool_name="find_operazioni_unresolved_transaction_by_id",
        evidence_label="Dettaglio transazione non risolta Operazioni",
        source_key=f"operazioni.unresolved-transactions.{row.id}",
        excerpt=excerpt,
        payload=payload,
    )


OPERAZIONI_WORKFLOW_TOOLS: tuple[WikiToolDefinition, ...] = (
    WikiToolDefinition(
        meta=WikiToolMeta(name="find_operazioni_case_by_id", module_key="operazioni"),
        intents=("live_data",),
        priority=100,
        matcher=_match_operazioni_case,
        handler=_find_operazioni_case_by_id,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="find_operazioni_assignment_by_id", module_key="operazioni"),
        intents=("live_data",),
        priority=105,
        matcher=_match_operazioni_assignment,
        handler=_find_operazioni_assignment_by_id,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="find_operazioni_maintenance_by_id", module_key="operazioni"),
        intents=("live_data",),
        priority=105,
        matcher=_match_operazioni_maintenance,
        handler=_find_operazioni_maintenance_by_id,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="find_operazioni_usage_session_by_id", module_key="operazioni"),
        intents=("live_data",),
        priority=105,
        matcher=_match_operazioni_usage_session,
        handler=_find_operazioni_usage_session_by_id,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="find_operazioni_activity_by_id", module_key="operazioni"),
        intents=("live_data",),
        priority=105,
        matcher=_match_operazioni_activity,
        handler=_find_operazioni_activity_by_id,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="find_operazioni_activity_approval_by_id", module_key="operazioni"),
        intents=("live_data",),
        priority=105,
        matcher=_match_operazioni_activity_approval,
        handler=_find_operazioni_activity_approval_by_id,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="find_operazioni_fuel_log_by_id", module_key="operazioni"),
        intents=("live_data",),
        priority=105,
        matcher=_match_operazioni_fuel_log,
        handler=_find_operazioni_fuel_log_by_id,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="find_operazioni_unresolved_transaction_by_id", module_key="operazioni"),
        intents=("live_data",),
        priority=105,
        matcher=_match_operazioni_unresolved_transaction,
        handler=_find_operazioni_unresolved_transaction_by_id,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="find_vehicle_by_id", module_key="operazioni"),
        intents=("live_data",),
        priority=100,
        matcher=match_vehicle,
        handler=find_vehicle_by_id,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="get_operazioni_dashboard_summary", module_key="operazioni"),
        intents=("live_data",),
        priority=10,
        matcher=lambda question: 1 if contains_any(question, "operazioni", "mezzi", "attivita", "pratiche", "storage") else 0,
        handler=_operazioni_summary,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="get_operazioni_pending_approvals", module_key="operazioni"),
        intents=("live_data",),
        priority=25,
        matcher=lambda question: 5 if contains_any(question, "approvazioni", "approvazione", "approval", "pending approvals", "in attesa approvazione", "in revisione") else 0,
        handler=_operazioni_pending_approvals,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="explain_operazioni_case_status", module_key="operazioni"),
        intents=("logic",),
        priority=60,
        matcher=_match_operazioni_case_logic,
        handler=_explain_operazioni_case_status,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="explain_operazioni_assignment_status", module_key="operazioni"),
        intents=("logic",),
        priority=65,
        matcher=_match_operazioni_assignment_logic,
        handler=_explain_operazioni_assignment_status,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="explain_operazioni_maintenance_status", module_key="operazioni"),
        intents=("logic",),
        priority=65,
        matcher=_match_operazioni_maintenance_logic,
        handler=_explain_operazioni_maintenance_status,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="explain_operazioni_usage_session_status", module_key="operazioni"),
        intents=("logic",),
        priority=65,
        matcher=_match_operazioni_usage_session_logic,
        handler=_explain_operazioni_usage_session_status,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="explain_operazioni_activity_status", module_key="operazioni"),
        intents=("logic",),
        priority=65,
        matcher=_match_operazioni_activity_logic,
        handler=_explain_operazioni_activity_status,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="explain_operazioni_activity_approval_decision", module_key="operazioni"),
        intents=("logic",),
        priority=65,
        matcher=_match_operazioni_activity_approval_logic,
        handler=_explain_operazioni_activity_approval_decision,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="explain_operazioni_fuel_log_status", module_key="operazioni"),
        intents=("logic",),
        priority=65,
        matcher=_match_operazioni_fuel_log_logic,
        handler=_explain_operazioni_fuel_log_status,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="explain_operazioni_unresolved_transaction_reason", module_key="operazioni"),
        intents=("logic",),
        priority=65,
        matcher=_match_operazioni_unresolved_transaction_logic,
        handler=_explain_operazioni_unresolved_transaction_reason,
    ),
)
