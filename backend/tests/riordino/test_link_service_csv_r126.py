"""Characterization tests for riordino parcel/party link services (R126)."""

from __future__ import annotations

import io
from collections.abc import Generator
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.application_user import ApplicationUser
from app.models.catasto_phase1 import CatParticella
from app.modules.riordino.models import RiordinoParcelLink, RiordinoPartyLink, RiordinoPractice
from app.modules.riordino.services import link_service
from app.modules.utenze.models import AnagraficaSubject


@pytest.fixture
def db() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autocommit=False, autoflush=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _practice(
    db: Session, *, municipality: str = "Comune Test", code: str = "PR-R126"
) -> RiordinoPractice:
    user = db.query(ApplicationUser).first()
    if user is None:
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
        code=code,
        title="Pratica R126",
        municipality=municipality,
        grid_code="G1",
        lot_code="L1",
        owner_user_id=user.id,
        created_by=user.id,
    )
    db.add(practice)
    db.flush()
    return practice


def _subject(db: Session) -> AnagraficaSubject:
    subject = AnagraficaSubject(source_name_raw="Soggetto R126", subject_type="person")
    db.add(subject)
    db.flush()
    return subject


def _cat(
    db: Session, *, foglio: str, particella: str, comune: str | None, subalterno: str | None = None
) -> CatParticella:
    item = CatParticella(
        cod_comune_capacitas=501,
        codice_catastale="H501",
        nome_comune=comune,
        foglio=foglio,
        particella=particella,
        subalterno=subalterno,
        source_type="test",
    )
    db.add(item)
    db.flush()
    return item


class _UnreadableFile:
    def read(self) -> bytes:
        raise AssertionError("file content must not be read")


def _upload(content: str | bytes, filename: str | None = "parcels.csv") -> UploadFile:
    data = content.encode("utf-8") if isinstance(content, str) else content
    return UploadFile(file=io.BytesIO(data), filename=filename)


# --- import_parcels_csv -----------------------------------------------------


def test_import_csv_unknown_practice_is_404_before_filename_check(db: Session) -> None:
    with pytest.raises(HTTPException) as exc:
        link_service.import_parcels_csv(
            db, uuid4(), UploadFile(file=_UnreadableFile(), filename="bad.txt")
        )
    assert exc.value.status_code == 404
    assert exc.value.detail == "Practice not found"


@pytest.mark.parametrize("filename", [None, "", "parcels.txt", "parcels.csv.bak"])
def test_import_csv_rejects_missing_or_non_csv_filename_without_reading(
    db: Session, filename: str | None
) -> None:
    practice = _practice(db)
    with pytest.raises(HTTPException) as exc:
        link_service.import_parcels_csv(
            db, practice.id, UploadFile(file=_UnreadableFile(), filename=filename)
        )
    assert exc.value.status_code == 422
    assert exc.value.detail == "CSV file required"


def test_import_csv_full_row_mapping_with_bom_and_uppercase_extension(db: Session) -> None:
    practice = _practice(db)
    subject = _subject(db)
    content = (
        "﻿foglio,particella,subalterno,quality_class,title_holder_name,source,notes,title_holder_subject_id\n"
        f" 1 , 10 , 2 , A , Mario Rossi , manual , nota , {subject.id} \n"
    )
    items = link_service.import_parcels_csv(
        db, practice.id, _upload(content, filename="PARCELS.CSV")
    )

    assert len(items) == 1
    item = items[0]
    assert isinstance(item, RiordinoParcelLink)
    assert item.practice_id == practice.id
    assert item.foglio == "1"
    assert item.particella == "10"
    assert item.subalterno == "2"
    assert item.quality_class == "A"
    assert item.title_holder_name == "Mario Rossi"
    assert item.source == "manual"
    assert item.notes == "nota"
    assert item.title_holder_subject_id == subject.id
    # flushed and refreshed: server defaults are loaded
    assert item.id is not None
    assert item.created_at is not None


def test_import_csv_optional_columns_absent_default_to_none_and_csv_import(db: Session) -> None:
    practice = _practice(db)
    items = link_service.import_parcels_csv(db, practice.id, _upload("foglio,particella\n3,30\n"))

    assert len(items) == 1
    item = items[0]
    assert (item.foglio, item.particella) == ("3", "30")
    assert item.subalterno is None
    assert item.quality_class is None
    assert item.title_holder_name is None
    assert item.notes is None
    assert item.title_holder_subject_id is None
    assert item.source == "csv_import"


