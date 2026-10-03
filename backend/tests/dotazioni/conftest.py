from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.deps import require_active_user
from app.core.database import Base, get_db
from app.db import base
from app.models.application_user import ApplicationUser
from app.models.section_permission import RoleSectionPermission, Section
from app.modules.dotazioni.models import DotazioneAsset, DotazioneCustody, DotazioneEvent
from app.modules.dotazioni.router import router
from app.modules.network.models import NetworkDevice, NetworkScan
from app.modules.operazioni.models.organizational import Team
from app.modules.operazioni.models.vehicles import Vehicle
from app.modules.organigramma.models import OrgAssignment, OrgUnit


@pytest.fixture
def context():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    tables = [
        ApplicationUser.__table__,
        Section.__table__,
        base.RoleSectionPermission.__table__,
        base.UserSectionPermission.__table__,
        OrgUnit.__table__,
        OrgAssignment.__table__,
        Team.__table__,
        Vehicle.__table__,
        NetworkScan.__table__,
        NetworkDevice.__table__,
        DotazioneAsset.__table__,
        DotazioneCustody.__table__,
        DotazioneEvent.__table__,
    ]
    Base.metadata.create_all(engine, tables=tables)
    with Session(engine) as db:
        users = {}
        for name, role in (
            ("admin", "super_admin"),
            ("op", "operator"),
            ("next", "operator"),
            ("viewer", "viewer"),
            ("outsider", "operator"),
        ):
            user = ApplicationUser(
                username=name,
                email=f"{name}@test.local",
                password_hash="unused",
                role=role,
                is_active=True,
                module_dotazioni=True,
            )
            db.add(user)
            users[name] = user
        for action, role in (
            ("view", "viewer"),
            ("history", "viewer"),
            ("manage", "admin"),
            ("assign", "admin"),
            ("custody", "admin"),
        ):
            db.add(
                Section(key=f"dotazioni.{action}", label=action, module="dotazioni", min_role=role)
            )
        unit = OrgUnit(nome="Nord", tipo="squadra")
        db.add(unit)
        db.flush()
        custody_section = db.query(Section).filter_by(key="dotazioni.custody").one()
        db.add(
            RoleSectionPermission(section_id=custody_section.id, role="operator", is_granted=True)
        )
        for name in ("op", "next"):
            db.add(
                OrgAssignment(
                    user_id=users[name].id,
                    org_unit_id=unit.id,
                    active=True,
                    valid_from=datetime.now(UTC),
                )
            )
        db.commit()
        app = FastAPI()
        app.include_router(router)
        active = {"user": users["admin"]}
        app.dependency_overrides[require_active_user] = lambda: active["user"]
        app.dependency_overrides[get_db] = lambda: db
        with TestClient(app) as client:
            yield client, db, users, unit, active
    engine.dispose()
