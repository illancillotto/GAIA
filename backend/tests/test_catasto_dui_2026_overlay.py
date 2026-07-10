from __future__ import annotations

from collections import Counter
from collections.abc import Generator
from decimal import Decimal
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
from app.modules.catasto.services import dui_overlay
from app.modules.catasto.services import dui_2026_overlay
from app.services.nas_connector import NasConnectorError
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


def test_legacy_module_alias_points_to_generic_dui_overlay() -> None:
    assert dui_2026_overlay is dui_overlay
    assert dui_2026_overlay.get_dui_2026_latest_layer is dui_overlay.get_dui_latest_layer
    assert dui_2026_overlay.get_dui_2026_domanda_detail is dui_overlay.get_dui_domanda_detail
    assert dui_2026_overlay.DUI_2026_TILE_LAYER == dui_overlay.DUI_TILE_LAYER


def test_dui_helper_edge_cases_are_normalized() -> None:
    assert dui_2026_overlay._norm_bool_label(None) is None
    assert dui_2026_overlay._norm_bool_label("yes") == "SI"
    assert dui_2026_overlay._norm_bool_label("0") == "NO"
    assert dui_2026_overlay._norm_bool_label("forse") == "FORSE"
    assert dui_2026_overlay._normalize_domanda_irrigua(None) is None
    assert dui_2026_overlay._normalize_domanda_irrigua("0016,0") == "16"
    assert dui_2026_overlay._normalize_domanda_irrigua("ABC") == "ABC"
    assert dui_2026_overlay._parse_snapshot_date("Dui2026-TOTALE-al_99-99-2026.shp") is None
    assert dui_2026_overlay._parse_snapshot_date("Dui2026-TOTALE.shp") is None
    assert dui_2026_overlay._is_smb_uri("smb://nas/path") is True
    assert dui_2026_overlay._is_smb_uri("/tmp/path") is False
    assert dui_2026_overlay._to_float(None, 2) is None
    assert dui_2026_overlay._to_float("bad", 2) is None
    assert dui_2026_overlay._to_float("12.345", 2) == 12.35
    assert dui_2026_overlay._find_dui_features_by_domanda("") == []


def test_find_latest_shapefile_path_prefers_newest_snapshot_date(tmp_path: Path) -> None:
    older = tmp_path / "Dui2026-TOTALE-al_03-06-2026.shp"
    newer = tmp_path / "Dui2026-TOTALE-al_25-06-2026.shp"
    older.write_text("")
    newer.write_text("")

    selected = dui_2026_overlay._find_latest_shapefile_path(tmp_path)

    assert selected == newer


def test_find_latest_shapefile_path_reports_missing_directory_and_files(tmp_path: Path) -> None:
    missing_dir = tmp_path / "missing"
    with pytest.raises(FileNotFoundError, match="Directory shapefile DUI 2026"):
        dui_2026_overlay._find_latest_shapefile_path(missing_dir)

    with pytest.raises(FileNotFoundError, match="Nessuno shapefile DUI 2026"):
        dui_2026_overlay._find_latest_shapefile_path(tmp_path)


