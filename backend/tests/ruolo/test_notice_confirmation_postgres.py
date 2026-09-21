"""Real commit fence and concurrent confirmation, isolated PostgreSQL schemas."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.ruolo.notice_confirmation_models import NoticeGenerationConfirmation
from app.modules.ruolo.services.notice_draft_review import confirm_generation
from app.modules.ruolo.services.notice_revision import GenerationRevisionChanged

from .test_notice_draft_inputs import _generate
from .test_notice_generation_concurrency import _change_eligibility
from .test_notice_revision import generation_engine as generation_engine
from .test_notice_revision import real_revision_engine as real_revision_engine


def test_concurrent_confirmation_is_idempotent(real_revision_engine, tmp_path, monkeypatch):
    engine = real_revision_engine
    identifier, _, _, _ = _generate(engine, tmp_path, monkeypatch, batch=True)
    barrier = Barrier(2, timeout=10)

    def confirm(_):
        with Session(engine) as db, db.begin():
            barrier.wait()
            return confirm_generation(db, identifier, batch=True, actor_id=1).id

    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(confirm, range(2)))
    assert ids[0] == ids[1]
    with Session(engine) as db:
        assert len(db.scalars(select(NoticeGenerationConfirmation)).all()) == 1


@pytest.mark.parametrize("change", ["payment", "notification", "step"])
def test_disqualifying_commit_blocks_confirmation(
    real_revision_engine, tmp_path, monkeypatch, change
):
    engine = real_revision_engine
    identifier, avviso_id, document_id, _ = _generate(engine, tmp_path, monkeypatch, batch=True)
    _change_eligibility(engine, avviso_id, document_id, change)
    with Session(engine) as db, db.begin():
        with pytest.raises(GenerationRevisionChanged):
            confirm_generation(db, identifier, batch=True, actor_id=1)
    with Session(engine) as db:
        assert db.scalar(select(NoticeGenerationConfirmation)) is None
