"""Parcel histories keep tax liability separate from documentary cadastral ownership."""

import os
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import ForeignKeyConstraint, MetaData, create_engine, func, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from app.models.application_user import ApplicationUser
from app.models.catasto import (
    CatastoDocument,
    CatastoSisterExtraction,
    CatastoSisterHistoryEvent,
    CatastoSisterOwner,
    CatastoSisterParcel,
)
from app.models.catasto_phase1 import CatParticella
from app.modules.ruolo.models import RuoloAvviso, RuoloImportJob, RuoloParticella, RuoloPartita
from app.modules.ruolo.parcel_control_models import ParcelControlCase, ParcelControlIndex
from app.modules.ruolo.routes.parcel_history_routes import HistoryFilters
from app.modules.ruolo.services.parcel_history import history, list_parcels, normalized

from .test_parcel_control import seed
from .test_parcel_control import workspace as workspace

PREFIX = "/ruolo/particelle/storia"


def document(db, user, row, status="completed", classification=None):
    doc = CatastoDocument(
        user_id=user.id,
        filename="storica.pdf",
        filepath="/synthetic.pdf",
        tipo_visura="Storica",
        parcel_classification=classification,
        parcel_suppressed_at=date(2022, 4, 1) if classification else None,
    )
    db.add(doc)
    db.flush()
    row.ade_scan_document_id = doc.id
    extraction = None
    if status:
        extraction = CatastoSisterExtraction(
            document_id=doc.id,
            parser_version="test",
            status=status,
            pdf_sha256="a" * 64,
            observed_at=date(2026, 11, 12),
            payload_json={},
        )
        db.add(extraction)
        db.flush()
    db.commit()
    return doc, extraction


def test_search_groups_full_history_and_never_creates_a_case(workspace):
    db, _, client = workspace
    old, _, first, _ = seed(db, 2011, parcel="00100", sheet="01")
    recent, _, last, _ = seed(db, 2025)
    first.nominativo_raw = "Contribuente precedente"
    last.nominativo_raw = "Contribuente attuale"
    seed(db, 2020, parcel="200")
    db.commit()
    response = client.get(
        PREFIX,
        params={"comune": "orist", "foglio": "001", "particella": "0100", "search": "precedente"},
    )
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "private, no-store"
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0] == {
        "id": min(str(old.id), str(recent.id)),
        "comune": "ORISTANO",
        "comune_codice": "G113",
        "foglio": "1",
        "particella": "100",
        "subalterno": "",
        "first_year": 2011,
        "last_year": 2025,
        "years_count": 2,
    }
    assert db.scalar(select(func.count()).select_from(ParcelControlCase)) == 0
    assert db.scalar(select(func.count()).select_from(ParcelControlIndex)) == 0
    assert client.get(PREFIX, params={"search": first.codice_fiscale_raw}).json()["total"] == 2
    assert client.get(PREFIX, params={"search": first.codice_cnc}).json()["total"] == 1


def test_pagination_empty_identifiers_literal_wildcards_and_invalid_filters(workspace):
    db, _, client = workspace
    for number in range(3):
        seed(db, 2020, parcel=str(number))
    a, _, _, _ = seed(db, 2021, code=None)
    b, _, _, _ = seed(db, 2022, code=None)
    result = client.get(PREFIX, params={"page_size": 2, "page": 2}).json()
    assert result["total"] == 5 and len(result["items"]) == 2 and result["page"] == 2
    assert client.get(PREFIX, params={"comune": "%"}).json()["total"] == 0
    assert client.get(PREFIX, params={"search": "_\\%"}).json()["total"] == 0
    detail = client.get(f"{PREFIX}/{a.id}").json()
    assert detail["identity_incomplete"] and len(detail["taxes"]) == 1
    assert detail["taxes"][0]["id"] != str(b.id)
    assert client.get(PREFIX, params={"page": 0}).status_code == 422
    assert client.get(PREFIX, params={"page_size": 101}).status_code == 422
    assert client.get(f"{PREFIX}/{uuid4()}").status_code == 404
    assert client.get(f"{PREFIX}/invalid-id").status_code == 422
    sql = str(
        select(normalized(RuoloParticella.foglio, "postgresql")).compile(
            dialect=postgresql.dialect()
        )
    )
    assert " ~ " in sql and "GLOB" not in sql


