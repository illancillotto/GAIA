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
from app.modules.catasto.routes.distretti import get_distretto_geojson
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


def _expected_graphical_area(db: Session, wkt: str) -> str:
    value = db.execute(
        text(
            """
            SELECT ROUND(ST_Area(ST_Transform(ST_GeomFromText(:wkt, 4326), 3003))::numeric, 2)
            """
        ),
        {"wkt": wkt},
    ).scalar_one()
    return str(value)


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
    geometry_wkt = _polygon_wkt(8.58, 39.78)
    new_geometry_wkt = _polygon_wkt(8.59, 39.79)
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
            "wkt": geometry_wkt,
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
        expected_graphical_area = _expected_graphical_area(db_session, geometry_wkt)

        assert result["status"] == "completed"
        assert batch is not None
        assert batch.tipo == "shapefile"
        assert batch.righe_totali == 1
        assert batch.righe_importate == 1
        assert batch.report_json["records_inserted_current"] == 1
        assert len(inserted) == 1
        assert inserted[0].cod_comune_capacitas == 165
        assert inserted[0].foglio == foglio
        assert inserted[0].particella == particella
        assert str(inserted[0].superficie_grafica_mq) == expected_graphical_area
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
        cod_comune_capacitas=165,
        codice_catastale="A357",
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
    old_geometry_wkt = _polygon_wkt(8.585, 39.785)
    old_graphical_area = _expected_graphical_area(db_session, old_geometry_wkt)
    db_session.execute(
        text(
            """
            UPDATE cat_particelle
            SET geometry = ST_GeomFromText(:wkt, 4326),
                superficie_grafica_mq = ROUND(ST_Area(ST_Transform(ST_GeomFromText(:wkt, 4326), 3003))::numeric, 2)
            WHERE id = :particella_id
            """
        ),
        {"wkt": old_geometry_wkt, "particella_id": str(existing_id)},
    )
    db_session.commit()

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
            "wkt": new_geometry_wkt,
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
                CatParticella.cod_comune_capacitas == 165,
                CatParticella.foglio == foglio,
                CatParticella.particella == particella,
                CatParticella.is_current.is_(True),
            )
        ).scalars().all()
        history_rows = db_session.execute(
            select(CatParticellaHistory).where(CatParticellaHistory.particella_id == existing_id)
        ).scalars().all()
        expected_new_graphical_area = _expected_graphical_area(db_session, new_geometry_wkt)

        assert result["status"] == "completed"
        assert existing.is_current is False
        assert existing.valid_to == date.today()
        assert len(current_rows) == 1
        assert current_rows[0].id != existing_id
        assert str(current_rows[0].superficie_mq) == "1450.00"
        assert str(current_rows[0].superficie_grafica_mq) == expected_new_graphical_area
        assert current_rows[0].cfm == "A357-NEW"
        assert len(history_rows) == 1
        assert str(history_rows[0].superficie_mq) == "1000.00"
        assert str(history_rows[0].superficie_grafica_mq) == old_graphical_area
        assert history_rows[0].change_reason == "import_shapefile"
    finally:
        _cleanup_shapefile_artifacts(
            db_session,
            staging_table=staging_table,
            num_distretto=num_distretto,
            foglio=foglio,
            particella=particella,
        )


def test_distretto_geojson_route_returns_feature_for_geometry(db_session: Session) -> None:
    suffix = uuid4().hex[:8]
    num_distretto = f"7{suffix[:3]}"
    distretto_id = uuid4()

    db_session.execute(text("DELETE FROM cat_distretti WHERE num_distretto = :n"), {"n": num_distretto})
    db_session.execute(
        text(
            """
            INSERT INTO cat_distretti (id, num_distretto, nome_distretto, geometry, attivo)
            VALUES (:id, :num, :nome, ST_GeomFromText(:wkt, 4326), true)
            """
        ),
        {
            "id": str(distretto_id),
            "num": num_distretto,
            "nome": f"Distretto geojson {suffix}",
            "wkt": _polygon_wkt(8.61, 39.81),
        },
    )
    db_session.commit()

    try:
        payload = get_distretto_geojson(distretto_id, db_session, object())
        assert payload["type"] == "Feature"
        assert payload["geometry"]["type"] in {"MultiPolygon", "Polygon"}
        assert payload["properties"]["id"] == str(distretto_id)
        assert payload["properties"]["num_distretto"] == num_distretto
    finally:
        db_session.execute(text("DELETE FROM cat_distretti WHERE num_distretto = :n"), {"n": num_distretto})
        db_session.commit()


