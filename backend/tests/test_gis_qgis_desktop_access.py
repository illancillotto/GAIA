from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.models.application_user import ApplicationUser
from app.modules.gis import qgis_desktop_access as access
from app.modules.gis.models import GisLayer


class _Result:
    def __init__(self, value: object) -> None:
        self.value = value

    def scalar_one_or_none(self) -> object:
        return self.value


class _Database:
    def __init__(self, session: Session, role_state: bool | None) -> None:
        self.session = session
        self.role_state = role_state
        self.statements: list[tuple[str, dict[str, object] | None]] = []
        self.commits = 0

    def execute(self, statement: object, params: dict[str, object] | None = None) -> _Result:
        sql = str(statement)
        self.statements.append((sql, params))
        return _Result(self.role_state if "FROM pg_roles" in sql else None)

    def scalars(self, statement: object):
        return self.session.scalars(statement)

    def commit(self) -> None:
        self.commits += 1

    def get_bind(self) -> SimpleNamespace:
        return SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))


@pytest.fixture
def db() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    GisLayer.metadata.create_all(
        engine,
        tables=[ApplicationUser.__table__, GisLayer.__table__],
    )
    with Session(engine) as session:
        yield session


def _user(*, module_gis: bool = True, is_active: bool = True) -> ApplicationUser:
    return ApplicationUser(
        id=42,
        username="alice",
        email="alice@example.local",
        password_hash="unused",
        role="super_admin",
        module_gis=module_gis,
        is_active=is_active,
    )


def _layer(db: Session) -> GisLayer:
    layer = GisLayer(
        workspace="rete",
        name="condotte",
        title="Condotte",
        source_type="postgis",
        postgis_schema="network",
        postgis_table="pipes",
        geometry_column="geometry",
        geometry_type="LINESTRING",
        is_active=True,
        metadata_json={"qgis": {"mode": "published"}},
    )
    db.add(layer)
    db.commit()
    return layer


def test_role_name_is_stable_and_scoped_to_gaia_user() -> None:
    assert access.role_name(_user()) == "gaia_qgis_u_42"


def test_visible_layers_follow_project_and_user_permissions(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    visible = _layer(db)
    hidden = GisLayer(
        workspace="rete",
        name="hidden",
        title="Hidden",
        source_type="postgis",
        postgis_table="hidden",
        geometry_column="geometry",
        is_active=True,
    )
    db.add(hidden)
    db.commit()
    monkeypatch.setitem(
        sys.modules,
        "app.modules.gis.services",
        SimpleNamespace(
            _permission_flags=lambda _db, layer_id, _user: {"can_view": layer_id == visible.id}
        ),
    )
    assert access._visible_layers(db, _user()) == [visible]


def test_status_requires_active_gis_account_and_existing_database_login(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    layer = _layer(db)
    monkeypatch.setattr(access, "_visible_layers", lambda *_args: [layer])
    active = _user()
    assert access.access_status(_Database(db, None), active) == {
        "enabled": False,
        "username": "gaia_qgis_u_42",
        "layer_count": 0,
    }
    assert access.access_status(_Database(db, True), active)["layer_count"] == 1
    assert access.access_status(_Database(db, True), _user(module_gis=False))["layer_count"] == 0
    assert access.access_status(_Database(db, True), _user(is_active=False))["enabled"] is False


def test_sqlite_status_and_disable_fail_closed(db: Session) -> None:
    assert access.access_status(db, _user()) == {
        "enabled": False,
        "username": "gaia_qgis_u_42",
        "layer_count": 0,
    }
    access.disable_access(db, _user())
    with pytest.raises(HTTPException) as error:
        access.provision_access(db, _user())
    assert error.value.status_code == 503


@pytest.mark.parametrize(
    "user",
    [_user(module_gis=False), _user(is_active=False)],
)
def test_provision_requires_active_user_with_gis_module(db: Session, user: ApplicationUser) -> None:
    with pytest.raises(HTTPException) as error:
        access.provision_access(_Database(db, None), user)
    assert error.value.status_code == 409


def test_provision_requires_at_least_one_visible_layer(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(access, "_visible_layers", lambda *_args: [])
    with pytest.raises(HTTPException, match="non ha layer GIS Desktop visibili"):
        access.provision_access(_Database(db, None), _user())


def test_provision_creates_read_only_role_and_one_time_password(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    layer = _layer(db)
    monkeypatch.setattr(access, "_visible_layers", lambda *_args: [layer])
    database = _Database(db, None)

    result = access.provision_access(database, _user())

    sql = "\n".join(statement for statement, _ in database.statements)
    assert result["enabled"] is True
    assert result["username"] == "gaia_qgis_u_42"
    assert len(str(result["password"])) >= 24
    assert result["layer_count"] == 1
    assert 'CREATE ROLE "gaia_qgis_u_42"' in sql
    assert "NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION" in sql
    assert 'CREATE OR REPLACE VIEW "gis_qgis".' in sql
    assert 'GRANT SELECT ON "gis_qgis".' in sql
    assert "GRANT INSERT" not in sql
    assert database.commits == 1


def test_provision_rotates_existing_role_without_recreating_it(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(access, "_visible_layers", lambda *_args: [_layer(db)])
    database = _Database(db, True)

    result = access.provision_access(database, _user())

    assert result["password"]
    assert not any(sql.startswith("CREATE ROLE") for sql, _ in database.statements)


def test_provision_skips_database_grant_without_database_name(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(access, "_visible_layers", lambda *_args: [_layer(db)])
    monkeypatch.setattr(
        access.settings,
        "database_url",
        "postgresql://admin:secret@postgres:5432/",
    )
    database = _Database(db, True)

    access.provision_access(database, _user())

    assert not any("GRANT CONNECT" in sql for sql, _ in database.statements)


def test_disable_is_idempotent_and_can_share_callers_transaction(db: Session) -> None:
    absent = _Database(db, None)
    access.disable_access(absent, _user())
    assert len(absent.statements) == 1
    assert "FROM pg_roles" in absent.statements[0][0]
    assert absent.commits == 0

    database = _Database(db, True)
    access.disable_access(database, _user(), commit=False)
    sql = "\n".join(statement for statement, _ in database.statements)
    assert 'ALTER ROLE "gaia_qgis_u_42" NOLOGIN' in sql
    assert "pg_terminate_backend" in sql
    assert "REVOKE ALL PRIVILEGES" in sql
    assert database.commits == 0

    access.disable_access(database, _user())
    assert database.commits == 1


def test_sync_enabled_users_reconciles_only_active_database_logins(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    users = [_user()]
    db.add(users[0])
    db.commit()
    monkeypatch.setattr(access, "_role_can_login", lambda *_args: True)
    monkeypatch.setattr(access, "_visible_layers", lambda *_args: [])
    database = _Database(db, True)

    access.sync_enabled_users(database)

    sql = "\n".join(statement for statement, _ in database.statements)
    assert "REVOKE ALL PRIVILEGES" in sql
    assert "REVOKE USAGE ON SCHEMA" in sql


def test_sync_skips_users_without_an_enabled_login(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = _user()
    db.add(user)
    db.commit()
    monkeypatch.setattr(access, "_role_can_login", lambda *_args: False)
    database = _Database(db, False)

    access.sync_enabled_users(database)

    assert database.statements == []


def test_sync_is_a_noop_for_sqlite(db: Session) -> None:
    access.sync_enabled_users(db)
