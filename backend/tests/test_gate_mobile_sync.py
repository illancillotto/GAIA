from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, date, datetime, time

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.core.database import Base
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.operazioni.models.gate_mobile_sync_run import GateMobileSyncRun
from app.modules.operazioni.models.organizational import OperatorProfile
from app.modules.operazioni.models.wc_operator import WCOperator
from app.modules.operazioni.schemas.operators import GateMobileConsoleUpdateRequest
from app.modules.presenze.models import (
    OrganizationTeam,
    OrganizationTeamMembership,
    OrganizationTeamSupervisorAssignment,
    PresenzeCollaborator,
    PresenzeCollaboratorScheduleAssignment,
    PresenzeDailyPunch,
    PresenzeDailyRecord,
    PresenzeHoliday,
    PresenzeImportJob,
    PresenzeOperaiRuleConfig,
    PresenzeScheduleRule,
    PresenzeScheduleTemplate,
    PresenzeSyncJob,
)
from app.modules.presenze.services import gate_mobile_payloads, gate_mobile_team_actions
from app.services import gate_mobile_sync as gate_mobile_sync_service
from app.services.gate_mobile_sync import (
    build_mobile_catalog_push_payloads,
    build_mobile_operator_push_payload,
    build_mobile_workset_push_payloads,
    build_presenze_anomalie_push_payload,
    build_presenze_giornaliere_push_payload,
    build_presenze_months_push_payload,
    build_presenze_rules_push_payload,
    build_presenze_teams_push_payload,
    execute_gate_mobile_sync,
    get_gate_mobile_sync_status,
    get_running_gate_mobile_sync_run,
    process_presenze_pending_actions,
    run_gate_mobile_sync_once,
)


class _FakeRecordItem:
    def __init__(self, record_id: uuid.UUID) -> None:
        self.record_id = record_id

    def model_dump(self, *, mode: str = "python") -> dict:
        return {
            "record_id": str(self.record_id),
            "collaborator_id": "018f88a2-1797-7365-bf5e-8bb8b7f9d001",
            "collaborator_name": "OPERATORE PRESENZE",
            "employee_code": "P001",
            "team_ids": ["018f88a2-1797-7365-bf5e-8bb8b7f9d002"],
            "work_date": "2026-07-10",
            "weekday": "venerdi",
            "status": "ok",
            "review_status": "pending",
            "severity": "warning",
            "contract_kind": "impiegato",
            "schedule_code": "STD",
            "ordinary_minutes": 420,
            "extra_minutes": 240,
            "missing_minutes": 0,
            "absence_cause": None,
            "has_request": False,
            "has_complete_punches": True,
            "validated_at": None,
            "validated_by_user_id": None,
        }


class _FakeAnalysis:
    severity = "warning"
    reasons = ["extra_over_3h"]
    operator_message = "Straordinario superiore a 3 ore."


class _FakeCatalogResponse:
    catalogs = [
        type(
            "Catalog",
            (),
            {
                "catalog_type": "meters",
                "version": "v1",
                "synced_from_gaia_at": datetime(2026, 6, 15, 10, 0, tzinfo=UTC),
                "payload": {"items": []},
            },
        )()
    ]


class _FakeWorksetResponse:
    worksets = [
        type(
            "Workset",
            (),
            {
                "operator_id": uuid.UUID("018f88a2-1797-7365-bf5e-8bb8b7f9c0aa"),
                "workset_type": "assigned_meters",
                "synced_from_gaia_at": datetime(2026, 6, 15, 10, 0, tzinfo=UTC),
                "items": [
                    type(
                        "WorksetItem",
                        (),
                        {
                            "gaia_entity_id": "meter-1",
                            "payload": {"meter": "A1"},
                        },
                    )()
                ],
            },
        )()
    ]


def test_build_mobile_operator_push_payload_serializes_wc_operators() -> None:
    db = _build_session()
    try:
        operator_id = uuid.UUID("018f88a2-1797-7365-bf5e-8bb8b7f9c0aa")
        profile_id = uuid.UUID("018f88a2-1797-7365-bf5e-8bb8b7f9c0ac")
        _seed_operator(db, operator_id=operator_id, profile_id=profile_id)

        payload = build_mobile_operator_push_payload(
            db,
            now=datetime(2026, 6, 15, 10, 0, tzinfo=UTC),
        )

        assert payload == {
            "synced_from_gaia_at": "2026-06-15T10:00:00Z",
            "operators": [
                {
                    "operator_id": str(operator_id),
                    "gaia_user_id": "42",
                    "gaia_operator_profile_id": str(profile_id),
                    "gaia_username": "mrossi",
                    "display_name": "Mario Rossi",
                    "email": "mario.rossi@example.test",
                    "phone": "+39070000000",
                    "personnel_area": "AGRARIO",
                    "status": "ACTIVE",
                    "domains": None,
                    "gate_mobile_console_enabled": False,
                    "gate_mobile_console_role": None,
                    "gate_mobile_console_pages": None,
                }
            ],
        }
    finally:
        db.close()


def test_gate_mobile_payloads_reject_missing_or_invalid_personnel_area() -> None:
    db = _build_session()
    try:
        _seed_operator(db)
        operator = db.scalar(select(WCOperator))
        assert operator is not None
        operator.personnel_area = None
        db.commit()
        try:
            build_mobile_operator_push_payload(db)
        except ValueError as exc:
            assert "personnel_area" in str(exc)
        else:
            raise AssertionError("Expected missing operator personnel_area to fail")

        _seed_presenze_team(db)
        team = db.scalar(select(OrganizationTeam))
        assert team is not None
        team.personnel_area = "UNKNOWN"
        try:
            db.commit()
        except IntegrityError as exc:
            assert "ck_organization_teams_personnel_area" in str(exc)
            db.rollback()
        else:
            raise AssertionError("Expected invalid team personnel_area constraint failure")
    finally:
        db.close()


def test_gate_mobile_console_update_request_validates_role_contract() -> None:
    disabled = GateMobileConsoleUpdateRequest(enabled=False, role="team_manager")
    assert disabled.role is None

    enabled = GateMobileConsoleUpdateRequest(enabled=True, role="team_manager")
    assert enabled.role == "team_manager"

    try:
        GateMobileConsoleUpdateRequest(enabled=True, role=None)
    except ValueError as exc:
        assert "role is required" in str(exc)
    else:
        raise AssertionError("Expected role validation error")


def test_enable_gate_mobile_console_for_giornaliere_workers_covers_selection_and_validation() -> None:
    db = _build_session()
    try:
        operator_id = uuid.UUID("018f88a2-1797-7365-bf5e-8bb8b7f9c0aa")
        _seed_operator(db, operator_id=operator_id)
        collaborator_id = uuid.UUID("018f88a2-1797-7365-bf5e-8bb8b7f9e101")
        collaborator = PresenzeCollaborator(
            id=collaborator_id,
            employee_code="EN001",
            company_code="53",
            name="Mario Rossi",
            contract_kind="operaio",
            application_user_id=42,
        )
        records = [
            PresenzeDailyRecord(collaborator_id=collaborator_id, work_date=date(2026, 7, 10)),
            PresenzeDailyRecord(collaborator_id=collaborator_id, work_date=date(2026, 7, 11)),
        ]
        db.add(collaborator)
        db.add_all(records)
        db.commit()

        try:
            gate_mobile_sync_service.enable_gate_mobile_console_for_giornaliere_workers(db, limit=0)
        except ValueError as exc:
            assert "limit must be greater" in str(exc)
        else:
            raise AssertionError("Expected limit validation error")

        dry_run = gate_mobile_sync_service.enable_gate_mobile_console_for_giornaliere_workers(
            db,
            limit=None,
            role="team_manager",
            dry_run=True,
        )
        assert dry_run.candidates_total == 1
        assert dry_run.enabled_total == 1
        assert dry_run.items[0].operator_id == operator_id
        assert dry_run.items[0].previous_role is None
        assert db.get(WCOperator, operator_id).gate_mobile_console_enabled is False

        applied = gate_mobile_sync_service.enable_gate_mobile_console_for_giornaliere_workers(
            db,
            role="team_manager",
            dry_run=False,
        )
        assert applied.enabled_total == 1
        updated = db.get(WCOperator, operator_id)
        assert updated.gate_mobile_console_enabled is True
        assert updated.gate_mobile_console_role == "team_manager"
    finally:
        db.close()


def test_build_mobile_catalog_and_workset_payloads_serialize_route_responses() -> None:
    db = _build_session()
    original_catalogs = gate_mobile_sync_service.get_mobile_catalogs
    original_worksets = gate_mobile_sync_service.get_mobile_worksets
    gate_mobile_sync_service.get_mobile_catalogs = lambda _db: _FakeCatalogResponse()
    gate_mobile_sync_service.get_mobile_worksets = lambda _db, operator_id=None: _FakeWorksetResponse()
    try:
        catalogs = build_mobile_catalog_push_payloads(db)
        worksets = build_mobile_workset_push_payloads(db)

        assert catalogs == [
            {
                "catalog_type": "meters",
                "version": "v1",
                "synced_from_gaia_at": "2026-06-15T10:00:00Z",
                "payload": {"items": []},
            }
        ]
        assert worksets[0]["workset_type"] == "assigned_meters"
        assert worksets[0]["items"][0]["gaia_entity_id"] == "meter-1"
    finally:
        gate_mobile_sync_service.get_mobile_catalogs = original_catalogs
        gate_mobile_sync_service.get_mobile_worksets = original_worksets
        db.close()


def test_build_presenze_teams_push_payload_serializes_teams_memberships_and_supervisors() -> None:
    db = _build_session()
    try:
        _seed_presenze_team(db)

        payload = build_presenze_teams_push_payload(
            db,
            now=datetime(2026, 7, 9, 9, 30, tzinfo=UTC),
        )

        assert payload["source"] == "gaia"
        assert payload["rules_version"] == "presenze-2026-07-extra-3h"
        assert payload["synced_from_gaia_at"] == "2026-07-09T09:30:00Z"
        assert payload["teams"][0]["name"] == "Squadra Presenze Nord"
        assert payload["teams"][0]["personnel_area"] == "AGRARIO"
        assert "scope" not in payload["teams"][0]
        assert payload["teams"][0]["created_from_channel"] == "gaia"
        assert payload["teams"][0]["audit"] == {}
        assert payload["teams"][0]["memberships"][0]["collaborator_name"] == "OPERATORE PRESENZE"
        assert payload["teams"][0]["memberships"][0]["gaia_user_id"] == "77"
        assert payload["teams"][0]["memberships"][0]["source_channel"] == "gaia"
        assert payload["teams"][0]["supervisors"][0]["username"] == "presenze.supervisor"
        assert payload["teams"][0]["supervisors"][0]["gaia_user_id"] == "77"
        assert payload["teams"][0]["supervisors"][0]["collaborator_id"] == "018f88a2-1797-7365-bf5e-8bb8b7f9d001"
        assert payload["teams"][0]["supervisors"][0]["employee_code"] == "P001"
        assert payload["teams"][0]["supervisors"][0]["collaborator_name"] == "OPERATORE PRESENZE"
        assert payload["teams"][0]["supervisors"][0]["permission_scope"] == "validate"
        assert gate_mobile_payloads.gate_channel("gate_mobile") == "gate"
        assert gate_mobile_payloads.gate_channel("gate") == "gate"
        assert gate_mobile_payloads.gate_channel("custom") == "custom"
        assert gate_mobile_payloads.gate_channel(None) == "gaia"

        collaborator = db.get(PresenzeCollaborator, uuid.UUID("018f88a2-1797-7365-bf5e-8bb8b7f9d001"))
        assert collaborator is not None
        collaborator.application_user_id = None
        db.commit()
        unmapped_payload = build_presenze_teams_push_payload(db)
        assert unmapped_payload["teams"][0]["memberships"] == []
        assert unmapped_payload["teams"][0]["supervisors"][0]["gaia_user_id"] == "77"
        assert unmapped_payload["teams"][0]["supervisors"][0]["collaborator_id"] is None
    finally:
        db.close()


