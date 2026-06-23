from __future__ import annotations

from pathlib import Path
import sys
import types

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.application_user import ApplicationUser
from app.models.catasto_phase1 import (
    CatDeliveryPoint,
    CatDistretto,
    CatIrrigationCanal,
    CatMeterReading,
    CatMeterReadingImport,
)
from app.modules.utenze.models import AnagraficaSubject
from app.modules.catasto.services import delivery_points_import as service


class _FakeShapeRecord:
    def __init__(self, record: list[object], geometry: dict[str, object]) -> None:
        self.record = record
        self.shape = types.SimpleNamespace(__geo_interface__=geometry)


class _FakeReader:
    def __init__(self, payload: dict[str, object]) -> None:
        self.fields = payload["fields"]
        self._records = payload["records"]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def iterShapeRecords(self):
        return iter(self._records)


def _install_fake_shapefile(monkeypatch, registry: dict[str, dict[str, object]]) -> None:
    module = types.ModuleType("shapefile")

    def reader(path: str):
        return _FakeReader(registry[path])

    module.Reader = reader
    monkeypatch.setitem(sys.modules, "shapefile", module)


def _build_engine():
    return create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def test_parse_delivery_points_shapefile_reads_points_and_canals(tmp_path: Path, monkeypatch) -> None:
    point_path = tmp_path / service.POINT_FOLDER_WITH_METER / "D24_Punti_Consegna_2026.shp"
    canal_path = tmp_path / service.POINT_FOLDER_WITHOUT_METER / "D08_Canalette_Irrigazione.shp"
    _touch(point_path)
    _touch(canal_path)

    registry = {
        str(point_path): {
            "fields": [
                ("DeletionFlag", "C", 1, 0),
                ("ID", "N", 4, 0),
                ("PUNTO_CON", "C", 15, 0),
                ("COD_CONT", "C", 20, 0),
                ("TIPOLOGIA", "C", 50, 0),
                ("TIPO", "C", 15, 0),
                ("X", "F", 11, 3),
                ("Y", "F", 11, 3),
                ("FOTO", "C", 120, 0),
            ],
            "records": [
                _FakeShapeRecord(
                    [312, "7W_11-20B", "10993", "idrometro Bermad dn. 125", "CONT_NO_TES", 1462222.773, 4398240.157, "foto.jpg"],
                    {"type": "Point", "coordinates": (1462222.77339385, 4398240.15719749)},
                )
            ],
        },
        str(canal_path): {
            "fields": [
                ("DeletionFlag", "C", 1, 0),
                ("ID_Canale", "C", 30, 0),
                ("Tipo_Canal", "C", 30, 0),
                ("Distretto", "C", 30, 0),
            ],
            "records": [
                _FakeShapeRecord(
                    ["CANALE-1", "canaletta", "Pauli_Bingias"],
                    {"type": "LineString", "coordinates": [(1458104.0, 4422004.4), (1458300.0, 4422200.0)]},
                )
            ],
        },
    }
    _install_fake_shapefile(monkeypatch, registry)

    point_features = service.parse_delivery_points_shapefile(point_path)
    assert len(point_features) == 1
    assert point_features[0].feature_kind == "point"
    assert point_features[0].distretto_code == "24"
    assert point_features[0].point_code == "7W_11-20B"
    assert point_features[0].has_meter is True

    canal_features = service.parse_delivery_points_shapefile(canal_path)
    assert len(canal_features) == 1
    assert canal_features[0].feature_kind == "canal"
    assert canal_features[0].distretto_code == "08"
    assert canal_features[0].canal_source_key is not None


