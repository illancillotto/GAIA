from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

try:
    from osgeo import ogr, osr
except ModuleNotFoundError:  # pragma: no cover - local env may use pyshp fallback instead
    ogr = None
    osr = None

from app.db.base import Base
from app.modules.catasto.schemas.gis_schemas import ParticellaPopupRuoloItem, ParticellaPopupRuoloSummary
from app.modules.catasto.services import dui_2026_overlay
from app.modules.ruolo.models import RuoloAvviso, RuoloParticella, RuoloPartita


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def setup_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    dui_2026_overlay._DATASET_CACHE = None
    yield
    dui_2026_overlay._DATASET_CACHE = None
    Base.metadata.drop_all(bind=engine)


def _write_test_shapefile(path: Path) -> None:
    if ogr is None or osr is None:
        pytest.skip("OSGeo non disponibile per generare lo shapefile di test.")

    driver = ogr.GetDriverByName("ESRI Shapefile")
    datasource = driver.CreateDataSource(str(path))
    assert datasource is not None

    spatial_ref = osr.SpatialReference()
    spatial_ref.ImportFromEPSG(3003)
    layer = datasource.CreateLayer(path.stem, spatial_ref, ogr.wkbPolygon)

    field_specs = [
        ("ID_OPERAT", ogr.OFTString),
        ("CODICEFISC", ogr.OFTString),
        ("COGN_NOME", ogr.OFTString),
        ("TELEFONO", ogr.OFTString),
        ("SUP_GRAFIC", ogr.OFTInteger64),
        ("COLTURA", ogr.OFTString),
        ("NUM_DOM", ogr.OFTInteger64),
        ("TIPO_DOM", ogr.OFTString),
        ("DATA", ogr.OFTDate),
        ("CONTATORE", ogr.OFTString),
        ("TELERILEV", ogr.OFTString),
        ("X", ogr.OFTReal),
        ("Y", ogr.OFTReal),
    ]
    for name, field_type in field_specs:
        layer.CreateField(ogr.FieldDefn(name, field_type))

    feature = ogr.Feature(layer.GetLayerDefn())
    feature.SetField("ID_OPERAT", "DDF")
    feature.SetField("CODICEFISC", "RSSMRA80A01H501U")
    feature.SetField("COGN_NOME", "Rossi Mario")
    feature.SetField("TELEFONO", "3400000000")
    feature.SetField("SUP_GRAFIC", 2337)
    feature.SetField("COLTURA", "OLIVO")
    feature.SetField("NUM_DOM", 16)
    feature.SetField("TIPO_DOM", "NW")
    feature.SetField("DATA", 2026, 6, 25, 0, 0, 0, 0)
    feature.SetField("CONTATORE", "SI")
    feature.SetField("TELERILEV", "NO")
    feature.SetField("X", 1459603.748)
    feature.SetField("Y", 4421548.212)

    ring = ogr.Geometry(ogr.wkbLinearRing)
    ring.AddPoint(1459571.04818183, 4421561.55479216)
    ring.AddPoint(1459596.33023544, 4421582.93762358)
    ring.AddPoint(1459638.21542874, 4421542.81336934)
    ring.AddPoint(1459605.8896189, 4421510.73912221)
    ring.AddPoint(1459571.04818183, 4421561.55479216)
    polygon = ogr.Geometry(ogr.wkbPolygon)
    polygon.AddGeometry(ring)
    feature.SetGeometry(polygon)
    layer.CreateFeature(feature)

    feature = None
    datasource = None


def test_parse_snapshot_date_extracts_expected_day() -> None:
    parsed = dui_2026_overlay._parse_snapshot_date("Dui2026-TOTALE-al_25-06-2026.shp")

    assert parsed is not None
    assert parsed.isoformat() == "2026-06-25"


def test_find_latest_shapefile_path_prefers_newest_snapshot_date(tmp_path: Path) -> None:
    older = tmp_path / "Dui2026-TOTALE-al_03-06-2026.shp"
    newer = tmp_path / "Dui2026-TOTALE-al_25-06-2026.shp"
    older.write_text("")
    newer.write_text("")

    selected = dui_2026_overlay._find_latest_shapefile_path(tmp_path)

    assert selected == newer


def test_load_raw_dataset_from_shapefile_reads_geometry_and_fields(tmp_path: Path) -> None:
    shapefile_path = tmp_path / "Dui2026-TOTALE-al_25-06-2026.shp"
    _write_test_shapefile(shapefile_path)

    payload = dui_2026_overlay._load_raw_dataset_from_shapefile(shapefile_path)

    assert payload["source_filename"] == shapefile_path.name
    assert payload["source_date"] == "2026-06-25"
    assert payload["feature_count"] == 1
    feature = payload["geojson"]["features"][0]
    assert feature["geometry"]["type"] == "Polygon"
    assert 8.0 < feature["geometry"]["coordinates"][0][0][0] < 10.0
    assert 39.0 < feature["geometry"]["coordinates"][0][0][1] < 41.0
    assert feature["properties"]["domanda_irrigua"] == "16"
    assert feature["properties"]["codice_fiscale"] == "RSSMRA80A01H501U"
    assert feature["properties"]["intestatario"] == "Rossi Mario"
    assert feature["properties"]["sup_grafica_mq"] == 2337
    assert feature["properties"]["contatore"] == "SI"
    assert feature["properties"]["telerilev"] == "NO"


