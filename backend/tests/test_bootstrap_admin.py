from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base as RuntimeBase
from app.core.security import verify_password
from app.db.base import Base
from app.main import _ensure_bootstrap_admin_on_startup, _ensure_gis_catalog_on_startup, _ensure_sections_on_startup
from app.models.application_user import ApplicationUser
from app.models.section_permission import Section
from app.modules.gis.bootstrap import CATASTO_GIS_LAYER_DEFINITIONS, NETWORK_GIS_LAYER_DEFINITIONS, RIORDINO_GIS_LAYER_DEFINITIONS
from app.modules.gis.models import GisLayer, GisLayerPermission
from app.services.bootstrap_admin import ensure_bootstrap_admin


def test_ensure_bootstrap_admin_creates_admin_once(monkeypatch) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    monkeypatch.setattr(
        "app.services.bootstrap_admin.settings.bootstrap_admin_username",
        "seedadmin",
    )
    monkeypatch.setattr(
        "app.services.bootstrap_admin.settings.bootstrap_admin_email",
        "seedadmin@example.local",
    )
    monkeypatch.setattr(
        "app.services.bootstrap_admin.settings.bootstrap_admin_password",
        "seed-secret",
    )

    db = SessionLocal()
    try:
        first_user, first_created = ensure_bootstrap_admin(db)
        second_user, second_created = ensure_bootstrap_admin(db)
    finally:
        db.close()

    assert first_created is True
    assert second_created is False
    assert first_user.id == second_user.id
    assert first_user.username == "seedadmin"
    assert first_user.role == "super_admin"
    assert first_user.enabled_modules == ["accessi", "rete", "inventario", "gis", "catasto", "utenze", "operazioni", "riordino", "ruolo", "presenze", "organigramma"]


def test_ensure_bootstrap_admin_updates_existing_admin(monkeypatch) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    monkeypatch.setattr(
        "app.services.bootstrap_admin.settings.bootstrap_admin_username",
        "seedadmin",
    )
    monkeypatch.setattr(
        "app.services.bootstrap_admin.settings.bootstrap_admin_email",
        "new-admin@example.local",
    )
    monkeypatch.setattr(
        "app.services.bootstrap_admin.settings.bootstrap_admin_password",
        "new-secret",
    )

    db = SessionLocal()
    try:
        db.add(
            ApplicationUser(
                username="seedadmin",
                email="old-admin@example.local",
                password_hash="pbkdf2_sha256$390000$invalid$invalid",
                role="viewer",
                is_active=False,
            )
        )
        db.commit()

        user, created = ensure_bootstrap_admin(db)
    finally:
        db.close()

    assert created is False
    assert user.email == "new-admin@example.local"
    assert user.role == "super_admin"
    assert user.is_active is True
    assert user.enabled_modules == ["accessi", "rete", "inventario", "gis", "catasto", "utenze", "operazioni", "riordino", "ruolo", "presenze", "organigramma"]
    assert verify_password("new-secret", user.password_hash) is True


def test_startup_bootstrap_skips_when_table_missing(monkeypatch) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    monkeypatch.setattr("app.main.engine", engine)
    monkeypatch.setattr("app.main.SessionLocal", SessionLocal)

    _ensure_bootstrap_admin_on_startup()


def test_startup_bootstrap_skips_when_schema_inspection_fails(monkeypatch) -> None:
    def broken_inspect(_engine):
        raise SQLAlchemyError("inspection failed")

    monkeypatch.setattr("app.main.inspect", broken_inspect)

    _ensure_bootstrap_admin_on_startup()


def test_startup_bootstrap_creates_user_when_table_exists(monkeypatch) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    RuntimeBase.metadata.create_all(bind=engine)

    monkeypatch.setattr("app.main.engine", engine)
    monkeypatch.setattr("app.main.SessionLocal", SessionLocal)
    monkeypatch.setattr("app.services.bootstrap_admin.settings.bootstrap_admin_username", "startupadmin")
    monkeypatch.setattr("app.services.bootstrap_admin.settings.bootstrap_admin_email", "startup@example.local")
    monkeypatch.setattr("app.services.bootstrap_admin.settings.bootstrap_admin_password", "startup-secret")

    _ensure_bootstrap_admin_on_startup()

    db = SessionLocal()
    try:
        user = db.query(ApplicationUser).filter(ApplicationUser.username == "startupadmin").one()
    finally:
        db.close()

    assert user.email == "startup@example.local"
    assert user.role == "super_admin"
    assert verify_password("startup-secret", user.password_hash) is True