def test_parse_delivery_points_shapefile_promotes_single_multipoint_to_point(tmp_path: Path, monkeypatch) -> None:
    point_path = tmp_path / service.POINT_FOLDER_WITH_METER / "D34_Punti_Consegna_2026.shp"
    _touch(point_path)

    registry = {
        str(point_path): {
            "fields": [
                ("DeletionFlag", "C", 1, 0),
                ("PUNTO_CONS", "C", 15, 0),
                ("COD_CONT", "C", 20, 0),
                ("TIPOLOGIA", "C", 50, 0),
                ("TIPO", "C", 15, 0),
                ("X", "F", 11, 3),
                ("Y", "F", 11, 3),
            ],
            "records": [
                _FakeShapeRecord(
                    ["66-2_3S", "", "Colonnina flangiata dn. 100", "FLANGIA", 1470945.920, 4398262.313],
                    {"type": "MultiPoint", "coordinates": [(1470945.92034393, 4398262.31308142)]},
                )
            ],
        }
    }
    _install_fake_shapefile(monkeypatch, registry)

    features = service.parse_delivery_points_shapefile(point_path)
    assert len(features) == 1
    assert features[0].feature_kind == "point"
    assert features[0].distretto_code == "34"
    assert features[0].point_code == "66-2_3S"
    assert "POINT" in features[0].geometry_wkt


def test_parse_delivery_points_shapefile_supports_punt_cons_alias(tmp_path: Path, monkeypatch) -> None:
    point_path = tmp_path / service.POINT_FOLDER_WITH_METER / "D04_Punti_Consegna_2026.shp"
    _touch(point_path)

    registry = {
        str(point_path): {
            "fields": [
                ("DeletionFlag", "C", 1, 0),
                ("ID", "N", 4, 0),
                ("PUNT_CONS", "C", 15, 0),
                ("COD_CONT", "C", 20, 0),
                ("TIPOLOGIA", "C", 50, 0),
                ("TIPO", "C", 15, 0),
                ("X", "F", 11, 3),
                ("Y", "F", 11, 3),
            ],
            "records": [
                _FakeShapeRecord(
                    [528, "C2F_17", "", "colonnina flangiata Ø 100", "FLANGIA", 1467441.316, 4429696.038],
                    {"type": "Point", "coordinates": (1467441.31624398, 4429696.0380983)},
                )
            ],
        }
    }
    _install_fake_shapefile(monkeypatch, registry)

    features = service.parse_delivery_points_shapefile(point_path)
    assert len(features) == 1
    assert features[0].distretto_code == "04"
    assert features[0].point_code == "C2F_17"