def test_require_dui_reader_dependency_raises_explicit_error_when_no_supported_reader_is_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dui_2026_overlay, "_OSGEO_IMPORT_ERROR", ModuleNotFoundError("No module named 'osgeo'"))
    monkeypatch.setattr(dui_2026_overlay, "ogr", None)
    monkeypatch.setattr(dui_2026_overlay, "osr", None)
    monkeypatch.setattr(dui_2026_overlay, "_PYSHAPE_IMPORT_ERROR", ModuleNotFoundError("No module named 'shapefile'"))
    monkeypatch.setattr(dui_2026_overlay, "pyshp", None)
    monkeypatch.setattr(dui_2026_overlay, "_PYPROJ_IMPORT_ERROR", ModuleNotFoundError("No module named 'pyproj'"))
    monkeypatch.setattr(dui_2026_overlay, "CRS", None)
    monkeypatch.setattr(dui_2026_overlay, "Transformer", None)

    with pytest.raises(dui_2026_overlay.Dui2026DependencyUnavailableError) as excinfo:
        dui_2026_overlay._require_dui_reader_dependency()

    assert str(excinfo.value) == "Layer DUI 2026 non disponibile: installare GDAL/OSGeo oppure pyshp+pyproj nel backend."


def test_load_raw_dataset_from_shapefile_uses_pyshp_fallback_when_osgeo_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shapefile_path = tmp_path / "Dui2026-TOTALE-al_25-06-2026.shp"
    shapefile_path.write_text("")
    shapefile_path.with_suffix(".prj").write_text(dui_2026_overlay.CRS.from_epsg(3003).to_wkt(), encoding="utf-8")

    class FakeRecord:
        def as_dict(self) -> dict[str, object]:
            return {
                "ID_OPERAT": "DDF",
                "CODICEFISC": "RSSMRA80A01H501U",
                "COGN_NOME": "Rossi Mario",
                "TELEFONO": "3400000000",
                "SUP_GRAFIC": 2337,
                "COLTURA": "OLIVO",
                "NUM_DOM": 16,
                "TIPO_DOM": "NW",
                "DATA": "2026-06-25",
                "CONTATORE": "SI",
                "TELERILEV": "NO",
                "X": 1459603.748,
                "Y": 4421548.212,
            }

    class FakeReader:
        fields = [("DeletionFlag", "C", 1, 0)]

        def __init__(self, _path: str) -> None:
            return None

        def iterShapeRecords(self):
            geometry = {
                "type": "Polygon",
                "coordinates": [[
                    [1459571.04818183, 4421561.55479216],
                    [1459596.33023544, 4421582.93762358],
                    [1459638.21542874, 4421542.81336934],
                    [1459605.8896189, 4421510.73912221],
                    [1459571.04818183, 4421561.55479216],
                ]],
            }
            yield SimpleNamespace(
                shape=SimpleNamespace(__geo_interface__=geometry),
                record=FakeRecord(),
            )

    monkeypatch.setattr(dui_2026_overlay, "_OSGEO_IMPORT_ERROR", ModuleNotFoundError("No module named 'osgeo'"))
    monkeypatch.setattr(dui_2026_overlay, "ogr", None)
    monkeypatch.setattr(dui_2026_overlay, "osr", None)
    monkeypatch.setattr(dui_2026_overlay, "_PYSHAPE_IMPORT_ERROR", None)
    monkeypatch.setattr(dui_2026_overlay, "pyshp", SimpleNamespace(Reader=FakeReader))
    monkeypatch.setattr(dui_2026_overlay, "_PYPROJ_IMPORT_ERROR", None)

    payload = dui_2026_overlay._load_raw_dataset_from_shapefile(shapefile_path)

    assert payload["feature_count"] == 1
    feature = payload["geojson"]["features"][0]
    assert feature["geometry"]["type"] == "Polygon"
    assert 8.0 < feature["geometry"]["coordinates"][0][0][0] < 10.0
    assert 39.0 < feature["geometry"]["coordinates"][0][0][1] < 41.0
    assert feature["properties"]["domanda_irrigua"] == "16"