def test_import_csv_blank_optional_values_become_none_and_blank_source_defaults(
    db: Session,
) -> None:
    practice = _practice(db)
    content = (
        "foglio,particella,subalterno,quality_class,title_holder_name,source,notes,title_holder_subject_id\n"
        "4,40,  ,  ,  ,   ,  ,   \n"
        "5,50,,,,,,\n"
    )
    items = link_service.import_parcels_csv(db, practice.id, _upload(content))

    assert [(i.foglio, i.particella) for i in items] == [("4", "40"), ("5", "50")]
    for item in items:
        assert item.subalterno is None
        assert item.quality_class is None
        assert item.title_holder_name is None
        assert item.notes is None
        assert item.title_holder_subject_id is None
        assert item.source == "csv_import"


def test_import_csv_skips_rows_missing_foglio_or_particella_and_keeps_order(db: Session) -> None:
    practice = _practice(db)
    content = (
        "foglio,particella,notes\n"
        "1,10,first\n"
        ",11,no foglio\n"
        "2,,no particella\n"
        "7\n"  # short row: particella is None
        "  ,12,whitespace foglio is kept\n"
        "3,30,last\n"
    )
    items = link_service.import_parcels_csv(db, practice.id, _upload(content))

    assert [(i.foglio, i.particella, i.notes) for i in items] == [
        ("1", "10", "first"),
        ("", "12", "whitespace foglio is kept"),
        ("3", "30", "last"),
    ]
    stored = (
        db.query(RiordinoParcelLink).filter(RiordinoParcelLink.practice_id == practice.id).count()
    )
    assert stored == 3


def test_import_csv_header_only_returns_empty_list(db: Session) -> None:
    practice = _practice(db)
    assert link_service.import_parcels_csv(db, practice.id, _upload("foglio,particella\n")) == []
    assert link_service.import_parcels_csv(db, practice.id, _upload("")) == []


def test_import_csv_invalid_subject_uuid_raises_value_error(db: Session) -> None:
    practice = _practice(db)
    content = "foglio,particella,title_holder_subject_id\n1,10,not-a-uuid\n"
    with pytest.raises(ValueError):
        link_service.import_parcels_csv(db, practice.id, _upload(content))


def test_import_csv_unknown_subject_is_404_before_adding_that_row(db: Session) -> None:
    practice = _practice(db)
    missing = UUID(int=987654321)
    content = f"foglio,particella,title_holder_subject_id\n1,10,\n2,20,{missing}\n3,30,\n"
    with pytest.raises(HTTPException) as exc:
        link_service.import_parcels_csv(db, practice.id, _upload(content))
    assert exc.value.status_code == 404
    assert exc.value.detail == "Subject not found"
    pending = [obj for obj in db.new if isinstance(obj, RiordinoParcelLink)]
    assert [(obj.foglio, obj.particella) for obj in pending] == [("1", "10")]


def test_import_csv_invalid_utf8_raises_unicode_error(db: Session) -> None:
    practice = _practice(db)
    with pytest.raises(UnicodeDecodeError):
        link_service.import_parcels_csv(db, practice.id, _upload(b"foglio,particella\n\xff,1\n"))


# --- parcels ----------------------------------------------------------------


def test_list_parcels_unknown_practice_is_404(db: Session) -> None:
    with pytest.raises(HTTPException) as exc:
        link_service.list_parcels(db, uuid4())
    assert exc.value.status_code == 404
    assert exc.value.detail == "Practice not found"


def test_create_parcel_requires_practice_and_existing_subject(db: Session) -> None:
    with pytest.raises(HTTPException) as exc:
        link_service.create_parcel(db, uuid4(), {"foglio": "1", "particella": "1"})
    assert exc.value.detail == "Practice not found"

    practice = _practice(db)
    with pytest.raises(HTTPException) as exc:
        link_service.create_parcel(
            db, practice.id, {"foglio": "1", "particella": "1", "title_holder_subject_id": uuid4()}
        )
    assert exc.value.status_code == 404
    assert exc.value.detail == "Subject not found"

    subject = _subject(db)
    with_subject = link_service.create_parcel(
        db, practice.id, {"foglio": "1", "particella": "1", "title_holder_subject_id": subject.id}
    )
    assert with_subject.title_holder_subject_id == subject.id
    without_subject = link_service.create_parcel(
        db, practice.id, {"foglio": "2", "particella": "2"}
    )
    assert without_subject.title_holder_subject_id is None
    assert without_subject.created_at is not None


