from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.application_user import ApplicationUser
from app.models.section_permission import RoleSectionPermission, Section
from app.modules.wiki.schemas import WikiChatResponse, WikiEvidence
from app.modules.wiki.services.policy import (
    WikiToolMeta,
    evaluate_tool_access,
    is_tool_allowed,
    sanitize_wiki_response,
)


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def setup_database() -> Generator[None, None, None]:
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


def test_is_tool_allowed_checks_module_flag() -> None:
    db: Session = TestingSessionLocal()
    user = ApplicationUser(
        username="viewer",
        email="viewer@test.local",
        password_hash="x",
        role="viewer",
        is_active=True,
        module_ruolo=False,
    )
    db.add(user)
    db.commit()

    allowed = is_tool_allowed(db, user, WikiToolMeta(name="find_ruolo_subject", module_key="ruolo"))

    assert allowed is False
    db.close()


def test_is_tool_allowed_checks_required_sections() -> None:
    db: Session = TestingSessionLocal()
    user = ApplicationUser(
        username="reviewer",
        email="reviewer@test.local",
        password_hash="x",
        role="reviewer",
        is_active=True,
        module_accessi=True,
    )
    section = Section(
        module="accessi",
        key="accessi.permissions",
        label="Permessi",
        min_role="admin",
        is_active=True,
        sort_order=1,
    )
    db.add_all([user, section])
    db.flush()
    db.add(RoleSectionPermission(section_id=section.id, role="reviewer", is_granted=True, updated_by_id=None))
    db.commit()

    allowed = is_tool_allowed(
        db,
        user,
        WikiToolMeta(name="explain_accessi_permissions", module_key="accessi", required_sections=("accessi.permissions",)),
    )

    assert allowed is True
    db.close()


def test_evaluate_tool_access_returns_reason_code_for_missing_module() -> None:
    db: Session = TestingSessionLocal()
    user = ApplicationUser(
        username="viewer_reason",
        email="viewer_reason@test.local",
        password_hash="x",
        role="viewer",
        is_active=True,
        module_operazioni=False,
    )
    db.add(user)
    db.commit()

    decision = evaluate_tool_access(db, user, WikiToolMeta(name="find_vehicle_by_id", module_key="operazioni"))

    assert decision.allowed is False
    assert decision.reason_code == "module_denied"
    db.close()


def test_sanitize_wiki_response_redacts_sensitive_payload_keys() -> None:
    response = WikiChatResponse(
        answer="Dettaglio",
        sources=[],
        found=True,
        mode="live_data",
        evidences=[
            WikiEvidence(
                type="live_data",
                label="Utente NAS",
                source_key="accessi.nas-users.mrossi",
                payload={
                    "username": "mrossi",
                    "email": "mrossi@test.local",
                    "notes": "nota interna troppo lunga " * 20,
                },
            )
        ],
    )

    sanitized = sanitize_wiki_response(WikiToolMeta(name="find_nas_user", module_key="accessi"), response)

    assert sanitized.evidences[0].payload == {"username": "mrossi"}


def test_sanitize_wiki_response_truncates_payload_lists() -> None:
    response = WikiChatResponse(
        answer="ok",
        sources=[],
        found=True,
        evidences=[
            WikiEvidence(
                type="live_data",
                label="Dettaglio",
                source_key="ruolo.subjects.1",
                payload={"latest_items": [{"idx": index} for index in range(8)]},
            )
        ],
    )

    sanitized = sanitize_wiki_response(WikiToolMeta(name="find_ruolo_subject", module_key="ruolo"), response)

    assert len(sanitized.evidences[0].payload["latest_items"]) == 5