def test_operator_and_membership_payloads_fail_closed_on_ambiguous_or_incoherent_identity() -> None:
    db = _build_session()
    try:
        _seed_operator(db)
        db.add(
            WCOperator(
                id=uuid.UUID("18f82137-e156-4790-b248-c0bf171389a1"),
                wc_id=1042,
                email="duplicate@example.test",
                enabled=True,
                personnel_area="AGRARIO",
                gaia_user_id=42,
            )
        )
        db.commit()
        assert build_mobile_operator_push_payload(db)["operators"] == []

        _seed_presenze_team(db)
        membership = db.scalar(select(OrganizationTeamMembership))
        collaborator = db.scalar(select(PresenzeCollaborator))
        assert membership is not None
        assert collaborator is not None
        membership.application_user_id = 77
        collaborator.application_user_id = None
        member_operator = WCOperator(
            id=uuid.UUID("18f82137-e156-4790-b248-c0bf171389a2"),
            wc_id=1077,
            first_name=" Directory ",
            last_name=" Member ",
            enabled=True,
            personnel_area="AGRARIO",
            gaia_user_id=77,
        )
        db.add(member_operator)
        db.commit()

        canonical = build_presenze_teams_push_payload(db)["teams"][0]["memberships"]
        assert canonical[0]["collaborator_id"] == str(member_operator.id)
        assert canonical[0]["collaborator_name"] == "Directory Member"
        assert canonical[0]["presenze_collaborator_id"] is None

        duplicate_operator = WCOperator(
            id=uuid.UUID("18f82137-e156-4790-b248-c0bf171389a3"),
            wc_id=2077,
            enabled=True,
            personnel_area="AGRARIO",
            gaia_user_id=77,
        )
        db.add(duplicate_operator)
        db.commit()
        assert build_presenze_teams_push_payload(db)["teams"][0]["memberships"] == []

        db.delete(duplicate_operator)
        collaborator.application_user_id = 77
        membership.application_user_id = 78
        db.add(
            ApplicationUser(
                id=78,
                username="incoherent.member",
                email="incoherent.member@example.test",
                password_hash="hash",
                role=ApplicationUserRole.OPERATOR.value,
                is_active=True,
            )
        )
        db.commit()
        assert build_presenze_teams_push_payload(db)["teams"][0]["memberships"] == []

        collaborator.application_user_id = None
        membership.application_user_id = 999
        db.commit()
        assert build_presenze_teams_push_payload(db)["teams"][0]["memberships"] == []
    finally:
        db.close()


def test_build_presenze_rules_months_giornaliere_and_anomalie_payloads(monkeypatch) -> None:
    db = _build_session()
    try:
        daily_record_id = _seed_presenze_daily_record(db)
        rules_payload = build_presenze_rules_push_payload(now=datetime(2026, 7, 10, 8, 0, tzinfo=UTC))
        months_payload = build_presenze_months_push_payload(db, now=datetime(2026, 7, 10, 8, 0, tzinfo=UTC))
        giornaliere_payload = build_presenze_giornaliere_push_payload(
            db,
            month="2026-07",
            now=datetime(2026, 7, 10, 8, 0, tzinfo=UTC),
        )
        anomalie_payload = build_presenze_anomalie_push_payload(
            db,
            month="2026-07",
            now=datetime(2026, 7, 10, 8, 0, tzinfo=UTC),
        )

        assert rules_payload["schema_version"] == 1
        assert rules_payload["export_rules_version"] == "presenze-xlsm-2026-08"
        assert rules_payload["rules"]["rules_version"] == "presenze-2026-07-extra-3h"
        assert months_payload["months"] == [{"month": "2026-07", "records_total": 1}]
        assert months_payload["inaz_sync"]["status"] == "never"
        assert giornaliere_payload["records"][0]["record_id"] == str(daily_record_id)
        assert giornaliere_payload["records"][0]["gaia_user_id"] == "77"
        assert giornaliere_payload["records"][0]["has_complete_punches"] is True
        assert giornaliere_payload["export_rules_version"] == "presenze-xlsm-2026-08"
        assert giornaliere_payload["records"][0]["km_value"] == 24
        assert giornaliere_payload["records"][0]["trasferta_minutes"] == 180
        assert giornaliere_payload["records"][0]["trasferta_montano"] is False
        assert giornaliere_payload["records"][0]["reperibilita_unit"] == "shifts"
        assert giornaliere_payload["records"][0]["reperibilita_quantity"] == 1
        assert giornaliere_payload["records"][0]["justified_minutes"] == 60
        assert giornaliere_payload["records"][0]["export_absence_code"] == "P"
        assert giornaliere_payload["records"][0]["export_special_day"] is False
        assert giornaliere_payload["records"][0]["export_ordinary_minutes"] == 420
        assert giornaliere_payload["records"][0]["export_extra_minutes"] == 240
        assert giornaliere_payload["giornaliere"] == giornaliere_payload["records"]
        assert giornaliere_payload["inaz_sync"]["status"] == "never"
        assert anomalie_payload["anomalies"][0]["reasons"] == ["extra_over_3h"]
        assert anomalie_payload["anomalies"][0]["gaia_user_id"] == "77"
        assert anomalie_payload["anomalie"] == anomalie_payload["anomalies"]
        assert anomalie_payload["inaz_sync"]["status"] == "never"

        db.get(PresenzeDailyRecord, daily_record_id).validation_status = "validated"
        db.commit()
        clean_payload = build_presenze_anomalie_push_payload(db, month="2026-07")
        assert clean_payload["anomalies"] == []
        assert clean_payload["anomalie"] == []

        record = db.get(PresenzeDailyRecord, daily_record_id)
        assert record is not None
        record.application_user_id = None
        db.commit()
        unmapped_payload = build_presenze_giornaliere_push_payload(db, month="2026-07")
        assert unmapped_payload["records"][0]["gaia_user_id"] == "77"

        record.application_user_id = 999
        db.commit()
        inconsistent_payload = build_presenze_giornaliere_push_payload(db, month="2026-07")
        assert inconsistent_payload["records"][0]["gaia_user_id"] is None

        collaborator = db.get(PresenzeCollaborator, record.collaborator_id)
        assert collaborator is not None
        collaborator.application_user_id = None
        record.application_user_id = None
        db.commit()
        missing_relation_payload = build_presenze_giornaliere_push_payload(db, month="2026-07")
        assert missing_relation_payload["records"][0]["gaia_user_id"] is None
    finally:
        db.close()


def test_presenze_snapshot_payloads_handle_empty_and_missing_analysis(monkeypatch) -> None:
    db = _build_session()
    try:
        empty_payload = build_presenze_giornaliere_push_payload(db, month="2026-08")
        assert empty_payload["records"] == []
        assert gate_mobile_sync_service._presenze_punches_by_record_id(db, []) == {}

        monkeypatch.setattr(
            gate_mobile_sync_service,
            "_presenze_mobile_record_items_for_month",
            lambda _db, *, month: ([{"record_id": "missing-analysis"}], {}),
        )
        anomalie_payload = build_presenze_anomalie_push_payload(db, month="2026-07")
        assert anomalie_payload["anomalies"] == []
        assert anomalie_payload["anomalie"] == []
    finally:
        db.close()


def test_build_mobile_operator_push_payload_uses_display_name_fallbacks() -> None:
    operator_id = uuid.UUID("018f88a2-1797-7365-bf5e-8bb8b7f9c104")
    operator = WCOperator(id=operator_id, wc_id=2004, first_name=None, last_name=None, username=None)

    operator.first_name = " Mario "
    operator.last_name = " Rossi "
    assert gate_mobile_sync_service._operator_display_name(operator, ApplicationUser(username="ignored")) == "Mario Rossi"

    operator.first_name = None
    operator.last_name = None
    assert gate_mobile_sync_service._operator_display_name(operator, ApplicationUser(full_name=" Nome Completo ")) == "Nome Completo"
    assert gate_mobile_sync_service._operator_display_name(operator, ApplicationUser(username="username_user")) == "username_user"

    operator.username = "wc_username"
    assert gate_mobile_sync_service._operator_display_name(operator, ApplicationUser(username="")) == "wc_username"

    operator.username = None
    assert gate_mobile_sync_service._operator_display_name(operator, ApplicationUser(username="")) == str(operator_id)


def test_operator_field_helpers_handle_absent_optional_relations_and_pages() -> None:
    db = _build_session()
    try:
        operator = WCOperator(id=uuid.uuid4(), wc_id=2005)

        gate_mobile_sync_service._apply_operator_identity_fields(
            db,
            operator,
            None,
            None,
            {"status": "DISABLED"},
        )
        gate_mobile_sync_service._apply_operator_console_fields(operator, {})

        assert operator.enabled is False
        assert operator.gate_mobile_console_role is None
        assert operator.gate_mobile_console_pages is None
    finally:
        db.close()


def test_run_gate_mobile_sync_once_requests_plan_then_pushes_operators() -> None:
    db = _build_session()
    try:
        _seed_operator(db)
        calls: list[httpx.Request] = []
        original_catalog_builder = gate_mobile_sync_service.build_mobile_catalog_push_payloads
        original_workset_builder = gate_mobile_sync_service.build_mobile_workset_push_payloads
        gate_mobile_sync_service.build_mobile_catalog_push_payloads = lambda _db: [
            {
                "catalog_type": "meters",
                "version": "v1",
                "synced_from_gaia_at": "2026-06-15T10:00:00Z",
                "payload": {"items": []},
            }
        ]
        gate_mobile_sync_service.build_mobile_workset_push_payloads = lambda _db: [
            {
                "operator_id": "018f88a2-1797-7365-bf5e-8bb8b7f9c0aa",
                "workset_type": "assigned_meters",
                "synced_from_gaia_at": "2026-06-15T10:00:00Z",
                "items": [],
            }
        ]

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            if request.url.path == "/api/mobile/connector/sync/plan":
                assert request.headers["authorization"] == "Bearer gate-token"
                return httpx.Response(
                    200,
                    json={
                        "plan": {
                            "generated_at": "2026-06-15T10:00:00Z",
                            "tasks": [{"type": "operators", "mode": "full"}],
                        }
                    },
                )
            if request.url.path == "/api/mobile/connector/operators/push":
                body = request.read().decode()
                assert "mario.rossi@example.test" in body
                assert "\"gaia_username\":\"mrossi\"" in body
                return httpx.Response(200, json={"operators": {"count": 1}})
            if request.url.path == "/api/mobile/connector/catalogs/push":
                body = request.read().decode()
                assert "meters" in body
                return httpx.Response(200, json={"catalog": {"catalog_type": "meters"}})
            if request.url.path == "/api/mobile/connector/worksets/push":
                body = request.read().decode()
                assert "assigned_meters" in body
                return httpx.Response(200, json={"workset": {"count": 0}})
            return httpx.Response(404)

        settings = Settings(
            _env_file=None,
            DATABASE_URL="sqlite:///./gate-mobile-sync-test.db",
            JWT_SECRET_KEY="test-secret",
            GATE_MOBILE_GATEWAY_BASE_URL="https://gateway.example.test",
            GATE_MOBILE_CONNECTOR_TOKEN="gate-token",
        )

        async def run() -> None:
            transport = httpx.MockTransport(handler)
            async with httpx.AsyncClient(transport=transport, base_url=settings.gate_mobile_gateway_base_url) as client:
                report = await run_gate_mobile_sync_once(db, app_settings=settings, client=client)
            assert report.catalogs_pushed == 1
            assert report.operators_pushed == 1
            assert report.worksets_pushed == 1

        try:
            asyncio.run(run())
        finally:
            gate_mobile_sync_service.build_mobile_catalog_push_payloads = original_catalog_builder
            gate_mobile_sync_service.build_mobile_workset_push_payloads = original_workset_builder

        assert [call.url.path for call in calls] == [
            "/api/mobile/connector/sync/plan",
            "/api/mobile/connector/catalogs/push",
            "/api/mobile/connector/operators/push",
            "/api/mobile/connector/worksets/push",
        ]
    finally:
        db.close()


