"""Characterization of the NAS subject-folder scoring used to pick a folder.

Exact numeric scores are pinned because they decide which NAS folder is
selected (highest score wins) and are exposed by the candidates endpoint.
"""

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.modules.utenze.models import AnagraficaCompany, AnagraficaPerson, AnagraficaSubject
from app.modules.utenze.services.import_service import (
    AnagraficaImportPreviewService,
    _score_subject_folder_candidate,
)

ARCHIVE_ROOT = "/archive"


class FakeNasConnector:
    def __init__(self, outputs: dict[str, str]) -> None:
        self.outputs = outputs

    def run_command(self, command: str) -> str:
        return self.outputs.get(command, "")


@pytest.fixture
def db_session() -> Session:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def _subject(db: Session, source_name_raw: str) -> AnagraficaSubject:
    subject = AnagraficaSubject(id=uuid.uuid4(), source_name_raw=source_name_raw)
    db.add(subject)
    db.flush()
    return subject


def _person(
    db: Session, source_name_raw: str, cognome: str, nome: str, codice_fiscale: str
) -> AnagraficaSubject:
    subject = _subject(db, source_name_raw)
    db.add(
        AnagraficaPerson(
            subject_id=subject.id, cognome=cognome, nome=nome, codice_fiscale=codice_fiscale
        )
    )
    db.commit()
    return subject


def _company(
    db: Session,
    source_name_raw: str,
    ragione_sociale: str,
    partita_iva: str,
    codice_fiscale: str | None,
) -> AnagraficaSubject:
    subject = _subject(db, source_name_raw)
    db.add(
        AnagraficaCompany(
            subject_id=subject.id,
            ragione_sociale=ragione_sociale,
            partita_iva=partita_iva,
            codice_fiscale=codice_fiscale,
        )
    )
    db.commit()
    return subject


@pytest.mark.parametrize(
    ("folder_name", "expected"),
    [
        # 5 identifiers x30 (ROSSIMARIO counted twice) + cf 500 + surname 150 + name 80
        ("Rossi_Mario_RSSMRA80A01H501U", 880),
        # 4 identifiers x30 + surname 150 + name 80
        ("Rossi_Mario", 350),
        ("rossi", 180),
        ("Mario-Bianchi", 110),
        ("rssmra80a01h501u", 530),
        ("Verdi Luca", 0),
        ("___", 0),
        ("", 0),
    ],
)
def test_person_scores(db_session: Session, folder_name: str, expected: int) -> None:
    subject = _person(db_session, "Rossi Mario", "Rossi", "Mario", "RSSMRA80A01H501U")

    score = _score_subject_folder_candidate(db_session, subject, folder_name)

    assert score == expected
    assert type(score) is int


def test_person_with_empty_fiscal_code_and_punctuation(db_session: Session) -> None:
    subject = _person(db_session, "D'ANGELO ANNA", "D'Angelo", "Anna", "")

    # identifiers DANGELOANNA x2, DANGELO, ANNA -> 120; surname 150 + name 80
    assert _score_subject_folder_candidate(db_session, subject, "Dangelo.Anna") == 350
    assert _score_subject_folder_candidate(db_session, subject, "ANNA") == 110


def test_identifier_normalizing_to_empty_is_ignored(db_session: Session) -> None:
    subject = _person(db_session, "***", "Neri", "Ugo", "NRIUGO70B02F205X")

    # NERI, UGO, NERIUGO -> 90; surname 150 + name 80
    assert _score_subject_folder_candidate(db_session, subject, "NERI UGO") == 320


@pytest.mark.parametrize(
    ("folder_name", "expected"),
    [
        # identifiers OLATISRL x2 + piva -> 90; piva 500 + name 180
        ("Olati_Srl_14542661005", 770),
        # 4 identifiers -> 120; piva 500 + cf 250 + name 180
        ("Olati Srl 14542661005 97000000001", 1050),
        ("97000000001", 280),
        ("14542661005", 530),
        ("olati-srl", 240),
        ("Altra Ditta", 0),
    ],
)
def test_company_scores(db_session: Session, folder_name: str, expected: int) -> None:
    subject = _company(db_session, "Olati Srl", "Olati Srl", "14542661005", "97000000001")

    assert _score_subject_folder_candidate(db_session, subject, folder_name) == expected


def test_company_without_fiscal_code(db_session: Session) -> None:
    subject = _company(db_session, "Olati Srl", "Olati Srl", "14542661005", None)

    assert _score_subject_folder_candidate(db_session, subject, "Olati srl") == 240
    assert _score_subject_folder_candidate(db_session, subject, "Olati Srl 14542661005") == 770


def test_person_takes_precedence_over_company(db_session: Session) -> None:
    subject = _subject(db_session, "Mix")
    db_session.add(
        AnagraficaPerson(
            subject_id=subject.id, cognome="Sanna", nome="Gavino", codice_fiscale="SNNGVN60C03B354Y"
        )
    )
    db_session.add(
        AnagraficaCompany(
            subject_id=subject.id,
            ragione_sociale="Sanna Srl",
            partita_iva="01234567890",
            codice_fiscale=None,
        )
    )
    db_session.commit()

    # identifiers SANNA, SANNASRL, piva -> 90; only person weights apply: surname 150
    assert _score_subject_folder_candidate(db_session, subject, "Sanna_Srl_01234567890") == 240


def test_subject_without_person_or_company(db_session: Session) -> None:
    subject = _subject(db_session, "Mario Rossi")
    db_session.commit()

    assert _score_subject_folder_candidate(db_session, subject, "Mario_Rossi_Srl") == 30
    assert _score_subject_folder_candidate(db_session, subject, "x") == 0


def test_lookup_calls_are_preserved(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    subject = _person(db_session, "Rossi Mario", "Rossi", "Mario", "RSSMRA80A01H501U")
    calls: list[tuple[type, uuid.UUID]] = []
    original_get = db_session.get

    def recording_get(model, ident, *args, **kwargs):
        calls.append((model, ident))
        return original_get(model, ident, *args, **kwargs)

    monkeypatch.setattr(db_session, "get", recording_get)

    assert _score_subject_folder_candidate(db_session, subject, "---") == 0
    assert calls == []

    assert _score_subject_folder_candidate(db_session, subject, "Rossi") == 180
    assert calls == [
        (AnagraficaPerson, subject.id),
        (AnagraficaCompany, subject.id),
        (AnagraficaPerson, subject.id),
        (AnagraficaCompany, subject.id),
    ]


def test_candidates_are_ranked_by_exact_score(db_session: Session) -> None:
    subject = _person(db_session, "D'ANGELO ANNA", "D'Angelo", "Anna", "")
    folders = ["Anna_Bianchi", "Dangelo", "Dangelo_Anna", "Deiana_Pietro"]
    command = f"find '{ARCHIVE_ROOT}/D' -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort"
    connector = FakeNasConnector(
        {command: "\n".join(f"{ARCHIVE_ROOT}/D/{name}" for name in folders)}
    )
    service = AnagraficaImportPreviewService(connector, archive_root=ARCHIVE_ROOT)

    candidates = service.list_existing_subject_folder_candidates(db_session, subject)
    matched = service.match_existing_subject_folder(db_session, subject)

    assert [(item.folder_name, item.score) for item in candidates] == [
        ("Dangelo_Anna", 350),
        ("Dangelo", 180),
        ("Anna_Bianchi", 110),
    ]
    assert matched.folder_name == "Dangelo_Anna"