def test_startup_sections_skip_when_table_missing(monkeypatch) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    monkeypatch.setattr("app.main.engine", engine)
    monkeypatch.setattr("app.main.SessionLocal", SessionLocal)

    _ensure_sections_on_startup()


def test_startup_sections_skip_when_schema_inspection_fails(monkeypatch) -> None:
    def broken_inspect(_engine):
        raise SQLAlchemyError("inspection failed")

    monkeypatch.setattr("app.main.inspect", broken_inspect)

    _ensure_sections_on_startup()


def test_startup_bootstrap_creates_default_sections_when_table_exists(monkeypatch) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    RuntimeBase.metadata.create_all(bind=engine)

    monkeypatch.setattr("app.main.engine", engine)
    monkeypatch.setattr("app.main.SessionLocal", SessionLocal)

    _ensure_sections_on_startup()

    db = SessionLocal()
    try:
        keys = {
            row[0]
            for row in db.query(Section.key)
            .filter(Section.module == "riordino")
            .all()
        }
    finally:
        db.close()

    assert "riordino.dashboard" in keys
    assert "riordino.practices" in keys
    assert "riordino.notifications" in keys


def test_startup_gis_catalog_skips_when_tables_missing(monkeypatch) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    monkeypatch.setattr("app.main.engine", engine)
    monkeypatch.setattr("app.main.SessionLocal", SessionLocal)

    _ensure_gis_catalog_on_startup()


def test_startup_gis_catalog_skips_when_schema_inspection_fails(monkeypatch) -> None:
    def broken_inspect(_engine):
        raise SQLAlchemyError("inspection failed")

    monkeypatch.setattr("app.main.inspect", broken_inspect)

    _ensure_gis_catalog_on_startup()


def test_startup_gis_catalog_creates_platform_layers_when_tables_exist(monkeypatch) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    RuntimeBase.metadata.create_all(bind=engine)

    monkeypatch.setattr("app.main.engine", engine)
    monkeypatch.setattr("app.main.SessionLocal", SessionLocal)

    _ensure_gis_catalog_on_startup()

    db = SessionLocal()
    try:
        layers = db.query(GisLayer).filter(GisLayer.workspace == "catasto").all()
        riordino_layers = db.query(GisLayer).filter(GisLayer.workspace == "riordino").all()
        network_layers = db.query(GisLayer).filter(GisLayer.workspace == "rete").all()
        permissions = (
            db.query(GisLayerPermission)
            .join(GisLayer)
            .filter(GisLayer.workspace == "catasto", GisLayerPermission.principal_key == "viewer")
            .all()
        )
        riordino_permissions = (
            db.query(GisLayerPermission)
            .join(GisLayer)
            .filter(GisLayer.workspace == "riordino", GisLayerPermission.principal_key == "viewer")
            .all()
        )
        network_viewer_permissions = (
            db.query(GisLayerPermission)
            .join(GisLayer)
            .filter(GisLayer.workspace == "rete", GisLayerPermission.principal_key == "viewer")
            .all()
        )
        network_operator_permissions = (
            db.query(GisLayerPermission)
            .join(GisLayer)
            .filter(GisLayer.workspace == "rete", GisLayerPermission.principal_key == "operator")
            .all()
        )
    finally:
        db.close()

    assert len(layers) == len(CATASTO_GIS_LAYER_DEFINITIONS)
    assert len(permissions) == len(CATASTO_GIS_LAYER_DEFINITIONS)
    assert len(riordino_layers) == len(RIORDINO_GIS_LAYER_DEFINITIONS)
    assert len(riordino_permissions) == len(RIORDINO_GIS_LAYER_DEFINITIONS)
    assert len(network_layers) == len(NETWORK_GIS_LAYER_DEFINITIONS)
    assert len(network_viewer_permissions) == len(NETWORK_GIS_LAYER_DEFINITIONS)
    assert len(network_operator_permissions) == len(NETWORK_GIS_LAYER_DEFINITIONS)
    assert network_operator_permissions[0].can_edit is True