def test_run_gate_mobile_sync_once_pushes_presenze_teams_when_gateway_requests_them() -> None:
    db = _build_session()
    try:
        _seed_presenze_team(db)
        original_catalog_builder = gate_mobile_sync_service.build_mobile_catalog_push_payloads
        original_workset_builder = gate_mobile_sync_service.build_mobile_workset_push_payloads
        gate_mobile_sync_service.build_mobile_catalog_push_payloads = lambda _db: []
        gate_mobile_sync_service.build_mobile_workset_push_payloads = lambda _db: []
        calls: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request.url.path)
            if request.url.path == "/api/mobile/connector/sync/plan":
                body = request.read().decode()
                assert "presenze_teams" in body
                return httpx.Response(
                    200,
                    json={
                        "plan": {
                            "generated_at": "2026-07-09T09:30:00Z",
                            "tasks": [{"type": "presenze_teams", "mode": "full"}],
                        }
                    },
                )
            if request.url.path == "/api/mobile/connector/presenze/teams/snapshot":
                body = request.read().decode()
                assert "Squadra Presenze Nord" in body
                assert "OPERATORE PRESENZE" in body
                return httpx.Response(200, json={"teams": {"count": 1}})
            return httpx.Response(404)

        settings = Settings(
            _env_file=None,
            DATABASE_URL="sqlite:///./gate-mobile-sync-test.db",
            JWT_SECRET_KEY="test-secret",
            GATE_MOBILE_GATEWAY_BASE_URL="https://gateway.example.test",
            GATE_MOBILE_CONNECTOR_TOKEN="gate-token",
        )

        async def run() -> None:
            transport = httpx.MockTransport(handler)
            async with httpx.AsyncClient(transport=transport, base_url=settings.gate_mobile_gateway_base_url) as client:
                report = await run_gate_mobile_sync_once(db, app_settings=settings, client=client)
            assert report.presenze_teams_pushed == 1

        try:
            asyncio.run(run())
        finally:
            gate_mobile_sync_service.build_mobile_catalog_push_payloads = original_catalog_builder
            gate_mobile_sync_service.build_mobile_workset_push_payloads = original_workset_builder

        assert calls == [
            "/api/mobile/connector/sync/plan",
            "/api/mobile/connector/presenze/teams/snapshot",
        ]
    finally:
        db.close()


def test_run_gate_mobile_sync_once_pushes_presenze_snapshots_and_processes_pending_actions(monkeypatch) -> None:
    db = _build_session()
    try:
        daily_record_id = _seed_presenze_daily_record(db)
        monkeypatch.setattr(gate_mobile_sync_service, "build_mobile_catalog_push_payloads", lambda _db: [])
        monkeypatch.setattr(gate_mobile_sync_service, "build_mobile_workset_push_payloads", lambda _db: [])
        monkeypatch.setattr(gate_mobile_sync_service, "build_presenze_rules_push_payload", lambda: {"rules": {}, "rules_version": "2026.07"})
        monkeypatch.setattr(gate_mobile_sync_service, "build_presenze_months_push_payload", lambda _db: {"months": [{"month": "2026-07"}]})
        monkeypatch.setattr(
            gate_mobile_sync_service,
            "build_presenze_giornaliere_push_payload",
            lambda _db, month: {"month": month, "records": [{"record_id": str(daily_record_id)}]},
        )
        monkeypatch.setattr(
            gate_mobile_sync_service,
            "build_presenze_anomalie_push_payload",
            lambda _db, month: {"month": month, "anomalies": [{"record_id": str(daily_record_id)}]},
        )
        calls: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request.url.path)
            if request.url.path == "/api/mobile/connector/sync/plan":
                body = request.read().decode()
                assert "presenze_rules" in body
                return httpx.Response(
                    200,
                    json={
                        "plan": {
                            "tasks": [
                                {"type": "presenze_rules"},
                                {"type": "presenze_months"},
                                {"type": "presenze_giornaliere", "months": ["2026-07"]},
                                {"type": "presenze_anomalie", "month": "2026-07"},
                                {"type": "presenze_pending_actions"},
                            ]
                        }
                    },
                )
            if request.url.path == "/api/mobile/connector/presenze/rules/snapshot":
                return httpx.Response(200, json={"ok": True})
            if request.url.path == "/api/mobile/connector/presenze/months/snapshot":
                return httpx.Response(200, json={"ok": True})
            if request.url.path == "/api/mobile/connector/presenze/giornaliere/snapshot":
                return httpx.Response(200, json={"records": {"count": 1}})
            if request.url.path == "/api/mobile/connector/presenze/anomalie/snapshot":
                return httpx.Response(200, json={"anomalies": {"count": 1}})
            if request.url.path == "/api/mobile/connector/presenze/pending-actions":
                return httpx.Response(
                    200,
                    json={
                        "actions": [
                            {
                                "id": "pending-1",
                                "type": "validate_daily_record",
                                "payload": {
                                    "record_id": str(daily_record_id),
                                    "gaia_user_id": 77,
                                    "validation_status": "validated",
                                    "operator_note": "ok",
                                    "client_request_id": "client-1",
                                },
                            }
                        ]
                    },
                )
            if request.url.path == "/api/mobile/connector/presenze/pending-actions/pending-1/ack":
                body = request.read().decode()
                assert "presenze_daily_record" in body
                return httpx.Response(200, json={"ok": True})
            return httpx.Response(404)

        settings = Settings(
            _env_file=None,
            DATABASE_URL="sqlite:///./gate-mobile-sync-test.db",
            JWT_SECRET_KEY="test-secret",
            GATE_MOBILE_GATEWAY_BASE_URL="https://gateway.example.test",
            GATE_MOBILE_CONNECTOR_TOKEN="gate-token",
        )

        async def run() -> None:
            transport = httpx.MockTransport(handler)
            async with httpx.AsyncClient(transport=transport, base_url=settings.gate_mobile_gateway_base_url) as client:
                report = await run_gate_mobile_sync_once(db, app_settings=settings, client=client)
            assert report.presenze_rules_pushed == 1
            assert report.presenze_months_pushed == 1
            assert report.presenze_giornaliere_pushed == 1
            assert report.presenze_anomalie_pushed == 1
            assert report.presenze_pending_actions_acknowledged == 1
            assert report.presenze_pending_actions_failed == 0

        asyncio.run(run())

        assert "/api/mobile/connector/presenze/rules/snapshot" in calls
        assert "/api/mobile/connector/presenze/pending-actions/pending-1/ack" in calls
        assert db.get(PresenzeDailyRecord, daily_record_id).validation_status == "validated"
    finally:
        db.close()


def test_run_gate_mobile_sync_once_falls_back_when_gateway_plan_accepts_only_legacy_capabilities(monkeypatch) -> None:
    db = _build_session()
    try:
        daily_record_id = _seed_presenze_daily_record(db)
        monkeypatch.setattr(gate_mobile_sync_service, "build_mobile_catalog_push_payloads", lambda _db: [])
        monkeypatch.setattr(gate_mobile_sync_service, "build_mobile_workset_push_payloads", lambda _db: [])
        monkeypatch.setattr(gate_mobile_sync_service, "build_presenze_rules_push_payload", lambda: {"rules": {}, "rules_version": "2026.07"})
        monkeypatch.setattr(gate_mobile_sync_service, "build_presenze_months_push_payload", lambda _db: {"months": [{"month": "2026-07"}]})
        monkeypatch.setattr(
            gate_mobile_sync_service,
            "build_presenze_giornaliere_push_payload",
            lambda _db, month: {"month": month, "records": [{"record_id": str(daily_record_id)}]},
        )
        monkeypatch.setattr(
            gate_mobile_sync_service,
            "build_presenze_anomalie_push_payload",
            lambda _db, month: {"month": month, "anomalies": []},
        )
        calls: list[str] = []
        plan_attempts = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal plan_attempts
            calls.append(request.url.path)
            if request.url.path == "/api/mobile/connector/sync/plan":
                plan_attempts += 1
                body = request.read().decode()
                if "presenze_giornaliere" in body:
                    return httpx.Response(400, request=request, json={"error": {"code": "VALIDATION_ERROR"}})
                return httpx.Response(200, request=request, json={"plan": {"tasks": [{"type": "presenze_teams"}]}})
            if request.url.path == "/api/mobile/connector/presenze/teams/snapshot":
                return httpx.Response(200, request=request, json={"teams": {"count": 1}})
            if request.url.path == "/api/mobile/connector/presenze/rules/snapshot":
                return httpx.Response(200, request=request, json={"ok": True})
            if request.url.path == "/api/mobile/connector/presenze/months/snapshot":
                return httpx.Response(200, request=request, json={"ok": True})
            if request.url.path == "/api/mobile/connector/presenze/giornaliere/snapshot":
                return httpx.Response(200, request=request, json={"records": {"count": 1}})
            if request.url.path == "/api/mobile/connector/presenze/anomalie/snapshot":
                return httpx.Response(200, request=request, json={"anomalies": {"count": 0}})
            if request.url.path == "/api/mobile/connector/presenze/pending-actions":
                return httpx.Response(200, request=request, json={"actions": []})
            return httpx.Response(404, request=request)

        settings = Settings(
            _env_file=None,
            DATABASE_URL="sqlite:///./gate-mobile-sync-test.db",
            JWT_SECRET_KEY="test-secret",
            GATE_MOBILE_GATEWAY_BASE_URL="https://gateway.example.test",
            GATE_MOBILE_CONNECTOR_TOKEN="gate-token",
        )

        async def run() -> None:
            transport = httpx.MockTransport(handler)
            async with httpx.AsyncClient(transport=transport, base_url=settings.gate_mobile_gateway_base_url) as client:
                report = await run_gate_mobile_sync_once(db, app_settings=settings, client=client)
            assert report.presenze_teams_pushed == 1
            assert report.presenze_rules_pushed == 1
            assert report.presenze_months_pushed == 1
            assert report.presenze_giornaliere_pushed >= 1

        asyncio.run(run())

        assert plan_attempts == 2
        assert "/api/mobile/connector/presenze/giornaliere/snapshot" in calls
    finally:
        db.close()


