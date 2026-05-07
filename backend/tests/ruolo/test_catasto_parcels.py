from collections.abc import Generator
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.catasto import CatastoComune, CatastoParcel
from app.modules.ruolo.services.import_service import _upsert_catasto_parcel


SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def setup_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    db.add(CatastoComune(nome="MOGORO", codice_sister="F272#MOGORO#0#0", ufficio="ORISTANO Territorio"))
    db.add(CatastoComune(nome="ARBOREA", codice_sister="A357", ufficio="ORISTANO Territorio"))
    db.commit()
    db.close()

    yield

    Base.metadata.drop_all(bind=engine)


def test_upsert_catasto_parcel_creates_new_current_record() -> None:
    db = TestingSessionLocal()
    try:
        parcel_id = _upsert_catasto_parcel(
            db,
            comune_nome="MOGORO",
            foglio="35",
            particella="41",
            subalterno="A",
            sup_catastale_are=Decimal("100"),
            anno=2025,
        )
        db.commit()

        saved = db.get(CatastoParcel, parcel_id)
        assert saved is not None
        assert saved.comune_codice == "F272"
        assert saved.valid_from == 2025
        assert saved.valid_to is None
        assert float(saved.sup_catastale_are) == 100.0
        assert float(saved.sup_catastale_ha) == 1.0
    finally:
        db.close()


def test_upsert_catasto_parcel_same_year_reuses_existing_record() -> None:
    db = TestingSessionLocal()
    try:
        first_id = _upsert_catasto_parcel(
            db,
            comune_nome="ARBOREA",
            foglio="5",
            particella="120",
            subalterno=None,
            sup_catastale_are=Decimal("95"),
            anno=2025,
        )
        db.commit()

        second_id = _upsert_catasto_parcel(
            db,
            comune_nome="ARBOREA",
            foglio="5",
            particella="120",
            subalterno=None,
            sup_catastale_are=Decimal("97"),
            anno=2025,
        )
        db.commit()

        rows = db.scalars(select(CatastoParcel)).all()
        assert second_id == first_id
        assert len(rows) == 1
        assert rows[0].valid_from == 2025
        assert rows[0].valid_to is None
    finally:
        db.close()


def test_upsert_catasto_parcel_next_year_same_surface_keeps_current_record() -> None:
    db = TestingSessionLocal()
    try:
        first_id = _upsert_catasto_parcel(
            db,
            comune_nome="ARBOREA",
            foglio="7",
            particella="98",
            subalterno=None,
            sup_catastale_are=Decimal("250"),
            anno=2024,
        )
        db.commit()

        second_id = _upsert_catasto_parcel(
            db,
            comune_nome="ARBOREA",
            foglio="7",
            particella="98",
            subalterno=None,
            sup_catastale_are=Decimal("250"),
            anno=2025,
        )
        db.commit()

        rows = db.scalars(select(CatastoParcel)).all()
        assert second_id == first_id
        assert len(rows) == 1
        assert rows[0].valid_from == 2024
        assert rows[0].valid_to is None
    finally:
        db.close()


def test_upsert_catasto_parcel_next_year_different_surface_versions_record() -> None:
    db = TestingSessionLocal()
    try:
        first_id = _upsert_catasto_parcel(
            db,
            comune_nome="MOGORO",
            foglio="28",
            particella="18",
            subalterno="A",
            sup_catastale_are=Decimal("2025"),
            anno=2024,
        )
        db.commit()

        second_id = _upsert_catasto_parcel(
            db,
            comune_nome="MOGORO",
            foglio="28",
            particella="18",
            subalterno="A",
            sup_catastale_are=Decimal("2030"),
            anno=2025,
        )
        db.commit()

        rows = db.scalars(
            select(CatastoParcel).order_by(CatastoParcel.valid_from.asc())
        ).all()
        assert second_id != first_id
        assert len(rows) == 2
        assert rows[0].valid_from == 2024
        assert rows[0].valid_to == 2024
        assert float(rows[0].sup_catastale_are) == 2025.0
        assert rows[1].valid_from == 2025
        assert rows[1].valid_to is None
        assert float(rows[1].sup_catastale_are) == 2030.0
    finally:
        db.close()


def test_upsert_catasto_parcel_same_year_updates_missing_surface() -> None:
    db = TestingSessionLocal()
    try:
        first_id = _upsert_catasto_parcel(
            db,
            comune_nome="ARBOREA",
            foglio="11",
            particella="525",
            subalterno=None,
            sup_catastale_are=None,
            anno=2025,
        )
        db.commit()

        second_id = _upsert_catasto_parcel(
            db,
            comune_nome="ARBOREA",
            foglio="11",
            particella="525",
            subalterno=None,
            sup_catastale_are=Decimal("7300"),
            anno=2025,
        )
        db.commit()

        saved = db.get(CatastoParcel, first_id)
        assert second_id == first_id
        assert saved is not None
        assert float(saved.sup_catastale_are) == 7300.0
        assert float(saved.sup_catastale_ha) == 73.0
    finally:
        db.close()