def test_distretto_geojson_route_returns_404_when_geometry_is_missing(db_session: Session) -> None:
    suffix = uuid4().hex[:8]
    num_distretto = f"5{suffix[:3]}"
    distretto_id = uuid4()

    db_session.execute(text("DELETE FROM cat_distretti WHERE num_distretto = :n"), {"n": num_distretto})
    db_session.execute(
        text(
            """
            INSERT INTO cat_distretti (id, num_distretto, nome_distretto, geometry, attivo)
            VALUES (:id, :num, :nome, NULL, true)
            """
        ),
        {
            "id": str(distretto_id),
            "num": num_distretto,
            "nome": f"Distretto senza geometria {suffix}",
        },
    )
    db_session.commit()

    try:
        with pytest.raises(Exception) as exc_info:
            get_distretto_geojson(distretto_id, db_session, object())
        assert "geometria" in str(exc_info.value).lower()
    finally:
        db_session.execute(text("DELETE FROM cat_distretti WHERE num_distretto = :n"), {"n": num_distretto})
        db_session.commit()


def test_finalize_shapefile_import_excludes_fd_distretto_from_upsert(db_session: Session) -> None:
    suffix = uuid4().hex[:8]
    staging_table = f"cat_particelle_staging_it_{suffix}"
    num_distretto = "FD"
    foglio = f"5{suffix[:2]}"
    particella = f"6{suffix[2:5]}"

    # NOTE: we deliberately avoid deleting by num_distretto='FD' because that value may
    # exist in shared dev DBs and be referenced by `cat_utenze_irrigue`.
    db_session.execute(text(f'DROP TABLE IF EXISTS "{staging_table}"'))  # nosec - generated local test table
    db_session.execute(
        text(
            """
            DELETE FROM cat_particelle_history
            WHERE foglio = :foglio AND particella = :particella
            """
        ),
        {"foglio": foglio, "particella": particella},
    )
    db_session.execute(
        text(
            """
            DELETE FROM cat_particelle
            WHERE foglio = :foglio AND particella = :particella
            """
        ),
        {"foglio": foglio, "particella": particella},
    )
    db_session.execute(text("DELETE FROM cat_import_batches WHERE filename = :filename"), {"filename": staging_table})
    db_session.commit()

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
              :foglio, :particella, '1', 'A357-FDTEST', '100.00', 'FD', 'Fuori distretto',
              ST_GeomFromText(:wkt, 4326)
            )
            '''
        ),
        {"foglio": foglio, "particella": particella, "wkt": _polygon_wkt(8.62, 39.82)},
    )
    db_session.commit()

    try:
        result = finalize_shapefile_import(
            db_session,
            created_by=_created_by(db_session),
            staging_table=staging_table,
        )
        assert result["status"] == "completed"

        fd_distretto = db_session.execute(select(CatDistretto).where(CatDistretto.num_distretto == "FD")).scalar_one_or_none()
        assert fd_distretto is None

        inserted = db_session.execute(
            select(CatParticella).where(CatParticella.foglio == foglio, CatParticella.particella == particella, CatParticella.is_current.is_(True))
        ).scalar_one_or_none()
        assert inserted is not None
        assert inserted.num_distretto == "FD"
        assert inserted.fuori_distretto is True
    finally:
        db_session.execute(text(f'DROP TABLE IF EXISTS "{staging_table}"'))  # nosec - generated local test table
        db_session.execute(
            text("DELETE FROM cat_particelle_history WHERE foglio = :foglio AND particella = :particella"),
            {"foglio": foglio, "particella": particella},
        )
        db_session.execute(
            text("DELETE FROM cat_particelle WHERE foglio = :foglio AND particella = :particella"),
            {"foglio": foglio, "particella": particella},
        )
        db_session.execute(text("DELETE FROM cat_import_batches WHERE filename = :filename"), {"filename": staging_table})
        db_session.commit()


def test_finalize_shapefile_import_maps_cod_catastale_from_reference_dataset(db_session: Session) -> None:
    suffix = uuid4().hex[:8]
    staging_table = f"cat_particelle_staging_it_{suffix}"
    num_distretto = f"6{suffix[:3]}"
    foglio = f"7{suffix[:2]}"
    particella = f"8{suffix[2:5]}"

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
              codi_fisc text,
              nume_fogl text,
              nume_part text,
              suba_part text,
              cfm text,
              nationalca text,
              supe_part text,
              num_dist text,
              nome_dist text,
              wkb_geometry geometry(MULTIPOLYGON, 4326)
            )
            '''
        )
    )

    # Row 1: mapping from CODI_FISC must win over fallback fields (A368 -> 286 / San Nicolo d'Arcidano)
    db_session.execute(
        text(
            f'''
            INSERT INTO "{staging_table}" (
              codi_fisc, nume_fogl, nume_part, suba_part, cfm, nationalca, supe_part, num_dist, nome_dist, wkb_geometry
            ) VALUES (
              'A368', :foglio, :particella, '1', 'B314-IGNORED', NULL, '10.00', :num_dist, 'Distretto map 1',
              ST_GeomFromText(:wkt1, 4326)
            )
            '''
        ),
        {"foglio": foglio, "particella": particella, "num_dist": num_distretto, "wkt1": _polygon_wkt(8.63, 39.83)},
    )

    # Row 2: mapping from national_code when cfm is missing (B314 -> 212)
    foglio2 = f"{foglio}X"
    particella2 = f"{particella}X"
    db_session.execute(
        text(
            f'''
            INSERT INTO "{staging_table}" (
              codi_fisc, nume_fogl, nume_part, suba_part, cfm, nationalca, supe_part, num_dist, nome_dist, wkb_geometry
            ) VALUES (
              NULL, :foglio2, :particella2, '1', NULL, 'B314TEST0001', '11.00', :num_dist, 'Distretto map 2',
              ST_GeomFromText(:wkt2, 4326)
            )
            '''
        ),
        {"foglio2": foglio2, "particella2": particella2, "num_dist": num_distretto, "wkt2": _polygon_wkt(8.64, 39.84)},
    )

    # Row 3: mapping from CFM prefix (H301 -> 232 / Riola Sardo)
    foglio3 = f"{foglio}Y"
    particella3 = f"{particella}Y"
    db_session.execute(
        text(
            f'''
            INSERT INTO "{staging_table}" (
              codi_fisc, nume_fogl, nume_part, suba_part, cfm, nationalca, supe_part, num_dist, nome_dist, wkb_geometry
            ) VALUES (
              NULL, :foglio3, :particella3, '1', 'H301-ITEST', NULL, '12.00', :num_dist, 'Distretto map 3',
              ST_GeomFromText(:wkt3, 4326)
            )
            '''
        ),
        {"foglio3": foglio3, "particella3": particella3, "num_dist": num_distretto, "wkt3": _polygon_wkt(8.65, 39.85)},
    )

    db_session.commit()

    try:
        result = finalize_shapefile_import(
            db_session,
            created_by=_created_by(db_session),
            staging_table=staging_table,
        )
        assert result["status"] == "completed"

        inserted_1 = db_session.execute(
            select(CatParticella).where(CatParticella.foglio == foglio, CatParticella.particella == particella, CatParticella.is_current.is_(True))
        ).scalar_one()
        inserted_2 = db_session.execute(
            select(CatParticella).where(CatParticella.foglio == foglio2, CatParticella.particella == particella2, CatParticella.is_current.is_(True))
        ).scalar_one()
        inserted_3 = db_session.execute(
            select(CatParticella).where(CatParticella.foglio == foglio3, CatParticella.particella == particella3, CatParticella.is_current.is_(True))
        ).scalar_one()

        assert inserted_1.cod_comune_capacitas == 286
        assert inserted_1.nome_comune == "San Nicolo d'Arcidano"
        assert inserted_2.cod_comune_capacitas == 212
        assert inserted_2.nome_comune == "Cabras"
        assert inserted_3.cod_comune_capacitas == 232
        assert inserted_3.nome_comune == "Riola Sardo"
    finally:
        db_session.execute(text(f'DROP TABLE IF EXISTS "{staging_table}"'))  # nosec - generated local test table
        db_session.execute(
            text("DELETE FROM cat_particelle WHERE foglio IN (:f1, :f2, :f3) AND particella IN (:p1, :p2, :p3)"),
            {"f1": foglio, "f2": foglio2, "f3": foglio3, "p1": particella, "p2": particella2, "p3": particella3},
        )
        db_session.execute(
            text("DELETE FROM cat_particelle_history WHERE foglio IN (:f1, :f2, :f3) AND particella IN (:p1, :p2, :p3)"),
            {"f1": foglio, "f2": foglio2, "f3": foglio3, "p1": particella, "p2": particella2, "p3": particella3},
        )
        db_session.execute(text("DELETE FROM cat_distretti WHERE num_distretto = :n"), {"n": num_distretto})
        db_session.execute(text("DELETE FROM cat_import_batches WHERE filename = :f"), {"f": staging_table})
        db_session.commit()


