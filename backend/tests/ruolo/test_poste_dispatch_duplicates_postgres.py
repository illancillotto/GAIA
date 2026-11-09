"""Race verification on a disposable PostgreSQL schema, with real unique indexes."""

import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from app.modules.ruolo.poste_dispatch_models import PosteDispatchItem
from app.modules.ruolo.services import poste_dispatch as service
from app.modules.ruolo.services.poste_dispatch_state import DispatchConflict

from .poste_dispatch_fixtures import (
    PDF,
    dispatch_metadata,
    payload,
    seed_account,
    seed_batch_item,
    seed_user,
)


@pytest.fixture
def postgres():
    url = os.getenv("GAIA_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Set GAIA_TEST_POSTGRES_URL to a disposable PostgreSQL database")
    base = create_engine(url)
    assert base.dialect.name == "postgresql"
    schema = "poste_duplicates_" + uuid4().hex
    with base.begin() as connection:
        connection.execute(CreateSchema(schema))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        dispatch_metadata().create_all(engine)
        yield engine
    finally:
        engine.dispose()
        with base.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        base.dispose()


@pytest.mark.postgres
@pytest.mark.parametrize("case", ["same_source", "regenerated_notice", "different_notices"])
def test_parallel_accounts_reserve_each_notice_once_without_serializing_other_notices(
    postgres, tmp_path, case
):
    with Session(postgres) as db:
        seed_user(db)
        seed_account(db, 2, "other")
        first = seed_batch_item(db, tmp_path)
        second = first
        if case != "same_source":
            number = (
                first.payload_json["notice_number"]
                if case == "regenerated_notice"
                else "020210000000002"
            )
            second = seed_batch_item(db, tmp_path, payload_json=payload(number))
        ids = first.id, second.id
        db.commit()
    barrier = Barrier(2)

    def create(account):
        with Session(postgres) as db:
            barrier.wait(timeout=10)
            try:
                service.create_lot(
                    db,
                    title=f"Account {account}",
                    batch_item_ids=[ids[account - 1]],
                    credential_id=account,
                    actor_id=1,
                    read=lambda _item: PDF,
                )
                db.commit()
                return "created"
            except DispatchConflict:
                db.rollback()
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(create, [1, 2]))
    expected = 2 if case == "different_notices" else 1
    assert results.count("created") == expected
    assert results.count("conflict") == 2 - expected
    with Session(postgres) as db:
        assert db.scalar(select(func.count()).select_from(PosteDispatchItem)) == expected
