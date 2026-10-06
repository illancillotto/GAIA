from __future__ import annotations

import uuid
from collections.abc import Iterator
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.ruolo.models import RuoloAvviso, RuoloImportJob
from app.modules.ruolo.services import incass_read_model
from app.modules.utenze.models import (
    AnagraficaCompany,
    AnagraficaPaymentNotice,
    AnagraficaPerson,
    AnagraficaSubject,
)


@pytest.fixture
def db() -> Iterator[Session]:
    engine = create_engine("sqlite://")
    tables = [
        ApplicationUser.__table__,
        AnagraficaSubject.__table__,
        AnagraficaPerson.__table__,
        AnagraficaCompany.__table__,
        RuoloImportJob.__table__,
        RuoloAvviso.__table__,
    ]
    AnagraficaSubject.metadata.create_all(engine, tables=tables)
    with Session(engine) as session:
        yield session
    engine.dispose()


def build_notice(db: Session, **overrides: object) -> AnagraficaPaymentNotice:
    subject = AnagraficaSubject(
        id=uuid.uuid4(), subject_type="person", source_name_raw="ARDU CRISTIAN"
    )
    db.add(subject)
    db.flush()
    db.add(
        AnagraficaPerson(
            subject_id=subject.id,
            cognome="Ardu",
            nome="Cristian",
            codice_fiscale="RDACST79D30G113S",
        )
    )
    db.flush()
    fields = {
        "source_system": "incass",
        "source_notice_id": "020230024242890",
        "anno": "2023",
        "subject_id": subject.id,
        "codice_fiscale": "RDACST79D30G113S",
        "display_name": "ARDU CRISTIAN",
        "indirizzo": "VIA IV NOVEMBRE 37",
        "cap": "09070",
        "citta": "ZERFALIU",
        "provincia": "OR",
        "importo_carico": "51.03",
    }
    return AnagraficaPaymentNotice(**(fields | overrides))


def test_ardu_cristian_without_partitario_is_visible_in_role(db: Session) -> None:
    notice = build_notice(db)
    avviso = incass_read_model.materialize_incass_notice_header(db, notice)
    assert avviso.subject_id == notice.subject_id
    assert avviso.codice_cnc == "01.02023002424289"
    assert avviso.anno_tributario == 2023
    assert avviso.codice_fiscale_raw == "RDACST79D30G113S"
    assert avviso.nominativo_raw == "ARDU CRISTIAN"
    assert avviso.domicilio_raw == "VIA IV NOVEMBRE 37 09070 ZERFALIU OR"
    assert avviso.residenza_raw == avviso.domicilio_raw
    assert avviso.importo_totale_euro == Decimal("51.03")
    assert avviso.importo_totale_0648 is None
    assert avviso.importo_totale_0985 is None
    assert avviso.importo_totale_0668 is None
    job = db.get(RuoloImportJob, avviso.import_job_id)
    assert job.params_json == {
        "source": "ana_payment_notices",
        "mode": "incass_header_sync",
        "partitario_materialized": False,
    }
    db.rollback()
    assert not db.scalars(select(RuoloAvviso)).all()


@pytest.mark.parametrize(
    "overrides",
    [
        {"source_system": "manual"},
        {"anno": None},
        {"anno": "2525"},
        {"anno": "7700"},
        {"anno": "9901"},
        {"anno": "2022"},
        {"source_notice_id": ""},
        {"source_notice_id": "AVV-1"},
        {"source_notice_id": "220230024242890"},
        {"subject_id": None},
    ],
)
def test_invalid_or_special_notices_do_not_create_role(db: Session, overrides: dict) -> None:
    notice = build_notice(db, **overrides)
    assert incass_read_model.materialize_incass_notice_header(db, notice) is None
    assert not db.scalars(select(RuoloAvviso)).all()
    assert not db.scalars(select(RuoloImportJob)).all()


@pytest.mark.parametrize("state", ["missing", "duplicate", "both", "no_cf", "mismatch"])
def test_identity_is_fail_closed(db: Session, state: str) -> None:
    notice = build_notice(db)
    subject = db.get(AnagraficaSubject, notice.subject_id)
    person = db.get(AnagraficaPerson, notice.subject_id)
    if state == "missing":
        db.delete(person)
        db.delete(subject)
    elif state == "duplicate":
        subject.status = "duplicate"
    elif state == "both":
        db.add(
            AnagraficaCompany(
                subject_id=subject.id, ragione_sociale="Conflict", partita_iva="01085390951"
            )
        )
    elif state == "no_cf":
        person.codice_fiscale = ""
    else:
        notice.codice_fiscale = "WRONG"
    db.flush()
    with pytest.raises(ValueError):
        incass_read_model.materialize_incass_notice_header(db, notice)
    assert not db.scalars(select(RuoloAvviso)).all()


def test_company_identifier_and_optional_fields(db: Session) -> None:
    notice = build_notice(db, codice_fiscale=None, partita_iva="01085390951")
    db.delete(db.get(AnagraficaPerson, notice.subject_id))
    db.add(
        AnagraficaCompany(
            subject_id=notice.subject_id,
            ragione_sociale="William Due S.R.L.",
            partita_iva="01085390951",
        )
    )
    notice.display_name = None
    notice.indirizzo = notice.cap = notice.citta = notice.provincia = None
    notice.source_internal_id = "X" * 35
    notice.importo_carico = None
    avviso = incass_read_model.materialize_incass_notice_header(db, notice)
    assert avviso.codice_fiscale_raw == "01085390951"
    assert avviso.nominativo_raw is None and avviso.domicilio_raw is None
    assert avviso.codice_utenza == "X" * 30 and avviso.importo_totale_euro is None


