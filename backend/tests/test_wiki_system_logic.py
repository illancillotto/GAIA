from datetime import datetime
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.application_user import ApplicationUser
from app.models.wc_sync_job import WCSyncJob
from app.modules.operazioni.models.activities import ActivityApproval, ActivityCatalog, OperatorActivity
from app.modules.operazioni.models.vehicles import Vehicle, VehicleAssignment, VehicleMaintenance, VehicleMaintenanceType
from app.modules.operazioni.models.vehicles import VehicleFuelLog, VehicleUsageSession
from app.modules.operazioni.models.vehicles import FleetUnresolvedTransaction
from app.modules.riordino.models import RiordinoIssue, RiordinoPhase, RiordinoPractice, RiordinoStep
from app.modules.wiki.services.system_logic import (
    explain_operazioni_activity_approval_decision,
    explain_operazioni_analytics_metric,
    explain_operazioni_activity_status,
    explain_operazioni_assignment_status,
    explain_operazioni_analytics_anomaly,
    explain_operazioni_autodoc_sync_status,
    explain_operazioni_fuel_log_status,
    explain_operazioni_maintenance_status,
    explain_operazioni_mobile_sync_flow,
    explain_operazioni_storage_alert_level,
    explain_operazioni_unresolved_transaction_reason,
    explain_operazioni_usage_session_status,
    explain_riordino_practice_state,
)


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def setup_module() -> None:
    Base.metadata.create_all(engine)


def teardown_module() -> None:
    Base.metadata.drop_all(engine)


def test_explain_riordino_practice_state_reports_blocking_elements() -> None:
    db: Session = TestingSessionLocal()
    practice_id = uuid4()
    phase_id = uuid4()
    step_id = uuid4()
    user = ApplicationUser(
        username="riordino_logic_unit",
        email="riordino_logic_unit@test.local",
        password_hash="x",
        role="viewer",
        is_active=True,
        module_riordino=True,
    )
    db.add(user)
    db.flush()
    db.add(
        RiordinoPractice(
            id=practice_id,
            code="RIO-UNIT-0001",
            title="Pratica unit",
            municipality="Oristano",
            grid_code="A1",
            lot_code="B1",
            current_phase="phase_1",
            status="blocked",
            owner_user_id=user.id,
            created_by=user.id,
        )
    )
    db.add(
        RiordinoPhase(
            id=phase_id,
            practice_id=practice_id,
            phase_code="phase_1",
            status="in_progress",
        )
    )
    db.add(
        RiordinoStep(
            id=step_id,
            practice_id=practice_id,
            phase_id=phase_id,
            code="F1_DOC",
            title="Documento",
            sequence_no=1,
            status="todo",
            is_required=True,
            is_decision=False,
            requires_document=True,
        )
    )
    db.add(
        RiordinoIssue(
            practice_id=practice_id,
            phase_id=phase_id,
            step_id=step_id,
            type="missing_document",
            category="documentary",
            severity="blocking",
            status="open",
            title="Documento mancante",
            opened_by=user.id,
        )
    )
    db.commit()

    response = explain_riordino_practice_state(db, user, practice_id)

    assert response.mode == "logic"
    assert "blocked" in response.answer
    assert response.evidences[0].payload["blocking_issues"][0]["title"] == "Documento mancante"
    db.close()


def test_explain_operazioni_assignment_status_reports_open_operator_assignment() -> None:
    db: Session = TestingSessionLocal()
    user = ApplicationUser(
        username="operazioni_logic_unit",
        email="operazioni_logic_unit@test.local",
        password_hash="x",
        role="viewer",
        is_active=True,
        module_operazioni=True,
    )
    assignee = ApplicationUser(
        username="driver_unit",
        email="driver_unit@test.local",
        password_hash="x",
        role="viewer",
        is_active=True,
        module_operazioni=True,
    )
    db.add_all([user, assignee])
    db.flush()

    vehicle = Vehicle(
        code="VEH-UNIT-01",
        name="Mezzo unit test",
        vehicle_type="pickup",
        current_status="assigned",
        created_by_user_id=user.id,
    )
    db.add(vehicle)
    db.flush()

    assignment = VehicleAssignment(
        vehicle_id=vehicle.id,
        assignment_target_type="operator",
        operator_user_id=assignee.id,
        assigned_by_user_id=user.id,
        start_at=datetime(2026, 5, 27, 9, 0, 0),
        reason="Test assignment",
    )
    db.add(assignment)
    db.commit()

    response = explain_operazioni_assignment_status(db, user, assignment.id)

    assert response.mode == "logic"
    assert "aperta" in response.answer
    assert response.evidences[0].payload["operator_username"] == "driver_unit"
    assert response.evidences[0].payload["vehicle_code"] == "VEH-UNIT-01"
    db.close()


