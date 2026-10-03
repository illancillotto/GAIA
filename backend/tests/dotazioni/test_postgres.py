from __future__ import annotations

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.util import load_python_file
from fastapi import HTTPException
from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from app.core.database import Base
from app.models.application_user import ApplicationUser
from app.models.section_permission import RoleSectionPermission, Section, UserSectionPermission
from app.modules.dotazioni import custody, services
from app.modules.dotazioni.models import DotazioneCustody, DotazioneEvent
from app.modules.network.models import NetworkDevice
from app.modules.operazioni.models.vehicles import Vehicle
from app.modules.organigramma.models import OrgAssignment, OrgUnit

pytestmark = pytest.mark.postgres


@pytest.fixture
def postgres():
    url = os.getenv("GAIA_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("GAIA_TEST_POSTGRES_URL non configurato")
    admin = create_engine(url)
    schema = f"test_dotazioni_{uuid4().hex}"
    with admin.begin() as connection:
        connection.execute(CreateSchema(schema))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        table_names = set()

        def include_table(table):
            if table.name in table_names:
                return
            table_names.add(table.name)
            for foreign_key in table.foreign_keys:
                include_table(foreign_key.column.table)

        for model in (
            ApplicationUser,
            OrgUnit,
            OrgAssignment,
            Section,
            RoleSectionPermission,
            UserSectionPermission,
            NetworkDevice,
            Vehicle,
        ):
            include_table(model.__table__)
        Base.metadata.create_all(
            engine, tables=[Base.metadata.tables[name] for name in table_names]
        )
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        admin.dispose()


def revision():
    return load_python_file(
        str(Path(__file__).resolve().parents[2] / "alembic/versions"), "20261001_1600_dotazioni.py"
    )


def migrate(engine, operation):
    with engine.begin() as connection:
        if operation == "upgrade":
            connection.execute(
                text("ALTER TABLE application_users DROP COLUMN IF EXISTS module_dotazioni")
            )
        with Operations.context(MigrationContext.configure(connection)):
            getattr(revision(), operation)()


def test_migration_and_concurrent_take(postgres):
    migrate(postgres, "upgrade")
    inspector = inspect(postgres)
    assert inspector.has_table("dotazioni_assets")
    assert any(
        index["name"] == "uq_dotazioni_open_custody" and index["unique"]
        for index in inspector.get_indexes("dotazioni_custodies")
    )
    with Session(postgres) as db:
        actor = ApplicationUser(
            username="admin",
            email="admin@test.local",
            password_hash="unused",
            role="super_admin",
            module_dotazioni=True,
        )
        first = ApplicationUser(
            username="first", email="first@test.local", password_hash="unused", is_active=True
        )
        second = ApplicationUser(
            username="second", email="second@test.local", password_hash="unused", is_active=True
        )
        db.add_all([actor, first, second])
        db.flush()
        asset = services.create_asset(
            db,
            actor,
            {
                "asset_code": "RAD-001",
                "asset_type": "radio",
                "name": "Radio",
                "status": "available",
            },
        )
        db.commit()
        asset_id, actor_id = asset.id, actor.id
        holder_ids = [first.id, second.id]
    barrier = threading.Barrier(2)

    def attempt(holder_id):
        with Session(postgres) as db:
            actor = db.get(ApplicationUser, actor_id)
            barrier.wait(timeout=10)
            try:
                custody.take(db, actor, asset_id, holder_id, None)
                db.commit()
                return 200
            except HTTPException as error:
                db.rollback()
                return error.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt, holder_ids)) == [200, 409]
    with Session(postgres) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(DotazioneCustody)
                .where(DotazioneCustody.returned_at.is_(None))
            )
            == 1
        )
        current = db.scalar(select(DotazioneCustody))
        actor = db.get(ApplicationUser, actor_id)
        next_id = next(
            identifier for identifier in holder_ids if identifier != current.holder_user_id
        )
        custody.transfer(db, actor, asset_id, next_id, "passaggio")
        db.rollback()
        assert db.scalar(select(func.count()).select_from(DotazioneCustody)) == 1
        assert db.scalar(select(func.count()).select_from(DotazioneEvent)) == 2
        custody.transfer(db, actor, asset_id, next_id, "passaggio")
        db.commit()
        rows = db.scalars(select(DotazioneCustody).order_by(DotazioneCustody.taken_at)).all()
        assert rows[0].returned_at == rows[1].taken_at
    migrate(postgres, "downgrade")
    assert not inspect(postgres).has_table("dotazioni_assets")
    migrate(postgres, "upgrade")
    assert inspect(postgres).has_table("dotazioni_custodies")