def test_resolve_backup_source_defaults_to_smb_uri(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CATASTO_DUI_BACKUP_PATH", raising=False)
    monkeypatch.delenv("CATASTO_DUI_2026_BACKUP_PATH", raising=False)

    assert dui_2026_overlay._resolve_backup_source().startswith("smb://nas_cbo.local/")


def test_resolve_backup_source_prefers_generic_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CATASTO_DUI_BACKUP_PATH", "/tmp/generic")
    monkeypatch.setenv("CATASTO_DUI_2026_BACKUP_PATH", "/tmp/legacy")

    assert dui_2026_overlay._resolve_backup_source() == "/tmp/generic"
    assert dui_2026_overlay._resolve_backup_dir() == Path("/tmp/generic")


def test_materialized_latest_shapefile_uses_local_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    shapefile_path = tmp_path / "Dui2026-TOTALE-al_25-06-2026.shp"
    shapefile_path.write_text("shape", encoding="utf-8")
    monkeypatch.setenv("CATASTO_DUI_BACKUP_PATH", str(tmp_path))

    with dui_2026_overlay._materialized_latest_shapefile() as (source_path, signature, display_source):
        assert source_path == shapefile_path
        assert signature[0] == str(shapefile_path)
        assert signature[2] == len("shape")
        assert display_source is None


def test_find_latest_remote_shapefile_reports_missing_directory_and_files() -> None:
    class FakeClient:
        def __init__(self, exists: bool, output: str) -> None:
            self.exists = exists
            self.output = output

        def path_exists(self, _path: str) -> bool:
            return self.exists

        def run_command(self, _command: str) -> str:
            return self.output

    with pytest.raises(FileNotFoundError, match="Directory shapefile DUI 2026"):
        dui_2026_overlay._find_latest_remote_shapefile(FakeClient(False, ""), "/remote")

    with pytest.raises(FileNotFoundError, match="Nessuno shapefile DUI 2026"):
        dui_2026_overlay._find_latest_remote_shapefile(FakeClient(True, ""), "/remote")


def test_materialized_latest_shapefile_wraps_nas_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailingClient:
        def path_exists(self, _path: str) -> bool:
            raise NasConnectorError("NAS offline")

    monkeypatch.delenv("CATASTO_DUI_BACKUP_PATH", raising=False)
    monkeypatch.delenv("CATASTO_DUI_2026_BACKUP_PATH", raising=False)
    monkeypatch.setattr(dui_2026_overlay, "get_nas_client", lambda: FailingClient())
    monkeypatch.setattr(dui_2026_overlay, "_smb_uri_to_remote_path", lambda _source: "/remote")
    monkeypatch.setattr(dui_2026_overlay, "_resolve_remote_directory_path_case_insensitive", lambda client, path: client.path_exists(path))

    with pytest.raises(FileNotFoundError, match="Errore accesso NAS DUI 2026"):
        with dui_2026_overlay._materialized_latest_shapefile():
            pass


def test_get_cached_dataset_materializes_latest_shapefile_from_smb(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeNasClient:
        def __init__(self) -> None:
            self.downloaded: list[tuple[str, str]] = []

        def path_exists(self, path: str) -> bool:
            return path in {
                "/volume1/Settore Catasto/DOMANDE UTENZA IRRIGUA/Dui2026/Shp_Dui2026/Backup",
                "/volume1",
                "/volume1/Settore Catasto",
                "/volume1/Settore Catasto/DOMANDE UTENZA IRRIGUA",
                "/volume1/Settore Catasto/DOMANDE UTENZA IRRIGUA/Dui2026",
                "/volume1/Settore Catasto/DOMANDE UTENZA IRRIGUA/Dui2026/Shp_Dui2026",
                "/volume1/Settore Catasto/DOMANDE UTENZA IRRIGUA/Dui2026/Shp_Dui2026/Backup/Dui2026-TOTALE-al_25-06-2026.shp",
                "/volume1/Settore Catasto/DOMANDE UTENZA IRRIGUA/Dui2026/Shp_Dui2026/Backup/Dui2026-TOTALE-al_25-06-2026.dbf",
                "/volume1/Settore Catasto/DOMANDE UTENZA IRRIGUA/Dui2026/Shp_Dui2026/Backup/Dui2026-TOTALE-al_25-06-2026.shx",
                "/volume1/Settore Catasto/DOMANDE UTENZA IRRIGUA/Dui2026/Shp_Dui2026/Backup/Dui2026-TOTALE-al_25-06-2026.prj",
            }

        def run_command(self, command: str) -> str:
            if "-maxdepth 1 -type f" in command:
                return "\n".join(
                    [
                        "/volume1/Settore Catasto/DOMANDE UTENZA IRRIGUA/Dui2026/Shp_Dui2026/Backup/Dui2026-TOTALE-al_03-06-2026.shp",
                        "/volume1/Settore Catasto/DOMANDE UTENZA IRRIGUA/Dui2026/Shp_Dui2026/Backup/Dui2026-TOTALE-al_25-06-2026.shp",
                    ]
                )
            if "Dui2026-TOTALE-al_03-06-2026.shp" in command:
                return "1780000000 10"
            if "Dui2026-TOTALE-al_25-06-2026.shp" in command:
                return "1781000000 20"
            raise AssertionError(f"Unexpected command: {command}")

        def download_to_local(self, remote_path: str, local_path: str) -> None:
            self.downloaded.append((remote_path, local_path))
            Path(local_path).write_text("", encoding="utf-8")

    fake_client = FakeNasClient()

    def fake_load(path: Path) -> dict[str, object]:
        assert path.name == "Dui2026-TOTALE-al_25-06-2026.shp"
        return {
            "source_path": str(path),
            "source_filename": path.name,
            "source_date": "2026-06-25",
            "source_updated_at": "2026-06-26T07:43:00",
            "feature_count": 0,
            "geojson": {"type": "FeatureCollection", "features": []},
        }

    monkeypatch.delenv("CATASTO_DUI_2026_BACKUP_PATH", raising=False)
    monkeypatch.setattr(dui_2026_overlay, "get_nas_client", lambda: fake_client)
    monkeypatch.setattr(
        dui_2026_overlay,
        "_resolve_remote_directory_path_case_insensitive",
        lambda _client, _path: "/volume1/Settore Catasto/DOMANDE UTENZA IRRIGUA/Dui2026/Shp_Dui2026/Backup",
    )
    monkeypatch.setattr(dui_2026_overlay, "_load_raw_dataset_from_shapefile", fake_load)

    payload = dui_2026_overlay._get_cached_dataset()
    cached_payload = dui_2026_overlay._get_cached_dataset()

    assert payload is cached_payload
    assert payload["source_path"].endswith("Dui2026-TOTALE-al_25-06-2026.shp")
    assert payload["source_path"].startswith("/volume1/Settore Catasto/")
    assert [Path(local).suffix for _, local in fake_client.downloaded[:4]] == [".shp", ".dbf", ".shx", ".prj"]


def test_materialized_latest_shapefile_reports_missing_downloaded_shp(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeNasClient:
        def path_exists(self, path: str) -> bool:
            return path.endswith(".shp") or path == "/remote"

        def run_command(self, command: str) -> str:
            if "-maxdepth 1 -type f" in command:
                return "/remote/Dui2026-TOTALE-al_25-06-2026.shp"
            return "1781000000 20"

        def download_to_local(self, _remote_path: str, _local_path: str) -> None:
            return None

    monkeypatch.delenv("CATASTO_DUI_BACKUP_PATH", raising=False)
    monkeypatch.delenv("CATASTO_DUI_2026_BACKUP_PATH", raising=False)
    monkeypatch.setattr(dui_2026_overlay, "get_nas_client", lambda: FakeNasClient())
    monkeypatch.setattr(dui_2026_overlay, "_smb_uri_to_remote_path", lambda _source: "/remote")
    monkeypatch.setattr(dui_2026_overlay, "_resolve_remote_directory_path_case_insensitive", lambda _client, _path: "/remote")

    with pytest.raises(FileNotFoundError, match="Shapefile DUI 2026 non scaricato"):
        with dui_2026_overlay._materialized_latest_shapefile():
            pass


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


def test_require_dui_reader_dependency_accepts_supported_reader(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dui_2026_overlay, "_supports_osgeo_reader", lambda: True)
    monkeypatch.setattr(dui_2026_overlay, "_supports_pyshp_reader", lambda: False)

    dui_2026_overlay._require_dui_reader_dependency()


def test_extract_feature_properties_from_mapping_handles_dates_and_unknown_flags() -> None:
    submitted_at = SimpleNamespace(strftime=lambda fmt: f"formatted:{fmt}")

    properties = dui_2026_overlay._extract_feature_properties_from_mapping(
        {
            "NUM_DOM": "ABC",
            "CONTATORE": "forse",
            "TELERILEV": None,
            "DATA": submitted_at,
            "SUP_GRAFIC": None,
            "CODICEFISC": " CF ",
            "COGN_NOME": " Nome ",
            "TELEFONO": "",
            "COLTURA": "OLIVO",
            "TIPO_DOM": "NW",
            "ID_OPERAT": "OP",
            "X": 1,
            "Y": 2,
        }
    )

    assert properties["domanda_irrigua"] == "ABC"
    assert properties["contatore"] == "FORSE"
    assert properties["telerilev"] is None
    assert properties["data_domanda"] == "formatted:%Y-%m-%d"
    assert properties["sup_grafica_mq"] is None
    assert properties["codice_fiscale"] == "CF"
    assert properties["telefono"] is None


def test_extract_feature_properties_reads_osgeo_like_feature() -> None:
    class FakeFeature:
        def GetField(self, name: str):
            return {"NUM_DOM": 16, "CONTATORE": "SI", "TELERILEV": "NO"}.get(name)

    properties = dui_2026_overlay._extract_feature_properties(FakeFeature())

    assert properties["domanda_irrigua"] == "16"
    assert properties["contatore"] == "SI"
    assert properties["telerilev"] == "NO"


def test_transform_geometry_helpers_and_fallback_crs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeTransformer:
        def transform(self, x: float, y: float) -> tuple[float, float]:
            return x + 10, y + 20

    class FakeCrs:
        @staticmethod
        def from_wkt(value: str) -> str:
            return f"wkt:{value}"

        @staticmethod
        def from_epsg(value: int) -> str:
            return f"epsg:{value}"

    geometry = {"type": "LineString", "coordinates": [[1, 2, 3], [4, 5]]}
    transformed = dui_2026_overlay._transform_geojson_geometry(geometry, FakeTransformer())
    unchanged = dui_2026_overlay._transform_geojson_geometry(geometry, None)

    assert transformed["coordinates"] == [[11, 22, 3], [14, 25]]
    assert unchanged is geometry
    assert dui_2026_overlay._transform_geojson_coordinates("bad", FakeTransformer()) == "bad"

    shapefile_path = tmp_path / "Dui2026-TOTALE-al_25-06-2026.shp"
    shapefile_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(dui_2026_overlay, "CRS", FakeCrs)
    assert dui_2026_overlay._resolve_fallback_source_crs(shapefile_path) == "epsg:3003"

    shapefile_path.with_suffix(".prj").write_text("LOCAL_WKT", encoding="utf-8")
    assert dui_2026_overlay._resolve_fallback_source_crs(shapefile_path) == "wkt:LOCAL_WKT"


def test_load_raw_dataset_from_shapefile_uses_pyshp_fallback_when_osgeo_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if dui_2026_overlay.CRS is None:
        pytest.skip("pyproj non disponibile per il fallback pyshp.")

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


def test_load_raw_dataset_from_pyshp_handles_list_records_and_missing_geometry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shapefile_path = tmp_path / "Dui2026-TOTALE-al_25-06-2026.shp"
    shapefile_path.write_text("", encoding="utf-8")

    class FakeCrs:
        @staticmethod
        def from_epsg(value: int) -> str:
            return f"epsg:{value}"

    class FakeTransformer:
        @staticmethod
        def from_crs(_source: str, _target: str, *, always_xy: bool):
            assert always_xy is True
            return SimpleNamespace(transform=lambda x, y: (x + 1, y + 1))

    class FakeReader:
        fields = [("DeletionFlag", "C", 1, 0), ("NUM_DOM", "N", 10, 0), ("CONTATORE", "C", 2, 0)]

        def __init__(self, _path: str) -> None:
            self.closed = False

        def iterShapeRecords(self):
            yield SimpleNamespace(shape=SimpleNamespace(__geo_interface__=None), record=[])
            yield SimpleNamespace(
                shape=SimpleNamespace(__geo_interface__={"type": "Point", "coordinates": [1, 2]}),
                record=[16, "SI"],
            )

        def close(self) -> None:
            self.closed = True

    monkeypatch.setattr(dui_2026_overlay, "_supports_osgeo_reader", lambda: False)
    monkeypatch.setattr(dui_2026_overlay, "_require_dui_reader_dependency", lambda: None)
    monkeypatch.setattr(dui_2026_overlay, "pyshp", SimpleNamespace(Reader=FakeReader))
    monkeypatch.setattr(dui_2026_overlay, "CRS", FakeCrs)
    monkeypatch.setattr(dui_2026_overlay, "Transformer", FakeTransformer)
    monkeypatch.setattr(dui_2026_overlay, "_resolve_fallback_source_crs", lambda _path: "epsg:3003")

    payload = dui_2026_overlay._load_raw_dataset_from_shapefile(shapefile_path)

    assert payload["feature_count"] == 1
    assert payload["geojson"]["features"][0]["geometry"]["coordinates"] == [2, 3]
    assert payload["geojson"]["features"][0]["properties"]["domanda_irrigua"] == "16"


def test_load_raw_dataset_from_shapefile_uses_osgeo_reader(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    shapefile_path = tmp_path / "Dui2026-TOTALE-al_25-06-2026.shp"
    shapefile_path.write_text("", encoding="utf-8")

    class FakeGeometry:
        def Clone(self):
            return self

        def Transform(self, transform) -> None:
            assert transform == "transform"

        def ExportToJson(self) -> str:
            return '{"type":"Point","coordinates":[8.5,39.9]}'

    class FakeFeature:
        def __init__(self, geometry):
            self.geometry = geometry

        def GetGeometryRef(self):
            return self.geometry

        def GetField(self, name: str):
            return {"NUM_DOM": "16", "CONTATORE": "SI", "TELERILEV": "NO"}.get(name)

    class FakeLayer:
        def GetSpatialRef(self):
            return "source"

        def __iter__(self):
            yield FakeFeature(None)
            yield FakeFeature(FakeGeometry())

    class FakeDatasource:
        def GetLayer(self, index: int):
            assert index == 0
            return FakeLayer()

    class FakeOgr:
        @staticmethod
        def Open(path: str):
            assert path == str(shapefile_path)
            return FakeDatasource()

    class FakeSpatialReference:
        def ImportFromEPSG(self, value: int) -> None:
            assert value == 4326

    class FakeOsr:
        SpatialReference = FakeSpatialReference

        @staticmethod
        def CoordinateTransformation(source, target):
            assert source == "source"
            assert isinstance(target, FakeSpatialReference)
            return "transform"

    monkeypatch.setattr(dui_2026_overlay, "_supports_osgeo_reader", lambda: True)
    monkeypatch.setattr(dui_2026_overlay, "_require_dui_reader_dependency", lambda: None)
    monkeypatch.setattr(dui_2026_overlay, "ogr", FakeOgr)
    monkeypatch.setattr(dui_2026_overlay, "osr", FakeOsr)

    payload = dui_2026_overlay._load_raw_dataset_from_shapefile(shapefile_path)

    assert payload["feature_count"] == 1
    assert payload["geojson"]["features"][0]["geometry"]["type"] == "Point"
    assert payload["geojson"]["features"][0]["properties"]["domanda_irrigua"] == "16"


def test_load_raw_dataset_from_shapefile_reports_osgeo_open_errors(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    shapefile_path = tmp_path / "Dui2026-TOTALE-al_25-06-2026.shp"
    shapefile_path.write_text("", encoding="utf-8")

    class MissingDatasourceOgr:
        @staticmethod
        def Open(_path: str):
            return None

    class MissingLayerDatasource:
        def GetLayer(self, _index: int):
            return None

    class MissingLayerOgr:
        @staticmethod
        def Open(_path: str):
            return MissingLayerDatasource()

    monkeypatch.setattr(dui_2026_overlay, "_supports_osgeo_reader", lambda: True)
    monkeypatch.setattr(dui_2026_overlay, "_require_dui_reader_dependency", lambda: None)
    monkeypatch.setattr(dui_2026_overlay, "ogr", MissingDatasourceOgr)
    with pytest.raises(ValueError, match="Impossibile aprire"):
        dui_2026_overlay._load_raw_dataset_from_shapefile(shapefile_path)

    monkeypatch.setattr(dui_2026_overlay, "ogr", MissingLayerOgr)
    with pytest.raises(ValueError, match="Layer DUI 2026 assente"):
        dui_2026_overlay._load_raw_dataset_from_shapefile(shapefile_path)


def test_get_dui_2026_latest_layer_marks_ruolo_2025_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dui_2026_overlay, "_require_dui_reader_dependency", lambda: None)
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
    assert payload.tile_layer == "cat_dui_2026_current"
    assert payload.rendering_mode == "geojson_fallback"
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
    monkeypatch.setattr(dui_2026_overlay, "_require_dui_reader_dependency", lambda: None)
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


def test_get_dui_domanda_detail_rejects_invalid_or_missing_domanda(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dui_2026_overlay, "_require_dui_reader_dependency", lambda: None)
    monkeypatch.setattr(
        dui_2026_overlay,
        "_get_cached_dataset",
        lambda: {
            "source_path": "/tmp/Dui2026-TOTALE-al_25-06-2026.shp",
            "source_filename": "Dui2026-TOTALE-al_25-06-2026.shp",
            "source_date": "2026-06-25",
            "source_updated_at": "2026-06-26T07:43:00",
            "feature_count": 0,
            "geojson": {"type": "FeatureCollection", "features": []},
        },
    )

    db = TestingSessionLocal()
    try:
        with pytest.raises(ValueError, match="Domanda irrigua non valida"):
            dui_2026_overlay.get_dui_domanda_detail(db, "")
        with pytest.raises(FileNotFoundError, match="Domanda irrigua 99 non trovata"):
            dui_2026_overlay.get_dui_domanda_detail(db, "99")
    finally:
        db.close()


def test_load_ruolo_2025_summary_by_domanda_aggregates_matching_rows() -> None:
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
        for index in range(13):
            db.add(
                RuoloParticella(
                    id=uuid4(),
                    partita_id=partita_id,
                    anno_tributario=2025,
                    domanda_irrigua="0016" if index % 2 == 0 else "16",
                    distretto="D01",
                    foglio=str(index + 1),
                    particella=str(index + 100),
                    subalterno=str(index % 3),
                    coltura="OLIVO",
                    sup_catastale_ha=Decimal("0.1000"),
                    sup_irrigata_ha=Decimal("0.0500"),
                    importo_manut=Decimal("1.10"),
                    importo_irrig=Decimal("2.20"),
                    importo_ist=Decimal("0.30"),
                )
            )
        db.add(
            RuoloParticella(
                id=uuid4(),
                partita_id=partita_id,
                anno_tributario=2024,
                domanda_irrigua="16",
                foglio="99",
                particella="999",
            )
        )
        db.commit()

        summary = dui_2026_overlay._load_ruolo_2025_summary_by_domanda(db, "16")
        missing = dui_2026_overlay._load_ruolo_2025_summary_by_domanda(db, "99")
        invalid = dui_2026_overlay._load_ruolo_2025_summary_by_domanda(db, "")
    finally:
        db.close()

    assert summary is not None
    assert summary.n_righe == 13
    assert summary.n_subalterni == 3
    assert summary.sup_catastale_ha_totale == 1.3
    assert summary.sup_irrigata_ha_totale == 0.65
    assert summary.importo_manut_euro_totale == 14.3
    assert summary.importo_irrig_euro_totale == 28.6
    assert summary.importo_ist_euro_totale == 3.9
    assert summary.importo_totale_euro == 46.8
    assert len(summary.items) == 12
    assert summary.items[0].codice_partita == "PART-16"
    assert summary.items[0].codice_cnc == "CNC-0016"
    assert missing is None
    assert invalid is None


def test_sync_dui_2026_tile_table_skips_non_postgresql_session() -> None:
    db = TestingSessionLocal()
    try:
        dui_2026_overlay._sync_dui_2026_tile_table(
            db,
            {
                "source_path": "/tmp/Dui2026-TOTALE-al_25-06-2026.shp",
                "source_filename": "Dui2026-TOTALE-al_25-06-2026.shp",
                "source_date": "2026-06-25",
                "source_updated_at": "2026-06-26T07:43:00",
                "geojson": {"type": "FeatureCollection", "features": []},
            },
            Counter(),
        )
    finally:
        db.close()


def test_sync_dui_2026_tile_table_materializes_postgresql_rows() -> None:
    executed: list[tuple[str, object | None]] = []

    class FakeBind:
        dialect = SimpleNamespace(name="postgresql")

    class FakeDb:
        def get_bind(self):
            return FakeBind()

        def execute(self, statement, params=None):
            executed.append((str(statement), params))

        def commit(self):
            executed.append(("COMMIT", None))

    dataset = {
        "source_path": "/tmp/Dui2026-TOTALE-al_25-06-2026.shp",
        "source_filename": "Dui2026-TOTALE-al_25-06-2026.shp",
        "source_date": "2026-06-25",
        "source_updated_at": "2026-06-26T07:43:00",
        "geojson": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [8.5, 39.9],
                            [8.51, 39.9],
                            [8.51, 39.91],
                            [8.5, 39.91],
                            [8.5, 39.9],
                        ]],
                    },
                    "properties": {
                        "domanda_irrigua": "16",
                        "codice_fiscale": "RSSMRA80A01H501U",
                        "intestatario": "Rossi Mario",
                        "telefono": "0783",
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
                {
                    "type": "Feature",
                    "geometry": None,
                    "properties": {"domanda_irrigua": "17"},
                },
            ],
        },
    }

    dui_2026_overlay._sync_dui_2026_tile_table(FakeDb(), dataset, Counter({"16": 2}))  # type: ignore[arg-type]

    assert "DELETE FROM cat_dui_2026_current" in executed[0][0]
    insert_params = executed[1][1]
    assert isinstance(insert_params, list)
    assert len(insert_params) == 1
    assert insert_params[0]["domanda_irrigua"] == "16"
    assert insert_params[0]["in_ruolo_2025"] is True
    assert insert_params[0]["ruolo_2025_match_count"] == 2
    assert insert_params[0]["source_payload_json"]
    assert insert_params[0]["geometry_geojson"]
    assert executed[-1] == ("COMMIT", None)