def test_explain_operazioni_maintenance_status_reports_completed_maintenance() -> None:
    db: Session = TestingSessionLocal()
    user = ApplicationUser(
        username="operazioni_maintenance_logic",
        email="operazioni_maintenance_logic@test.local",
        password_hash="x",
        role="viewer",
        is_active=True,
        module_operazioni=True,
    )
    db.add(user)
    db.flush()

    vehicle = Vehicle(
        code="VEH-UNIT-02",
        name="Mezzo manutenzione",
        vehicle_type="van",
        current_status="maintenance",
        created_by_user_id=user.id,
    )
    maintenance_type = VehicleMaintenanceType(code="TAGL", name="Tagliando")
    db.add_all([vehicle, maintenance_type])
    db.flush()

    maintenance = VehicleMaintenance(
        vehicle_id=vehicle.id,
        maintenance_type_id=maintenance_type.id,
        title="Tagliando completo",
        status="completed",
        opened_at=datetime(2026, 5, 20, 9, 0, 0),
        completed_at=datetime(2026, 5, 21, 15, 0, 0),
        supplier_name="Officina Test",
        created_by_user_id=user.id,
    )
    db.add(maintenance)
    db.commit()

    response = explain_operazioni_maintenance_status(db, user, maintenance.id)

    assert response.mode == "logic"
    assert "completed" in response.answer
    assert response.evidences[0].payload["maintenance_type_code"] == "TAGL"
    assert response.evidences[0].payload["vehicle_code"] == "VEH-UNIT-02"
    db.close()


def test_explain_operazioni_usage_session_status_reports_validated_session() -> None:
    db: Session = TestingSessionLocal()
    user = ApplicationUser(
        username="operazioni_usage_logic",
        email="operazioni_usage_logic@test.local",
        password_hash="x",
        role="viewer",
        is_active=True,
        module_operazioni=True,
    )
    validator = ApplicationUser(
        username="validator_usage",
        email="validator_usage@test.local",
        password_hash="x",
        role="admin",
        is_active=True,
        module_operazioni=True,
    )
    db.add_all([user, validator])
    db.flush()

    vehicle = Vehicle(
        code="VEH-UNIT-03",
        name="Mezzo sessione",
        vehicle_type="suv",
        current_status="available",
        created_by_user_id=user.id,
    )
    db.add(vehicle)
    db.flush()

    session = VehicleUsageSession(
        vehicle_id=vehicle.id,
        started_by_user_id=user.id,
        actual_driver_user_id=user.id,
        started_at=datetime(2026, 5, 27, 7, 30, 0),
        ended_at=datetime(2026, 5, 27, 9, 0, 0),
        start_odometer_km=1000,
        end_odometer_km=1035,
        status="validated",
        validated_by_user_id=validator.id,
        validated_at=datetime(2026, 5, 27, 9, 15, 0),
    )
    db.add(session)
    db.commit()

    response = explain_operazioni_usage_session_status(db, user, session.id)

    assert response.mode == "logic"
    assert "validated" in response.answer
    assert response.evidences[0].payload["validated_by_username"] == "validator_usage"
    assert response.evidences[0].payload["vehicle_code"] == "VEH-UNIT-03"
    db.close()


