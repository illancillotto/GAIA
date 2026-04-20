"""PostgreSQL integration tests for Catasto shapefile finalize flow."""

from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.application_user import ApplicationUser
from app.models.catasto_phase1 import CatDistretto, CatImportBatch, CatParticella, CatParticellaHistory
from app.modules.catasto.services.import_shapefile import finalize_shapefile_import


def _polygon_wkt(x0: float, y0: float) -> str:
    return (
        "MULTIPOLYGON((("
        f"{x0} {y0}, "
        f"{x0 + 0.001} {y0}, "
        f"{x0 + 0.001} {y0 + 0.001}, "
        f"{x0} {y0 + 0.001}, "
        f"{x0} {y0}"
        ")))"
    )


@pytest.fixture(scope="module")
def engine():
    if not settings.database_url.startswith("postgresql"):
        pytest.skip("PostgreSQL integration tests require a PostgreSQL DATABASE_URL")
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    with engine.connect() as conn:
        conn.execute(text("SELECT PostGIS_version()"))
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(engine):
    session = Session(engine)
    yield session
    session.close()


def _created_by(db: Session) -> int:
    user_id = db.execute(select(func.min(ApplicationUser.id))).scalar_one_or_none()
    if user_id is None:
        pytest.skip("ApplicationUser bootstrap data is required for integration tests")
    return int(user_id)


def _cleanup_shapefile_artifacts(db: Session, *, staging_table: str, num_distretto: str, foglio: str, particella: str) -> None:
    db.execute(text(f'DROP TABLE IF EXISTS "{staging_table}"'))  # nosec - generated local test table
    db.execute(
        delete_stmt := text(
            """
            DELETE FROM cat_particelle_history
            WHERE num_distretto = :num_distretto
               OR (foglio = :foglio AND particella = :particella)
            """
        ),
        {"num_distretto": num_distretto, "foglio": foglio, "particella": particella},
    )
    db.execute(
        text(
            """
            DELETE FROM cat_particelle
            WHERE num_distretto = :num_distretto
               OR (foglio = :foglio AND particella = :particella)
            """
        ),
        {"num_distretto": num_distretto, "foglio": foglio, "particella": particella},
    )
    db.execute(text("DELETE FROM cat_distretti WHERE num_distretto = :num_distretto"), {"num_distretto": num_distretto})
    db.execute(text("DELETE FROM cat_import_batches WHERE filename = :filename"), {"filename": staging_table})
    db.commit()


def test_finalize_shapefile_import_inserts_current_particelle_and_distretti(db_session: Session) -> None:
    suffix = uuid4().hex[:8]
    staging_table = f"cat_particelle_staging_it_{suffix}"
    num_distretto = f"9{suffix[:3]}"
    foglio = f"1{suffix[:2]}"
    particella = f"2{suffix[2:5]}"

    _cleanup_shapefile_artifacts(
        db_session,
        staging_table=staging_table,
        num_distretto=num_distretto,
        foglio=foglio,
        particella=particella,
    )

    db_session.execute(
        text(
            f'''
            CREATE TABLE "{staging_table}" (
              nume_fogl text,
              nume_part text,
              suba_part text,
              cfm text,
              supe_part text,
              num_dist text,
              nome_dist text,
              wkb_geometry geometry(MULTIPOLYGON, 4326)
            )
            '''
        )
    )
    db_session.execute(
        text(
            f'''
            INSERT INTO "{staging_table}" (
              nume_fogl, nume_part, suba_part, cfm, supe_part, num_dist, nome_dist, wkb_geometry
            ) VALUES (
              :foglio, :particella, '1', 'A357-ITEST', '1234.50', :num_distretto, 'Distretto test {suffix}',
              ST_GeomFromText(:wkt, 4326)
            )
            '''
        ),
        {
            "foglio": foglio,
            "particella": particella,
            "num_distretto": num_distretto,
            "wkt": _polygon_wkt(8.58, 39.78),
        },
    )
    db_session.commit()

    try:
        result = finalize_shapefile_import(
            db_session,
            created_by=_created_by(db_session),
            staging_table=staging_table,
        )

        batch_id = UUID(result["batch_id"])
        batch = db_session.get(CatImportBatch, batch_id)
        inserted = db_session.execute(
            select(CatParticella).where(CatParticella.import_batch_id == batch_id, CatParticella.is_current.is_(True))
        ).scalars().all()
        distretto = db_session.execute(
            select(CatDistretto).where(CatDistretto.num_distretto == num_distretto)
        ).scalar_one_or_none()

        assert result["status"] == "completed"
        assert batch is not None
        assert batch.tipo == "shapefile"
        assert batch.righe_totali == 1
        assert batch.righe_importate == 1
        assert batch.report_json["records_inserted_current"] == 1
        assert len(inserted) == 1
        assert inserted[0].cod_comune_istat == 165
        assert inserted[0].foglio == foglio
        assert inserted[0].particella == particella
        assert inserted[0].num_distretto == num_distretto
        assert distretto is not None
        assert distretto.nome_distretto == f"Distretto test {suffix}"
    finally:
        _cleanup_shapefile_artifacts(
            db_session,
            staging_table=staging_table,
            num_distretto=num_distretto,
            foglio=foglio,
            particella=particella,
        )


