from __future__ import annotations

from collections.abc import Generator

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.models.section_permission import Section
from app.services.catasto_credentials import get_credential_fernet


@pytest.fixture
def session_factory(monkeypatch: pytest.MonkeyPatch) -> Generator[sessionmaker, None, None]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    key = Fernet.generate_key().decode("utf-8")
    monkeypatch.setattr("app.services.catasto_credentials.settings.credential_master_key", key)
    get_credential_fernet.cache_clear()
    yield sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    get_credential_fernet.cache_clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db(session_factory: sessionmaker) -> Generator[Session, None, None]:
    with session_factory() as session:
        yield session


@pytest.fixture
def storage_dirs(tmp_path, monkeypatch: pytest.MonkeyPatch):
    documents = tmp_path / "documents"
    imports = tmp_path / "import"
    monkeypatch.setenv("STEP_DOCUMENT_STORAGE_PATH", str(documents))
    monkeypatch.setenv("STEP_IMPORT_ROOT", str(imports))
    return documents, imports


@pytest.fixture
def client(session_factory: sessionmaker) -> Generator[TestClient, None, None]:
    def override() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override
    with session_factory() as session:
        for username, role in (
            ("step-admin", ApplicationUserRole.SUPER_ADMIN.value),
            ("step-viewer", "viewer"),
        ):
            session.add(
                ApplicationUser(
                    username=username,
                    email=f"{username}@example.local",
                    password_hash=hash_password("secret123"),
                    role=role,
                    is_active=True,
                )
            )
        session.add(
            Section(
                key="ruolo.tributi.view",
                label="Ruolo Tributi view",
                module="ruolo",
                min_role="viewer",
            )
        )
        session.commit()
    yield TestClient(app)
    app.dependency_overrides.clear()
