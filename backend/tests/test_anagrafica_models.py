import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.utenze.models import AnagraficaCompany, AnagraficaPerson, AnagraficaPersonSnapshot, AnagraficaSubject


@pytest.fixture
def db_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_anagrafica_tables_are_registered_in_metadata() -> None:
    table_names = set(Base.metadata.tables.keys())

    assert "ana_subjects" in table_names
    assert "ana_persons" in table_names
    assert "ana_person_snapshots" in table_names
    assert "ana_companies" in table_names
    assert "ana_documents" in table_names
    assert "ana_import_jobs" in table_names
    assert "ana_audit_log" in table_names


def test_can_persist_person_and_company_subjects(db_session: Session) -> None:
    person_subject = AnagraficaSubject(
        subject_type="person",
        status="active",
        source_name_raw="Rossi_Mario_RSSMRA80A01H501Z",
        nas_folder_path="/volume1/settore catasto/ARCHIVIO/R/Rossi_Mario_RSSMRA80A01H501Z",
        nas_folder_letter="R",
        requires_review=False,
    )
    company_subject = AnagraficaSubject(
        subject_type="company",
        status="active",
        source_name_raw="Acme_Srl_12345678901",
        nas_folder_path="/volume1/settore catasto/ARCHIVIO/A/Acme_Srl_12345678901",
        nas_folder_letter="A",
        requires_review=False,
    )
    db_session.add_all([person_subject, company_subject])
    db_session.flush()

    db_session.add(
        AnagraficaPerson(
            subject_id=person_subject.id,
            cognome="Rossi",
            nome="Mario",
            codice_fiscale="RSSMRA80A01H501Z",
        )
    )
    db_session.add(
        AnagraficaCompany(
            subject_id=company_subject.id,
            ragione_sociale="Acme Srl",
            partita_iva="12345678901",
        )
    )
    db_session.commit()

    assert db_session.get(AnagraficaSubject, person_subject.id) is not None
    assert db_session.get(AnagraficaSubject, company_subject.id) is not None


def test_person_codice_fiscale_must_be_unique(db_session: Session) -> None:
    first = AnagraficaSubject(
        subject_type="person",
        status="active",
        source_name_raw="Bianchi_Luca_BNCLCU80A01H501Z",
        nas_folder_path=str(uuid.uuid4()),
    )
    second = AnagraficaSubject(
        subject_type="person",
        status="active",
        source_name_raw="Bianchi_Luca_Duplicato",
        nas_folder_path=str(uuid.uuid4()),
    )
    db_session.add_all([first, second])
    db_session.flush()

    db_session.add(
        AnagraficaPerson(
            subject_id=first.id,
            cognome="Bianchi",
            nome="Luca",
            codice_fiscale="BNCLCU80A01H501Z",
        )
    )
    db_session.commit()

    db_session.add(
        AnagraficaPerson(
            subject_id=second.id,
            cognome="Bianchi",
            nome="Luca",
            codice_fiscale="BNCLCU80A01H501Z",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_can_persist_person_snapshot(db_session: Session) -> None:
    subject = AnagraficaSubject(
        subject_type="person",
        status="active",
        source_name_raw="Rossi_Mario_RSSMRA80A01H501Z",
        nas_folder_path=str(uuid.uuid4()),
    )
    db_session.add(subject)
    db_session.flush()

    db_session.add(
        AnagraficaPerson(
            subject_id=subject.id,
            cognome="Rossi",
            nome="Mario",
            codice_fiscale="RSSMRA80A01H501Z",
            comune_residenza="Oristano",
        )
    )
    db_session.flush()
    db_session.add(
        AnagraficaPersonSnapshot(
            subject_id=subject.id,
            source_system="xlsx_import",
            cognome="Rossi",
            nome="Mario",
            codice_fiscale="RSSMRA80A01H501Z",
            comune_residenza="Oristano",
        )
    )
    db_session.commit()

    assert db_session.query(AnagraficaPersonSnapshot).count() == 1


def test_import_job_can_reference_application_user(db_session: Session) -> None:
    user = ApplicationUser(
        username="anagrafica_admin",
        email="anagrafica_admin@example.local",
        password_hash=hash_password("secret123"),
        role=ApplicationUserRole.ADMIN.value,
        is_active=True,
        module_accessi=True,
        module_anagrafica=True,
    )
    db_session.add(user)
    db_session.commit()

    table = Base.metadata.tables["ana_import_jobs"]
    foreign_keys = {fk.target_fullname for fk in table.foreign_keys}

    assert "application_users.id" in foreign_keys