def test_tax_amounts_are_per_parcel_and_missing_is_not_zero(workspace):
    db, _, client = workspace
    row, partita, notice, _ = seed(db, 2008)
    row.importo_manut, row.importo_irrig, row.importo_ist = (
        Decimal("12.34"),
        Decimal("0"),
        Decimal("1.23"),
    )
    partita.contribuente_cf = "ALTRO"
    partita.co_intestati_raw = "Cointestatario"
    notice.importo_totale_euro = Decimal("9999")
    seed(db, 2026)
    db.commit()
    response = client.get(f"{PREFIX}/{row.id}")
    assert response.status_code == 200 and response.headers["cache-control"] == "private, no-store"
    result = response.json()
    assert result["first_year"] == 2008 and result["last_year"] == 2026
    assert result["taxes"][0]["total"] == 13.57
    assert result["taxes"][0]["partita_tax_code"] == "ALTRO"
    assert result["taxes"][0]["co_holders"] == "Cointestatario"
    assert result["taxes"][1]["total"] is None
    assert result["cadastre"] == {
        "documents": [],
        "events": [],
        "completeness": "not_certified",
        "cessation": "not_documented",
    }


def test_history_owners_and_suppression_have_sources_but_no_inferred_transfer(workspace):
    db, user, client = workspace
    row, _, _, _ = seed(db, 2021)
    doc, extraction = document(db, user, row, classification="suppressed")
    parcel = CatastoSisterParcel(extraction_id=extraction.id, payload_json={})
    db.add(parcel)
    db.flush()
    db.add(
        CatastoSisterOwner(
            sister_parcel_id=parcel.id,
            denominazione="Attuale",
            diritto="Usufrutto",
            quota="1/2",
            payload_json={},
        )
    )
    db.add(
        CatastoSisterHistoryEvent(
            extraction_id=extraction.id,
            from_date=date(1990, 1, 1),
            act_date=date(1989, 12, 1),
            denominazione="Precedente",
            codice_fiscale="STORICO",
            diritto="Proprietà",
            quota="1/1",
            act_description="Atto sintetico",
            payload_json={},
        )
    )
    db.commit()
    result = client.get(f"{PREFIX}/{row.id}").json()["cadastre"]
    assert result["cessation"] == "documented_suppression"
    assert result["completeness"] == "not_certified"
    assert result["documents"][0]["owners"][0]["name"] == "Attuale"
    assert result["documents"][0]["suppressed_at"] == "2022-04-01"
    assert result["events"][0]["from_date"] == "1990-01-01"
    assert result["events"][0]["document_id"] == str(doc.id)
    assert result["events"][0]["act"] == "Atto sintetico"
    assert "filepath" not in str(result)


@pytest.mark.parametrize("status", [None, "failed", "completed"])
def test_missing_failed_and_ambiguous_extractions_do_not_invent_owners(workspace, status):
    db, user, client = workspace
    row, _, _, _ = seed(db, 2020)
    _, extraction = document(db, user, row, status=status)
    if extraction and status == "completed":
        db.add_all(
            [CatastoSisterParcel(extraction_id=extraction.id, payload_json={}) for _ in range(2)]
        )
        db.commit()
    result = client.get(f"{PREFIX}/{row.id}").json()["cadastre"]
    assert result["events"] == [] and result["documents"][0]["owners"] == []
    assert result["documents"][0]["ambiguous"] == (status == "completed")


