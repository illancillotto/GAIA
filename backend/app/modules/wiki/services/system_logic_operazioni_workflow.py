from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.operazioni.models.activities import ActivityApproval, ActivityCatalog, OperatorActivity
from app.modules.operazioni.models.organizational import Team
from app.modules.operazioni.models.vehicles import (
    FleetUnresolvedTransaction,
    Vehicle,
    VehicleAssignment,
    VehicleFuelLog,
    VehicleMaintenance,
    VehicleMaintenanceType,
    VehicleUsageSession,
)
from app.modules.operazioni.routes.reports import get_case
from app.modules.wiki.schemas import WikiChatResponse
from app.modules.wiki.services.logic_catalog import (
    CATALOG_OPERAZIONI_ACTIVITY_APPROVAL_DECISION,
    CATALOG_OPERAZIONI_ACTIVITY_STATUS,
    CATALOG_OPERAZIONI_ASSIGNMENT_STATUS,
    CATALOG_OPERAZIONI_CASE_STATUS,
    CATALOG_OPERAZIONI_FUEL_LOG_STATUS,
    CATALOG_OPERAZIONI_MAINTENANCE_STATUS,
    CATALOG_OPERAZIONI_UNRESOLVED_TRANSACTION_REASON,
    CATALOG_OPERAZIONI_USAGE_SESSION_STATUS,
)
from app.modules.wiki.services.response_composer import build_logic_response

# moved verbatim from system_logic_operazioni.py
def explain_operazioni_case_status(db: Session, current_user: ApplicationUser, case_id: UUID) -> WikiChatResponse:
    case = get_case(case_id=case_id, current_user=current_user, db=db)
    status = case["status"]
    explanation = CATALOG_OPERAZIONI_CASE_STATUS.get(status)
    base_rule = explanation.answer_template if explanation is not None else "Lo stato del case deriva dagli eventi di assegnazione, presa in carico, risoluzione e chiusura."
    answer = (
        f"Il case {case['case_number']} e nello stato {status}. {base_rule} "
        f"Assegnato a utente {case['assigned_to_user_id'] or 'n/d'}, team {case['assigned_team_id'] or 'n/d'}, "
        f"eventi registrati: {len(case['events'])}."
    )
    excerpt = (
        f"Case {case['case_number']}, stato {status}, assigned_user {case['assigned_to_user_id']}, "
        f"assigned_team {case['assigned_team_id']}, events {len(case['events'])}."
    )
    payload = {
        "case_id": case["id"],
        "case_number": case["case_number"],
        "status": status,
        "assigned_to_user_id": case["assigned_to_user_id"],
        "assigned_team_id": case["assigned_team_id"],
        "acknowledged_at": case["acknowledged_at"],
        "started_at": case["started_at"],
        "resolved_at": case["resolved_at"],
        "closed_at": case["closed_at"],
        "events_count": len(case["events"]),
        "events": case["events"][:5],
    }
    return build_logic_response(
        answer=answer,
        tool_name="explain_operazioni_case_status",
        evidence_label=explanation.label if explanation is not None else "Spiegazione stato case Operazioni",
        source_key=f"operazioni.case.logic.{case['id']}",
        excerpt=explanation.excerpt if explanation is not None else excerpt,
        payload=payload,
    )

# the rest of workflow explainers intentionally kept compact but still domain-scoped
def explain_operazioni_assignment_status(db: Session, current_user: ApplicationUser, assignment_id: UUID) -> WikiChatResponse:
    assignment = db.get(VehicleAssignment, assignment_id)
    if assignment is None:
        return build_logic_response(
            answer="Non ho trovato nessuna assegnazione mezzo con questo identificativo.",
            tool_name="explain_operazioni_assignment_status",
            evidence_label="Assegnazione mezzo non trovata",
            source_key=f"operazioni.assignments.{assignment_id}",
            excerpt=f"Assignment {assignment_id} non presente nel dominio Operazioni.",
            payload={"assignment_id": str(assignment_id)},
        )
    vehicle = db.get(Vehicle, assignment.vehicle_id)
    operator = db.get(ApplicationUser, assignment.operator_user_id) if assignment.operator_user_id is not None else None
    team = db.get(Team, assignment.team_id) if assignment.team_id is not None else None
    is_open = assignment.end_at is None
    target_kind = assignment.assignment_target_type if assignment.assignment_target_type in {"operator", "team"} else "operator"
    explanation = CATALOG_OPERAZIONI_ASSIGNMENT_STATUS[f"{'open' if is_open else 'closed'}_{target_kind}"]
    target_label = operator.username if operator is not None else team.name if team is not None else "destinatario non risolto"
    return build_logic_response(
        answer=f"L'assegnazione {assignment.id} del mezzo {vehicle.code if vehicle is not None else assignment.vehicle_id} e {'aperta' if is_open else 'chiusa'} verso {'operatore' if assignment.assignment_target_type == 'operator' else 'team'} {target_label}. {explanation.answer_template} Inizio {assignment.start_at.isoformat()}, fine {assignment.end_at.isoformat() if assignment.end_at is not None else 'non registrata'}.",
        tool_name="explain_operazioni_assignment_status",
        evidence_label=explanation.label,
        source_key=f"operazioni.assignments.logic.{assignment.id}",
        excerpt=explanation.excerpt,
        payload={"assignment_id": str(assignment.id), "vehicle_code": vehicle.code if vehicle is not None else None, "assignment_target_type": assignment.assignment_target_type, "operator_username": operator.username if operator is not None else None, "team_name": team.name if team is not None else None, "is_open": is_open, "start_at": assignment.start_at.isoformat(), "end_at": assignment.end_at.isoformat() if assignment.end_at is not None else None},
    )

