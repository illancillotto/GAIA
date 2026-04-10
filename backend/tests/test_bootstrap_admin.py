from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base as RuntimeBase
from app.core.security import verify_password
from app.db.base import Base
from app.main import _ensure_bootstrap_admin_on_startup
from app.models.application_user import ApplicationUser
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
    assert first_user.enabled_modules == ["accessi", "rete", "inventario", "catasto", "utenze", "operazioni", "riordino"]


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
    assert user.enabled_modules == ["accessi", "rete", "inventario", "catasto", "utenze", "operazioni", "riordino"]
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