def test_import_delivery_points_links_existing_meter_readings_and_marks_stale_points_inactive(
    tmp_path: Path, monkeypatch
) -> None:
    point_with_meter = tmp_path / service.POINT_FOLDER_WITH_METER / "D24_Punti_Consegna_2026.shp"
    point_without_meter = tmp_path / service.POINT_FOLDER_WITHOUT_METER / "D20_Punti_Consegna.shp"
    canal_path = tmp_path / service.POINT_FOLDER_WITHOUT_METER / "D08_Canalette_Irrigazione.shp"
    _touch(point_with_meter)
    _touch(point_without_meter)
    _touch(canal_path)

    registry = {
        str(point_with_meter): {
            "fields": [
                ("DeletionFlag", "C", 1, 0),
                ("ID", "N", 4, 0),
                ("PUNTO_CON", "C", 15, 0),
                ("COD_CONT", "C", 20, 0),
                ("TIPOLOGIA", "C", 50, 0),
                ("TIPO", "C", 15, 0),
                ("X", "F", 11, 3),
                ("Y", "F", 11, 3),
            ],
            "records": [
                _FakeShapeRecord(
                    [312, "7W_11-20B", "10993", "idrometro Bermad dn. 125", "CONT_NO_TES", 1462222.773, 4398240.157],
                    {"type": "Point", "coordinates": (1462222.77339385, 4398240.15719749)},
                )
            ],
        },
        str(point_without_meter): {
            "fields": [
                ("DeletionFlag", "C", 1, 0),
                ("ID", "N", 4, 0),
                ("PUNTO_CONS", "C", 15, 0),
                ("COD_CONT", "C", 20, 0),
                ("TIPOLOGIA", "C", 50, 0),
                ("TIPO", "C", 15, 0),
                ("X", "F", 11, 3),
                ("Y", "F", 11, 3),
            ],
            "records": [
                _FakeShapeRecord(
                    [45, "C13_B_10", "", "punto senza contatore", "", 1466410.263, 4413615.277],
                    {"type": "Point", "coordinates": (1466410.263915, 4413615.277135)},
                )
            ],
        },
        str(canal_path): {
            "fields": [
                ("DeletionFlag", "C", 1, 0),
                ("ID_Canale", "C", 30, 0),
                ("Tipo_Canal", "C", 30, 0),
                ("Distretto", "C", 30, 0),
            ],
            "records": [
                _FakeShapeRecord(
                    ["CANALE-1", "canaletta", "Pauli_Bingias"],
                    {"type": "LineString", "coordinates": [(1458104.0, 4422004.4), (1458300.0, 4422200.0)]},
                )
            ],
        },
    }
    _install_fake_shapefile(monkeypatch, registry)

    engine = _build_engine()
    Base.metadata.create_all(
        bind=engine,
        tables=[
            ApplicationUser.__table__,
            AnagraficaSubject.__table__,
            CatDistretto.__table__,
            CatDeliveryPoint.__table__,
            CatIrrigationCanal.__table__,
            CatMeterReadingImport.__table__,
            CatMeterReading.__table__,
        ],
    )
    with Session(engine) as db:
        distretto = CatDistretto(num_distretto="24", nome_distretto="Lotto Sud Arborea")
        db.add(distretto)
        db.flush()
        db.add(
            CatDeliveryPoint(
                distretto_code="24",
                punto_consegna_code="OLD_POINT",
                source_dataset=service.SOURCE_DATASET_2026_DEF,
                is_active=True,
            )
        )
        db.add(
            CatMeterReading(
                anno=2026,
                distretto_id=distretto.id,
                punto_consegna="7W_11-20B",
                source="excel",
            )
        )
        db.commit()

        result = service.import_delivery_points_2026_def(db, root_path=tmp_path)
        assert result == {
            "points_processed": 2,
            "canals_processed": 1,
            "meter_readings_linked": 1,
            "meter_readings_unlinked": 0,
        }

        points = db.execute(select(CatDeliveryPoint).order_by(CatDeliveryPoint.punto_consegna_code)).scalars().all()
        imported = {point.punto_consegna_code: point for point in points}
        assert imported["7W_11-20B"].has_meter is True
        assert imported["7W_11-20B"].cod_cont == "10993"
        assert "POINT" in str(imported["7W_11-20B"].geometry)
        assert imported["C13_B_10"].has_meter is False
        assert imported["OLD_POINT"].is_active is False

        canals = db.execute(select(CatIrrigationCanal)).scalars().all()
        assert len(canals) == 1
        assert canals[0].distretto_code == "08"
        assert "LINESTRING" in str(canals[0].geometry)

        reading = db.execute(select(CatMeterReading)).scalar_one()
        assert reading.delivery_point_id == imported["7W_11-20B"].id
        assert service.resolve_delivery_point_id(
            db,
            distretto=distretto,
            punto_consegna=" 7W_11-20B ",
            cache={},
        ) == imported["7W_11-20B"].id


def test_normalizers_cover_composite_codes() -> None:
    assert service.normalize_distretto_code("D24") == "24"
    assert service.normalize_distretto_code("D12-D13") == "12-13"
    assert service.normalize_distretto_code(" D28_1D_1L ") == "28_1D_1L"
    assert service.normalize_point_code("  abc   1 ") == "ABC 1"
    assert service.strip_activity_suffix(" 11_13_2_A ") == "11_13_2"
    assert service.strip_activity_suffix("11_13_2") == "11_13_2"
    assert service.insert_dot_after_numeric_prefix("10E_1-29C") == "10.E_1-29C"
    assert service.insert_dot_after_numeric_prefix("7W.1_1") == "7W.1_1"