def test_finalize_shapefile_import_writes_history_on_changed_particella(db_session: Session) -> None:
    suffix = uuid4().hex[:8]
    staging_table = f"cat_particelle_staging_it_{suffix}"
    num_distretto = f"8{suffix[:3]}"
    foglio = f"3{suffix[:2]}"
    particella = f"4{suffix[2:5]}"

    _cleanup_shapefile_artifacts(
        db_session,
        staging_table=staging_table,
        num_distretto=num_distretto,
        foglio=foglio,
        particella=particella,
    )

    existing = CatParticella(
        national_code="A357TEST0001",
        cod_comune_istat=165,
        nome_comune="Arborea",
        foglio=foglio,
        particella=particella,
        subalterno="1",
        cfm="A357-OLD",
        superficie_mq=1000,
        num_distretto=num_distretto,
        nome_distretto="Distretto old",
        source_type="seed",
        valid_from=date(2024, 1, 1),
        is_current=True,
        suppressed=False,
    )
    db_session.add(existing)
    db_session.commit()
    existing_id = existing.id

    db_session.execute(
        text(
            f'''
            CREATE TABLE "{staging_table}" (
              nume_fogl text,
              nume_part text,
              suba_part text,
              cfm text,
              supe_part text,
              num_dist text,
              nome_dist text,
              wkb_geometry geometry(MULTIPOLYGON, 4326)
            )
            '''
        )
    )
    db_session.execute(
        text(
            f'''
            INSERT INTO "{staging_table}" (
              nume_fogl, nume_part, suba_part, cfm, supe_part, num_dist, nome_dist, wkb_geometry
            ) VALUES (
              :foglio, :particella, '1', 'A357-NEW', '1450.00', :num_distretto, 'Distretto new',
              ST_GeomFromText(:wkt, 4326)
            )
            '''
        ),
        {
            "foglio": foglio,
            "particella": particella,
            "num_distretto": num_distretto,
            "wkt": _polygon_wkt(8.59, 39.79),
        },
    )
    db_session.commit()

    try:
        result = finalize_shapefile_import(
            db_session,
            created_by=_created_by(db_session),
            staging_table=staging_table,
        )

        db_session.refresh(existing)
        current_rows = db_session.execute(
            select(CatParticella).where(
                CatParticella.cod_comune_istat == 165,
                CatParticella.foglio == foglio,
                CatParticella.particella == particella,
                CatParticella.is_current.is_(True),
            )
        ).scalars().all()
        history_rows = db_session.execute(
            select(CatParticellaHistory).where(CatParticellaHistory.particella_id == existing_id)
        ).scalars().all()

        assert result["status"] == "completed"
        assert existing.is_current is False
        assert existing.valid_to == date.today()
        assert len(current_rows) == 1
        assert current_rows[0].id != existing_id
        assert str(current_rows[0].superficie_mq) == "1450.00"
        assert current_rows[0].cfm == "A357-NEW"
        assert len(history_rows) == 1
        assert str(history_rows[0].superficie_mq) == "1000.00"
        assert history_rows[0].change_reason == "import_shapefile"
    finally:
        _cleanup_shapefile_artifacts(
            db_session,
            staging_table=staging_table,
            num_distretto=num_distretto,
            foglio=foglio,
            particella=particella,
        )
