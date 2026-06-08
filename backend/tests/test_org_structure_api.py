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
from app.modules.accessi.org_structure import OrgStructureAssignment
from app.modules.operazioni.models.wc_operator import WCOperator

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
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
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def create_user(username: str, role: str = "admin") -> ApplicationUser:
    db = TestingSessionLocal()
    user = ApplicationUser(
        username=username,
        email=f"{username}@example.local",
        password_hash=hash_password("secret123"),
        role=role,
        is_active=True,
        module_accessi=True,
        module_operazioni=True,
        module_inaz=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def login(username: str) -> str:
    response = client.post("/auth/login", json={"username": username, "password": "secret123"})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_org_structure_bootstrap_and_update_flow() -> None:
    admin = create_user("root", ApplicationUserRole.ADMIN.value)
    manager = create_user("mrossi", ApplicationUserRole.VIEWER.value)
    employee = create_user("lbianchi", ApplicationUserRole.VIEWER.value)
    token = login(admin.username)

    db = TestingSessionLocal()
    db.add(WCOperator(wc_id=101, username="mrossi", role="Caposettore", enabled=True, gaia_user_id=manager.id))
    db.add(WCOperator(wc_id=102, username="lbianchi", role="Operatore", enabled=True, gaia_user_id=employee.id))
    db.commit()
    db.close()

    bootstrap = client.post("/admin/org-structure/bootstrap", headers={"Authorization": f"Bearer {token}"})
    assert bootstrap.status_code == 200
    assert bootstrap.json()["created"] == 2

    workspace = client.get("/admin/org-structure", headers={"Authorization": f"Bearer {token}"})
    assert workspace.status_code == 200
    assert workspace.json()["metrics"]["published_nodes"] == 2

    update = client.put(
        f"/admin/org-structure/users/{employee.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "manager_user_id": manager.id,
            "title": "Operatore settore",
            "area_label": "Distretto Nord",
            "notes": "Validazione giornaliere",
            "is_active": True,
        },
    )
    assert update.status_code == 200
    assert update.json()["manager_user_id"] == manager.id
    assert update.json()["source_mode"] == "hybrid"


def test_org_structure_rejects_reporting_cycles() -> None:
    admin = create_user("cycle_admin", ApplicationUserRole.ADMIN.value)
    first = create_user("cycle_first", ApplicationUserRole.VIEWER.value)
    second = create_user("cycle_second", ApplicationUserRole.VIEWER.value)
    token = login(admin.username)

    db = TestingSessionLocal()
    db.add(OrgStructureAssignment(application_user_id=first.id, manager_user_id=second.id, source_mode="manual"))
    db.add(OrgStructureAssignment(application_user_id=second.id, manager_user_id=None, source_mode="manual"))
    db.commit()
    db.close()

    cycle_attempt = client.put(
        f"/admin/org-structure/users/{second.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "manager_user_id": first.id,
            "title": "Responsabile",
            "area_label": None,
            "notes": None,
            "is_active": True,
        },
    )
    assert cycle_attempt.status_code == 400
    assert cycle_attempt.json()["detail"] == "This assignment would create a reporting cycle"