def test_process_presenze_pending_actions_acks_and_fails_gateway_actions() -> None:
    db = _build_session()
    try:
        daily_record_id = _seed_presenze_daily_record(db)
        calls: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request.url.path)
            if request.url.path == "/api/mobile/connector/presenze/pending-actions":
                return httpx.Response(
                    200,
                    json=[
                        {
                            "pending_action_id": "pending-ok",
                            "action_type": "patch_daily_record",
                            "record_id": str(daily_record_id),
                            "actor": {"gaia_user_id": 77},
                            "km_value": 12,
                            "operator_note": "km",
                        },
                        {
                            "pending_action_id": "pending-fail",
                            "action_type": "propose_team_change",
                            "gaia_user_id": 77,
                        },
                    ],
                )
            if request.url.path == "/api/mobile/connector/presenze/pending-actions/pending-ok/ack":
                return httpx.Response(200, json={"ok": True})
            if request.url.path == "/api/mobile/connector/presenze/pending-actions/pending-fail/fail":
                body = request.read().decode()
                assert "propose_team_change" in body
                return httpx.Response(200, json={"ok": True})
            return httpx.Response(404)

        async def run() -> None:
            transport = httpx.MockTransport(handler)
            async with httpx.AsyncClient(transport=transport, base_url="https://gateway.example.test") as client:
                result = await process_presenze_pending_actions(db, client=client, headers={"Authorization": "Bearer token"})
            assert result == {"acknowledged": 1, "failed": 1}

        asyncio.run(run())

        assert "/api/mobile/connector/presenze/pending-actions/pending-ok/ack" in calls
        assert db.get(PresenzeDailyRecord, daily_record_id).km_value == 12
    finally:
        db.close()


def test_presenze_team_pending_actions_are_canonical_idempotent_and_reconciliable() -> None:
    db = _build_session()
    try:
        actor = ApplicationUser(
            id=177,
            username="gate.team.manager",
            email="gate.team.manager@example.test",
            password_hash="hash",
            role=ApplicationUserRole.REVIEWER.value,
            is_active=True,
            module_presenze=False,
        )
        member = ApplicationUser(
            id=238,
            username="canonical.member",
            email="canonical.member@example.test",
            password_hash="hash",
            role=ApplicationUserRole.OPERATOR.value,
            is_active=True,
        )
        supervisor = ApplicationUser(
            id=181,
            username="canonical.supervisor",
            email="canonical.supervisor@example.test",
            password_hash="hash",
            role=ApplicationUserRole.REVIEWER.value,
            is_active=True,
            module_presenze=True,
        )
        collaborator = PresenzeCollaborator(
            id=uuid.UUID("13126cf8-32b6-4206-9910-58374f125681"),
            employee_code="1423",
            name="Canonical Member",
            application_user_id=member.id,
        )
        member_operator_id = uuid.UUID("18f82137-e156-4790-b248-c0bf171389bc")
        member_operator = WCOperator(
            id=member_operator_id,
            wc_id=1238,
            first_name="Canonical",
            last_name="Member",
            enabled=True,
            personnel_area="IMPIANTI",
            gaia_user_id=member.id,
        )
        db.add_all([actor, member, supervisor, collaborator, member_operator])
        db.commit()

        legacy_team_id = "gate-team-manutenzione-nord-1-1787898841204"
        team_payload = {
            "team_id": legacy_team_id,
            "name": "Reparto Nord",
            "code": "MANUTENZIONE-NORD-1",
            "personnel_area": "IMPIANTI",
            "active": True,
        }
        create_action = {
            "pending_action_id": "team-create",
            "action_type": "propose_team_create",
            "payload_json": {
                "operation": "create_team",
                "gaia_user_id": str(actor.id),
                "team": team_payload,
            },
        }
        create_ack = gate_mobile_sync_service._apply_presenze_pending_action(db, create_action)
        team_id = uuid.UUID(create_ack["gaia_entity_id"])
        created = db.get(OrganizationTeam, team_id)
        assert created is not None
        assert created.personnel_area == "IMPIANTI"
        assert created.gate_mobile_team_id == legacy_team_id
        assert created.created_by_user_id == actor.id

        membership_action = {
            "action_type": "propose_team_membership",
            "payload_json": {
                "operation": "update_team_memberships",
                "gaia_user_id": str(actor.id),
                "team": team_payload,
                "requested_memberships": [
                    {
                        "gaia_user_id": str(member.id),
                        "collaborator_id": "238",
                        "employee_code": "238",
                        "role": "member",
                    }
                ],
            },
        }
        supervisor_action = {
            "action_type": "propose_team_supervisor",
            "payload_json": {
                "operation": "update_team_supervisors",
                "gaia_user_id": str(actor.id),
                "team": team_payload,
                "requested_supervisors": [
                    {
                        "gaia_user_id": str(supervisor.id),
                        "application_user_id": "wrong-namespace",
                        "permission_scope": "team",
                    }
                ],
            },
        }
        gate_mobile_sync_service._apply_presenze_pending_action(db, membership_action)
        gate_mobile_sync_service._apply_presenze_pending_action(db, supervisor_action)
        membership = db.scalar(select(OrganizationTeamMembership).where(OrganizationTeamMembership.team_id == team_id))
        assignment = db.scalar(
            select(OrganizationTeamSupervisorAssignment).where(
                OrganizationTeamSupervisorAssignment.team_id == team_id
            )
        )
        assert membership is not None
        assert membership.application_user_id == member.id
        assert membership.collaborator_id == collaborator.id
        assert assignment is not None
        assert assignment.application_user_id == supervisor.id
        membership_id = membership.id
        assignment_id = assignment.id

        db.add(
            OrganizationTeamMembership(
                team_id=team_id,
                collaborator_id=collaborator.id,
                role="duplicate",
            )
        )
        db.commit()

        gate_mobile_sync_service._apply_presenze_pending_action(db, create_action)
        gate_mobile_sync_service._apply_presenze_pending_action(db, membership_action)
        gate_mobile_sync_service._apply_presenze_pending_action(db, supervisor_action)
        memberships = list(
            db.scalars(
                select(OrganizationTeamMembership).where(OrganizationTeamMembership.team_id == team_id)
            )
        )
        assert len(memberships) == 1
        assert memberships[0].id == membership_id
        assert db.scalar(
            select(OrganizationTeamSupervisorAssignment).where(
                OrganizationTeamSupervisorAssignment.team_id == team_id
            )
        ).id == assignment_id

        renamed_payload = dict(team_payload, name="Reparto Nord Definitivo", previous_code=team_payload["code"])
        gate_mobile_sync_service._apply_presenze_pending_action(
            db,
            {
                "action_type": "propose_team_change",
                "payload_json": {
                    "operation": "rename_team",
                    "gaia_user_id": str(actor.id),
                    "team": renamed_payload,
                },
            },
        )
        assert db.get(OrganizationTeam, team_id).name == "Reparto Nord Definitivo"
        snapshot = gate_mobile_sync_service.build_presenze_teams_push_payload(db)
        assert snapshot["teams"][0]["team_id"] == legacy_team_id
        assert snapshot["teams"][0]["memberships"] == [
            {
                "membership_id": str(membership_id),
                "collaborator_id": str(member_operator_id),
                "gaia_user_id": str(member.id),
                "employee_code": "1423",
                "presenze_collaborator_id": str(collaborator.id),
                "presenze_employee_code": "1423",
                "collaborator_name": "Canonical Member",
                "role": "member",
                "valid_from": None,
                "valid_to": None,
                "source_channel": "gate",
                "updated_at": snapshot["teams"][0]["memberships"][0]["updated_at"],
            }
        ]
    finally:
        db.close()


def test_presenze_team_pending_actions_fail_closed_on_noncanonical_identity(monkeypatch) -> None:
    db = _build_session()
    try:
        actor = ApplicationUser(
            id=178,
            username="gate.team.validator",
            email="gate.team.validator@example.test",
            password_hash="hash",
            role=ApplicationUserRole.REVIEWER.value,
            is_active=True,
            module_presenze=True,
        )
        unmapped = ApplicationUser(
            id=179,
            username="unmapped.member",
            email="unmapped.member@example.test",
            password_hash="hash",
            role=ApplicationUserRole.OPERATOR.value,
            is_active=True,
        )
        team = OrganizationTeam(
            id=uuid.UUID("018f88a2-1797-7365-bf5e-8bb8b7f9a201"),
            name="Squadra Esistente",
            code="EXIST",
            scope="presenze",
            personnel_area="AGRARIO",
            active=True,
            created_from_channel="gaia_web",
            created_by_user_id=actor.id,
        )
        db.add_all([actor, unmapped, team])
        db.commit()
        team_ref = {"team_id": str(team.id), "code": team.code, "personnel_area": "AGRARIO"}
        cases = [
            ({"operation": "create_team", "team": {"name": "Missing area"}}, "personnel_area"),
            ({"operation": "delete_team", "team": team_ref}, "operation"),
            ({"operation": "create_team", "team": []}, "team mancante"),
            (
                {
                    "operation": "update_team_memberships",
                    "team": team_ref,
                    "requested_memberships": [{"collaborator_id": str(uuid.uuid4())}],
                },
                "gaia_user_id",
            ),
            (
                {
                    "operation": "update_team_supervisors",
                    "team": team_ref,
                    "requested_supervisors": [{"gaia_user_id": "999999"}],
                },
                "non trovato",
            ),
            (
                {
                    "operation": "update_team_supervisors",
                    "team": team_ref,
                    "requested_supervisors": "not-a-list",
                },
                "lista di oggetti",
            ),
            (
                {
                    "operation": "rename_team",
                    "team": dict(team_ref, personnel_area="IMPIANTI", name="Wrong area"),
                },
                "incoerente",
            ),
        ]
        action_types = [
            "propose_team_create",
            "propose_team_create",
            "propose_team_create",
            "propose_team_membership",
            "propose_team_supervisor",
            "propose_team_supervisor",
            "propose_team_change",
        ]
        for action_type, (payload, message) in zip(action_types, cases, strict=True):
            try:
                gate_mobile_team_actions.apply_presenze_team_proposal(
                    db,
                    payload,
                    actor=actor,
                    action_type=action_type,
                )
            except Exception as exc:
                assert message in str(exc)
                db.rollback()
            else:
                raise AssertionError(f"Expected validation error containing {message}")

        gate_mobile_team_actions.apply_presenze_team_proposal(
            db,
            {
                "operation": "update_team_memberships",
                "team": team_ref,
                "requested_memberships": [{"gaia_user_id": str(unmapped.id)}],
            },
            actor=actor,
            action_type="propose_team_membership",
        )
        membership = db.scalar(
            select(OrganizationTeamMembership).where(
                OrganizationTeamMembership.team_id == team.id
            )
        )
        assert membership is not None
        assert membership.application_user_id == unmapped.id
        assert membership.collaborator_id is None
        snapshot = gate_mobile_sync_service.build_presenze_teams_push_payload(db)
        assert snapshot["teams"][0]["memberships"][0]["gaia_user_id"] == str(unmapped.id)
        assert snapshot["teams"][0]["memberships"][0]["presenze_collaborator_id"] is None

        class AmbiguousCollaborators:
            @staticmethod
            def all() -> list[object]:
                return [object(), object()]

        monkeypatch.setattr(db, "scalars", lambda _statement: AmbiguousCollaborators())
        try:
            gate_mobile_team_actions._optional_canonical_collaborator(db, unmapped.id)
        except gate_mobile_team_actions.TeamChangeApplyError as exc:
            assert "non univoca" in str(exc)
        else:
            raise AssertionError("Expected ambiguous Presenze relation to fail closed")
    finally:
        db.close()


