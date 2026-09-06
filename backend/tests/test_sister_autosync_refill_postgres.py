"""Real row-lock races against a disposable PostgreSQL schema."""

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, CreateTable, DropSchema

from app.models.catasto import (
    CatastoBatch,
    CatastoPerpetualSyncItem,
    CatastoRuoloAutoSyncConfig,
    CatastoVisuraRequest,
)
from app.services.elaborazioni_perpetual_sync import _refill_deferred_batch


@pytest.mark.parametrize(
    "locked_model", [CatastoBatch, CatastoVisuraRequest, CatastoPerpetualSyncItem]
)
def test_refill_cannot_overtake_worker_or_another_planner(locked_model):
    url = os.getenv("GAIA_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("GAIA_TEST_POSTGRES_URL not configured")
    schema = "test_sister_refill_" + uuid4().hex
    admin = create_engine(url)
    assert admin.dialect.name == "postgresql"
    with admin.begin() as connection:
        connection.execute(CreateSchema(schema))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        with engine.begin() as connection:
            for model in (
                CatastoBatch,
                CatastoVisuraRequest,
                CatastoPerpetualSyncItem,
                CatastoRuoloAutoSyncConfig,
            ):
                connection.execute(CreateTable(model.__table__, include_foreign_key_constraints=[]))
        now = datetime.now(UTC)
        with Session(engine) as db:
            batch = CatastoBatch(
                user_id=1,
                name="Refill",
                batch_kind="perpetual_sync",
                status="processing",
                total_items=1,
            )
            config = CatastoRuoloAutoSyncConfig(user_id=1, enabled=True, batch_size=2)
            db.add_all([batch, config])
            db.flush()
            request = CatastoVisuraRequest(
                batch_id=batch.id,
                user_id=1,
                row_index=1,
                status="pending",
                sister_remote_state="pending",
                sister_remote_request_id="ORIGINAL",
                sister_remote_request_url="https://sister/requests",
                sister_credential_id=uuid4(),
                sister_first_submitted_at=now,
                retry_not_before=now + timedelta(minutes=5),
            )
            item = CatastoPerpetualSyncItem(
                user_id=1,
                scope="ruolo_particella",
                target_key="new",
                status="pending",
                priority=10,
                search_mode="immobile",
                comune="Comune",
                comune_codice="C",
                foglio="1",
                particella="1",
                next_due_at=now,
            )
            db.add_all([request, item])
            db.commit()
            ids = {
                CatastoBatch: batch.id,
                CatastoVisuraRequest: request.id,
                CatastoPerpetualSyncItem: item.id,
            }
            config_id = config.id
        with Session(engine) as owner, Session(engine) as planner:
            config = planner.get(CatastoRuoloAutoSyncConfig, config_id)
            owner.get(locked_model, ids[locked_model], with_for_update=True)
            assert _refill_deferred_batch(planner, config) is None
            planner.rollback()
            assert len(list(planner.scalars(select(CatastoVisuraRequest)))) == 1
            owner.rollback()
            assert _refill_deferred_batch(planner, config).id == ids[CatastoBatch]
            requests = list(
                planner.scalars(
                    select(CatastoVisuraRequest).order_by(CatastoVisuraRequest.row_index)
                )
            )
            assert len(requests) == 2
            assert requests[0].sister_remote_request_id == "ORIGINAL"
            assert requests[1].row_index == 2
            assert _refill_deferred_batch(planner, config) is None
            assert len(list(planner.scalars(select(CatastoBatch)))) == 1
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        admin.dispose()