def test_list_parcels_enriches_catasto_match_states(db: Session) -> None:
    practice = _practice(db, municipality="Comune Test")
    matched_cat = _cat(db, foglio="1", particella="10", comune="Comune Test")
    _cat(db, foglio="1", particella="10", comune="Comune Test", subalterno="3")
    fallback_cat = _cat(db, foglio="2", particella="20", comune="Altro Comune")
    _cat(db, foglio="3", particella="30", comune="Comune Test")
    _cat(db, foglio="3", particella="30", comune="Comune Test")
    sub_cat = _cat(db, foglio="5", particella="50", comune="comune test", subalterno="a")

    specs = {
        "matched": {"foglio": " 1 ", "particella": "10"},
        "fallback": {"foglio": "2", "particella": "20"},
        "ambiguous": {"foglio": "3", "particella": "30"},
        "unmatched": {"foglio": "9", "particella": "90"},
        "subalterno": {"foglio": "5", "particella": "50", "subalterno": "A"},
        "blank_key": {"foglio": "  ", "particella": "10"},
    }
    ids = {
        name: link_service.create_parcel(db, practice.id, data).id for name, data in specs.items()
    }

    parcels = {parcel.id: parcel for parcel in link_service.list_parcels(db, practice.id)}
    assert len(parcels) == len(specs)

    matched = parcels[ids["matched"]]
    assert matched.cat_particella_id == matched_cat.id
    assert matched.cat_particella_match_status == "matched"
    assert matched.cat_particella_match_reason is None
    assert matched.cat_particella_nome_comune == "Comune Test"
    assert matched.cat_particella_num_distretto == matched_cat.num_distretto
    assert matched.cat_particella_has_geometry is False

    fallback = parcels[ids["fallback"]]
    assert fallback.cat_particella_id == fallback_cat.id
    assert fallback.cat_particella_match_status == "matched"
    assert fallback.cat_particella_match_reason == "no_match_in_practice_municipality"
    assert fallback.cat_particella_nome_comune == "Altro Comune"

    ambiguous = parcels[ids["ambiguous"]]
    assert ambiguous.cat_particella_id is None
    assert ambiguous.cat_particella_match_status == "ambiguous"
    assert ambiguous.cat_particella_match_reason == "multiple_cat_particelle_matches"
    assert ambiguous.cat_particella_nome_comune is None
    assert ambiguous.cat_particella_num_distretto is None
    assert ambiguous.cat_particella_has_geometry is None

    for name in ("unmatched", "blank_key"):
        parcel = parcels[ids[name]]
        assert parcel.cat_particella_id is None
        assert parcel.cat_particella_match_status == "unmatched"
        assert parcel.cat_particella_match_reason == "no_cat_particella_match"

    assert parcels[ids["subalterno"]].cat_particella_id == sub_cat.id


def test_list_parcels_without_practice_municipality_skips_fallback(db: Session) -> None:
    practice = _practice(db, municipality="")
    cat = _cat(db, foglio="1", particella="10", comune="Ovunque")
    parcel = link_service.create_parcel(db, practice.id, {"foglio": "1", "particella": "10"})
    missing = link_service.create_parcel(db, practice.id, {"foglio": "8", "particella": "80"})

    parcels = {item.id: item for item in link_service.list_parcels(db, practice.id)}
    assert parcels[parcel.id].cat_particella_id == cat.id
    assert parcels[parcel.id].cat_particella_match_reason is None
    assert parcels[missing.id].cat_particella_match_status == "unmatched"


def test_delete_parcel_found_and_not_found(db: Session) -> None:
    practice = _practice(db)
    parcel = link_service.create_parcel(db, practice.id, {"foglio": "1", "particella": "1"})
    with pytest.raises(HTTPException) as exc:
        link_service.delete_parcel(db, uuid4(), parcel.id)
    assert exc.value.status_code == 404
    assert exc.value.detail == "Parcel link not found"

    deleted = link_service.delete_parcel(db, practice.id, parcel.id)
    assert deleted.id == parcel.id
    assert db.get(RiordinoParcelLink, parcel.id) is None


# --- parties ----------------------------------------------------------------


def test_party_lifecycle(db: Session) -> None:
    practice = _practice(db)
    with pytest.raises(HTTPException) as exc:
        link_service.create_party(db, uuid4(), {"subject_id": uuid4(), "role": "owner"})
    assert exc.value.detail == "Practice not found"
    with pytest.raises(HTTPException) as exc:
        link_service.create_party(db, practice.id, {"subject_id": uuid4(), "role": "owner"})
    assert exc.value.detail == "Subject not found"

    subject = _subject(db)
    party = link_service.create_party(db, practice.id, {"subject_id": subject.id, "role": "owner"})
    assert isinstance(party, RiordinoPartyLink)
    assert party.created_at is not None
    assert [item.id for item in link_service.list_parties(db, practice.id)] == [party.id]

    with pytest.raises(HTTPException) as exc:
        link_service.delete_party(db, practice.id, uuid4())
    assert exc.value.status_code == 404
    assert exc.value.detail == "Party link not found"
    assert link_service.delete_party(db, practice.id, party.id).id == party.id
    assert link_service.list_parties(db, practice.id) == []