def test_explain_operazioni_activity_status_reports_submitted_activity() -> None:
    db: Session = TestingSessionLocal()
    user = ApplicationUser(
        username="operazioni_activity_logic",
        email="operazioni_activity_logic@test.local",
        password_hash="x",
        role="viewer",
        is_active=True,
        module_operazioni=True,
    )
    reviewer = ApplicationUser(
        username="activity_reviewer",
        email="activity_reviewer@test.local",
        password_hash="x",
        role="reviewer",
        is_active=True,
        module_operazioni=True,
    )
    db.add_all([user, reviewer])
    db.flush()

    vehicle = Vehicle(
        code="VEH-UNIT-03A",
        name="Mezzo attivita",
        vehicle_type="pickup",
        current_status="available",
        created_by_user_id=user.id,
    )
    catalog = ActivityCatalog(
        code="SOPR",
        name="Sopralluogo",
        category="field",
        requires_vehicle=True,
    )
    db.add_all([vehicle, catalog])
    db.flush()

    activity = OperatorActivity(
        activity_catalog_id=catalog.id,
        operator_user_id=user.id,
        vehicle_id=vehicle.id,
        status="submitted",
        started_at=datetime(2026, 5, 27, 8, 0, 0),
        ended_at=datetime(2026, 5, 27, 9, 20, 0),
        duration_minutes_declared=80,
        duration_minutes_calculated=80,
        submitted_at=datetime(2026, 5, 27, 9, 21, 0),
        reviewed_by_user_id=reviewer.id,
        review_outcome="needs_integration",
        review_note="Integrare nota operativa",
    )
    db.add(activity)
    db.commit()

    response = explain_operazioni_activity_status(db, user, activity.id)

    assert response.mode == "logic"
    assert "submitted" in response.answer
    assert response.evidences[0].payload["activity_catalog_code"] == "SOPR"
    assert response.evidences[0].payload["vehicle_code"] == "VEH-UNIT-03A"
    db.close()


def test_explain_operazioni_activity_approval_decision_reports_needs_integration() -> None:
    db: Session = TestingSessionLocal()
    user = ApplicationUser(
        username="operazioni_activity_approval_logic",
        email="operazioni_activity_approval_logic@test.local",
        password_hash="x",
        role="viewer",
        is_active=True,
        module_operazioni=True,
    )
    reviewer = ApplicationUser(
        username="activity_approval_reviewer",
        email="activity_approval_reviewer@test.local",
        password_hash="x",
        role="reviewer",
        is_active=True,
        module_operazioni=True,
    )
    db.add_all([user, reviewer])
    db.flush()

    catalog = ActivityCatalog(
        code="CHK",
        name="Checklist impianto",
        category="inspection",
        requires_vehicle=False,
    )
    db.add(catalog)
    db.flush()

    activity = OperatorActivity(
        activity_catalog_id=catalog.id,
        operator_user_id=user.id,
        status="under_review",
        started_at=datetime(2026, 5, 27, 10, 0, 0),
        ended_at=datetime(2026, 5, 27, 10, 30, 0),
        submitted_at=datetime(2026, 5, 27, 10, 31, 0),
        review_outcome="needs_integration",
        reviewed_by_user_id=reviewer.id,
        reviewed_at=datetime(2026, 5, 27, 11, 0, 0),
    )
    db.add(activity)
    db.flush()

    approval = ActivityApproval(
        operator_activity_id=activity.id,
        reviewer_user_id=reviewer.id,
        decision="needs_integration",
        decision_at=datetime(2026, 5, 27, 11, 0, 0),
        note="Manca dettaglio finale",
    )
    db.add(approval)
    db.commit()

    response = explain_operazioni_activity_approval_decision(db, user, approval.id)

    assert response.mode == "logic"
    assert "needs_integration" in response.answer
    assert response.evidences[0].payload["activity_catalog_code"] == "CHK"
    assert response.evidences[0].payload["reviewer_username"] == "activity_approval_reviewer"
    db.close()


def test_explain_operazioni_autodoc_sync_status_reports_failed_job() -> None:
    db: Session = TestingSessionLocal()
    user = ApplicationUser(
        username="operazioni_autodoc_logic",
        email="operazioni_autodoc_logic@test.local",
        password_hash="x",
        role="viewer",
        is_active=True,
        module_operazioni=True,
    )
    db.add(user)
    db.flush()

    job = WCSyncJob(
        entity="autodoc_vehicle_details",
        status="failed",
        records_synced=3,
        records_skipped=1,
        records_errors=2,
        error_detail="Timeout browser worker",
        triggered_by=user.id,
        params_json={"selected_total": 6},
    )
    db.add(job)
    db.commit()

    response = explain_operazioni_autodoc_sync_status(db, user, job.id)

    assert response.mode == "logic"
    assert "failed" in response.answer
    assert response.evidences[0].payload["records_errors"] == 2
    assert response.evidences[0].payload["entity"] == "autodoc_vehicle_details"
    db.close()


def test_explain_operazioni_analytics_metric_reports_total_km_rule() -> None:
    response = explain_operazioni_analytics_metric("Spiega come viene calcolato l'indicatore km analytics operazioni")

    assert response.mode == "logic"
    assert "sessioni d'uso chiuse" in response.answer
    assert response.evidences[0].payload["metric_key"] == "total_km"


