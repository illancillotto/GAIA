"""API regression tests for the riordino parcel CSV import route (R137).

An invalid ``title_holder_subject_id`` or non UTF-8 content must reject the
whole import with HTTP 422 and must not commit any parcel, including rows
that preceded the invalid one.
"""

from __future__ import annotations

from collections.abc import Generator
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import require_active_user
from app.core.database import get_db
from app.db.base import Base
from app.models.application_user import ApplicationUser
from app.modules.riordino.models import RiordinoParcelLink, RiordinoPractice
from app.modules.riordino.routes.links import router as links_router
from app.modules.utenze.models import AnagraficaSubject


@pytest.fixture
def engine() -> Generator[Engine, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    # autoflush enabled on purpose: earlier rows may be flushed by the subject
    # lookup, so the test proves that only the missing commit protects them.
    return sessionmaker(bind=engine, autocommit=False, autoflush=True)


@pytest.fixture
def seeded(session_factory: sessionmaker[Session]) -> tuple[UUID, UUID]:
    with session_factory() as db:
        user = ApplicationUser(
            username="admin",
            email="admin@example.local",
            password_hash="x",
            role="admin",
            is_active=True,
        )
        db.add(user)
        db.flush()
        practice = RiordinoPractice(
            code="PR-R137",
            title="Pratica R137",
            municipality="Comune Test",
            grid_code="G1",
            lot_code="L1",
            owner_user_id=user.id,
            created_by=user.id,
        )
        subject = AnagraficaSubject(source_name_raw="Soggetto R137", subject_type="person")
        db.add_all([practice, subject])
        db.commit()
        return practice.id, subject.id


@pytest.fixture
def client(session_factory: sessionmaker[Session], seeded: tuple[UUID, UUID]) -> TestClient:
    app = FastAPI()
    app.include_router(links_router, prefix="/api/riordino/practices")

    def override_get_db() -> Generator[Session, None, None]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    def override_user() -> ApplicationUser:
        return ApplicationUser(username="admin", role="admin", is_active=True)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_active_user] = override_user
    for dependency in links_router.dependencies:
        app.dependency_overrides[dependency.dependency] = override_user
    return TestClient(app)


def _post_csv(client: TestClient, practice_id: UUID, content: bytes):
    return client.post(
        f"/api/riordino/practices/{practice_id}/parcels/import-csv",
        files={"file": ("particelle.csv", content, "text/csv")},
    )


def _stored_parcels(session_factory: sessionmaker[Session], practice_id: UUID) -> int:
    with session_factory() as db:
        return db.scalar(
            select(func.count())
            .select_from(RiordinoParcelLink)
            .where(RiordinoParcelLink.practice_id == practice_id)
        )


def test_import_csv_invalid_subject_uuid_returns_422_and_commits_nothing(
    client: TestClient, session_factory: sessionmaker[Session], seeded: tuple[UUID, UUID]
) -> None:
    practice_id, subject_id = seeded
    content = (
        f"foglio,particella,title_holder_subject_id\n1,10,{subject_id}\n2,20,\n3,30,not-a-uuid\n"
    ).encode()

    response = _post_csv(client, practice_id, content)

    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid title_holder_subject_id at row 3"}
    assert _stored_parcels(session_factory, practice_id) == 0


def test_import_csv_invalid_utf8_returns_422_and_commits_nothing(
    client: TestClient, session_factory: sessionmaker[Session], seeded: tuple[UUID, UUID]
) -> None:
    practice_id, _ = seeded

    response = _post_csv(client, practice_id, b"foglio,particella\n1,10\n\xff,2\n")

    assert response.status_code == 422
    assert response.json() == {"detail": "CSV file must be UTF-8 encoded"}
    assert _stored_parcels(session_factory, practice_id) == 0


def test_import_csv_valid_file_still_commits_all_rows(
    client: TestClient, session_factory: sessionmaker[Session], seeded: tuple[UUID, UUID]
) -> None:
    practice_id, subject_id = seeded
    content = f"foglio,particella,title_holder_subject_id\n1,10,{subject_id}\n2,20,\n".encode()

    response = _post_csv(client, practice_id, content)

    assert response.status_code == 200
    body = response.json()
    assert [(item["foglio"], item["particella"]) for item in body] == [("1", "10"), ("2", "20")]
    assert body[0]["title_holder_subject_id"] == str(subject_id)
    assert _stored_parcels(session_factory, practice_id) == 2
