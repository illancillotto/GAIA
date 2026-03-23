from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.models.effective_permission import EffectivePermission
from app.models.nas_group import NasGroup
from app.models.nas_user import NasUser
from app.models.permission_entry import PermissionEntry
from app.models.share import Share
from app.models.snapshot import Snapshot
from app.models.sync_run import SyncRun
from app.services.nas_connector import NasConnectorError


SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database() -> Generator[None, None, None]:
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    db.add(
        ApplicationUser(
            username="syncadmin",
            email="syncadmin@example.local",
            password_hash=hash_password("secret123"),
            role=ApplicationUserRole.ADMIN.value,
            is_active=True,
        )
    )
    db.commit()
    db.close()

    yield

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def auth_headers() -> dict[str, str]:
    login_response = client.post(
        "/auth/login",
        json={"username": "syncadmin", "password": "secret123"},
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_sync_capabilities_requires_authentication() -> None:
    response = client.get("/sync/capabilities")
    assert response.status_code == 401


def test_sync_capabilities_returns_configured_connector_info() -> None:
    app.dependency_overrides[get_db] = override_get_db
    response = client.get("/sync/capabilities", headers=auth_headers())

    assert response.status_code == 200
    assert response.json()["ssh_configured"] is True
    assert response.json()["supports_live_sync"] is True
    assert response.json()["host"]
    assert response.json()["auth_mode"] == "password"
    assert response.json()["retry_strategy"] == "fixed"
    assert response.json()["retry_max_attempts"] == 3
    assert response.json()["retry_jitter_enabled"] is False
    assert response.json()["retry_jitter_ratio"] == 0.2


def test_sync_preview_parses_inline_samples() -> None:
    payload = {
        "passwd_text": "mrossi:x:1001:100:Mario Rossi:/var/services/homes/mrossi:/sbin/nologin\n",
        "group_text": "amministrazione:x:2001:mrossi\n",
        "shares_text": "contabilita\n",
        "acl_texts": ["allow: group:amministrazione:read,write\ndeny: user:ospite:read\n"],
    }

    response = client.post("/sync/preview", json=payload, headers=auth_headers())

    assert response.status_code == 200
    body = response.json()
    assert body["users"][0]["username"] == "mrossi"
    assert body["groups"][0]["name"] == "amministrazione"
    assert body["shares"][0]["name"] == "contabilita"
    assert body["acl_entries"][1]["effect"] == "deny"


def test_sync_apply_persists_snapshot_domain_and_effective_permissions() -> None:
    payload = {
        "passwd_text": (
            "mrossi:x:1001:100:Mario Rossi:/var/services/homes/mrossi:/sbin/nologin\n"
            "lbianchi:x:1002:100:Laura Bianchi:/var/services/homes/lbianchi:/sbin/nologin\n"
        ),
        "group_text": (
            "amministrazione:x:2001:mrossi\n"
            "direzione:x:2002:lbianchi\n"
        ),
        "shares_text": "contabilita\ndirezione\n",
        "acl_texts": [
            "allow: group:amministrazione:read,write\ndeny: user:ospite:read\n",
            "allow: group:direzione:write\n",
        ],
    }

    response = client.post("/sync/apply", json=payload, headers=auth_headers())

    assert response.status_code == 200
    assert response.json() == {
        "snapshot_id": 1,
        "snapshot_checksum": response.json()["snapshot_checksum"],
        "persisted_users": 2,
        "persisted_groups": 2,
        "persisted_shares": 2,
        "persisted_permission_entries": 3,
        "persisted_effective_permissions": 4,
        "share_acl_pairs_used": 2,
    }

    db = TestingSessionLocal()
    try:
        assert db.query(Snapshot).count() == 1
        assert db.query(NasUser).count() == 2
        assert db.query(NasGroup).count() == 2
        assert db.query(Share).count() == 2
        assert db.query(PermissionEntry).count() == 3
        assert db.query(EffectivePermission).count() == 4
    finally:
        db.close()

    dashboard_response = client.get("/dashboard/summary", headers=auth_headers())
    effective_permissions_response = client.get("/effective-permissions", headers=auth_headers())

    assert dashboard_response.status_code == 200
    assert dashboard_response.json() == {
        "nas_users": 2,
        "nas_groups": 2,
        "shares": 2,
        "reviews": 0,
        "snapshots": 1,
        "sync_runs": 1,
    }
    assert effective_permissions_response.status_code == 200
    assert len(effective_permissions_response.json()) == 4


def test_sync_apply_accepts_synology_acl_and_share_listing_formats() -> None:
    payload = {
        "passwd_text": (
            "admin:x:1024:100:System default user:/var/services/homes/admin:/bin/sh\n"
            "AlessandroPorcu:x:1090:100::/var/services/homes/AlessandroPorcu:/bin/sh\n"
            "anonymous:x:21:21::/nonexist:/usr/bin/nologin\n"
        ),
        "group_text": (
            "#$_@GID__INDEX@_$65539$\n"
            "administrators:x:101:admin,AlessandroPorcu,svc_naap\n"
        ),
        "shares_text": "@appconf\nEmailSaver\n'PROGETTO ADDUTTORE DX'\n",
        "acl_texts": [
            (
                "ACL version: 1\n"
                "Archive: has_ACL,is_support_ACL\n"
                "Owner: [root(user)]\n"
                "---------------------\n"
                "\t [0] group:administrators:allow:rwxpdDaARWc--:fd-- (level:0)\n"
                "\t [1] user:svc_naap:allow:rwxpdDaARWc--:fd-- (level:0)\n"
            ),
            (
                "ACL version: 1\n"
                "Archive: has_ACL,is_support_ACL\n"
                "Owner: [root(user)]\n"
                "---------------------\n"
                "\t [0] user:AlessandroPorcu:allow:r-x-----------:fd-- (level:0)\n"
            ),
        ],
    }

    response = client.post("/sync/apply", json=payload, headers=auth_headers())

    assert response.status_code == 200
    assert response.json()["persisted_users"] == 2
    assert response.json()["persisted_groups"] == 1
    assert response.json()["persisted_shares"] == 2
    assert response.json()["persisted_permission_entries"] == 3
    assert response.json()["persisted_effective_permissions"] == 4

    db = TestingSessionLocal()
    try:
        assert db.query(NasUser).count() == 2
        assert db.query(Share).count() == 2
        assert db.query(PermissionEntry).count() == 3
    finally:
        db.close()


def test_sync_live_apply_uses_connector_payload(monkeypatch) -> None:
    class FakeJobResult:
        def __init__(self) -> None:
            self.sync_result = {
                "snapshot_id": 9,
                "snapshot_checksum": "live-checksum",
                "persisted_users": 2,
                "persisted_groups": 2,
                "persisted_shares": 2,
                "persisted_permission_entries": 3,
                "persisted_effective_permissions": 4,
                "share_acl_pairs_used": 2,
            }

    monkeypatch.setattr(
        "app.api.routes.sync.run_live_sync_job",
        lambda db, trigger_type='api', initiated_by=None, source_label=None: FakeJobResult(),
    )

    response = client.post("/sync/live-apply", headers=auth_headers())

    assert response.status_code == 200
    assert response.json()["snapshot_id"] == 9
    assert response.json()["snapshot_checksum"] == "live-checksum"


def test_sync_live_apply_returns_503_when_connector_fails(monkeypatch) -> None:
    def fake_run_live_sync_job(db, trigger_type="api", initiated_by=None, source_label=None):
        raise NasConnectorError("SSH command failed: getent passwd")

    monkeypatch.setattr("app.api.routes.sync.run_live_sync_job", fake_run_live_sync_job)

    response = client.post("/sync/live-apply", headers=auth_headers())

    assert response.status_code == 503
    assert response.json()["detail"] == "SSH command failed: getent passwd"
