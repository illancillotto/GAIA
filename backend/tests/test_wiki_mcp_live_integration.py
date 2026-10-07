from datetime import date
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.router import api_router
from app.core.config import settings
from app.core.database import Base, get_db
from app.models.application_user import ApplicationUser
from app.models.catasto import CatastoBatch, CatastoVisuraRequest
from app.models.section_permission import Section, UserSectionPermission
from app.modules.dotazioni.models import DotazioneAsset
from app.modules.presenze.models import PresenzeCollaborator, PresenzeDailyRecord
from app.modules.wiki.mcps.audit import AuditStore
from app.modules.wiki.mcps.live.api import GaiaAPI
from app.modules.wiki.mcps.live.service import LiveService
from app.services.auth import issue_access_token

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def database(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret_key", "gaia-live-test-signing-key-at-least-32-bytes")
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine) as database:
        users = [
            ApplicationUser(
                username=f"live-test-{index}",
                email=f"live-test-{index}@example.test",
                password_hash="unused",
                role="viewer",
                is_active=True,
                module_presenze=True,
                module_dotazioni=True,
            )
            for index in range(2)
        ]
        database.add_all(users)
        database.flush()
        asset = DotazioneAsset(
            asset_code="TEST-MCP",
            asset_type="phone",
            name="Test phone",
            notes="private-asset-note",
            created_by_user_id=users[0].id,
            updated_by_user_id=users[0].id,
        )
        section = Section(
            key="dotazioni.view",
            label="View assets",
            module="dotazioni",
            min_role="viewer",
            is_active=True,
        )
        database.add_all([asset, section])
        for index, user in enumerate(users):
            collaborator = PresenzeCollaborator(
                id=uuid4(),
                employee_code=f"TEST-{index}",
                name="Same name",
                application_user_id=user.id,
            )
            database.add(collaborator)
            database.flush()
            database.add(
                PresenzeDailyRecord(
                    collaborator_id=collaborator.id,
                    application_user_id=user.id,
                    work_date=date.today(),
                    ordinary_minutes=480 + index,
                    resolved_absence_cause="private-medical-reason",
                    manual_note="private-personnel-note",
                )
            )
        database.commit()
        yield database, users, asset, section
    engine.dispose()


@pytest.fixture
def gateway(database):
    application = FastAPI()
    application.include_router(api_router)
    application.dependency_overrides[get_db] = lambda: database[0]
    gateway = FastAPI()
    gateway.mount("/api", application)
    return gateway


async def test_real_gaia_auth_asset_projection_and_permission_revocation(
    tmp_path, database, gateway
):
    database, users, asset, section = database
    token = issue_access_token(users[0])
    api = GaiaAPI("https://gaia.lan", token, transport=httpx.ASGITransport(app=gateway))
    audit = AuditStore(tmp_path / "gaia-mcp-audit.sqlite")
    try:
        service = LiveService(api, audit, ["search_assets", "get_asset", "get_asset_custody"])
        assert await service.tools() == ["search_assets", "get_asset", "get_asset_custody"]
        result = await service.call("search_assets", {"search": "Test phone"})
        assert result["data"]["total"] == 1
        assert result["data"]["items"][0]["asset_code"] == "TEST-MCP"
        assert "notes" not in result["data"]["items"][0]
        detail = await service.call("get_asset", {"record_id": str(asset.id)})
        assert detail["data"]["name"] == "Test phone"
        assert (await service.call("get_asset_custody", {"record_id": str(asset.id)}))[
            "data"
        ] is None
        database.add(
            UserSectionPermission(user_id=users[0].id, section_id=section.id, is_granted=False)
        )
        database.commit()
        assert await service.tools() == []
        assert await service.call("get_asset", {"record_id": str(asset.id)}) == {
            "error": {"code": "PERMISSION_DENIED"}
        }
        users[0].is_active = False
        database.commit()
        assert await service.call("search_assets", {}) == {"error": {"code": "AUTH_REQUIRED"}}
        assert "private-asset-note" not in str(
            audit.connection.execute("SELECT payload FROM calls").fetchall()
        )
    finally:
        await api.close()
        audit.close()


async def test_processing_status_enforces_backend_ownership_and_never_writes(
    tmp_path, database, gateway
):
    database, users, _asset, _section = database
    users[0].module_catasto = True
    database.add(
        Section(
            key="catasto.dashboard",
            label="Dashboard",
            module="catasto",
            min_role="viewer",
            is_active=True,
        )
    )
    requests = []
    for user in users:
        batch = CatastoBatch(user_id=user.id, total_items=1)
        database.add(batch)
        database.flush()
        request = CatastoVisuraRequest(
            batch_id=batch.id,
            user_id=user.id,
            row_index=1,
            status="pending",
            error_message="private-portal-error",
            captcha_image_path="private-captcha-path",
        )
        database.add(request)
        requests.append(request)
    database.commit()
    identifiers = [str(request.id) for request in requests]
    audit = AuditStore(tmp_path / "gaia-mcp-audit.sqlite")
    api = GaiaAPI(
        "https://gaia.lan", issue_access_token(users[0]), transport=httpx.ASGITransport(app=gateway)
    )
    statements = []

    def capture_statement(_connection, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement)

    engine = database.get_bind()
    event.listen(engine, "before_cursor_execute", capture_statement)
    try:
        service = LiveService(api, audit, ["get_processing_request"])
        result = await service.call("get_processing_request", {"record_id": identifiers[0]})
        assert result["data"]["status"] == "pending"
        assert "private" not in str(result)
        assert await service.call("get_processing_request", {"record_id": identifiers[1]}) == {
            "error": {"code": "NOT_FOUND"}
        }
        assert statements
        assert all(statement.lstrip().upper().startswith("SELECT") for statement in statements)
    finally:
        event.remove(engine, "before_cursor_execute", capture_statement)
        await api.close()
        audit.close()


async def test_real_self_service_canonical_identity_isolation_and_no_medical_data(
    tmp_path, database, gateway
):
    database, users, _asset, _section = database
    audit = AuditStore(tmp_path / "gaia-mcp-audit.sqlite")
    api = GaiaAPI(
        "https://gaia.lan", issue_access_token(users[0]), transport=httpx.ASGITransport(app=gateway)
    )
    try:
        service = LiveService(api, audit, ["get_my_presenze"])
        result = await service.call("get_my_presenze", {})
        assert result["data"]["total"] == 1
        assert result["data"]["items"][0]["ordinary_minutes"] == 480
        assert "private" not in str(result)
        assert await service.call("get_my_presenze", {"application_user_id": users[1].id}) == {
            "error": {"code": "INVALID_ARGUMENT"}
        }
        own = database.scalar(
            select(PresenzeDailyRecord).where(
                PresenzeDailyRecord.application_user_id == users[0].id
            )
        )
        own.application_user_id = None
        database.commit()
        assert (await service.call("get_my_presenze", {}))["data"]["total"] == 0
        users[0].module_presenze = False
        database.commit()
        assert await service.call("get_my_presenze", {}) == {"error": {"code": "PERMISSION_DENIED"}}
    finally:
        await api.close()
        audit.close()