def test_presenze_team_action_replacement_and_validation_edges() -> None:
    db = _build_session()
    try:
        actor = ApplicationUser(
            id=301,
            username="team.edge.actor",
            email="team.edge.actor@example.test",
            password_hash="hash",
            role=ApplicationUserRole.REVIEWER.value,
            is_active=True,
            module_presenze=True,
        )
        person = ApplicationUser(
            id=302,
            username="team.edge.person",
            email="team.edge.person@example.test",
            password_hash="hash",
            role=ApplicationUserRole.OPERATOR.value,
            is_active=True,
        )
        collaborator = PresenzeCollaborator(
            id=uuid.uuid4(),
            employee_code="EDGE-302",
            name="Edge Person",
            application_user_id=person.id,
        )
        db.add_all([actor, person, collaborator])
        db.commit()

        created = gate_mobile_team_actions.apply_presenze_team_change_proposal(
            db,
            {
                "operation": "create_team",
                "team": {"name": "No Code Team", "personnel_area": "AGRARIO"},
            },
            actor=actor,
        ).team
        assert created.code is None
        assert created.active is True

        gate_mobile_team_actions.apply_presenze_team_change_proposal(
            db,
            {
                "operation": "update_team",
                "team": {"team_id": str(created.id), "personnel_area": "AGRARIO"},
            },
            actor=actor,
        )

        membership_payload = {
            "operation": "update_team_memberships",
            "team": {"team_id": str(created.id), "personnel_area": "AGRARIO"},
            "requested_memberships": [
                {"gaia_user_id": str(person.id)},
                {"gaia_user_id": str(person.id)},
            ],
        }
        supervisor_payload = {
            "operation": "update_team_supervisors",
            "team": {"team_id": str(created.id), "personnel_area": "AGRARIO"},
            "requested_supervisors": [
                {"gaia_user_id": str(person.id)},
                {"gaia_user_id": str(person.id)},
            ],
        }
        for action_type, payload, message in [
            ("unknown", {"operation": "none", "team": {}}, "non supportato"),
            ("propose_team_membership", membership_payload, "duplicato"),
            ("propose_team_supervisor", supervisor_payload, "duplicato"),
        ]:
            try:
                gate_mobile_team_actions.apply_presenze_team_proposal(
                    db,
                    payload,
                    actor=actor,
                    action_type=action_type,
                )
            except ValueError as exc:
                assert message in str(exc)
                db.rollback()
            else:
                raise AssertionError(f"Expected {message}")

        membership_payload["requested_memberships"] = [{"gaia_user_id": str(person.id)}]
        supervisor_payload["requested_supervisors"] = [{"gaia_user_id": str(person.id)}]
        gate_mobile_team_actions.apply_presenze_team_proposal(
            db,
            membership_payload,
            actor=actor,
            action_type="propose_team_membership",
        )
        gate_mobile_team_actions.apply_presenze_team_proposal(
            db,
            supervisor_payload,
            actor=actor,
            action_type="propose_team_supervisor",
        )
        membership_payload["requested_memberships"] = []
        supervisor_payload["requested_supervisors"] = []
        gate_mobile_team_actions.apply_presenze_team_proposal(
            db,
            membership_payload,
            actor=actor,
            action_type="propose_team_membership",
        )
        gate_mobile_team_actions.apply_presenze_team_proposal(
            db,
            supervisor_payload,
            actor=actor,
            action_type="propose_team_supervisor",
        )
        assert db.scalar(
            select(OrganizationTeamMembership).where(OrganizationTeamMembership.team_id == created.id)
        ) is None
        assert db.scalar(
            select(OrganizationTeamSupervisorAssignment).where(
                OrganizationTeamSupervisorAssignment.team_id == created.id
            )
        ) is None

        existing_a = OrganizationTeam(
            name="Existing A",
            code="AMB-A",
            scope="presenze",
            personnel_area="IMPIANTI",
        )
        existing_b = OrganizationTeam(
            name="Existing B",
            code="AMB-B",
            scope="gate",
            personnel_area="IMPIANTI",
        )
        target = OrganizationTeam(
            name="Target",
            code="TARGET",
            scope="presenze",
            personnel_area="IMPIANTI",
        )
        db.add_all([existing_a, existing_b, target])
        db.commit()
        validation_cases = [
            (
                "propose_team_change",
                {"operation": "rename_team", "team": {"team_id": "legacy", "code": "MISSING", "personnel_area": "AGRARIO"}},
                "non trovata",
            ),
            (
                "propose_team_membership",
                {
                    "operation": "update_team_memberships",
                    "team": {"team_id": str(uuid.uuid4()), "code": "MISSING", "personnel_area": "AGRARIO"},
                    "requested_memberships": [],
                },
                "non trovata",
            ),
            (
                "propose_team_change",
                {
                    "operation": "rename_team",
                    "team": {
                        "team_id": "legacy",
                        "previous_code": "AMB-A",
                        "code": "AMB-B",
                        "personnel_area": "IMPIANTI",
                    },
                },
                "non trovata",
            ),
            (
                "propose_team_change",
                {
                    "operation": "rename_team",
                    "team": {
                        "team_id": str(target.id),
                        "code": "AMB-A",
                        "name": "Conflict",
                        "personnel_area": "IMPIANTI",
                    },
                },
                "code gia assegnato",
            ),
            (
                "propose_team_create",
                {"operation": "create_team", "team": {"personnel_area": "AGRARIO"}},
                "name mancante",
            ),
            (
                "propose_team_create",
                {"operation": "create_team", "team": {"name": 123, "personnel_area": "AGRARIO"}},
                "stringa",
            ),
            (
                "propose_team_create",
                {"operation": "create_team", "team": {"name": " ", "personnel_area": "AGRARIO"}},
                "vuoto",
            ),
            (
                "propose_team_create",
                {"operation": "create_team", "team": {"name": "X" * 256, "personnel_area": "AGRARIO"}},
                "supera",
            ),
            (
                "propose_team_create",
                {"operation": "create_team", "team": {"name": "Bad flag", "personnel_area": "AGRARIO", "active": "yes"}},
                "booleano",
            ),
            (
                "propose_team_supervisor",
                {
                    "operation": "update_team_supervisors",
                    "team": {"team_id": str(created.id), "personnel_area": "AGRARIO"},
                    "requested_supervisors": [{"gaia_user_id": "not-an-id"}],
                },
                "gaia_user_id non valido",
            ),
            (
                "propose_team_supervisor",
                {
                    "operation": "update_team_supervisors",
                    "team": {"team_id": str(created.id), "personnel_area": "AGRARIO"},
                    "requested_supervisors": [{"gaia_user_id": "0"}],
                },
                "gaia_user_id non valido",
            ),
        ]
        for action_type, payload, message in validation_cases:
            try:
                gate_mobile_team_actions.apply_presenze_team_proposal(
                    db,
                    payload,
                    actor=actor,
                    action_type=action_type,
                )
            except ValueError as exc:
                assert message in str(exc)
                db.rollback()
            else:
                raise AssertionError(f"Expected {message}")
    finally:
        db.close()


def test_process_presenze_pending_actions_applies_operator_update_proposal() -> None:
    db = _build_session()
    try:
        operator_id = uuid.UUID("24c5b756-fee9-48cb-a18f-759534dea1f1")
        profile_id = uuid.UUID("018f88a2-1797-7365-bf5e-8bb8b7f9c0ac")
        user = ApplicationUser(
            id=151,
            username="andrea.old",
            email="andrea.old@example.test",
            full_name="Andrea Old",
            password_hash="hash",
            role=ApplicationUserRole.OPERATOR.value,
            is_active=True,
            module_operazioni=True,
            module_presenze=True,
        )
        operator = WCOperator(
            id=operator_id,
            wc_id=15101,
            username="andrea.old",
            email="andrea.old@example.test",
            first_name="Andrea",
            last_name="Old",
            enabled=True,
            gaia_user_id=151,
        )
        profile = OperatorProfile(id=profile_id, user_id=151, phone=None, is_active=True)
        db.add_all([user, operator, profile])
        db.commit()
        calls: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request.url.path)
            if request.url.path == "/api/mobile/connector/presenze/pending-actions":
                return httpx.Response(
                    200,
                    json={
                        "actions": [
                            {
                                "pending_action_id": "7ece2064-178e-4945-a22a-087d028ad8e2",
                                "action_type": "propose_operator_update",
                                "payload_json": {
                                    "schema_version": 1,
                                    "source": "gate_admin_console",
                                    "operation": "update_operator",
                                    "changed_fields": [
                                        "domains",
                                        "gate_mobile_console_enabled",
                                        "gate_mobile_console_role",
                                        "gate_mobile_console_pages",
                                    ],
                                    "password_changed": False,
                                    "operator": {
                                        "operator_id": str(operator_id),
                                        "display_name": "Andrea Mele",
                                        "email": "melea@bonificaoristanese.it",
                                        "gaia_user_id": "151",
                                        "gaia_operator_profile_id": str(profile_id),
                                        "gaia_username": "mele.andrea",
                                        "phone": None,
                                        "status": "ACTIVE",
                                        "domains": ["GAIA"],
                                        "gate_mobile_console_enabled": True,
                                        "gate_mobile_console_role": "team_manager",
                                        "gate_mobile_console_pages": [
                                            "dashboard",
                                            "daily-reports",
                                            "presenze",
                                            "presenze-teams",
                                            "diagnostics",
                                        ],
                                    },
                                },
                            }
                        ]
                    },
                )
            if request.url.path == "/api/mobile/connector/presenze/pending-actions/7ece2064-178e-4945-a22a-087d028ad8e2/ack":
                body = request.read().decode()
                assert "wc_operator" in body
                return httpx.Response(200, json={"ok": True})
            return httpx.Response(404)

        async def run() -> None:
            transport = httpx.MockTransport(handler)
            async with httpx.AsyncClient(transport=transport, base_url="https://gateway.example.test") as client:
                result = await process_presenze_pending_actions(db, client=client, headers={"Authorization": "Bearer token"})
            assert result == {"acknowledged": 1, "failed": 0}

        asyncio.run(run())

        updated_operator = db.get(WCOperator, operator_id)
        updated_user = db.get(ApplicationUser, 151)
        assert updated_operator is not None
        assert updated_user is not None
        assert updated_operator.email == "melea@bonificaoristanese.it"
        assert updated_operator.username == "mele.andrea"
        assert updated_operator.first_name == "Andrea"
        assert updated_operator.last_name == "Mele"
        assert updated_operator.domains == ["GAIA"]
        assert updated_operator.gate_mobile_console_enabled is True
        assert updated_operator.gate_mobile_console_role == "team_manager"
        assert updated_operator.gate_mobile_console_pages == [
            "dashboard",
            "daily-reports",
            "presenze",
            "presenze-teams",
            "diagnostics",
        ]
        assert updated_user.email == "melea@bonificaoristanese.it"
        assert updated_user.username == "mele.andrea"
        assert updated_user.full_name == "Andrea Mele"
        assert "/api/mobile/connector/presenze/pending-actions/7ece2064-178e-4945-a22a-087d028ad8e2/ack" in calls
    finally:
        db.close()


def test_process_presenze_pending_actions_fails_invalid_operator_update_proposal() -> None:
    db = _build_session()
    try:
        fail_bodies: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/mobile/connector/presenze/pending-actions":
                return httpx.Response(
                    200,
                    json=[
                        {
                            "pending_action_id": "bad-operator-update",
                            "action_type": "propose_operator_update",
                            "payload_json": {
                                "schema_version": 1,
                                "source": "unknown_console",
                                "operation": "update_operator",
                                "operator": {"operator_id": str(uuid.uuid4())},
                            },
                        }
                    ],
                )
            if request.url.path == "/api/mobile/connector/presenze/pending-actions/bad-operator-update/fail":
                fail_bodies.append(request.read().decode())
                return httpx.Response(200, json={"ok": True})
            return httpx.Response(404)

        async def run() -> None:
            transport = httpx.MockTransport(handler)
            async with httpx.AsyncClient(transport=transport, base_url="https://gateway.example.test") as client:
                result = await process_presenze_pending_actions(db, client=client, headers={"Authorization": "Bearer token"})
            assert result == {"acknowledged": 0, "failed": 1}

        asyncio.run(run())

        assert len(fail_bodies) == 1
        assert "source non supportata" in fail_bodies[0]
        assert '"retryable":false' in fail_bodies[0].replace(" ", "")
    finally:
        db.close()


