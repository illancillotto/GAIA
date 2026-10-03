"""Real PostgreSQL serialization and reversible additive voucher migration."""

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.util import load_python_file
from fastapi import HTTPException
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from app.models.application_user import ApplicationUser
from app.modules.presenze.models import (
    PresenzeCollaborator,
    PresenzeCredential,
    PresenzeDailyRecord,
    PresenzeImportJob,
    PresenzeSyncJob,
)
from app.modules.presenze.services.auto_sync import _try_acquire_auto_sync_lock
from app.modules.presenze.services.meal_vouchers import apply_manual_meal_voucher
from app.modules.presenze.services.sync_start import ensure_sync_start_available

pytestmark = pytest.mark.postgres


@pytest.fixture
def operations_engine():
    url = os.getenv("GAIA_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("GAIA_TEST_POSTGRES_URL not configured")
    schema = "test_presenze_ops_" + uuid.uuid4().hex
    admin = create_engine(url)
    with admin.begin() as conn:
        conn.execute(CreateSchema(schema))
    engine = create_engine(url, connect_args={"options": "-csearch_path=" + schema})
    tables = [
        ApplicationUser.__table__,
        PresenzeCollaborator.__table__,
        PresenzeCredential.__table__,
        PresenzeImportJob.__table__,
        PresenzeDailyRecord.__table__,
        PresenzeSyncJob.__table__,
    ]
    for table in tables:
        table.create(engine)
    with Session(engine) as db:
        db.add(
            ApplicationUser(
                id=1,
                username="test",
                email="test@example.invalid",
                password_hash="not-a-real-password",
                role="admin",
                is_active=True,
            )
        )
        db.commit()
    try:
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as conn:
            conn.execute(DropSchema(schema, cascade=True))
        admin.dispose()


def test_manual_start_and_scheduler_share_lock_through_commit(operations_engine):
    with Session(operations_engine) as first, Session(operations_engine) as second:
        ensure_sync_start_available(first)
        assert not _try_acquire_auto_sync_lock(second)
        second.rollback()
        with pytest.raises(HTTPException) as conflict:
            ensure_sync_start_available(second)
        assert conflict.value.status_code == 409
        second.rollback()
        first.add(
            PresenzeSyncJob(
                status="pending",
                requested_by_user_id=1,
                period_start=date(2026, 10, 1),
                period_end=date(2026, 10, 31),
                params_json={"mode": "sync"},
            )
        )
        first.commit()
        with pytest.raises(HTTPException) as pending:
            ensure_sync_start_available(second)
        assert pending.value.status_code == 409
        second.rollback()
        first.execute(text("UPDATE presenze_sync_jobs SET status='failed'"))
        first.commit()
        ensure_sync_start_available(second)
        second.rollback()
        assert _try_acquire_auto_sync_lock(first)
        first.rollback()


def test_concurrent_manual_grants_create_one_audit_entry(operations_engine):
    with Session(operations_engine) as db:
        person = PresenzeCollaborator(employee_code="test", name="Test", owner_user_id=1)
        db.add(person)
        db.flush()
        record = PresenzeDailyRecord(
            collaborator_id=person.id, owner_user_id=1, work_date=date(2026, 10, 1)
        )
        db.add(record)
        db.commit()
        rid = record.id

    def grant():
        with Session(operations_engine) as db:
            record = db.get(PresenzeDailyRecord, rid)
            apply_manual_meal_voucher(db, record, True, 1)
            db.commit()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(grant) for _ in range(2)]
        for future in futures:
            future.result(timeout=10)
    with Session(operations_engine) as db:
        record = db.get(PresenzeDailyRecord, rid)
        assert record.meal_voucher_manual and len(record.meal_voucher_audit) == 1


def test_voucher_migration_round_trip_preserves_existing_daily_data(operations_engine):
    module = load_python_file(
        str(Path(__file__).parents[1] / "alembic/versions"),
        "20261001_1400_presenze_manual_meal_voucher.py",
    )
    with operations_engine.begin() as conn:
        conn.execute(text("ALTER TABLE presenze_daily_records DROP COLUMN meal_voucher_manual"))
        conn.execute(text("ALTER TABLE presenze_daily_records DROP COLUMN meal_voucher_audit"))
        person = uuid.uuid4()
        record = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO presenze_collaborators (id,employee_code,name,is_active) VALUES (:id,'test','Test',true)"
            ),
            {"id": person},
        )
        conn.execute(
            text(
                "INSERT INTO presenze_daily_records (id,collaborator_id,work_date,ordinary_minutes,trasferta_montano,reperibilita_unit,validation_status) VALUES (:id,:cid,'2026-10-01',420,false,'none','pending')"
            ),
            {"id": record, "cid": person},
        )
        with Operations.context(MigrationContext.configure(conn)):
            module.upgrade()
        row = conn.execute(
            text(
                "SELECT ordinary_minutes,meal_voucher_manual,meal_voucher_audit FROM presenze_daily_records"
            )
        ).one()
        assert tuple(row) == (420, False, None)
        with Operations.context(MigrationContext.configure(conn)):
            module.downgrade()
        assert conn.scalar(text("SELECT ordinary_minutes FROM presenze_daily_records")) == 420
        assert "meal_voucher_manual" not in {
            c["name"] for c in inspect(conn).get_columns("presenze_daily_records")
        }
        with Operations.context(MigrationContext.configure(conn)):
            module.upgrade()