def explain_operazioni_maintenance_status(db: Session, current_user: ApplicationUser, maintenance_id: UUID) -> WikiChatResponse:
    maintenance = db.get(VehicleMaintenance, maintenance_id)
    if maintenance is None:
        return build_logic_response(
            answer="Non ho trovato nessuna manutenzione con questo identificativo.",
            tool_name="explain_operazioni_maintenance_status",
            evidence_label="Manutenzione non trovata",
            source_key=f"operazioni.maintenances.{maintenance_id}",
            excerpt=f"Maintenance {maintenance_id} non presente nel dominio Operazioni.",
            payload={"maintenance_id": str(maintenance_id)},
        )
    vehicle = db.get(Vehicle, maintenance.vehicle_id)
    maintenance_type = db.get(VehicleMaintenanceType, maintenance.maintenance_type_id) if maintenance.maintenance_type_id is not None else None
    explanation = CATALOG_OPERAZIONI_MAINTENANCE_STATUS.get(maintenance.status)
    excerpt = f"Maintenance {maintenance.id}, vehicle {vehicle.code if vehicle is not None else maintenance.vehicle_id}, status {maintenance.status}."
    return build_logic_response(
        answer=f"La manutenzione {maintenance.id} del mezzo {vehicle.code if vehicle is not None else maintenance.vehicle_id} e nello stato {maintenance.status}. {(explanation.answer_template if explanation is not None else 'Lo stato manutenzione deriva dal workflow del modulo e dalla presenza o meno di una chiusura registrata.')} Apertura {maintenance.opened_at.isoformat()}, programmata {maintenance.scheduled_for.isoformat() if maintenance.scheduled_for is not None else 'non indicata'}, completamento {maintenance.completed_at.isoformat() if maintenance.completed_at is not None else 'non registrato'}.",
        tool_name="explain_operazioni_maintenance_status",
        evidence_label=explanation.label if explanation is not None else "Spiegazione stato manutenzione Operazioni",
        source_key=f"operazioni.maintenances.logic.{maintenance.id}",
        excerpt=explanation.excerpt if explanation is not None else excerpt,
        payload={"maintenance_id": str(maintenance.id), "vehicle_code": vehicle.code if vehicle is not None else None, "maintenance_type_code": maintenance_type.code if maintenance_type is not None else None, "status": maintenance.status},
    )