def test_operator_update_proposal_create_and_validation_branches() -> None:
    db = _build_session()
    try:
        user = ApplicationUser(
            id=151,
            username="new.operator",
            email="new.operator@example.local",
            full_name="New Operator",
            password_hash="hash",
            role=ApplicationUserRole.OPERATOR.value,
            is_active=True,
            module_operazioni=True,
        )
        conflict_user = ApplicationUser(
            id=152,
            username="conflict.operator",
            email="conflict.operator@example.local",
            full_name="Conflict Operator",
            password_hash="hash",
            role=ApplicationUserRole.OPERATOR.value,
            is_active=True,
            module_operazioni=True,
        )
        db.add_all([user, conflict_user])
        db.commit()

        operator_id = uuid.UUID("018f88a2-1797-7365-bf5e-8bb8b7f9e001")
        conflict_wc_id = gate_mobile_sync_service._synthetic_wc_id(db, operator_id)
        db.add(
            WCOperator(
                id=uuid.UUID("018f88a2-1797-7365-bf5e-8bb8b7f9e002"),
                wc_id=conflict_wc_id,
                username="wc.conflict",
                email="wc.conflict@example.test",
            )
        )
        db.commit()

        ack = gate_mobile_sync_service._apply_presenze_pending_action(
            db,
            {
                "pending_action_id": "create-operator",
                "action_type": "propose_operator_update",
                "payload_json": {
                    "schema_version": 1,
                    "source": "gate_admin_console",
                    "operation": "create_operator",
                    "password_changed": True,
                    "operator": {
                        "operator_id": str(operator_id),
                        "display_name": "Singlename",
                        "email": None,
                        "gaia_user_id": "151",
                        "gaia_operator_profile_id": None,
                        "gaia_username": "created.operator",
                        "phone": "+39070000001",
                        "status": "DISABLED",
                        "domains": ["GAIA", "GAIA", ""],
                        "gate_mobile_console_enabled": False,
                        "gate_mobile_console_role": "viewer",
                        "gate_mobile_console_pages": None,
                    },
                },
            },
        )

        created = db.get(WCOperator, operator_id)
        created_user = db.get(ApplicationUser, 151)
        assert ack["gaia_entity_id"] == str(operator_id)
        assert created is not None
        assert created.wc_id == conflict_wc_id - 1
        assert created.first_name == "Singlename"
        assert created.last_name is None
        assert created.email is None
        assert created.enabled is False
        assert created.domains == ["GAIA"]
        assert created.gate_mobile_console_enabled is False
        assert created.gate_mobile_console_role is None
        assert created.gate_mobile_console_pages is None
        assert created_user is not None
        assert created_user.username == "created.operator"
        assert created_user.phone_extension == "+39070000001"
        assert created_user.is_active is False

        gate_mobile_sync_service._apply_presenze_pending_action(
            db,
            {
                "action_type": "propose_operator_update",
                "payload_json": json.dumps(
                    {
                        "schema_version": 1,
                        "source": "gate_admin_console",
                        "operation": "update_operator_domains",
                        "operator": {
                            "operator_id": str(operator_id),
                            "gaia_user_id": None,
                            "display_name": None,
                            "email": "created.operator@example.local",
                            "gaia_username": None,
                            "phone": None,
                            "status": "ACTIVE",
                            "domains": None,
                            "gate_mobile_console_enabled": True,
                            "gate_mobile_console_role": "viewer",
                            "gate_mobile_console_pages": ["dashboard", "dashboard"],
                        },
                    }
                ),
            },
        )
        updated = db.get(WCOperator, operator_id)
        assert updated is not None
        assert updated.gaia_user_id is None
        assert updated.first_name is None
        assert updated.last_name is None
        assert updated.email == "created.operator@example.local"
        assert updated.username is None
        assert updated.enabled is True
        assert updated.domains is None
        assert updated.gate_mobile_console_pages == ["dashboard"]

        validation_cases = [
            ({"payload_json": "not-json", "action_type": "propose_operator_update"}, "payload_json non e un JSON valido"),
            ({"payload_json": [], "action_type": "propose_operator_update"}, "payload_json deve essere un oggetto JSON"),
            (
                {
                    "action_type": "propose_operator_update",
                    "payload_json": {"schema_version": 2, "source": "gate_admin_console", "operation": "update_operator", "operator": {}},
                },
                "schema_version",
            ),
            (
                {
                    "action_type": "propose_operator_update",
                    "payload_json": {"schema_version": 1, "source": "gate_admin_console", "operation": "bad", "operator": {}},
                },
                "operation",
            ),
            (
                {
                    "action_type": "propose_operator_update",
                    "payload_json": {"schema_version": 1, "source": "gate_admin_console", "operation": "update_operator", "operator": None},
                },
                "operator mancante",
            ),
            (
                {
                    "action_type": "propose_operator_update",
                    "payload_json": {
                        "schema_version": 1,
                        "source": "gate_admin_console",
                        "operation": "update_operator",
                        "changed_fields": [1],
                        "operator": {},
                    },
                },
                "changed_fields",
            ),
            (
                {
                    "action_type": "propose_operator_update",
                    "payload_json": {
                        "schema_version": 1,
                        "source": "gate_admin_console",
                        "operation": "update_operator",
                        "password_changed": "yes",
                        "operator": {},
                    },
                },
                "password_changed",
            ),
            (
                {
                    "action_type": "propose_operator_update",
                    "payload_json": {
                        "schema_version": 1,
                        "source": "gate_admin_console",
                        "operation": "update_operator",
                        "operator": {"operator_id": str(uuid.uuid4())},
                    },
                },
                "non trovato",
            ),
            (
                {
                    "action_type": "propose_operator_update",
                    "payload_json": {
                        "schema_version": 1,
                        "source": "gate_admin_console",
                        "operation": "create_operator",
                        "operator": {"operator_id": None},
                    },
                },
                "operator_id mancante",
            ),
            (
                {
                    "action_type": "propose_operator_update",
                    "payload_json": {
                        "schema_version": 1,
                        "source": "gate_admin_console",
                        "operation": "create_operator",
                        "operator": {"operator_id": "bad-uuid"},
                    },
                },
                "operator_id non e un UUID",
            ),
            (
                {
                    "action_type": "propose_operator_update",
                    "payload_json": {
                        "schema_version": 1,
                        "source": "gate_admin_console",
                        "operation": "create_operator",
                        "operator": {"operator_id": str(uuid.uuid4()), "gaia_user_id": "not-int"},
                    },
                },
                "gaia_user_id non valido",
            ),
            (
                {
                    "action_type": "propose_operator_update",
                    "payload_json": {
                        "schema_version": 1,
                        "source": "gate_admin_console",
                        "operation": "create_operator",
                        "operator": {"operator_id": str(uuid.uuid4()), "gaia_user_id": "999"},
                    },
                },
                "Application user 999 non trovato",
            ),
            (
                {
                    "action_type": "propose_operator_update",
                    "payload_json": {
                        "schema_version": 1,
                        "source": "gate_admin_console",
                        "operation": "update_operator",
                        "operator": {"operator_id": str(operator_id), "display_name": ""},
                    },
                },
                "display_name non puo essere vuoto",
            ),
            (
                {
                    "action_type": "propose_operator_update",
                    "payload_json": {
                        "schema_version": 1,
                        "source": "gate_admin_console",
                        "operation": "update_operator",
                        "operator": {"operator_id": str(operator_id), "email": "not-email"},
                    },
                },
                "email operatore non valida",
            ),
            (
                {
                    "action_type": "propose_operator_update",
                    "payload_json": {
                        "schema_version": 1,
                        "source": "gate_admin_console",
                        "operation": "update_operator",
                        "operator": {"operator_id": str(operator_id), "email": "conflict.operator@example.local"},
                    },
                },
                "email gia assegnata",
            ),
            (
                {
                    "action_type": "propose_operator_update",
                    "payload_json": {
                        "schema_version": 1,
                        "source": "gate_admin_console",
                        "operation": "update_operator",
                        "operator": {"operator_id": str(operator_id), "gaia_username": "conflict.operator"},
                    },
                },
                "username gia assegnato",
            ),
            (
                {
                    "action_type": "propose_operator_update",
                    "payload_json": {
                        "schema_version": 1,
                        "source": "gate_admin_console",
                        "operation": "update_operator",
                        "operator": {"operator_id": str(operator_id), "status": "UNKNOWN"},
                    },
                },
                "status operatore non supportato",
            ),
            (
                {
                    "action_type": "propose_operator_update",
                    "payload_json": {
                        "schema_version": 1,
                        "source": "gate_admin_console",
                        "operation": "update_operator",
                        "operator": {"operator_id": str(operator_id), "domains": "GAIA"},
                    },
                },
                "operator.domains",
            ),
            (
                {
                    "action_type": "propose_operator_update",
                    "payload_json": {
                        "schema_version": 1,
                        "source": "gate_admin_console",
                        "operation": "update_operator",
                        "operator": {"operator_id": str(operator_id), "gate_mobile_console_enabled": "yes"},
                    },
                },
                "gate_mobile_console_enabled",
            ),
            (
                {
                    "action_type": "propose_operator_update",
                    "payload_json": {
                        "schema_version": 1,
                        "source": "gate_admin_console",
                        "operation": "update_operator",
                        "operator": {
                            "operator_id": str(operator_id),
                            "gate_mobile_console_enabled": True,
                            "gate_mobile_console_role": None,
                        },
                    },
                },
                "gate_mobile_console_role richiesto",
            ),
            (
                {
                    "action_type": "propose_operator_update",
                    "payload_json": {
                        "schema_version": 1,
                        "source": "gate_admin_console",
                        "operation": "update_operator",
                        "operator": {"operator_id": str(operator_id), "gate_mobile_console_role": "bad-role"},
                    },
                },
                "gate_mobile_console_role non supportato",
            ),
            (
                {
                    "action_type": "propose_operator_update",
                    "payload_json": {
                        "schema_version": 1,
                        "source": "gate_admin_console",
                        "operation": "update_operator",
                        "operator": {"operator_id": str(operator_id), "gate_mobile_console_pages": [1]},
                    },
                },
                "gate_mobile_console_pages",
            ),
        ]
        for payload, message in validation_cases:
            try:
                gate_mobile_sync_service._apply_presenze_pending_action(db, payload)
            except Exception as exc:
                assert message in str(exc)
                db.rollback()
            else:
                raise AssertionError(f"Expected validation error containing {message}")
    finally:
        db.close()


def test_operator_update_proposal_profile_validation_branches() -> None:
    db = _build_session()
    try:
        _seed_operator(db)
        other_profile_id = uuid.UUID("018f88a2-1797-7365-bf5e-8bb8b7f9c0ad")
        db.add(
            ApplicationUser(
                id=153,
                username="profile.owner",
                email="profile.owner@example.test",
                full_name="Profile Owner",
                password_hash="hash",
                role=ApplicationUserRole.OPERATOR.value,
                is_active=True,
                module_operazioni=True,
            )
        )
        db.add(OperatorProfile(id=other_profile_id, user_id=153, phone="+39070000002", is_active=True))
        db.commit()

        for profile_id, message in [
            (uuid.uuid4(), "Operator profile"),
            (other_profile_id, "non appartiene"),
        ]:
            try:
                gate_mobile_sync_service._apply_presenze_pending_action(
                    db,
                    {
                        "action_type": "propose_operator_update",
                        "payload_json": {
                            "schema_version": 1,
                            "source": "gate_admin_console",
                            "operation": "update_operator",
                            "operator": {
                                "operator_id": "018f88a2-1797-7365-bf5e-8bb8b7f9c0aa",
                                "gaia_user_id": "42",
                                "gaia_operator_profile_id": str(profile_id),
                            },
                        },
                    },
                )
            except Exception as exc:
                assert message in str(exc)
                db.rollback()
            else:
                raise AssertionError(f"Expected profile validation error containing {message}")
    finally:
        db.close()