def test_document_access_and_canonical_links_are_preserved(workspace):
    db, user, client = workspace
    row, _, _, _ = seed(db, 2020)
    cat = CatParticella(cod_comune_capacitas=1, foglio="1", particella="100")
    db.add(cat)
    db.flush()
    row.cat_particella_id = cat.id
    doc, extraction = document(db, user, row)
    row.ade_scan_document_id = None
    db.add(
        CatastoSisterParcel(extraction_id=extraction.id, cat_particella_id=cat.id, payload_json={})
    )
    other = ApplicationUser(
        username="other", email="other@example.org", password_hash="test", role="viewer"
    )
    db.add(other)
    db.commit()
    result = client.get(f"{PREFIX}/{row.id}").json()
    assert result["taxes"][0]["catasto_id"] == str(cat.id)
    assert len(result["cadastre"]["documents"]) == 1
    doc.user_id = other.id
    db.commit()
    assert client.get(f"{PREFIX}/{row.id}").json()["cadastre"]["documents"] == []


def test_events_from_multiple_surveys_are_chronological_with_undated_evidence_last(workspace):
    db, user, client = workspace
    old, _, _, _ = seed(db, 2010)
    new, _, _, _ = seed(db, 2025)
    expected = []
    for row, dates in ((old, [date(2000, 1, 1), None]), (new, [date(1990, 1, 1)])):
        doc, extraction = document(db, user, row)
        db.add(CatastoSisterParcel(extraction_id=extraction.id, payload_json={}))
        for when in dates:
            event = CatastoSisterHistoryEvent(
                extraction_id=extraction.id,
                from_date=when,
                denominazione=f"Proprietario {when}",
                payload_json={},
            )
            db.add(event)
            db.flush()
            expected.append((str(when or "9999"), str(event.id), str(doc.id)))
    db.commit()
    result = client.get(f"{PREFIX}/{old.id}").json()["cadastre"]
    assert len(result["documents"]) == 2
    assert [(event["id"], event["document_id"]) for event in result["events"]] == [
        (identity, source) for _, identity, source in sorted(expected)
    ]
    assert result["completeness"] == "not_certified"


def test_read_only_user_can_consult_but_no_module_access_is_denied(workspace):
    db, user, client = workspace
    row, _, _, _ = seed(db, 2020)
    user.role = "viewer"
    user.module_ruolo = True
    db.commit()
    assert client.get(PREFIX).status_code == 200
    assert client.get(f"{PREFIX}/{row.id}").status_code == 200
    user.module_ruolo = False
    db.commit()
    assert client.get(PREFIX).status_code == 403


@pytest.mark.postgres
def test_postgres_real_search_and_history_keep_canonical_numbers_and_decimal_amounts():
    url = os.getenv("PARCEL_HISTORY_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Richiede PostgreSQL isolato: PARCEL_HISTORY_TEST_POSTGRES_URL")
    engine = create_engine(url)
    assert engine.url.database == "parcel_history_test", "Solo database sintetico isolato"
    schema = f"history_{uuid4().hex}"
    with engine.begin() as connection:
        connection.execute(CreateSchema(schema))
    scoped = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    metadata = MetaData()
    # This test exercises read queries, not write constraints: unrelated domains stay outside it.
    for model in (
        RuoloImportJob,
        RuoloAvviso,
        RuoloPartita,
        RuoloParticella,
        CatastoDocument,
        CatastoSisterExtraction,
        CatastoSisterParcel,
        CatastoSisterOwner,
        CatastoSisterHistoryEvent,
    ):
        table = model.__table__.to_metadata(metadata)
        for constraint in list(table.constraints):
            if isinstance(constraint, ForeignKeyConstraint):
                table.constraints.remove(constraint)
        table.foreign_keys.clear()
        for column in table.columns:
            column.foreign_keys.clear()
    try:
        metadata.create_all(scoped)
        with Session(scoped) as db:
            row, _, _, _ = seed(db, 2010, parcel="00100", sheet="001")
            seed(db, 2025)
            row.importo_manut, row.importo_irrig, row.importo_ist = (
                Decimal("0.10"),
                Decimal("0.20"),
                Decimal("0"),
            )
            db.commit()
            result = list_parcels(db, HistoryFilters(foglio="01", particella="100"))
            assert result["total"] == 1 and result["items"][0]["years_count"] == 2
            result = history(db, row.id, 1)
            assert result["first_year"] == 2010 and result["last_year"] == 2025
            assert result["taxes"][0]["total"] == Decimal("0.30")
    finally:
        scoped.dispose()
        with engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        engine.dispose()
