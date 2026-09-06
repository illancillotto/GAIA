"""Verify the retry row locks against an isolated PostgreSQL schema."""

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, CreateTable, DropSchema

from app.models.catasto import CatastoBatch, CatastoVisuraRequest
from app.services.elaborazioni_batches import BatchConflictError, retry_failed_batch


def test_manual_retry_waits_for_batch_owner_and_rechecks_status():
    url = os.getenv("GAIA_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("GAIA_TEST_POSTGRES_URL not configured")
    schema = "test_sister_retry_" + uuid4().hex
    admin = create_engine(url)
    assert admin.dialect.name == "postgresql"
    with admin.begin() as connection:
        connection.execute(CreateSchema(schema))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        with engine.begin() as connection:
            for table in (CatastoBatch.__table__, CatastoVisuraRequest.__table__):
                connection.execute(CreateTable(table, include_foreign_key_constraints=[]))
        with Session(engine) as db:
            batch = CatastoBatch(user_id=1, name="Lock test", status="failed", total_items=1)
            db.add(batch)
            db.flush()
            db.add(CatastoVisuraRequest(batch_id=batch.id, user_id=1, row_index=1, status="failed"))
            db.commit()
            batch_id = batch.id
        with Session(engine) as owner, Session(engine) as retry:
            batch = owner.get(CatastoBatch, batch_id, with_for_update=True)
            retry.execute(text("SET LOCAL lock_timeout = '200ms'"))
            with pytest.raises(OperationalError, match="lock timeout"):
                retry_failed_batch(retry, 1, batch_id)
            retry.rollback()
            batch.status = "processing"
            owner.commit()
            with pytest.raises(BatchConflictError, match="while batch is processing"):
                retry_failed_batch(retry, 1, batch_id)
            retry.rollback()
            row = retry.query(CatastoVisuraRequest).one()
            assert row.status == "failed"
            assert row.attempts == 0
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        admin.dispose()
