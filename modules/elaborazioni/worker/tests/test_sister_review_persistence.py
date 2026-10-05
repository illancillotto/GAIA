from datetime import UTC, datetime
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.application_user import ApplicationUser
from app.models.catasto import CatastoBatch, CatastoDocument, CatastoVisuraRequest
from sister_exceptions import SisterNonEvadibileReviewRequiredError


@pytest.mark.parametrize("claim", ["current", "stale", "cancelled"])
def test_non_evadibile_review_persists_only_active_claim(tmp_path, monkeypatch, claim):
    monkeypatch.setenv("CREDENTIAL_MASTER_KEY", Fernet.generate_key().decode())
    import worker as worker_module

    engine = create_engine(f"sqlite:///{tmp_path / 'review.sqlite'}")
    for model in (ApplicationUser, CatastoBatch, CatastoDocument, CatastoVisuraRequest):
        model.__table__.create(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False)
    monkeypatch.setattr(worker_module, "SessionLocal", session_factory)
    worker = object.__new__(worker_module.CatastoWorker)
    token = uuid4()
    credential_id = uuid4()
    submitted = datetime(2026, 10, 5, 6, 37, tzinfo=UTC)
    error = SisterNonEvadibileReviewRequiredError(
        "SISTER non evadibile: richiesta remota 2060784896 conservata; verifica manuale necessaria"
    )
    try:
        with session_factory() as db:
            user = ApplicationUser(
                username="review-test",
                email="review@example.local",
                password_hash="hash",
                role="admin",
                is_active=True,
            )
            db.add(user)
            db.flush()
            batch = CatastoBatch(
                user_id=user.id,
                total_items=1,
                status="cancelled" if claim == "cancelled" else "processing",
            )
            db.add(batch)
            db.flush()
            request = CatastoVisuraRequest(
                batch_id=batch.id,
                user_id=user.id,
                row_index=1,
                status="processing",
                execution_token=token,
                sister_credential_id=credential_id,
                sister_remote_request_id="2060784896",
                sister_remote_request_url="https://sister/richieste",
                sister_remote_state="pending",
                sister_first_submitted_at=submitted,
                attempts=1,
            )
            db.add(request)
            db.flush()
            batch_id, request_id, user_id = batch.id, request.id, user.id
            db.commit()
        worker._request_repository().fail_request(
            batch_id, request_id, str(error), uuid4() if claim == "stale" else token
        )
        with session_factory() as db:
            request = db.get(CatastoVisuraRequest, request_id)
            batch = db.get(CatastoBatch, batch_id)
            assert request.user_id == user_id
            assert request.sister_credential_id == credential_id
            assert request.sister_remote_request_id == "2060784896"
            assert request.sister_remote_request_url == "https://sister/richieste"
            assert request.sister_remote_state == "pending"
            assert request.sister_first_submitted_at == submitted.replace(tzinfo=None)
            assert request.attempts == 1
            assert request.document_id is None
            if claim == "current":
                assert request.status == "failed"
                assert request.error_message == str(error)
                assert request.execution_token is None
                assert request.retry_not_before is None
                assert request.processed_at is not None
                assert batch.failed_items == 1
            else:
                assert request.status == "processing"
                assert request.execution_token == token
                assert request.error_message is None
                assert batch.failed_items == 0
    finally:
        engine.dispose()