def test_finalize_shapefile_import_writes_history_when_only_geometry_changes(db_session: Session) -> None:
    suffix = uuid4().hex[:8]
    staging_table = f"cat_particelle_staging_it_{suffix}"
    num_distretto = f"4{suffix[:3]}"
    foglio = f"9{suffix[:2]}"
    particella = f"7{suffix[2:5]}"

    _cleanup_shapefile_artifacts(
        db_session,
        staging_table=staging_table,
        num_distretto=num_distretto,
        foglio=foglio,
        particella=particella,
    )

    existing = CatParticella(
        national_code="A357TESTGEO1",
        cod_comune_capacitas=165,
        codice_catastale="A357",
        nome_comune="Arborea",
        foglio=foglio,
        particella=particella,
        subalterno="1",
        cfm="A357-GEO",
        superficie_mq=1111,
        num_distretto=num_distretto,
        nome_distretto="Distretto geometry only",
        source_type="seed",
        valid_from=date(2024, 1, 1),
        is_current=True,
        suppressed=False,
        geometry=f"SRID=4326;{_polygon_wkt(8.66, 39.86)}",
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
              :foglio, :particella, '1', 'A357-GEO', '1111.00', :num_distretto, 'Distretto geometry only',
              ST_GeomFromText(:wkt, 4326)
            )
            '''
        ),
        {
            "foglio": foglio,
            "particella": particella,
            "num_distretto": num_distretto,
            "wkt": _polygon_wkt(8.68, 39.88),
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
                CatParticella.cod_comune_capacitas == 165,
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
        assert len(current_rows) == 1
        assert current_rows[0].id != existing_id
        assert current_rows[0].cfm == "A357-GEO"
        assert str(current_rows[0].superficie_mq) == "1111.00"
        assert len(history_rows) == 1
        assert history_rows[0].change_reason == "import_shapefile"
    finally:
        _cleanup_shapefile_artifacts(
            db_session,
            staging_table=staging_table,
            num_distretto=num_distretto,
            foglio=foglio,
            particella=particella,
        )
