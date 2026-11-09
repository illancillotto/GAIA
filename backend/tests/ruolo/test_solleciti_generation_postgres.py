"""Concurrency and JSON/window query semantics on an isolated PostgreSQL schema."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.ruolo.models import RuoloTributiReminderBatch, RuoloTributiReminderBatchItem
from app.modules.ruolo.services import solleciti_generation
from app.modules.ruolo.services.solleciti_workspace import workspace

from .poste_dispatch_fixtures import seed_batch_item, seed_user
from .test_poste_dispatch_duplicates_postgres import postgres as postgres


@pytest.mark.postgres
def test_two_generation_requests_persist_one_pdf_set(postgres, tmp_path, monkeypatch):
    source_id = str(uuid4())
    with Session(postgres) as db:
        seed_user(db)
        db.commit()
    monkeypatch.setattr(
        solleciti_generation.generation,
        "_candidates",
        lambda *args: [{"avvisi": [{"id": source_id}]}],
    )

    def render(db, candidates, **fields):
        item = seed_batch_item(db, tmp_path, avviso_ids_json=[source_id])
        return db.get(RuoloTributiReminderBatch, item.batch_id)

    monkeypatch.setattr(solleciti_generation.repo, "generate_reminder_batch", render)
    barrier = Barrier(2)

    def generate():
        with Session(postgres) as db:
            barrier.wait(timeout=10)
            result = solleciti_generation.generate(
                db, year=2021, tax_code="12345678901", actor_id=1
            )
            db.commit()
            return result

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: generate(), range(2)))
    assert sorted(len(result["created"]) for result in results) == [0, 1]
    assert sorted(len(result["reused"]) for result in results) == [0, 1]
    with Session(postgres) as db:
        assert db.scalar(select(func.count()).select_from(RuoloTributiReminderBatchItem)) == 1
        result = workspace(
            db,
            {
                "q": "",
                "year": 2021,
                "account": "none",
                "stage": "available",
                "page": 1,
                "page_size": 20,
            },
        )
        assert result["total"] == 1 and result["items"][0]["can_prepare"]