def test_resolve_delivery_point_id_falls_back_to_subdistrict_and_meter_code(tmp_path: Path, monkeypatch) -> None:
    engine = _build_engine()
    Base.metadata.create_all(
        bind=engine,
        tables=[
            ApplicationUser.__table__,
            AnagraficaSubject.__table__,
            CatDistretto.__table__,
            CatDeliveryPoint.__table__,
            CatIrrigationCanal.__table__,
            CatMeterReadingImport.__table__,
            CatMeterReading.__table__,
        ],
    )
    with Session(engine) as db:
        distretto = CatDistretto(num_distretto="28", nome_distretto="Distretto 28")
        db.add(distretto)
        db.flush()
        point_a = CatDeliveryPoint(
            distretto_code="28_1D_1L",
            punto_consegna_code="14_1_1",
            cod_cont="673090",
            has_meter=True,
            is_active=True,
            source_dataset=service.SOURCE_DATASET_2026_DEF,
        )
        point_b = CatDeliveryPoint(
            distretto_code="28_1D_2L",
            punto_consegna_code="14_1_1",
            cod_cont="674070",
            has_meter=True,
            is_active=True,
            source_dataset=service.SOURCE_DATASET_2026_DEF,
        )
        db.add_all([point_a, point_b])
        db.commit()

        assert (
            service.resolve_delivery_point_id(
                db,
                distretto=distretto,
                punto_consegna="14_1_1",
                matricola="673090",
                cache={},
            )
            == point_a.id
        )
        assert (
            service.resolve_delivery_point_id(
                db,
                distretto=distretto,
                punto_consegna="14_1_1",
                matricola="674070",
                cache={},
            )
            == point_b.id
        )
        assert (
            service.resolve_delivery_point_id(
                db,
                distretto=distretto,
                punto_consegna="14_1_1",
                matricola=None,
                cache={},
            )
            is None
        )


def test_resolve_delivery_point_id_strips_activity_suffix_and_cache_is_meter_aware() -> None:
    engine = _build_engine()
    Base.metadata.create_all(
        bind=engine,
        tables=[
            ApplicationUser.__table__,
            AnagraficaSubject.__table__,
            CatDistretto.__table__,
            CatDeliveryPoint.__table__,
            CatIrrigationCanal.__table__,
            CatMeterReadingImport.__table__,
            CatMeterReading.__table__,
        ],
    )
    with Session(engine) as db:
        distretto = CatDistretto(num_distretto="28", nome_distretto="Distretto 28")
        db.add(distretto)
        db.flush()
        point_a = CatDeliveryPoint(
            distretto_code="28_1D_1L",
            punto_consegna_code="13_1_1",
            cod_cont="205770044",
            has_meter=True,
            is_active=True,
            source_dataset=service.SOURCE_DATASET_2026_DEF,
        )
        point_b = CatDeliveryPoint(
            distretto_code="28_1D_2L",
            punto_consegna_code="13_1_1",
            cod_cont=None,
            has_meter=True,
            is_active=True,
            source_dataset=service.SOURCE_DATASET_2026_DEF,
        )
        db.add_all([point_a, point_b])
        db.commit()

        cache: dict[tuple[str, str, str | None], object | None] = {}
        assert (
            service.resolve_delivery_point_id(
                db,
                distretto=distretto,
                punto_consegna="13_1_1_A",
                matricola="205770044",
                cache=cache,
            )
            == point_a.id
        )
        assert (
            service.resolve_delivery_point_id(
                db,
                distretto=distretto,
                punto_consegna="13_1_1_A",
                matricola=None,
                cache=cache,
            )
            is None
        )


def test_resolve_delivery_point_id_supports_dotted_numeric_prefix_variant() -> None:
    engine = _build_engine()
    Base.metadata.create_all(
        bind=engine,
        tables=[
            ApplicationUser.__table__,
            AnagraficaSubject.__table__,
            CatDistretto.__table__,
            CatDeliveryPoint.__table__,
            CatIrrigationCanal.__table__,
            CatMeterReadingImport.__table__,
            CatMeterReading.__table__,
        ],
    )
    with Session(engine) as db:
        distretto = CatDistretto(num_distretto="24", nome_distretto="Distretto 24")
        db.add(distretto)
        db.flush()
        point = CatDeliveryPoint(
            distretto_code="24",
            punto_consegna_code="10.E_1-29C",
            cod_cont="10248",
            has_meter=True,
            is_active=True,
            source_dataset=service.SOURCE_DATASET_2026_DEF,
        )
        db.add(point)
        db.commit()

        assert (
            service.resolve_delivery_point_id(
                db,
                distretto=distretto,
                punto_consegna="10E_1-29C",
                matricola="10248",
                cache={},
            )
            == point.id
        )
