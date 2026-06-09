from collections.abc import Callable, Generator

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
from app.scripts.bootstrap_sections import ensure_default_sections

engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_database() -> Generator[None, None, None]:
    app.dependency_overrides[get_db] = _override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        ensure_default_sections(db)
    finally:
        db.close()
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def session() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def make_user() -> Callable[..., ApplicationUser]:
    def _make(
        username: str,
        *,
        role: str = ApplicationUserRole.ADMIN.value,
        module_organigramma: bool = True,
        module_inaz: bool = False,
        full_name: str | None = None,
        is_active: bool = True,
    ) -> ApplicationUser:
        db = TestingSessionLocal()
        try:
            user = ApplicationUser(
                username=username,
                email=f"{username}@example.local",
                full_name=full_name or username.title(),
                password_hash=hash_password("secret123"),
                role=role,
                is_active=is_active,
                module_organigramma=module_organigramma,
                module_inaz=module_inaz,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            db.expunge(user)
            return user
        finally:
            db.close()

    return _make


@pytest.fixture
def login(client: TestClient) -> Callable[[str], str]:
    def _login(username: str) -> str:
        response = client.post(
            "/auth/login", json={"username": username, "password": "secret123"}
        )
        assert response.status_code == 200, response.text
        return response.json()["access_token"]

    return _login


@pytest.fixture
def auth_header(login: Callable[[str], str]) -> Callable[[str], dict[str, str]]:
    def _header(username: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {login(username)}"}

    return _header
