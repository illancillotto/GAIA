from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.models.snapshot import Snapshot
from app.models.sync_run import SyncRun
from app.schemas.sync import SyncPreviewRequest
from app.services.nas_connector import NasConnectorError
from app.services.sync import apply_live_sync, build_live_sync_payload


class FakeNasClient:
    def __init__(self) -> None:
        self.commands: list[str] = []

    def run_command(self, command: str) -> str:
        self.commands.append(command)
        mapping = {
            "getent passwd": (
                "mrossi:x:1001:100:Mario Rossi:/var/services/homes/mrossi:/sbin/nologin\n"
                "lbianchi:x:1002:100:Laura Bianchi:/var/services/homes/lbianchi:/sbin/nologin\n"
            ),
            "getent group": (
                "amministrazione:x:2001:mrossi\n"
                "direzione:x:2002:lbianchi\n"
            ),
            "ls /volume1": "contabilita\ndirezione\n",
            "find /volume1/contabilita \\( -name '@*' -o -name '#recycle' \\) -prune -o -mindepth 1 -type d -print 2>/dev/null || true": "/volume1/contabilita/reporting\n",
            "find /volume1/direzione \\( -name '@*' -o -name '#recycle' \\) -prune -o -mindepth 1 -type d -print 2>/dev/null || true": "",
            "synoacltool -get /volume1/contabilita": (
                "allow: group:amministrazione:read,write\n"
                "deny: user:ospite:read\n"
            ),
            "synoacltool -get /volume1/direzione": "allow: group:direzione:write\n",
            "synoacltool -get /volume1/contabilita/reporting": "allow: group:amministrazione:write\n",
        }
        return mapping[command]


def test_build_live_sync_payload_fetches_base_and_acl_commands(monkeypatch) -> None:
    monkeypatch.setattr("app.services.sync.settings.nas_passwd_command", "getent passwd")
    monkeypatch.setattr("app.services.sync.settings.nas_group_command", "getent group")
    monkeypatch.setattr("app.services.sync.settings.nas_shares_command", "ls /volume1")
    monkeypatch.setattr(
        "app.services.sync.settings.nas_share_subpaths_command",
        "find /volume1/{share} \\( -name '@*' -o -name '#recycle' \\) -prune -o -mindepth 1 -type d -print 2>/dev/null || true",
    )
    monkeypatch.setattr(
        "app.services.sync.settings.nas_acl_command_template",
        "synoacltool -get /volume1/{share}",
    )

    client = FakeNasClient()
    payload = build_live_sync_payload(client)

    assert isinstance(payload, SyncPreviewRequest)
    assert payload.shares_text == "contabilita\ndirezione\ncontabilita/reporting\n"
    assert payload.acl_texts == [
        "allow: group:amministrazione:read,write\ndeny: user:ospite:read\n",
        "allow: group:direzione:write\n",
        "allow: group:amministrazione:write\n",
    ]
    assert client.commands == [
        "getent passwd",
        "getent group",
        "ls /volume1",
        "find /volume1/contabilita \\( -name '@*' -o -name '#recycle' \\) -prune -o -mindepth 1 -type d -print 2>/dev/null || true",
        "find /volume1/direzione \\( -name '@*' -o -name '#recycle' \\) -prune -o -mindepth 1 -type d -print 2>/dev/null || true",
        "synoacltool -get /volume1/contabilita",
        "synoacltool -get /volume1/direzione",
        "synoacltool -get /volume1/contabilita/reporting",
    ]


def test_apply_live_sync_persists_snapshot_from_live_payload(monkeypatch) -> None:
    monkeypatch.setattr("app.services.sync.settings.nas_passwd_command", "getent passwd")
    monkeypatch.setattr("app.services.sync.settings.nas_group_command", "getent group")
    monkeypatch.setattr("app.services.sync.settings.nas_shares_command", "ls /volume1")
    monkeypatch.setattr(
        "app.services.sync.settings.nas_share_subpaths_command",
        "find /volume1/{share} \\( -name '@*' -o -name '#recycle' \\) -prune -o -mindepth 1 -type d -print 2>/dev/null || true",
    )
    monkeypatch.setattr(
        "app.services.sync.settings.nas_acl_command_template",
        "synoacltool -get /volume1/{share}",
    )

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        reviewer = ApplicationUser(
            username="reviewer",
            email="reviewer@example.local",
            password_hash=hash_password("secret123"),
            role=ApplicationUserRole.ADMIN.value,
            is_active=True,
        )
        db.add(reviewer)
        db.commit()

        result = apply_live_sync(db, FakeNasClient())

        assert result.persisted_users == 2
        assert result.persisted_groups == 2
        assert result.persisted_shares == 3
        assert result.persisted_permission_entries == 4
        assert result.persisted_effective_permissions == 6
        assert db.query(Snapshot).count() == 1
        assert db.query(SyncRun).count() == 0
    finally:
        db.close()


def test_build_live_sync_payload_skips_shares_with_unreadable_acl(monkeypatch) -> None:
    class PartialAclClient(FakeNasClient):
        def run_command(self, command: str) -> str:
            if command == "synoacltool -get /volume1/contabilita/reporting":
                raise NasConnectorError("acl denied")
            return super().run_command(command)

    monkeypatch.setattr("app.services.sync.settings.nas_passwd_command", "getent passwd")
    monkeypatch.setattr("app.services.sync.settings.nas_group_command", "getent group")
    monkeypatch.setattr("app.services.sync.settings.nas_shares_command", "ls /volume1")
    monkeypatch.setattr(
        "app.services.sync.settings.nas_share_subpaths_command",
        "find /volume1/{share} \\( -name '@*' -o -name '#recycle' \\) -prune -o -mindepth 1 -type d -print 2>/dev/null || true",
    )
    monkeypatch.setattr(
        "app.services.sync.settings.nas_acl_command_template",
        "synoacltool -get /volume1/{share}",
    )

    payload = build_live_sync_payload(PartialAclClient())

    assert payload.shares_text == "contabilita\ndirezione\n"
    assert payload.acl_texts == [
        "allow: group:amministrazione:read,write\ndeny: user:ospite:read\n",
        "allow: group:direzione:write\n",
    ]