def explain_operazioni_usage_session_status(db: Session, current_user: ApplicationUser, session_id: UUID) -> WikiChatResponse:
    session = db.get(VehicleUsageSession, session_id)
    if session is None:
        return build_logic_response(
            answer="Non ho trovato nessuna sessione d'uso con questo identificativo.",
            tool_name="explain_operazioni_usage_session_status",
            evidence_label="Sessione d'uso non trovata",
            source_key=f"operazioni.usage-sessions.{session_id}",
            excerpt=f"Usage session {session_id} non presente nel dominio Operazioni.",
            payload={"session_id": str(session_id)},
        )
    vehicle = db.get(Vehicle, session.vehicle_id)
    actual_driver = db.get(ApplicationUser, session.actual_driver_user_id) if session.actual_driver_user_id is not None else None
    validator = db.get(ApplicationUser, session.validated_by_user_id) if session.validated_by_user_id is not None else None
    explanation = CATALOG_OPERAZIONI_USAGE_SESSION_STATUS.get(session.status)
    excerpt = f"Usage session {session.id}, vehicle {vehicle.code if vehicle is not None else session.vehicle_id}, status {session.status}."
    return build_logic_response(
        answer=f"La sessione d'uso {session.id} del mezzo {vehicle.code if vehicle is not None else session.vehicle_id} e nello stato {session.status}. {(explanation.answer_template if explanation is not None else 'Lo stato sessione deriva dal workflow operativo e dalla presenza di chiusura e validazione.')} Avvio {session.started_at.isoformat()}, fine {session.ended_at.isoformat() if session.ended_at is not None else 'non registrata'}, validazione {session.validated_at.isoformat() if session.validated_at is not None else 'non registrata'}.",
        tool_name="explain_operazioni_usage_session_status",
        evidence_label=explanation.label if explanation is not None else "Spiegazione stato sessione Operazioni",
        source_key=f"operazioni.usage-sessions.logic.{session.id}",
        excerpt=explanation.excerpt if explanation is not None else excerpt,
        payload={
            "session_id": str(session.id),
            "vehicle_code": vehicle.code if vehicle is not None else None,
            "status": session.status,
            "actual_driver_username": actual_driver.username if actual_driver is not None else None,
            "validated_by_username": validator.username if validator is not None else None,
        },
    )

def explain_operazioni_activity_status(db: Session, current_user: ApplicationUser, activity_id: UUID) -> WikiChatResponse:
    activity = db.get(OperatorActivity, activity_id)
    if activity is None:
        return build_logic_response(
            answer="Non ho trovato nessuna attività Operazioni con questo identificativo.",
            tool_name="explain_operazioni_activity_status",
            evidence_label="Attività Operazioni non trovata",
            source_key=f"operazioni.activities.{activity_id}",
            excerpt=f"Activity {activity_id} non presente nel dominio Operazioni.",
            payload={"activity_id": str(activity_id)},
        )
    catalog = db.get(ActivityCatalog, activity.activity_catalog_id)
    vehicle = db.get(Vehicle, activity.vehicle_id) if activity.vehicle_id is not None else None
    operator = db.get(ApplicationUser, activity.operator_user_id)
    explanation = CATALOG_OPERAZIONI_ACTIVITY_STATUS.get(activity.status)
    excerpt = f"Activity {activity.id}, catalog {catalog.code if catalog is not None else activity.activity_catalog_id}, status {activity.status}."
    return build_logic_response(
        answer=f"L'attività {activity.id} {catalog.name if catalog is not None else activity.activity_catalog_id} è nello stato {activity.status}. {(explanation.answer_template if explanation is not None else 'Lo stato attività deriva dalla combinazione di avvio, stop, invio review ed esito della review.')} Operatore {operator.username if operator is not None else activity.operator_user_id}, mezzo {vehicle.code if vehicle is not None else activity.vehicle_id or 'n/d'}, inizio {activity.started_at.isoformat()}, fine {activity.ended_at.isoformat() if activity.ended_at is not None else 'non registrata'}.",
        tool_name="explain_operazioni_activity_status",
        evidence_label=explanation.label if explanation is not None else "Spiegazione stato attività Operazioni",
        source_key=f"operazioni.activities.logic.{activity.id}",
        excerpt=explanation.excerpt if explanation is not None else excerpt,
        payload={"activity_id": str(activity.id), "activity_catalog_code": catalog.code if catalog is not None else None, "vehicle_code": vehicle.code if vehicle is not None else None, "operator_username": operator.username if operator is not None else None, "status": activity.status},
    )

