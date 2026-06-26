from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.application_user import ApplicationUser
from app.modules.accessi.routes.admin_users import _build_gate_mobile_console_map, _serialize_application_user
from app.modules.operazioni.models.wc_operator import WCOperator

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _db() -> Generator[Session, None, None]:
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_build_gate_mobile_console_map_returns_linked_operator_summary() -> None:
    Base.metadata.create_all(bind=engine)
    session = next(_db())
    try:
        user = ApplicationUser(
            username="operatore",
            email="operatore@example.local",
            password_hash="hash",
            role="viewer",
            is_active=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        operator = WCOperator(
            wc_id=900,
            first_name="Mario",
            last_name="Rossi",
            enabled=True,
            gate_mobile_console_enabled=True,
            gate_mobile_console_role="device_manager",
            gaia_user_id=user.id,
        )
        session.add(operator)
        session.commit()
        session.refresh(operator)

        summary_by_user_id = _build_gate_mobile_console_map(session, user_ids=[user.id])
        serialized = _serialize_application_user(user, gate_mobile_console=summary_by_user_id.get(user.id))

        assert serialized.gate_mobile_console is not None
        assert serialized.gate_mobile_console.operator_id == str(operator.id)
        assert serialized.gate_mobile_console.enabled is True
        assert serialized.gate_mobile_console.role == "device_manager"
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_build_gate_mobile_console_map_returns_empty_without_linked_operator() -> None:
    Base.metadata.create_all(bind=engine)
    session = next(_db())
    try:
        user = ApplicationUser(
            username="viewer",
            email="viewer@example.local",
            password_hash="hash",
            role="viewer",
            is_active=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        summary_by_user_id = _build_gate_mobile_console_map(session, user_ids=[user.id])
        serialized = _serialize_application_user(user, gate_mobile_console=summary_by_user_id.get(user.id))

        assert summary_by_user_id == {}
        assert serialized.gate_mobile_console is None
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