def test_get_dui_2026_latest_layer_marks_ruolo_2025_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        dui_2026_overlay,
        "_get_cached_dataset",
        lambda: {
            "source_path": "/tmp/Dui2026-TOTALE-al_25-06-2026.shp",
            "source_filename": "Dui2026-TOTALE-al_25-06-2026.shp",
            "source_date": "2026-06-25",
            "source_updated_at": "2026-06-26T07:43:00",
            "feature_count": 2,
            "geojson": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {"type": "Polygon", "coordinates": []},
                        "properties": {
                            "domanda_irrigua": "16",
                            "contatore": "SI",
                            "telerilev": "NO",
                        },
                    },
                    {
                        "type": "Feature",
                        "geometry": {"type": "Polygon", "coordinates": []},
                        "properties": {
                            "domanda_irrigua": "99",
                            "contatore": "NO",
                            "telerilev": "SI",
                        },
                    },
                ],
            },
        },
    )

    db = TestingSessionLocal()
    try:
        avviso_id = uuid4()
        partita_id = uuid4()
        db.add(
            RuoloAvviso(
                id=avviso_id,
                import_job_id=uuid4(),
                codice_cnc="CNC-0016",
                anno_tributario=2025,
            )
        )
        db.add(
            RuoloPartita(
                id=partita_id,
                avviso_id=avviso_id,
                codice_partita="PART-16",
                comune_nome="Arborea",
            )
        )
        db.add(
            RuoloParticella(
                id=uuid4(),
                partita_id=partita_id,
                anno_tributario=2025,
                domanda_irrigua="0016",
                foglio="1",
                particella="2",
            )
        )
        db.add(
            RuoloParticella(
                id=uuid4(),
                partita_id=uuid4(),
                anno_tributario=2024,
                domanda_irrigua="99",
                foglio="1",
                particella="2",
            )
        )
        db.commit()

        payload = dui_2026_overlay.get_dui_2026_latest_layer(db)
    finally:
        db.close()

    assert payload.label == "DUI 2026 live"
    assert payload.stats.total_polygons == 2
    assert payload.stats.in_ruolo_2025 == 1
    assert payload.stats.not_in_ruolo_2025 == 1
    assert payload.stats.with_contatore == 1
    assert payload.stats.without_contatore == 1
    assert payload.stats.with_telerilev == 1
    first, second = payload.geojson["features"]
    assert first["properties"]["in_ruolo_2025"] is True
    assert first["properties"]["ruolo_2025_match_count"] == 1
    assert first["properties"]["__overlayColor"] == dui_2026_overlay.ROLE_MATCH_COLOR
    assert second["properties"]["in_ruolo_2025"] is False
    assert second["properties"]["ruolo_2025_match_count"] == 0
    assert second["properties"]["__overlayColor"] == dui_2026_overlay.ROLE_MISSING_COLOR


def test_get_dui_2026_domanda_detail_returns_ruolo_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        dui_2026_overlay,
        "_get_cached_dataset",
        lambda: {
            "source_path": "/tmp/Dui2026-TOTALE-al_25-06-2026.shp",
            "source_filename": "Dui2026-TOTALE-al_25-06-2026.shp",
            "source_date": "2026-06-25",
            "source_updated_at": "2026-06-26T07:43:00",
            "feature_count": 1,
            "geojson": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {"type": "Polygon", "coordinates": []},
                        "properties": {
                            "domanda_irrigua": "16",
                            "codice_fiscale": "RSSMRA80A01H501U",
                            "intestatario": "Rossi Mario",
                            "sup_grafica_mq": 2337,
                            "coltura": "OLIVO",
                            "tipo_domanda": "NW",
                            "data_domanda": "2026-06-25",
                            "contatore": "SI",
                            "telerilev": "NO",
                            "operatore": "DDF",
                            "point_x": 1459603.748,
                            "point_y": 4421548.212,
                        },
                    },
                ],
            },
        },
    )

    monkeypatch.setattr(
        dui_2026_overlay,
        "_load_ruolo_2025_summary_by_domanda",
        lambda db, domanda_irrigua: ParticellaPopupRuoloSummary(
            anno_tributario_latest=2025,
            anno_tributario_richiesto=2025,
            source_mode="dui_domanda",
            source_note="Dettaglio ruolo 2025 aggregato per domanda irrigua.",
            n_righe=1,
            n_subalterni=1,
            sup_catastale_ha_totale=0.3,
            sup_irrigata_ha_totale=0.2337,
            importo_manut_euro_totale=10.0,
            importo_irrig_euro_totale=20.0,
            importo_ist_euro_totale=3.0,
            importo_totale_euro=33.0,
            items=[
                ParticellaPopupRuoloItem(
                    anno_tributario=2025,
                    domanda_irrigua="0016",
                    subalterno="1",
                    coltura="OLIVO",
                    sup_irrigata_ha=0.2337,
                    importo_totale_euro=33.0,
                ),
            ],
        ),
    )

    db = TestingSessionLocal()
    try:
        detail = dui_2026_overlay.get_dui_2026_domanda_detail(db, "16")
    finally:
        db.close()

    assert detail.domanda_irrigua == "16"
    assert detail.intestatario == "Rossi Mario"
    assert detail.n_poligoni == 1
    assert detail.in_ruolo_2025 is True
    assert detail.ruolo_2025_match_count == 1
    assert detail.ruolo_summary is not None
    assert detail.ruolo_summary.source_mode == "dui_domanda"
    assert detail.ruolo_summary.importo_totale_euro == 33.0