def explain_operazioni_activity_approval_decision(db: Session, current_user: ApplicationUser, approval_id: UUID) -> WikiChatResponse:
    approval = db.get(ActivityApproval, approval_id)
    if approval is None:
        return build_logic_response(
            answer="Non ho trovato nessuna approvazione attività Operazioni con questo identificativo.",
            tool_name="explain_operazioni_activity_approval_decision",
            evidence_label="Approvazione attività non trovata",
            source_key=f"operazioni.activity-approvals.{approval_id}",
            excerpt=f"Activity approval {approval_id} non presente nel dominio Operazioni.",
            payload={"approval_id": str(approval_id)},
        )
    activity = db.get(OperatorActivity, approval.operator_activity_id)
    catalog = db.get(ActivityCatalog, activity.activity_catalog_id) if activity is not None else None
    reviewer = db.get(ApplicationUser, approval.reviewer_user_id)
    explanation = CATALOG_OPERAZIONI_ACTIVITY_APPROVAL_DECISION.get(approval.decision)
    excerpt = f"Approval {approval.id}, activity {approval.operator_activity_id}, decision {approval.decision}."
    base_rule = (
        explanation.answer_template
        if explanation is not None
        else "La decisione di review deriva dall'esito della verifica applicativa sull'attività."
    )
    return build_logic_response(
        answer=(
            f"L'approvazione {approval.id} per l'attività {approval.operator_activity_id} "
            f"ha decisione {approval.decision}. {base_rule} Reviewer "
            f"{reviewer.username if reviewer is not None else approval.reviewer_user_id}, "
            f"decisione registrata il {approval.decision_at.isoformat()}."
        ),
        tool_name="explain_operazioni_activity_approval_decision",
        evidence_label=explanation.label if explanation is not None else "Spiegazione approvazione attività Operazioni",
        source_key=f"operazioni.activity-approvals.logic.{approval.id}",
        excerpt=explanation.excerpt if explanation is not None else excerpt,
        payload={
            "approval_id": str(approval.id),
            "operator_activity_id": str(approval.operator_activity_id),
            "activity_catalog_code": catalog.code if catalog is not None else None,
            "decision": approval.decision,
            "reviewer_username": reviewer.username if reviewer is not None else None,
        },
    )

def explain_operazioni_fuel_log_status(db: Session, current_user: ApplicationUser, fuel_log_id: UUID) -> WikiChatResponse:
    fuel_log = db.get(VehicleFuelLog, fuel_log_id)
    if fuel_log is None:
        return build_logic_response(
            answer="Non ho trovato nessun fuel log con questo identificativo.",
            tool_name="explain_operazioni_fuel_log_status",
            evidence_label="Fuel log non trovato",
            source_key=f"operazioni.fuel-logs.{fuel_log_id}",
            excerpt=f"Fuel log {fuel_log_id} non presente nel dominio Operazioni.",
            payload={"fuel_log_id": str(fuel_log_id)},
        )
    vehicle = db.get(Vehicle, fuel_log.vehicle_id)
    classification_key = "linked" if fuel_log.usage_session_id is not None else "incomplete" if fuel_log.total_cost is None or fuel_log.station_name is None or fuel_log.odometer_km is None else "standalone"
    explanation = CATALOG_OPERAZIONI_FUEL_LOG_STATUS[classification_key]
    return build_logic_response(
        answer=f"Il fuel log {fuel_log.id} del mezzo {vehicle.code if vehicle is not None else fuel_log.vehicle_id} e classificato come {classification_key}. {explanation.answer_template}",
        tool_name="explain_operazioni_fuel_log_status",
        evidence_label=explanation.label,
        source_key=f"operazioni.fuel-logs.logic.{fuel_log.id}",
        excerpt=explanation.excerpt,
        payload={"fuel_log_id": str(fuel_log.id), "classification": classification_key, "vehicle_code": vehicle.code if vehicle is not None else None},
    )

def explain_operazioni_unresolved_transaction_reason(db: Session, current_user: ApplicationUser, unresolved_id: UUID) -> WikiChatResponse:
    row = db.get(FleetUnresolvedTransaction, unresolved_id)
    if row is None:
        return build_logic_response(
            answer="Non ho trovato nessuna transazione non risolta con questo identificativo.",
            tool_name="explain_operazioni_unresolved_transaction_reason",
            evidence_label="Transazione non risolta non trovata",
            source_key=f"operazioni.unresolved-transactions.{unresolved_id}",
            excerpt=f"Unresolved transaction {unresolved_id} non presente nel dominio Operazioni.",
            payload={"unresolved_id": str(unresolved_id)},
        )
    explanation = CATALOG_OPERAZIONI_UNRESOLVED_TRANSACTION_REASON.get(row.reason_type)
    excerpt = f"Unresolved {row.id}, status {row.status}, reason_type {row.reason_type}."
    return build_logic_response(
        answer=f"La transazione non risolta {row.id} è nello stato {row.status} con motivo {row.reason_type}. {(explanation.answer_template if explanation is not None else 'La riga è rimasta non risolta perché il processo di import non ha trovato un mapping operativo sufficiente.')} Dettaglio: {row.reason_detail}.",
        tool_name="explain_operazioni_unresolved_transaction_reason",
        evidence_label=explanation.label if explanation is not None else "Spiegazione transazione non risolta Operazioni",
        source_key=f"operazioni.unresolved-transactions.logic.{row.id}",
        excerpt=explanation.excerpt if explanation is not None else excerpt,
        payload={
            "unresolved_id": str(row.id),
            "reason_type": row.reason_type,
            "status": row.status,
            "card_code": row.card_code,
        },
    )