def test_company_cf_fallback(db: Session) -> None:
    notice = build_notice(db)
    db.delete(db.get(AnagraficaPerson, notice.subject_id))
    db.add(
        AnagraficaCompany(
            subject_id=notice.subject_id,
            ragione_sociale="Company",
            partita_iva="",
            codice_fiscale=notice.codice_fiscale,
        )
    )
    assert incass_read_model.materialize_incass_notice_header(db, notice) is not None


def test_company_distinct_canonical_cf_and_piva_are_not_conflated(db: Session) -> None:
    notice = build_notice(db, codice_fiscale="90000000001", partita_iva="01085390951")
    db.delete(db.get(AnagraficaPerson, notice.subject_id))
    db.add(
        AnagraficaCompany(
            subject_id=notice.subject_id,
            ragione_sociale="Company",
            partita_iva="01085390951",
            codice_fiscale="90000000001",
        )
    )
    avviso = incass_read_model.materialize_incass_notice_header(db, notice)
    assert avviso.codice_fiscale_raw == "90000000001"


def test_same_subject_without_identifier_is_rejected(db: Session) -> None:
    notice = build_notice(db)
    db.delete(db.get(AnagraficaPerson, notice.subject_id))
    db.flush()
    with pytest.raises(ValueError):
        incass_read_model.materialize_incass_notice_header(db, notice)


def test_existing_header_is_idempotent_and_historical_fields_preserved(db: Session) -> None:
    notice = build_notice(db)
    avviso = incass_read_model.materialize_incass_notice_header(db, notice)
    db.commit()
    original = {column.name: getattr(avviso, column.name) for column in avviso.__table__.columns}
    notice.display_name = "New spelling"
    notice.indirizzo = "New address"
    notice.importo_carico = "1000"
    assert incass_read_model.materialize_incass_notice_header(db, notice).id == avviso.id
    assert {
        column.name: getattr(avviso, column.name) for column in avviso.__table__.columns
    } == original
    assert len(db.scalars(select(RuoloImportJob)).all()) == 1
    assert len(db.scalars(select(RuoloAvviso)).all()) == 1


@pytest.mark.parametrize("field", ["subject_id", "codice_fiscale_raw"])
def test_existing_header_identity_conflict_is_rejected(db: Session, field: str) -> None:
    notice = build_notice(db)
    avviso = incass_read_model.materialize_incass_notice_header(db, notice)
    setattr(avviso, field, uuid.uuid4() if field == "subject_id" else "WRONG")
    db.flush()
    with pytest.raises(ValueError, match="confligge"):
        incass_read_model.materialize_incass_notice_header(db, notice)


def test_existing_unlinked_header_is_not_reassigned(db: Session) -> None:
    notice = build_notice(db)
    avviso = incass_read_model.materialize_incass_notice_header(db, notice)
    avviso.subject_id = None
    avviso.codice_fiscale_raw = None
    db.flush()
    assert incass_read_model.materialize_incass_notice_header(db, notice).subject_id is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("bad", None),
        ("NaN", None),
        ("Infinity", None),
        ("10000000000", None),
        ("51.03", Decimal("51.03")),
        ("1.234,56", Decimal("1234.56")),
        ("0", Decimal("0.00")),
    ],
)
def test_source_amount_is_not_invented(value: str | None, expected: Decimal | None) -> None:
    assert incass_read_model._notice_amount(value) == expected


def test_import_job_and_header_conflicts_are_safe(db: Session, monkeypatch) -> None:
    notice = build_notice(db)
    avviso = incass_read_model.materialize_incass_notice_header(db, notice)
    db.commit()
    original_scalar = db.scalar
    calls = 0

    def simulate_concurrent_insert(statement):
        nonlocal calls
        calls += 1
        return None if calls == 1 else original_scalar(statement)

    monkeypatch.setattr(db, "scalar", simulate_concurrent_insert)
    assert incass_read_model.materialize_incass_notice_header(db, notice).id == avviso.id
    assert len(db.scalars(select(RuoloAvviso)).all()) == 1
    assert len(db.scalars(select(RuoloImportJob)).all()) == 1


def test_lightweight_sync_materializes_header_and_preserves_existing_details(db: Session) -> None:
    from app.modules.elaborazioni.capacitas.models import CapacitasInCassNoticeRow
    from app.services.elaborazioni_capacitas_incass import _upsert_payment_notice

    AnagraficaPaymentNotice.__table__.create(db.get_bind())
    notice = build_notice(db)
    notice.raw_detail_json = {"partitario": {"partite": [{"codice_partita": "ABC"}]}}
    db.add(notice)
    db.flush()
    row = CapacitasInCassNoticeRow(
        avviso=notice.source_notice_id,
        anno="2023",
        codice_fiscale=notice.codice_fiscale,
        denominazione=notice.display_name,
        indirizzo="VIA IV NOVEMBRE",
        civico="37",
        cap="09070",
        citta="ZERFALIU",
        provincia="OR",
        carico="51.03",
    )
    _upsert_payment_notice(
        db,
        subject_id=notice.subject_id,
        identifier=notice.codice_fiscale,
        display_name=notice.display_name,
        row=row,
        detail_info_html=None,
        detail_info_text=None,
        pdf_links_json=[],
        detail_payload=None,
        existing=notice,
        preserve_heavy_fields=True,
    )
    db.flush()
    avviso = db.scalar(select(RuoloAvviso))
    assert avviso.subject_id == notice.subject_id and avviso.anno_tributario == 2023
    assert avviso.domicilio_raw == "VIA IV NOVEMBRE 37 09070 ZERFALIU OR"
    assert notice.raw_detail_json["partitario"]["partite"][0]["codice_partita"] == "ABC"