def test_process_presenze_pending_actions_marks_unexpected_errors_retryable(monkeypatch) -> None:
    db = _build_session()
    try:
        fail_bodies: list[str] = []
        errors = [ValueError("bad value"), gate_mobile_sync_service.SQLAlchemyError("db unavailable"), RuntimeError("boom")]

        def fake_apply(_db: Session, _action: dict) -> dict:
            raise errors.pop(0)

        monkeypatch.setattr(gate_mobile_sync_service, "_apply_presenze_pending_action", fake_apply)

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/mobile/connector/presenze/pending-actions":
                return httpx.Response(
                    200,
                    json=[
                        {"pending_action_id": "value-error"},
                        {"pending_action_id": "sql-error"},
                        {"pending_action_id": "runtime-error"},
                    ],
                )
            if request.url.path.endswith("/fail"):
                fail_bodies.append(request.read().decode())
                return httpx.Response(200, json={"ok": True})
            return httpx.Response(404)

        async def run() -> None:
            transport = httpx.MockTransport(handler)
            async with httpx.AsyncClient(transport=transport, base_url="https://gateway.example.test") as client:
                result = await process_presenze_pending_actions(db, client=client, headers={"Authorization": "Bearer token"})
            assert result == {"acknowledged": 0, "failed": 3}

        asyncio.run(run())

        assert '"retryable":false' in fail_bodies[0].replace(" ", "")
        assert '"retryable":true' in fail_bodies[1].replace(" ", "")
        assert '"retryable":true' in fail_bodies[2].replace(" ", "")
    finally:
        db.close()


def test_apply_presenze_pending_action_variants_and_validation_errors() -> None:
    db = _build_session()
    try:
        daily_record_id = _seed_presenze_daily_record(db)

        pending_ack = gate_mobile_sync_service._apply_presenze_pending_action(
            db,
            {
                "client_request_id": "client-pending",
                "type": "validate_daily_record",
                "record_id": str(daily_record_id),
                "gaia_user_id": 77,
                "validation_status": "pending",
            },
        )
        assert pending_ack["gaia_entity_type"] == "presenze_daily_record"
        record = db.get(PresenzeDailyRecord, daily_record_id)
        assert record.validation_status == "pending"
        assert record.validated_by_user_id is None

        resolve_ack = gate_mobile_sync_service._apply_presenze_pending_action(
            db,
            {
                "id": "resolve-1",
                "type": "resolve_anomaly",
                "record_id": str(daily_record_id),
                "gaia_user_id": 77,
                "operator_note": "risolta",
            },
        )
        assert resolve_ack["extra"]["pending_action_id"] == "resolve-1"
        assert db.get(PresenzeDailyRecord, daily_record_id).validation_status == "validated"

        assert gate_mobile_sync_service._pending_action_id({}) != ""
        assert len(gate_mobile_sync_service._task_months({})) == 2

        stale_record_id = uuid.uuid4()
        stale_payload = {
            "collaborator_id": "018f88a2-1797-7365-bf5e-8bb8b7f9d001",
            "work_date": "2026-07-10",
        }
        assert gate_mobile_sync_service._current_pending_action_record_id(
            db,
            stale_payload,
            stale_record_id,
        ) == daily_record_id
        assert gate_mobile_sync_service._current_pending_action_record_id(
            db,
            {},
            stale_record_id,
        ) == stale_record_id
        assert gate_mobile_sync_service._current_pending_action_record_id(
            db,
            stale_payload,
            daily_record_id,
        ) == daily_record_id

        for payload, message in [
            ({}, "gaia_user_id"),
            ({"application_user_id": 77}, "gaia_user_id"),
            ({"gaia_user_id": "not-an-integer"}, "gaia_user_id non valido"),
            ({"gaia_user_id": 999}, "Application user not found"),
            ({"gaia_user_id": 77, "type": "validate_daily_record"}, "record_id"),
            ({"gaia_user_id": 77, "type": "validate_daily_record", "record_id": str(uuid.uuid4())}, "Daily record not found"),
            ({"gaia_user_id": 77, "record_id": str(daily_record_id), "type": "unknown"}, "non supportato"),
        ]:
            try:
                gate_mobile_sync_service._apply_presenze_pending_action(db, payload)
            except Exception as exc:
                assert message in str(exc)
            else:
                raise AssertionError(f"Expected ValueError containing {message}")

        disabled_user = ApplicationUser(
            id=88,
            username="disabled.presenze",
            email="disabled.presenze@example.test",
            password_hash="hash",
            role=ApplicationUserRole.OPERATOR.value,
            is_active=True,
            module_presenze=False,
        )
        db.add(disabled_user)
        db.commit()
        try:
            gate_mobile_sync_service._apply_presenze_pending_action(
                db,
                {"gaia_user_id": 88, "record_id": str(daily_record_id), "type": "validate_daily_record"},
            )
        except ValueError as exc:
            assert "non abilitato" in str(exc)
        else:
            raise AssertionError("Expected disabled presenze user to fail")
    finally:
        db.close()


def test_execute_gate_mobile_sync_records_success_run() -> None:
    db = _build_session()
    try:
        _seed_operator(db)
        original_catalog_builder = gate_mobile_sync_service.build_mobile_catalog_push_payloads
        original_workset_builder = gate_mobile_sync_service.build_mobile_workset_push_payloads
        gate_mobile_sync_service.build_mobile_catalog_push_payloads = lambda _db: []
        gate_mobile_sync_service.build_mobile_workset_push_payloads = lambda _db: []

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/mobile/connector/sync/plan":
                return httpx.Response(
                    200,
            json={"plan": {"generated_at": "2026-06-15T10:00:00Z", "tasks": [{"type": "operators"}]}},
                )
            if request.url.path == "/api/mobile/connector/operators/push":
                return httpx.Response(200, json={"operators": {"count": 1}})
            return httpx.Response(404)

        settings = Settings(
            _env_file=None,
            DATABASE_URL="sqlite:///./gate-mobile-sync-test.db",
            JWT_SECRET_KEY="test-secret",
            GATE_MOBILE_GATEWAY_BASE_URL="https://gateway.example.test",
            GATE_MOBILE_CONNECTOR_TOKEN="gate-token",
            GATE_MOBILE_SYNC_ENABLED="true",
        )

        async def run() -> None:
            transport = httpx.MockTransport(handler)
            async with httpx.AsyncClient(transport=transport, base_url=settings.gate_mobile_gateway_base_url) as client:
                result = await execute_gate_mobile_sync(db, app_settings=settings, client=client, trigger_source="pytest")
            assert result.status == "succeeded"
            assert result.report is not None
            assert result.report.operators_pushed == 1

        try:
            asyncio.run(run())
        finally:
            gate_mobile_sync_service.build_mobile_catalog_push_payloads = original_catalog_builder
            gate_mobile_sync_service.build_mobile_workset_push_payloads = original_workset_builder

        run_row = db.query(GateMobileSyncRun).one()
        assert run_row.status == "succeeded"
        assert run_row.requested_tasks_count == 1
        assert run_row.operators_pushed == 1
        assert run_row.error_kind is None
        assert run_row.finished_at is not None
    finally:
        db.close()


def test_execute_gate_mobile_sync_records_failure_run() -> None:
    db = _build_session()
    try:
        settings = Settings(
            _env_file=None,
            DATABASE_URL="sqlite:///./gate-mobile-sync-test.db",
            JWT_SECRET_KEY="test-secret",
            GATE_MOBILE_GATEWAY_BASE_URL="https://gateway.example.test",
            GATE_MOBILE_CONNECTOR_TOKEN="gate-token",
            GATE_MOBILE_SYNC_ENABLED="true",
        )

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, request=request)

        async def run() -> None:
            transport = httpx.MockTransport(handler)
            async with httpx.AsyncClient(transport=transport, base_url=settings.gate_mobile_gateway_base_url) as client:
                try:
                    await execute_gate_mobile_sync(db, app_settings=settings, client=client, trigger_source="pytest")
                except httpx.HTTPStatusError:
                    return
            raise AssertionError("HTTPStatusError not raised")

        asyncio.run(run())

        run_row = db.query(GateMobileSyncRun).one()
        assert run_row.status == "failed"
        assert run_row.error_kind == "http_status_error"
        assert "status=503" in (run_row.error_message or "")
    finally:
        db.close()


def test_execute_gate_mobile_sync_run_survives_task_rollback(monkeypatch) -> None:
    db = _build_session()
    try:
        async def rollback_task(
            session: Session,
            **_kwargs,
        ) -> gate_mobile_sync_service.GateMobileSyncReport:
            session.rollback()
            return gate_mobile_sync_service.GateMobileSyncReport(
                requested_tasks=[{"type": "presenze_pending_actions"}],
                catalogs_pushed=0,
                operators_pushed=0,
                worksets_pushed=0,
            )

        monkeypatch.setattr(gate_mobile_sync_service, "run_gate_mobile_sync_once", rollback_task)
        settings = Settings(
            _env_file=None,
            DATABASE_URL="sqlite:///./gate-mobile-sync-test.db",
            JWT_SECRET_KEY="test-secret",
            GATE_MOBILE_SYNC_ENABLED="true",
        )

        result = asyncio.run(
            execute_gate_mobile_sync(
                db,
                app_settings=settings,
                trigger_source="pytest-rollback",
            )
        )

        assert result.status == "succeeded"
        run_row = db.query(GateMobileSyncRun).one()
        assert run_row.status == "succeeded"
        assert run_row.requested_tasks_count == 1
    finally:
        db.close()


def test_run_gate_mobile_sync_once_validates_required_configuration() -> None:
    db = _build_session()
    try:
        missing_url = Settings(_env_file=None, DATABASE_URL="sqlite:///./gate-mobile-sync-test.db", JWT_SECRET_KEY="test-secret")
        missing_token = Settings(
            _env_file=None,
            DATABASE_URL="sqlite:///./gate-mobile-sync-test.db",
            JWT_SECRET_KEY="test-secret",
            GATE_MOBILE_GATEWAY_BASE_URL="https://gateway.example.test",
        )

        async def run() -> None:
            try:
                await run_gate_mobile_sync_once(db, app_settings=missing_url)
            except RuntimeError as exc:
                assert "GATE_MOBILE_GATEWAY_BASE_URL" in str(exc)
            else:
                raise AssertionError("missing URL did not fail")

            try:
                await run_gate_mobile_sync_once(db, app_settings=missing_token)
            except RuntimeError as exc:
                assert "GATE_MOBILE_CONNECTOR_TOKEN" in str(exc)
            else:
                raise AssertionError("missing token did not fail")

        asyncio.run(run())
    finally:
        db.close()


def test_run_gate_mobile_sync_once_closes_owned_client(monkeypatch) -> None:
    db = _build_session()
    try:
        closed = {"value": False}
        monkeypatch.setattr(gate_mobile_sync_service, "build_mobile_catalog_push_payloads", lambda _db: [])
        monkeypatch.setattr(gate_mobile_sync_service, "build_mobile_workset_push_payloads", lambda _db: [])

        class FakeAsyncClient:
            def __init__(self, **_kwargs):
                pass

            async def post(self, path: str, **_kwargs) -> httpx.Response:
                request = httpx.Request("POST", f"https://gateway.example.test{path}")
                if path == "/api/mobile/connector/sync/plan":
                    return httpx.Response(200, request=request, json={"plan": {"tasks": []}})
                return httpx.Response(404, request=request)

            async def aclose(self) -> None:
                closed["value"] = True

        monkeypatch.setattr(gate_mobile_sync_service.httpx, "AsyncClient", FakeAsyncClient)
        settings = Settings(
            _env_file=None,
            DATABASE_URL="sqlite:///./gate-mobile-sync-test.db",
            JWT_SECRET_KEY="test-secret",
            GATE_MOBILE_GATEWAY_BASE_URL="https://gateway.example.test",
            GATE_MOBILE_CONNECTOR_TOKEN="gate-token",
        )

        asyncio.run(run_gate_mobile_sync_once(db, app_settings=settings))

        assert closed["value"] is True
    finally:
        db.close()


