from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

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
from app.services.gate_mobile_sync import (
    build_mobile_operator_push_payload,
    execute_gate_mobile_sync,
    get_running_gate_mobile_sync_run,
    get_gate_mobile_sync_status,
    run_gate_mobile_sync_once,
)


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
                    "display_name": "Mario Rossi",
                    "email": "mario.rossi@example.test",
                    "phone": "+39070000000",
                    "status": "ACTIVE",
                }
            ],
        }
    finally:
        db.close()


def test_run_gate_mobile_sync_once_requests_plan_then_pushes_operators() -> None:
    db = _build_session()
    try:
        _seed_operator(db)
        calls: list[httpx.Request] = []

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
                return httpx.Response(200, json={"operators": {"count": 1}})
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
            assert report.operators_pushed == 1

        asyncio.run(run())

        assert [call.url.path for call in calls] == [
            "/api/mobile/connector/sync/plan",
            "/api/mobile/connector/operators/push",
        ]
    finally:
        db.close()


def test_execute_gate_mobile_sync_records_success_run() -> None:
    db = _build_session()
    try:
        _seed_operator(db)

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

        asyncio.run(run())

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
        assert payload["outbound_scope"] == ["operators"]
        assert payload["internal_connector_api"]["path_prefix"] == "/api/mobile-sync"
        assert payload["last_run"]["operators_pushed"] == 276
        assert len(payload["recent_runs"]) == 1
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