def test_explain_operazioni_analytics_metric_reports_work_hours_team_rule() -> None:
    response = explain_operazioni_analytics_metric("Spiega come viene calcolato l'indicatore ore per team analytics operazioni")

    assert response.mode == "logic"
    assert "team_id" in response.answer
    assert response.evidences[0].payload["metric_key"] == "work_hours_by_team"


def test_explain_operazioni_fuel_log_status_reports_incomplete_log() -> None:
    db: Session = TestingSessionLocal()
    user = ApplicationUser(
        username="operazioni_fuel_logic",
        email="operazioni_fuel_logic@test.local",
        password_hash="x",
        role="viewer",
        is_active=True,
        module_operazioni=True,
    )
    db.add(user)
    db.flush()

    vehicle = Vehicle(
        code="VEH-UNIT-04",
        name="Mezzo fuel",
        vehicle_type="van",
        current_status="available",
        created_by_user_id=user.id,
    )
    db.add(vehicle)
    db.flush()

    fuel_log = VehicleFuelLog(
        vehicle_id=vehicle.id,
        recorded_by_user_id=user.id,
        fueled_at=datetime(2026, 5, 27, 10, 0, 0),
        liters=42.5,
        station_name=None,
    )
    db.add(fuel_log)
    db.commit()

    response = explain_operazioni_fuel_log_status(db, user, fuel_log.id)

    assert response.mode == "logic"
    assert "incomplete" in response.answer
    assert response.evidences[0].payload["classification"] == "incomplete"
    assert response.evidences[0].payload["vehicle_code"] == "VEH-UNIT-04"
    db.close()


def test_explain_operazioni_unresolved_transaction_reason_reports_reason_type() -> None:
    db: Session = TestingSessionLocal()
    user = ApplicationUser(
        username="operazioni_unresolved_logic",
        email="operazioni_unresolved_logic@test.local",
        password_hash="x",
        role="viewer",
        is_active=True,
        module_operazioni=True,
    )
    db.add(user)
    db.flush()

    row = FleetUnresolvedTransaction(
        import_ref="import-001",
        status="pending",
        row_index=4,
        reason_type="no_vehicle",
        reason_detail="nessun mezzo assegnato all'operatore alla data del rifornimento",
        operator_name="Mario Rossi",
        card_code="CARD-77",
        created_by_user_id=user.id,
    )
    db.add(row)
    db.commit()

    response = explain_operazioni_unresolved_transaction_reason(db, user, row.id)

    assert response.mode == "logic"
    assert "no_vehicle" in response.answer
    assert response.evidences[0].payload["card_code"] == "CARD-77"
    assert response.evidences[0].payload["reason_type"] == "no_vehicle"
    db.close()


def test_explain_operazioni_analytics_anomaly_reports_excessive_fuel() -> None:
    db: Session = TestingSessionLocal()
    user = ApplicationUser(
        username="operazioni_analytics_logic",
        email="operazioni_analytics_logic@test.local",
        password_hash="x",
        role="viewer",
        is_active=True,
        module_operazioni=True,
    )
    db.add(user)
    db.flush()

    vehicle = Vehicle(
        code="VEH-UNIT-05",
        name="Mezzo analitica",
        vehicle_type="truck",
        current_status="available",
        created_by_user_id=user.id,
    )
    db.add(vehicle)
    db.flush()

    fuel_log = VehicleFuelLog(
        vehicle_id=vehicle.id,
        recorded_by_user_id=user.id,
        fueled_at=datetime.now(),
        liters=130.0,
        total_cost=210.0,
        station_name="Test station",
    )
    db.add(fuel_log)
    db.commit()

    response = explain_operazioni_analytics_anomaly(db, user, str(fuel_log.id))

    assert response.mode == "logic"
    assert "excessive_fuel" in response.answer
    assert response.evidences[0].payload["type"] == "excessive_fuel"
    assert response.evidences[0].payload["entity_id"] == str(fuel_log.id)
    db.close()


def test_explain_operazioni_storage_alert_level_reports_warning_rule() -> None:
    response = explain_operazioni_storage_alert_level("Spiega la soglia warning storage operazioni")

    assert response.mode == "logic"
    assert "warning" in response.answer
    assert response.evidences[0].payload["explanation_key"] == "warning"


def test_explain_operazioni_mobile_sync_flow_reports_worksets_rule() -> None:
    response = explain_operazioni_mobile_sync_flow("Spiega come funzionano i workset del mobile sync operazioni")

    assert response.mode == "logic"
    assert "workset" in response.answer
    assert response.evidences[0].payload["explanation_key"] == "worksets"