def test_execute_gate_mobile_sync_records_disabled_configuration_runtime_and_transport_errors(monkeypatch) -> None:
    db = _build_session()
    try:
        disabled_settings = Settings(
            _env_file=None,
            DATABASE_URL="sqlite:///./gate-mobile-sync-test.db",
            JWT_SECRET_KEY="test-secret",
            GATE_MOBILE_SYNC_ENABLED="false",
        )

        async def run_disabled() -> None:
            result = await execute_gate_mobile_sync(db, app_settings=disabled_settings, trigger_source="pytest-disabled")
            assert result.status == "skipped"
            assert result.error_kind == "disabled"

        asyncio.run(run_disabled())

        async def raise_runtime(*_args, **_kwargs):
            raise RuntimeError("missing configuration")

        monkeypatch.setattr(gate_mobile_sync_service, "run_gate_mobile_sync_once", raise_runtime)
        runtime_settings = Settings(
            _env_file=None,
            DATABASE_URL="sqlite:///./gate-mobile-sync-test.db",
            JWT_SECRET_KEY="test-secret",
            GATE_MOBILE_SYNC_ENABLED="true",
        )

        async def run_runtime() -> None:
            result = await execute_gate_mobile_sync(
                db,
                app_settings=runtime_settings,
                trigger_source="pytest-runtime",
                raise_on_error=False,
            )
            assert result.status == "failed"
            assert result.error_kind == "configuration_error"

        asyncio.run(run_runtime())

        async def raise_transport(*_args, **_kwargs):
            request = httpx.Request("POST", "https://gateway.example.test/api/mobile/connector/sync/plan")
            raise httpx.ConnectError("connection refused", request=request)

        monkeypatch.setattr(gate_mobile_sync_service, "run_gate_mobile_sync_once", raise_transport)

        async def run_transport() -> None:
            result = await execute_gate_mobile_sync(
                db,
                app_settings=runtime_settings,
                trigger_source="pytest-transport",
                raise_on_error=False,
            )
            assert result.status == "failed"
            assert result.error_kind == "transport_error"

        asyncio.run(run_transport())

        async def raise_unexpected(*_args, **_kwargs):
            raise ValueError("boom")

        monkeypatch.setattr(gate_mobile_sync_service, "run_gate_mobile_sync_once", raise_unexpected)

        async def run_unexpected() -> None:
            result = await execute_gate_mobile_sync(
                db,
                app_settings=runtime_settings,
                trigger_source="pytest-unexpected",
                raise_on_error=False,
            )
            assert result.status == "failed"
            assert result.error_kind == "unexpected_error"

        asyncio.run(run_unexpected())
    finally:
        db.close()


def test_execute_gate_mobile_sync_can_return_failed_result_without_raising() -> None:
    db = _build_session()
    try:
        settings = Settings(
            _env_file=None,
            DATABASE_URL="sqlite:///./gate-mobile-sync-test.db",
            JWT_SECRET_KEY="test-secret",
            GATE_MOBILE_GATEWAY_BASE_URL="https://gateway.example.test",
            GATE_MOBILE_CONNECTOR_TOKEN="gate-token",
            GATE_MOBILE_SYNC_ENABLED="true",
        )

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, request=request)

        async def run() -> None:
            transport = httpx.MockTransport(handler)
            async with httpx.AsyncClient(transport=transport, base_url=settings.gate_mobile_gateway_base_url) as client:
                result = await execute_gate_mobile_sync(
                    db,
                    app_settings=settings,
                    client=client,
                    trigger_source="pytest-api",
                    raise_on_error=False,
                )
            assert result.status == "failed"
            assert result.error_kind == "http_status_error"
            assert result.error_message is not None

        asyncio.run(run())

        run_row = db.query(GateMobileSyncRun).one()
        assert run_row.status == "failed"
    finally:
        db.close()


def test_get_gate_mobile_sync_status_reports_latest_run() -> None:
    db = _build_session()
    try:
        db.add(
            GateMobileSyncRun(
                trigger_source="pytest",
                status="succeeded",
                requested_tasks_count=1,
                operators_pushed=276,
            )
        )
        db.commit()

        settings = Settings(
            _env_file=None,
            DATABASE_URL="sqlite:///./gate-mobile-sync-test.db",
            JWT_SECRET_KEY="test-secret",
            GATE_MOBILE_GATEWAY_BASE_URL="https://gateway.example.test",
            GATE_MOBILE_CONNECTOR_TOKEN="gate-token",
            GATE_MOBILE_SYNC_ENABLED="true",
            MOBILE_CONNECTOR_HEADER_NAME="X-GAIA-Connector-Token",
        )
        payload = get_gate_mobile_sync_status(db, app_settings=settings)

        assert payload["sync_enabled"] is True
        assert payload["gateway_configured"] is True
        assert payload["token_configured"] is True
        assert payload["outbound_scope"] == [
            "catalogs",
            "operators",
            "worksets",
            "presenze_teams",
            "presenze_months",
            "presenze_giornaliere",
            "presenze_anomalie",
            "presenze_rules",
            "presenze_pending_actions",
        ]
        assert payload["internal_connector_api"]["path_prefix"] == "/api/mobile-sync"
        assert payload["last_run"]["operators_pushed"] == 276
        assert len(payload["recent_runs"]) == 1
    finally:
        db.close()


def test_get_gate_mobile_sync_status_reports_empty_run_history() -> None:
    db = _build_session()
    try:
        settings = Settings(
            _env_file=None,
            DATABASE_URL="sqlite:///./gate-mobile-sync-test.db",
            JWT_SECRET_KEY="test-secret",
        )
        payload = get_gate_mobile_sync_status(db, app_settings=settings)

        assert payload["last_run"] is None
        assert payload["recent_runs"] == []
    finally:
        db.close()


def test_get_running_gate_mobile_sync_run_returns_latest_running() -> None:
    db = _build_session()
    try:
        first = GateMobileSyncRun(trigger_source="pytest-1", status="running", requested_tasks_count=0, operators_pushed=0)
        second = GateMobileSyncRun(trigger_source="pytest-2", status="running", requested_tasks_count=0, operators_pushed=0)
        db.add_all([first, second])
        db.commit()

        running = get_running_gate_mobile_sync_run(db)

        assert running is not None
        assert running.status == "running"
        assert running.trigger_source in {"pytest-1", "pytest-2"}
    finally:
        db.close()


def _build_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[
            ApplicationUser.__table__,
            GateMobileSyncRun.__table__,
            WCOperator.__table__,
            OperatorProfile.__table__,
            PresenzeCollaborator.__table__,
            PresenzeHoliday.__table__,
            PresenzeScheduleTemplate.__table__,
            PresenzeScheduleRule.__table__,
            PresenzeCollaboratorScheduleAssignment.__table__,
            PresenzeOperaiRuleConfig.__table__,
            PresenzeImportJob.__table__,
            PresenzeSyncJob.__table__,
            PresenzeDailyRecord.__table__,
            PresenzeDailyPunch.__table__,
            OrganizationTeam.__table__,
            OrganizationTeamMembership.__table__,
            OrganizationTeamSupervisorAssignment.__table__,
        ],
    )
    return sessionmaker(bind=engine)()


def _seed_operator(
    db: Session,
    *,
    operator_id: uuid.UUID = uuid.UUID("018f88a2-1797-7365-bf5e-8bb8b7f9c0aa"),
    profile_id: uuid.UUID = uuid.UUID("018f88a2-1797-7365-bf5e-8bb8b7f9c0ac"),
) -> None:
    user = ApplicationUser(
        id=42,
        username="mrossi",
        email="mario.rossi@example.test",
        full_name="Mario Rossi",
        password_hash="hash",
        role=ApplicationUserRole.OPERATOR.value,
        is_active=True,
        module_operazioni=True,
    )
    operator = WCOperator(
        id=operator_id,
        wc_id=1001,
        username="mrossi",
        email="mario.rossi@example.test",
        first_name="Mario",
        last_name="Rossi",
        enabled=True,
        personnel_area="AGRARIO",
        gaia_user_id=42,
    )
    profile = OperatorProfile(
        id=profile_id,
        user_id=42,
        phone="+39070000000",
        is_active=True,
    )
    db.add_all([user, operator, profile])
    db.commit()


def _seed_presenze_team(db: Session) -> None:
    user = ApplicationUser(
        id=77,
        username="presenze.supervisor",
        email="presenze.supervisor@example.test",
        full_name="Responsabile Presenze",
        password_hash="hash",
        role=ApplicationUserRole.REVIEWER.value,
        is_active=True,
        module_presenze=True,
    )
    collaborator = PresenzeCollaborator(
        id=uuid.UUID("018f88a2-1797-7365-bf5e-8bb8b7f9d001"),
        employee_code="P001",
        company_code="53",
        name="OPERATORE PRESENZE",
        application_user_id=77,
    )
    team = OrganizationTeam(
        id=uuid.UUID("018f88a2-1797-7365-bf5e-8bb8b7f9d002"),
        name="Squadra Presenze Nord",
        code="PNORD",
        scope="presenze",
        personnel_area="AGRARIO",
        active=True,
        created_from_channel="gaia_web",
        created_by_user_id=77,
    )
    membership = OrganizationTeamMembership(
        id=uuid.UUID("018f88a2-1797-7365-bf5e-8bb8b7f9d003"),
        team_id=team.id,
        collaborator_id=collaborator.id,
        role="member",
        source_channel="gaia_web",
        created_by_user_id=77,
    )
    supervisor = OrganizationTeamSupervisorAssignment(
        id=uuid.UUID("018f88a2-1797-7365-bf5e-8bb8b7f9d004"),
        team_id=team.id,
        application_user_id=77,
        permission_scope="validate",
        source_channel="gaia_web",
        assigned_by_user_id=77,
    )
    db.add_all([user, collaborator, team, membership, supervisor])
    db.commit()


def _seed_presenze_daily_record(db: Session) -> uuid.UUID:
    _seed_presenze_team(db)
    record = PresenzeDailyRecord(
        id=uuid.UUID("018f88a2-1797-7365-bf5e-8bb8b7f9d101"),
        collaborator_id=uuid.UUID("018f88a2-1797-7365-bf5e-8bb8b7f9d001"),
        owner_user_id=77,
        application_user_id=77,
        work_date=date(2026, 7, 10),
        schedule_code="STD",
        teo_minutes=420,
        ordinary_minutes=420,
        justified_minutes=60,
        straordinario_minutes=240,
        km_value=24,
        trasferta_minutes=180,
        reperibilita_unit="shifts",
        reperibilita_quantity=1,
        request_description="P. ORD - Permesso ordinario",
        raw_payload_json={},
    )
    punch = PresenzeDailyPunch(
        id=uuid.UUID("018f88a2-1797-7365-bf5e-8bb8b7f9d102"),
        daily_record_id=record.id,
        sequence=1,
        entry_time=time(8, 0),
        exit_time=time(15, 0),
    )
    db.add_all([record, punch])
    db.commit()
    return record.id
