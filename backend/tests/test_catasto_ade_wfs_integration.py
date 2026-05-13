"""PostgreSQL/PostGIS integration tests for AdE WFS alignment apply flow."""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.catasto_phase1 import CatParticella, CatParticellaHistory
from app.modules.catasto.services.ade_wfs import (
    apply_ade_alignment,
    get_ade_alignment_report,
    preview_ade_alignment_apply,
)


def _polygon_wkt(x0: float, y0: float, size: float = 0.001) -> str:
    return (
        "MULTIPOLYGON((("
        f"{x0} {y0}, "
        f"{x0 + size} {y0}, "
        f"{x0 + size} {y0 + size}, "
        f"{x0} {y0 + size}, "
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
        missing_tables = conn.execute(
            text(
                """
                SELECT table_name
                FROM unnest(ARRAY['cat_ade_sync_runs', 'cat_ade_particelle']) AS table_name
                WHERE to_regclass('public.' || table_name) IS NULL
                """
            )
        ).scalars().all()
        if missing_tables:
            pytest.skip(f"AdE WFS migration not applied: {', '.join(missing_tables)}")
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(engine):
    session = Session(engine)
    yield session
    session.close()


def _ensure_comune_arborea(db: Session) -> None:
    db.execute(
        text(
            """
            INSERT INTO cat_comuni (
                id,
                nome_comune,
                codice_catastale,
                cod_comune_capacitas,
                codice_comune_formato_numerico,
                codice_comune_numerico_2017_2025,
                nome_comune_legacy,
                cod_provincia,
                sigla_provincia,
                regione
            )
            VALUES (
                gen_random_uuid(),
                'Arborea',
                'A357',
                165,
                115006,
                95006,
                'Arborea',
                115,
                'OR',
                'Sardegna'
            )
            ON CONFLICT (codice_catastale) DO NOTHING
            """
        )
    )


def _create_run(db: Session, *, min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> str:
    run_id = str(uuid4())
    db.execute(
        text(
            """
            INSERT INTO cat_ade_sync_runs (
                id,
                status,
                request_bbox_json,
                max_tile_km2,
                max_tiles,
                count_per_page,
                max_pages_per_tile,
                tiles,
                features,
                upserted,
                with_geometry,
                started_at,
                completed_at
            )
            VALUES (
                :id,
                'completed',
                CAST(:bbox AS json),
                4,
                25,
                1000,
                20,
                1,
                0,
                0,
                0,
                :now,
                :now
            )
            """
        ),
        {
            "id": run_id,
            "bbox": (
                "{"
                f'"min_lon": {min_lon}, "min_lat": {min_lat}, '
                f'"max_lon": {max_lon}, "max_lat": {max_lat}'
                "}"
            ),
            "now": datetime.now(timezone.utc),
        },
    )
    return run_id


def _insert_ade_particella(
    db: Session,
    *,
    run_id: str,
    national_ref: str,
    foglio: str,
    particella: str,
    wkt: str,
    codice_catastale: str = "A357",
) -> None:
    db.execute(
        text(
            """
            INSERT INTO cat_ade_particelle (
                id,
                source_run_id,
                national_cadastral_reference,
                administrative_unit,
                codice_catastale,
                foglio,
                foglio_raw,
                particella,
                particella_raw,
                geometry,
                source_crs,
                raw_payload_json,
                fetched_at,
                updated_at
            )
            VALUES (
                gen_random_uuid(),
                CAST(:run_id AS uuid),
                CAST(:national_ref AS varchar),
                CAST(:codice_catastale AS varchar),
                CAST(:codice_catastale AS varchar),
                CAST(:foglio AS varchar),
                LPAD(CAST(:foglio AS text), 4, '0'),
                CAST(:particella AS varchar),
                CAST(:particella AS varchar),
                ST_GeomFromText(:wkt, 4326),
                'EPSG:6706',
                CAST(:payload AS json),
                :now,
                :now
            )
            """
        ),
        {
            "run_id": run_id,
            "national_ref": national_ref,
            "codice_catastale": codice_catastale,
            "foglio": foglio,
            "particella": particella,
            "wkt": wkt,
            "payload": "{}",
            "now": datetime.now(timezone.utc),
        },
    )


def _insert_particella(
    db: Session,
    *,
    foglio: str,
    particella: str,
    wkt: str,
    suffix: str,
) -> str:
    particella_id = str(uuid4())
    db.execute(
        text(
            """
            INSERT INTO cat_particelle (
                id,
                comune_id,
                national_code,
                cod_comune_capacitas,
                codice_catastale,
                nome_comune,
                foglio,
                particella,
                superficie_mq,
                superficie_grafica_mq,
                num_distretto,
                nome_distretto,
                geometry,
                source_type,
                valid_from,
                is_current,
                suppressed,
                created_at,
                updated_at
            )
            SELECT
                :id,
                c.id,
                :national_code,
                c.cod_comune_capacitas,
                c.codice_catastale,
                c.nome_comune,
                :foglio,
                :particella,
                1000,
                ROUND(ST_Area(ST_Transform(ST_GeomFromText(:wkt, 4326), 32632))::numeric, 2),
                :num_distretto,
                'Distretto AdE test',
                ST_GeomFromText(:wkt, 4326),
                'test',
                :valid_from,
                true,
                false,
                now(),
                now()
            FROM cat_comuni c
            WHERE c.codice_catastale = 'A357'
            """
        ),
        {
            "id": particella_id,
            "national_code": f"A357TEST{suffix}",
            "foglio": foglio,
            "particella": particella,
            "wkt": wkt,
            "num_distretto": f"TA{suffix[:4]}",
            "valid_from": date(2024, 1, 1),
        },
    )
    return particella_id


def _cleanup(db: Session, *, suffix: str, run_ids: list[str] | None = None) -> None:
    db.rollback()
    foglio_prefix = f"8{suffix[:2]}"
    db.execute(
        text(
            """
            DELETE FROM cat_gis_saved_selection_items
            WHERE particella_id IN (
                SELECT id FROM cat_particelle WHERE foglio LIKE :foglio_prefix
            )
            """
        ),
        {"foglio_prefix": f"{foglio_prefix}%"},
    )
    db.execute(
        text(
            """
            DELETE FROM cat_consorzio_units
            WHERE particella_id IN (
                SELECT id FROM cat_particelle WHERE foglio LIKE :foglio_prefix
            )
            """
        ),
        {"foglio_prefix": f"{foglio_prefix}%"},
    )
    db.execute(
        text(
            """
            DELETE FROM cat_utenze_irrigue
            WHERE particella_id IN (
                SELECT id FROM cat_particelle WHERE foglio LIKE :foglio_prefix
            )
            """
        ),
        {"foglio_prefix": f"{foglio_prefix}%"},
    )
    db.execute(
        text(
            """
            DELETE FROM cat_particelle_history
            WHERE foglio LIKE :foglio_prefix
               OR particella_id IN (
                    SELECT id FROM cat_particelle WHERE foglio LIKE :foglio_prefix
               )
            """
        ),
        {"foglio_prefix": f"{foglio_prefix}%"},
    )
    db.execute(text("DELETE FROM cat_particelle WHERE foglio LIKE :foglio_prefix"), {"foglio_prefix": f"{foglio_prefix}%"})
    if run_ids:
        db.execute(text("DELETE FROM cat_ade_particelle WHERE source_run_id = ANY(:run_ids)"), {"run_ids": run_ids})
        db.execute(text("DELETE FROM cat_ade_sync_runs WHERE id = ANY(:run_ids)"), {"run_ids": run_ids})
    db.execute(text("DELETE FROM cat_import_batches WHERE filename = :filename"), {"filename": f"ade-it-{suffix}"})
    db.commit()


def _insert_fk_dependents(db: Session, *, particella_id: str, suffix: str) -> tuple[str, str]:
    batch_id = str(uuid4())
    utenza_id = str(uuid4())
    unit_id = str(uuid4())
    db.execute(
        text(
            """
            INSERT INTO cat_import_batches (id, filename, tipo, righe_totali, righe_importate, righe_anomalie, status)
            VALUES (:id, :filename, 'capacitas', 1, 1, 0, 'completed')
            """
        ),
        {"id": batch_id, "filename": f"ade-it-{suffix}"},
    )
    db.execute(
        text(
            """
            INSERT INTO cat_utenze_irrigue (
                id,
                import_batch_id,
                anno_campagna,
                cco,
                cod_comune_capacitas,
                nome_comune,
                foglio,
                particella,
                particella_id
            )
            VALUES (:id, :batch_id, 2026, :cco, 165, 'Arborea', :foglio, :particella, :particella_id)
            """
        ),
        {
            "id": utenza_id,
            "batch_id": batch_id,
            "cco": f"CCO{suffix[:6]}",
            "foglio": f"8{suffix[:2]}",
            "particella": f"1{suffix[2:5]}",
            "particella_id": particella_id,
        },
    )
    db.execute(
        text(
            """
            INSERT INTO cat_consorzio_units (
                id,
                particella_id,
                cod_comune_capacitas,
                foglio,
                particella,
                is_active
            )
            VALUES (:id, :particella_id, 165, :foglio, :particella, true)
            """
        ),
        {
            "id": unit_id,
            "particella_id": particella_id,
            "foglio": f"8{suffix[:2]}",
            "particella": f"1{suffix[2:5]}",
        },
    )
    return utenza_id, unit_id


def test_apply_ade_alignment_updates_geometry_in_place_and_preserves_fk(db_session: Session) -> None:
    suffix = uuid4().hex[:8]
    foglio = f"8{suffix[:2]}"
    particella = f"1{suffix[2:5]}"
    run_ids: list[str] = []

    _ensure_comune_arborea(db_session)
    _cleanup(db_session, suffix=suffix)
    old_wkt = _polygon_wkt(8.01, 39.01)
    new_wkt = _polygon_wkt(8.02, 39.02)
    try:
        particella_id = _insert_particella(
            db_session,
            foglio=foglio,
            particella=particella,
            wkt=old_wkt,
            suffix=suffix,
        )
        utenza_id, unit_id = _insert_fk_dependents(db_session, particella_id=particella_id, suffix=suffix)
        run_id = _create_run(db_session, min_lon=8.0, min_lat=39.0, max_lon=8.04, max_lat=39.04)
        run_ids.append(run_id)
        _insert_ade_particella(
            db_session,
            run_id=run_id,
            national_ref=f"A357A{foglio.zfill(4)}00.{particella}",
            foglio=foglio,
            particella=particella,
            wkt=new_wkt,
        )
        db_session.commit()

        preview = preview_ade_alignment_apply(
            db_session,
            run_id,
            categories=["geometrie_variate"],
            geometry_threshold_m=1,
        )
        result = apply_ade_alignment(
            db_session,
            run_id,
            categories=["geometrie_variate"],
            geometry_threshold_m=1,
            confirm=True,
        )
        db_session.expire_all()

        current = db_session.get(CatParticella, particella_id)
        history_rows = db_session.execute(
            select(CatParticellaHistory).where(CatParticellaHistory.particella_id == particella_id)
        ).scalars().all()
        is_new_geometry = db_session.execute(
            text(
                """
                SELECT ST_Equals(geometry, ST_GeomFromText(:new_wkt, 4326))
                FROM cat_particelle
                WHERE id = :id
                """
            ),
            {"id": particella_id, "new_wkt": new_wkt},
        ).scalar_one()
        linked_utenza = db_session.execute(
            text("SELECT particella_id::text FROM cat_utenze_irrigue WHERE id = :id"),
            {"id": utenza_id},
        ).scalar_one()
        linked_unit = db_session.execute(
            text("SELECT particella_id::text FROM cat_consorzio_units WHERE id = :id"),
            {"id": unit_id},
        ).scalar_one()

        assert preview["counters"]["update_geometry"] == 1
        assert result["counters"]["updated_geometry"] == 1
        assert current is not None
        assert str(current.id) == particella_id
        assert current.is_current is True
        assert current.suppressed is False
        assert current.source_type == "ade_wfs"
        assert is_new_geometry is True
        assert linked_utenza == particella_id
        assert linked_unit == particella_id
        assert len(history_rows) == 1
        assert history_rows[0].change_reason == "ade_wfs_alignment"

        report_after = get_ade_alignment_report(db_session, run_id, geometry_threshold_m=1)
        assert report_after["counters"]["geometrie_variate"] == 0
        assert report_after["counters"]["allineate"] == 1
    finally:
        _cleanup(db_session, suffix=suffix, run_ids=run_ids)


def test_apply_ade_alignment_suppresses_missing_only_with_explicit_flag(db_session: Session) -> None:
    suffix = uuid4().hex[:8]
    foglio = f"8{suffix[:2]}"
    particella = f"2{suffix[2:5]}"
    run_ids: list[str] = []

    _ensure_comune_arborea(db_session)
    _cleanup(db_session, suffix=suffix)
    wkt = _polygon_wkt(8.11, 39.11)
    try:
        particella_id = _insert_particella(
            db_session,
            foglio=foglio,
            particella=particella,
            wkt=wkt,
            suffix=suffix,
        )
        run_id = _create_run(db_session, min_lon=8.10, min_lat=39.10, max_lon=8.13, max_lat=39.13)
        run_ids.append(run_id)
        db_session.commit()

        with pytest.raises(ValueError, match="Soppressione mancanti"):
            apply_ade_alignment(
                db_session,
                run_id,
                categories=["mancanti_in_ade"],
                geometry_threshold_m=1,
                confirm=True,
                allow_suppress_missing=False,
            )

        result = apply_ade_alignment(
            db_session,
            run_id,
            categories=["mancanti_in_ade"],
            geometry_threshold_m=1,
            confirm=True,
            allow_suppress_missing=True,
        )
        db_session.expire_all()
        current = db_session.get(CatParticella, particella_id)
        history_rows = db_session.execute(
            select(CatParticellaHistory).where(CatParticellaHistory.particella_id == particella_id)
        ).scalars().all()

        assert result["counters"]["suppressed_missing"] == 1
        assert current is not None
        assert current.is_current is True
        assert current.suppressed is True
        assert current.source_type == "ade_wfs"
        assert len(history_rows) == 1
        assert history_rows[0].change_reason == "ade_wfs_alignment_missing"
    finally:
        _cleanup(db_session, suffix=suffix, run_ids=run_ids)


def test_apply_ade_alignment_handles_split_as_parent_suppressed_and_new_children(db_session: Session) -> None:
    suffix = uuid4().hex[:8]
    foglio = f"8{suffix[:2]}"
    parent = f"3{suffix[2:5]}"
    child_a = f"4{suffix[2:5]}"
    child_b = f"5{suffix[2:5]}"
    run_ids: list[str] = []

    _ensure_comune_arborea(db_session)
    _cleanup(db_session, suffix=suffix)
    parent_wkt = _polygon_wkt(8.21, 39.21, 0.002)
    child_a_wkt = _polygon_wkt(8.21, 39.21, 0.001)
    child_b_wkt = _polygon_wkt(8.211, 39.21, 0.001)
    try:
        parent_id = _insert_particella(
            db_session,
            foglio=foglio,
            particella=parent,
            wkt=parent_wkt,
            suffix=suffix,
        )
        run_id = _create_run(db_session, min_lon=8.20, min_lat=39.20, max_lon=8.23, max_lat=39.23)
        run_ids.append(run_id)
        _insert_ade_particella(
            db_session,
            run_id=run_id,
            national_ref=f"A357A{foglio.zfill(4)}00.{child_a}",
            foglio=foglio,
            particella=child_a,
            wkt=child_a_wkt,
        )
        _insert_ade_particella(
            db_session,
            run_id=run_id,
            national_ref=f"A357A{foglio.zfill(4)}00.{child_b}",
            foglio=foglio,
            particella=child_b,
            wkt=child_b_wkt,
        )
        db_session.commit()

        preview = preview_ade_alignment_apply(
            db_session,
            run_id,
            categories=["nuove_in_ade", "mancanti_in_ade"],
            geometry_threshold_m=1,
        )
        result = apply_ade_alignment(
            db_session,
            run_id,
            categories=["nuove_in_ade", "mancanti_in_ade"],
            geometry_threshold_m=1,
            confirm=True,
            allow_suppress_missing=True,
        )
        db_session.expire_all()
        parent_row = db_session.get(CatParticella, parent_id)
        children = db_session.execute(
            select(CatParticella).where(
                CatParticella.codice_catastale == "A357",
                CatParticella.foglio == foglio,
                CatParticella.particella.in_([child_a, child_b]),
                CatParticella.is_current.is_(True),
            )
        ).scalars().all()
        history_rows = db_session.execute(
            select(CatParticellaHistory).where(CatParticellaHistory.particella_id == parent_id)
        ).scalars().all()

        assert preview["counters"]["insert_new"] == 2
        assert preview["counters"]["suppress_missing"] == 1
        assert result["counters"]["inserted_new"] == 2
        assert result["counters"]["suppressed_missing"] == 1
        assert parent_row is not None
        assert parent_row.suppressed is True
        assert {row.particella for row in children} == {child_a, child_b}
        assert all(row.source_type == "ade_wfs" for row in children)
        assert len(history_rows) == 1
        assert history_rows[0].change_reason == "ade_wfs_alignment_missing"
    finally:
        _cleanup(db_session, suffix=suffix, run_ids=run_ids)


def test_apply_ade_alignment_skips_new_parcels_when_comune_is_unmapped(db_session: Session) -> None:
    suffix = uuid4().hex[:8]
    foglio = f"8{suffix[:2]}"
    particella = f"6{suffix[2:5]}"
    run_ids: list[str] = []

    _cleanup(db_session, suffix=suffix)
    try:
        run_id = _create_run(db_session, min_lon=8.30, min_lat=39.30, max_lon=8.33, max_lat=39.33)
        run_ids.append(run_id)
        _insert_ade_particella(
            db_session,
            run_id=run_id,
            national_ref=f"Z999A{foglio.zfill(4)}00.{particella}",
            foglio=foglio,
            particella=particella,
            wkt=_polygon_wkt(8.31, 39.31),
            codice_catastale="Z999",
        )
        db_session.commit()

        result = apply_ade_alignment(
            db_session,
            run_id,
            categories=["nuove_in_ade"],
            geometry_threshold_m=1,
            confirm=True,
        )
        inserted = db_session.execute(
            select(CatParticella).where(CatParticella.codice_catastale == "Z999", CatParticella.foglio == foglio)
        ).scalars().all()

        assert result["counters"]["inserted_new"] == 0
        assert result["counters"]["skipped_missing_comune"] == 1
        assert inserted == []
    finally:
        _cleanup(db_session, suffix=suffix, run_ids=run_ids)


def test_apply_ade_alignment_standard_does_not_suppress_missing_gaia(db_session: Session) -> None:
    suffix = uuid4().hex[:8]
    foglio = f"8{suffix[:2]}"
    missing_particella = f"7{suffix[2:5]}"
    new_particella = f"8{suffix[2:5]}"
    run_ids: list[str] = []

    _ensure_comune_arborea(db_session)
    _cleanup(db_session, suffix=suffix)
    try:
        missing_id = _insert_particella(
            db_session,
            foglio=foglio,
            particella=missing_particella,
            wkt=_polygon_wkt(8.41, 39.41),
            suffix=suffix,
        )
        run_id = _create_run(db_session, min_lon=8.40, min_lat=39.40, max_lon=8.43, max_lat=39.43)
        run_ids.append(run_id)
        _insert_ade_particella(
            db_session,
            run_id=run_id,
            national_ref=f"A357A{foglio.zfill(4)}00.{new_particella}",
            foglio=foglio,
            particella=new_particella,
            wkt=_polygon_wkt(8.42, 39.42),
        )
        db_session.commit()

        preview = preview_ade_alignment_apply(
            db_session,
            run_id,
            categories=["nuove_in_ade", "geometrie_variate"],
            geometry_threshold_m=1,
        )
        result = apply_ade_alignment(
            db_session,
            run_id,
            categories=["nuove_in_ade", "geometrie_variate"],
            geometry_threshold_m=1,
            confirm=True,
        )
        db_session.expire_all()
        missing = db_session.get(CatParticella, missing_id)
        inserted = db_session.execute(
            select(CatParticella).where(
                CatParticella.codice_catastale == "A357",
                CatParticella.foglio == foglio,
                CatParticella.particella == new_particella,
                CatParticella.is_current.is_(True),
            )
        ).scalar_one()
        missing_history = db_session.execute(
            select(CatParticellaHistory).where(CatParticellaHistory.particella_id == missing_id)
        ).scalars().all()
        report_after = get_ade_alignment_report(db_session, run_id, geometry_threshold_m=1)

        assert preview["counters"]["insert_new"] == 1
        assert preview["counters"]["suppress_missing"] == 0
        assert preview["counters"]["skipped_not_selected"] == 1
        assert result["counters"]["inserted_new"] == 1
        assert result["counters"]["suppressed_missing"] == 0
        assert missing is not None
        assert missing.suppressed is False
        assert missing.is_current is True
        assert inserted.source_type == "ade_wfs"
        assert missing_history == []
        assert report_after["counters"]["mancanti_in_ade"] == 1
    finally:
        _cleanup(db_session, suffix=suffix, run_ids=run_ids)
