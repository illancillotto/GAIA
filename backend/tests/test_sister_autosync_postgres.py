"""Campaign preflight must serialize with both item and request owners."""

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, CreateTable, DropSchema

from app.models.catasto import CatastoBatch, CatastoPerpetualSyncItem, CatastoVisuraRequest
from app.modules.elaborazioni.sister_manual_retry import BatchConflictError
from app.services.elaborazioni_perpetual_sync import retry_perpetual_sync_failures


@pytest.mark.parametrize("lock_item", [True, False])
def test_campaign_retry_locks_and_reloads_remote_evidence(lock_item):
    url = os.getenv("GAIA_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("GAIA_TEST_POSTGRES_URL not configured")
    schema = "test_sister_campaign_" + uuid4().hex
    admin = create_engine(url)
    assert admin.dialect.name == "postgresql"
    with admin.begin() as connection:
        connection.execute(CreateSchema(schema))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        with engine.begin() as connection:
            for model in (CatastoBatch, CatastoVisuraRequest, CatastoPerpetualSyncItem):
                connection.execute(CreateTable(model.__table__, include_foreign_key_constraints=[]))
        with Session(engine) as db:
            batch = CatastoBatch(
                user_id=1, name="Campaign lock test", status="failed", total_items=1
            )
            db.add(batch)
            db.flush()
            request = CatastoVisuraRequest(
                batch_id=batch.id, user_id=1, row_index=1, status="failed", attempts=0
            )
            db.add(request)
            db.flush()
            item = CatastoPerpetualSyncItem(
                user_id=1,
                scope="ruolo_particella",
                target_key="test",
                status="failed",
                priority=10,
                search_mode="immobile",
                next_due_at=datetime.now(UTC),
                linked_request_id=request.id,
                linked_batch_id=batch.id,
            )
            db.add(item)
            db.commit()
            item_id, request_id = item.id, request.id
        with Session(engine) as owner, Session(engine) as retry:
            stale = retry.get(CatastoVisuraRequest, request_id)
            assert stale.attempts == 0
            model, identifier = (
                (CatastoPerpetualSyncItem, item_id)
                if lock_item
                else (CatastoVisuraRequest, request_id)
            )
            owner.get(model, identifier, with_for_update=True)
            retry.execute(text("SET LOCAL lock_timeout = '200ms'"))
            with pytest.raises(OperationalError, match="lock timeout"):
                retry_perpetual_sync_failures(retry, 1, "ruolo_particella")
            retry.rollback()
            stale = retry.get(CatastoVisuraRequest, request_id)
            remote = owner.get(CatastoVisuraRequest, request_id)
            remote.attempts = 1
            remote.sister_remote_request_id = "REMOTE"
            owner.commit()
            with pytest.raises(BatchConflictError, match="Nessun elemento"):
                retry_perpetual_sync_failures(retry, 1, "ruolo_particella")
            assert stale.attempts == 1
            retry.rollback()
            assert retry.get(CatastoPerpetualSyncItem, item_id).status == "failed"
            assert retry.get(CatastoPerpetualSyncItem, item_id).linked_request_id == request_id
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        admin.dispose()
