from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def create_sister_extraction_tables(request: pytest.FixtureRequest) -> None:
    if "worker_db" not in request.fixturenames:
        return

    from app.models.catasto import CatastoSisterExtraction, CatastoSisterOwner, CatastoSisterParcel

    _, session_factory, _ = request.getfixturevalue("worker_db")
    engine = session_factory.kw["bind"]
    CatastoSisterExtraction.__table__.create(bind=engine)
    CatastoSisterParcel.__table__.create(bind=engine)
    CatastoSisterOwner.__table__.create(bind=engine)
