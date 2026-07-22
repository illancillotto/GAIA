from __future__ import annotations

import asyncio
import uuid
from datetime import date, datetime, timezone

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.core.database import Base
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.operazioni.models.gate_mobile_sync_run import GateMobileSyncRun
from app.modules.operazioni.models.organizational import OperatorProfile
from app.modules.operazioni.models.wc_operator import WCOperator
from app.modules.presenze.models import (
    OrganizationTeam,
    OrganizationTeamMembership,
    OrganizationTeamSupervisorAssignment,
    PresenzeCollaborator,
    PresenzeDailyRecord,
    PresenzeImportJob,
)
from app.services import gate_mobile_sync as gate_mobile_sync_service
from app.services.gate_mobile_sync import (
    build_mobile_operator_push_payload,
    build_mobile_catalog_push_payloads,
    build_mobile_workset_push_payloads,
    build_presenze_teams_push_payload,
    build_presenze_rules_push_payload,
    build_presenze_months_push_payload,
    build_presenze_giornaliere_push_payload,
    build_presenze_anomalie_push_payload,
    execute_gate_mobile_sync,
    get_running_gate_mobile_sync_run,
    get_gate_mobile_sync_status,
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
                "synced_from_gaia_at": datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc),
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
                "synced_from_gaia_at": datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc),
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
            now=datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc),
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
                    "status": "ACTIVE",
                    "gate_mobile_console_enabled": False,
                    "gate_mobile_console_role": None,
                }
            ],
        }
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
            now=datetime(2026, 7, 9, 9, 30, tzinfo=timezone.utc),
        )

        assert payload["source"] == "gaia"
        assert payload["rules_version"] == "presenze-2026-07-extra-3h"
        assert payload["synced_from_gaia_at"] == "2026-07-09T09:30:00Z"
        assert payload["teams"][0]["name"] == "Squadra Presenze Nord"
        assert payload["teams"][0]["created_from_channel"] == "gaia"
        assert payload["teams"][0]["audit"] == {}
        assert payload["teams"][0]["memberships"][0]["collaborator_name"] == "OPERATORE PRESENZE"
        assert payload["teams"][0]["memberships"][0]["source_channel"] == "gaia"
        assert payload["teams"][0]["supervisors"][0]["username"] == "presenze.supervisor"
        assert payload["teams"][0]["supervisors"][0]["permission_scope"] == "validate"
        assert gate_mobile_sync_service._gate_channel("gate_mobile") == "gate"
        assert gate_mobile_sync_service._gate_channel("gate") == "gate"
        assert gate_mobile_sync_service._gate_channel("custom") == "custom"
        assert gate_mobile_sync_service._gate_channel(None) == "gaia"
    finally:
        db.close()


def test_build_presenze_rules_months_giornaliere_and_anomalie_payloads(monkeypatch) -> None:
    db = _build_session()
    try:
        daily_record_id = _seed_presenze_daily_record(db)
        monkeypatch.setattr(gate_mobile_sync_service, "_serialize_gate_record_item", lambda _db, record, **_kwargs: _FakeRecordItem(record.id))
        monkeypatch.setattr(gate_mobile_sync_service, "_gate_record_analysis", lambda _db, _record: _FakeAnalysis())

        rules_payload = build_presenze_rules_push_payload(now=datetime(2026, 7, 10, 8, 0, tzinfo=timezone.utc))
        months_payload = build_presenze_months_push_payload(db, now=datetime(2026, 7, 10, 8, 0, tzinfo=timezone.utc))
        giornaliere_payload = build_presenze_giornaliere_push_payload(
            db,
            month="2026-07",
            now=datetime(2026, 7, 10, 8, 0, tzinfo=timezone.utc),
        )
        anomalie_payload = build_presenze_anomalie_push_payload(
            db,
            month="2026-07",
            now=datetime(2026, 7, 10, 8, 0, tzinfo=timezone.utc),
        )

        assert rules_payload["schema_version"] == 1
        assert rules_payload["export_rules_version"] == "presenze-xlsm-2026-07"
        assert rules_payload["rules"]["rules_version"] == "presenze-2026-07-extra-3h"
        assert months_payload["months"] == [{"month": "2026-07", "records_total": 1}]
        assert giornaliere_payload["records"][0]["record_id"] == str(daily_record_id)
        assert giornaliere_payload["giornaliere"] == giornaliere_payload["records"]
        assert anomalie_payload["anomalies"][0]["reasons"] == ["extra_over_3h"]
        assert anomalie_payload["anomalie"] == anomalie_payload["anomalies"]

        monkeypatch.setattr(gate_mobile_sync_service, "_serialize_gate_record_item", lambda _db, record, **_kwargs: _FakeRecordItem(uuid.uuid4()))
        missing_record_payload = build_presenze_anomalie_push_payload(db, month="2026-07")
        assert missing_record_payload["anomalies"] == []
        assert missing_record_payload["anomalie"] == []

        monkeypatch.setattr(gate_mobile_sync_service, "_serialize_gate_record_item", lambda _db, record, **_kwargs: _FakeRecordItem(record.id))
        monkeypatch.setattr(gate_mobile_sync_service, "_gate_record_analysis", lambda _db, _record: type("Analysis", (), {"severity": "none"})())
        clean_payload = build_presenze_anomalie_push_payload(db, month="2026-07")
        assert clean_payload["anomalies"] == []
        assert clean_payload["anomalie"] == []
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
                                    "application_user_id": 77,
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
                            "actor": {"application_user_id": 77},
                            "km_value": 12,
                            "operator_note": "km",
                        },
                        {
                            "pending_action_id": "pending-fail",
                            "action_type": "propose_team_change",
                            "application_user_id": 77,
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
                "user_id": 77,
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
                "application_user_id": 77,
                "operator_note": "risolta",
            },
        )
        assert resolve_ack["extra"]["pending_action_id"] == "resolve-1"
        assert db.get(PresenzeDailyRecord, daily_record_id).validation_status == "validated"

        assert gate_mobile_sync_service._pending_action_id({}) != ""
        assert len(gate_mobile_sync_service._task_months({})) == 2

        for payload, message in [
            ({}, "application_user_id"),
            ({"application_user_id": 999}, "Application user not found"),
            ({"application_user_id": 77, "type": "validate_daily_record"}, "record_id"),
            ({"application_user_id": 77, "type": "validate_daily_record", "record_id": str(uuid.uuid4())}, "Daily record not found"),
            ({"application_user_id": 77, "record_id": str(daily_record_id), "type": "unknown"}, "non supportato"),
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
                {"application_user_id": 88, "record_id": str(daily_record_id), "type": "validate_daily_record"},
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
            PresenzeImportJob.__table__,
            PresenzeDailyRecord.__table__,
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
        straordinario_minutes=240,
        raw_payload_json={},
    )
    db.add(record)
    db.commit()
    return record.id
