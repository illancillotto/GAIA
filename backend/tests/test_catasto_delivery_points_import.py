from __future__ import annotations

from pathlib import Path
import sys
import types
from uuid import uuid4

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
    CatMeterReadingDeliveryPointMapping,
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
            CatMeterReadingDeliveryPointMapping.__table__,
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


def test_import_delivery_points_supports_smb_root_path(tmp_path: Path, monkeypatch) -> None:
    remote_root_requested = "/volume1/settore catasto/DOMANDE UTENZA IRRIGUA/SHP_PUNTI_CONSEGNA/PUNTI_CONSEGNA 2026_DEF"
    remote_root_actual = "/volume1/Settore Catasto/DOMANDE UTENZA IRRIGUA/SHP_PUNTI_CONSEGNA/PUNTI_CONSEGNA 2026_DEF"
    remote_point_path = f"{remote_root_actual}/{service.POINT_FOLDER_WITH_METER}/D24_Punti_Consegna_2026.shp"
    remote_dbf_path = remote_point_path[:-4] + ".dbf"
    remote_shx_path = remote_point_path[:-4] + ".shx"
    remote_without_meter_dir = f"{remote_root_actual}/{service.POINT_FOLDER_WITHOUT_METER}"
    source_local_root = tmp_path / "nas-source"
    local_point_path = source_local_root / service.POINT_FOLDER_WITH_METER / "D24_Punti_Consegna_2026.shp"
    _touch(local_point_path)
    _touch(source_local_root / service.POINT_FOLDER_WITH_METER / "D24_Punti_Consegna_2026.dbf")
    _touch(source_local_root / service.POINT_FOLDER_WITH_METER / "D24_Punti_Consegna_2026.shx")
    (source_local_root / service.POINT_FOLDER_WITHOUT_METER).mkdir(parents=True, exist_ok=True)

    registry = {
        str(local_point_path): {
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
        }
    }
    _install_fake_shapefile(monkeypatch, registry)

    class _FakeNasClient:
        def path_exists(self, path: str) -> bool:
            return path in {
                "/volume1",
                "/volume1/Settore Catasto",
                "/volume1/Settore Catasto/DOMANDE UTENZA IRRIGUA",
                "/volume1/Settore Catasto/DOMANDE UTENZA IRRIGUA/SHP_PUNTI_CONSEGNA",
                remote_root_actual,
                f"{remote_root_actual}/{service.POINT_FOLDER_WITH_METER}",
                remote_without_meter_dir,
            }

        def run_command(self, command: str) -> str:
            if " -type d -print" in command:
                if "find / -mindepth 1 -maxdepth 1 -type d -print" in command:
                    return "/volume1"
                if "find /volume1 -mindepth 1 -maxdepth 1 -type d -print" in command:
                    return "/volume1/Settore Catasto"
                if "find '/volume1/Settore Catasto' -mindepth 1 -maxdepth 1 -type d -print" in command:
                    return "/volume1/Settore Catasto/DOMANDE UTENZA IRRIGUA"
                if (
                    "find '/volume1/Settore Catasto/DOMANDE UTENZA IRRIGUA' -mindepth 1 -maxdepth 1 -type d -print"
                    in command
                ):
                    return "/volume1/Settore Catasto/DOMANDE UTENZA IRRIGUA/SHP_PUNTI_CONSEGNA"
                if (
                    "find '/volume1/Settore Catasto/DOMANDE UTENZA IRRIGUA/SHP_PUNTI_CONSEGNA' "
                    "-mindepth 1 -maxdepth 1 -type d -print"
                    in command
                ):
                    return remote_root_actual
            assert remote_root_actual in command
            return "\n".join([remote_point_path, remote_dbf_path, remote_shx_path])

        def download_to_local(self, remote_path: str, local_path: str) -> None:
            relative = Path(remote_path.removeprefix(remote_root_actual).lstrip("/"))
            source_path = source_local_root / relative
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            Path(local_path).write_bytes(source_path.read_bytes())
            if source_path.suffix.lower() == ".shp":
                registry[str(Path(local_path))] = registry[str(source_path)]

    monkeypatch.setattr(service, "get_nas_client", lambda: _FakeNasClient())

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
            CatMeterReadingDeliveryPointMapping.__table__,
            CatMeterReading.__table__,
        ],
    )
    with Session(engine) as db:
        db.add(CatDistretto(num_distretto="24", nome_distretto="Lotto Sud Arborea"))
        db.commit()

        result = service.import_delivery_points_2026_def(
            db,
            root_path=(
                "smb://nas_cbo.local/settore catasto/"
                "DOMANDE UTENZA IRRIGUA/SHP_PUNTI_CONSEGNA/PUNTI_CONSEGNA 2026_DEF/"
            ),
        )

        assert result == {
            "points_processed": 1,
            "canals_processed": 0,
            "meter_readings_linked": 0,
            "meter_readings_unlinked": 0,
        }
        imported_points = db.execute(select(CatDeliveryPoint)).scalars().all()
        assert len(imported_points) == 1
        assert imported_points[0].punto_consegna_code == "7W_11-20B"


def test_smb_uri_to_remote_path_accepts_hostname_alias() -> None:
    result = service._smb_uri_to_remote_path(
        "smb://nas_cbo.local/settore catasto/DOMANDE UTENZA IRRIGUA/SHP_PUNTI_CONSEGNA/PUNTI_CONSEGNA 2026_DEF/"
    )

    assert result == "/volume1/settore catasto/DOMANDE UTENZA IRRIGUA/SHP_PUNTI_CONSEGNA/PUNTI_CONSEGNA 2026_DEF"


def test_resolve_remote_directory_path_case_insensitive_matches_real_share_name() -> None:
    class _FakeNasClient:
        def path_exists(self, path: str) -> bool:
            return path in {"/volume1", "/volume1/Settore Catasto"}

        def run_command(self, command: str) -> str:
            assert command == "find /volume1 -mindepth 1 -maxdepth 1 -type d -print"
            return "/volume1/Settore Catasto"

    result = service._resolve_remote_directory_path_case_insensitive(
        _FakeNasClient(),
        "/volume1/settore catasto",
    )

    assert result == "/volume1/Settore Catasto"


def test_normalizers_cover_composite_codes() -> None:
    assert service.normalize_distretto_code(None) is None
    assert service.normalize_distretto_code("   ") is None
    assert service.normalize_point_code(None) is None
    assert service.normalize_distretto_code("D24") == "24"
    assert service.normalize_distretto_code("D12-D13") == "12-13"
    assert service.normalize_distretto_code(" D28_1D_1L ") == "28_1D_1L"
    assert service.normalize_point_code("  abc   1 ") == "ABC 1"
    assert service.strip_activity_suffix(" 11_13_2_A ") == "11_13_2"
    assert service.strip_activity_suffix("11_13_2") == "11_13_2"
    assert service.insert_dot_after_numeric_prefix("10E_1-29C") == "10.E_1-29C"
    assert service.insert_dot_after_numeric_prefix("7W.1_1") == "7W.1_1"
    assert service.map_alpha_suffix_to_numeric("P2.S1_A") == "P2.S1_1"
    assert service.map_alpha_suffix_to_numeric("P4.S2_H") == "P4.S2_8"
    assert service.map_alpha_suffix_to_numeric("15_11_4-F") == "15_11_4_6"
    assert service.map_alpha_suffix_to_numeric("18_1_16_M") == "18_1_16_13"
    assert service.map_alpha_suffix_to_numeric("P2.S1_1") == "P2.S1_1"
    assert service.strip_activity_suffix(None) is None
    assert service.insert_dot_after_numeric_prefix(None) is None
    assert service.map_alpha_suffix_to_numeric(None) is None
    assert service._normalize_decimal(None) is None
    assert service._normalize_decimal("") is None
    assert service._normalize_decimal("not-a-number") is None


def test_parse_delivery_points_shapefile_rejects_unsupported_folder(tmp_path: Path) -> None:
    path = tmp_path / "unsupported" / "D24_Punti_Consegna_2026.shp"
    _touch(path)

    try:
        service.parse_delivery_points_shapefile(path)
    except ValueError as exc:
        assert "Cartella sorgente non supportata" in str(exc)
    else:
        raise AssertionError("Expected unsupported source folder error")


def test_parse_delivery_points_shapefile_skips_point_without_code(tmp_path: Path, monkeypatch) -> None:
    point_path = tmp_path / service.POINT_FOLDER_WITH_METER / "D24_Punti_Consegna_2026.shp"
    _touch(point_path)
    registry = {
        str(point_path): {
            "fields": [
                ("DeletionFlag", "C", 1, 0),
                ("PUNTO_CON", "C", 15, 0),
            ],
            "records": [
                _FakeShapeRecord(
                    [""],
                    {"type": "Point", "coordinates": (1462222.77339385, 4398240.15719749)},
                )
            ],
        }
    }
    _install_fake_shapefile(monkeypatch, registry)

    assert service.parse_delivery_points_shapefile(point_path) == []


def test_distretto_code_from_path_rejects_unusable_stem(tmp_path: Path) -> None:
    path = tmp_path / "   .shp"

    try:
        service._distretto_code_from_path(path)
    except ValueError as exc:
        assert "Impossibile derivare il distretto" in str(exc)
    else:
        raise AssertionError("Expected distretto derivation error")


def test_smb_uri_to_remote_path_rejects_invalid_values() -> None:
    for value, expected in [
        ("file:///tmp/punti", "Percorso NAS non supportato"),
        ("smb:///settore catasto", "Host SMB mancante"),
        ("smb://nas_cbo.local", "Share SMB mancante"),
    ]:
        try:
            service._smb_uri_to_remote_path(value)
        except ValueError as exc:
            assert expected in str(exc)
        else:
            raise AssertionError(f"Expected error for {value}")


def test_resolve_remote_directory_path_handles_direct_and_missing_paths() -> None:
    class _DirectClient:
        def path_exists(self, path: str) -> bool:
            return path == "/volume1/Settore Catasto"

    assert (
        service._resolve_remote_directory_path_case_insensitive(_DirectClient(), "/volume1/Settore Catasto/")
        == "/volume1/Settore Catasto"
    )

    class _MissingClient:
        def path_exists(self, path: str) -> bool:
            return path == "/"

        def run_command(self, command: str) -> str:
            return "/volume1/Altro"

    try:
        service._resolve_remote_directory_path_case_insensitive(_MissingClient(), "/volume1/settore catasto")
    except ValueError as exc:
        assert "Cartella non trovata" in str(exc)
    else:
        raise AssertionError("Expected missing remote folder error")


def test_download_remote_delivery_points_tree_validates_remote_layout(monkeypatch) -> None:
    class _MissingRootClient:
        def path_exists(self, path: str) -> bool:
            return path == "/volume1"

        def run_command(self, command: str) -> str:
            return ""

    monkeypatch.setattr(service, "get_nas_client", lambda: _MissingRootClient())
    try:
        service._download_remote_delivery_points_tree("smb://nas_cbo.local/share/root")
    except ValueError as exc:
        assert "Cartella non trovata" in str(exc)
    else:
        raise AssertionError("Expected missing remote root error")

    class _RootDisappearsClient:
        def __init__(self) -> None:
            self.calls = 0

        def path_exists(self, path: str) -> bool:
            if path == "/volume1/share/root":
                self.calls += 1
                return self.calls == 1
            return False

    disappearing_client = _RootDisappearsClient()
    monkeypatch.setattr(service, "get_nas_client", lambda: disappearing_client)
    try:
        service._download_remote_delivery_points_tree("smb://nas_cbo.local/share/root")
    except ValueError as exc:
        assert "Cartella non trovata" in str(exc)
    else:
        raise AssertionError("Expected disappearing remote root error")

    class _MissingSubdirsClient:
        def path_exists(self, path: str) -> bool:
            return path in {"/volume1/share/root"}

    monkeypatch.setattr(service, "get_nas_client", lambda: _MissingSubdirsClient())
    try:
        service._download_remote_delivery_points_tree("smb://nas_cbo.local/share/root")
    except ValueError as exc:
        assert "deve contenere" in str(exc)
    else:
        raise AssertionError("Expected missing subfolders error")

    class _NoFilesClient:
        def path_exists(self, path: str) -> bool:
            return path in {
                "/volume1/share/root",
                f"/volume1/share/root/{service.POINT_FOLDER_WITH_METER}",
                f"/volume1/share/root/{service.POINT_FOLDER_WITHOUT_METER}",
            }

        def run_command(self, command: str) -> str:
            return ""

    monkeypatch.setattr(service, "get_nas_client", lambda: _NoFilesClient())
    try:
        service._download_remote_delivery_points_tree("smb://nas_cbo.local/share/root")
    except ValueError as exc:
        assert "Nessuno shapefile trovato" in str(exc)
    else:
        raise AssertionError("Expected no shapefiles error")


def test_download_remote_delivery_points_tree_wraps_unexpected_errors(monkeypatch) -> None:
    class _BrokenClient:
        def path_exists(self, path: str) -> bool:
            raise RuntimeError("ssh down")

    monkeypatch.setattr(service, "get_nas_client", lambda: _BrokenClient())

    try:
        service._download_remote_delivery_points_tree("smb://nas_cbo.local/share/root")
    except ValueError as exc:
        assert "Errore accesso NAS" in str(exc)
    else:
        raise AssertionError("Expected wrapped NAS access error")


def test_download_remote_delivery_points_tree_ignores_unexpected_file_extensions(tmp_path: Path, monkeypatch) -> None:
    remote_root = "/volume1/share/root"
    remote_txt = f"{remote_root}/{service.POINT_FOLDER_WITH_METER}/notes.txt"
    remote_shp = f"{remote_root}/{service.POINT_FOLDER_WITH_METER}/D24_Punti_Consegna_2026.shp"

    class _FakeClient:
        def path_exists(self, path: str) -> bool:
            return path in {
                remote_root,
                f"{remote_root}/{service.POINT_FOLDER_WITH_METER}",
                f"{remote_root}/{service.POINT_FOLDER_WITHOUT_METER}",
            }

        def run_command(self, command: str) -> str:
            return "\n".join([remote_txt, remote_shp])

        def download_to_local(self, remote_path: str, local_path: str) -> None:
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            Path(local_path).write_text("shape", encoding="utf-8")

    monkeypatch.setattr(service, "get_nas_client", lambda: _FakeClient())
    temp_dir = service._download_remote_delivery_points_tree("smb://nas_cbo.local/share/root")
    try:
        local_root = Path(temp_dir.name)
        assert not (local_root / service.POINT_FOLDER_WITH_METER / "notes.txt").exists()
        assert (local_root / service.POINT_FOLDER_WITH_METER / "D24_Punti_Consegna_2026.shp").exists()
    finally:
        temp_dir.cleanup()


def test_apply_geometry_update_uses_postgresql_transform() -> None:
    class _Dialect:
        name = "postgresql"

    class _Bind:
        dialect = _Dialect()

    class _FakeDb:
        bind = _Bind()

        def __init__(self) -> None:
            self.calls: list[tuple[object, dict[str, object]]] = []

        def execute(self, statement, params):
            self.calls.append((statement, params))

    db = _FakeDb()
    row_id = uuid4()

    service._apply_geometry_update(
        db,
        table_name="cat_delivery_points",
        row_id=row_id,
        geometry_column="geometry",
        geometry_wkt="POINT (1 2)",
        source_srid=3003,
    )

    assert db.calls[0][1] == {"geometry_wkt": "POINT (1 2)", "source_srid": 3003, "row_id": str(row_id)}


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
            CatMeterReadingDeliveryPointMapping.__table__,
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
            CatMeterReadingDeliveryPointMapping.__table__,
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
            CatMeterReadingDeliveryPointMapping.__table__,
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


def test_resolve_delivery_point_id_supports_dotted_stripped_activity_variant() -> None:
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
            CatMeterReadingDeliveryPointMapping.__table__,
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
                punto_consegna="10E_1-29C_A",
                matricola="10248",
                cache={},
            )
            == point.id
        )


def test_resolve_delivery_point_id_supports_alpha_suffix_numeric_variant() -> None:
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
            CatMeterReadingDeliveryPointMapping.__table__,
            CatMeterReading.__table__,
        ],
    )
    with Session(engine) as db:
        distretto = CatDistretto(num_distretto="293", nome_distretto="Distretto 293")
        db.add(distretto)
        db.flush()
        point = CatDeliveryPoint(
            distretto_code="293",
            punto_consegna_code="P2.S1_1",
            has_meter=False,
            is_active=True,
            source_dataset=service.SOURCE_DATASET_2026_DEF,
        )
        db.add(point)
        db.commit()

        assert (
            service.resolve_delivery_point_id(
                db,
                distretto=distretto,
                punto_consegna="P2.S1_A",
                cache={},
            )
            == point.id
        )


def test_resolve_delivery_point_id_supports_alpha_suffix_after_activity_strip() -> None:
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
            CatMeterReadingDeliveryPointMapping.__table__,
            CatMeterReading.__table__,
        ],
    )
    with Session(engine) as db:
        distretto = CatDistretto(num_distretto="293", nome_distretto="Distretto 293")
        db.add(distretto)
        db.flush()
        point = CatDeliveryPoint(
            distretto_code="293",
            punto_consegna_code="P2.S1_1",
            has_meter=False,
            is_active=True,
            source_dataset=service.SOURCE_DATASET_2026_DEF,
        )
        db.add(point)
        db.commit()

        assert (
            service.resolve_delivery_point_id(
                db,
                distretto=distretto,
                punto_consegna="P2.S1_A_X",
                cache={},
            )
            == point.id
        )


def test_import_delivery_points_rejects_missing_local_root_and_subfolders(tmp_path: Path) -> None:
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
            CatMeterReadingDeliveryPointMapping.__table__,
            CatMeterReading.__table__,
        ],
    )
    with Session(engine) as db:
        try:
            service.import_delivery_points_2026_def(db, root_path=tmp_path / "missing")
        except ValueError as exc:
            assert "Cartella non trovata" in str(exc)
        else:
            raise AssertionError("Expected missing root error")

        partial_root = tmp_path / "partial"
        partial_root.mkdir()
        try:
            service.import_delivery_points_2026_def(db, root_path=partial_root)
        except ValueError as exc:
            assert "deve contenere" in str(exc)
        else:
            raise AssertionError("Expected missing subfolders error")


def test_link_meter_readings_counts_missing_codes_and_clears_stale_links() -> None:
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
            CatMeterReadingDeliveryPointMapping.__table__,
            CatMeterReading.__table__,
        ],
    )
    with Session(engine) as db:
        distretto = CatDistretto(num_distretto="24", nome_distretto="Distretto 24")
        db.add(distretto)
        db.flush()
        stale_point = CatDeliveryPoint(
            distretto_code="24",
            punto_consegna_code="STALE",
            has_meter=True,
            is_active=False,
            source_dataset=service.SOURCE_DATASET_2026_DEF,
        )
        db.add(stale_point)
        db.flush()
        missing_code = CatMeterReading(
            anno=2026,
            distretto_id=distretto.id,
            punto_consegna="   ",
            source="excel",
        )
        stale_link = CatMeterReading(
            anno=2026,
            distretto_id=distretto.id,
            punto_consegna="STALE",
            source="excel",
            delivery_point_id=stale_point.id,
        )
        db.add_all([missing_code, stale_link])
        db.commit()

        result = service.link_meter_readings_to_delivery_points(db)

        assert result == {"linked": 0, "unlinked": 2}
        assert stale_link.delivery_point_id is None


def test_resolve_delivery_point_id_returns_none_for_missing_inputs_and_uses_cache() -> None:
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
            CatMeterReadingDeliveryPointMapping.__table__,
            CatMeterReading.__table__,
        ],
    )
    with Session(engine) as db:
        distretto = CatDistretto(num_distretto="24", nome_distretto="Distretto 24")
        db.add(distretto)
        db.flush()
        cached_id = uuid4()
        cache = {("24", "POINT-1", None): cached_id}

        assert service.resolve_delivery_point_id(db, distretto=None, punto_consegna="POINT-1") is None
        assert service.resolve_delivery_point_id(db, distretto=distretto, punto_consegna=None) is None
        assert service.resolve_delivery_point_id(db, distretto=distretto, punto_consegna="POINT-1", cache=cache) == cached_id


def test_resolve_delivery_point_id_prefers_manual_mapping_and_caches_result() -> None:
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
            CatMeterReadingDeliveryPointMapping.__table__,
            CatMeterReading.__table__,
        ],
    )
    with Session(engine) as db:
        distretto = CatDistretto(num_distretto="24", nome_distretto="Distretto 24")
        db.add(distretto)
        db.flush()
        point = CatDeliveryPoint(
            distretto_code="24",
            punto_consegna_code="MANUAL-TARGET",
            has_meter=True,
            is_active=True,
            source_dataset=service.SOURCE_DATASET_2026_DEF,
        )
        db.add(point)
        db.flush()
        db.add(
            CatMeterReadingDeliveryPointMapping(
                distretto_code="24",
                source_point_code="SOURCE-POINT",
                delivery_point_id=point.id,
            )
        )
        db.commit()

        cache: dict[tuple[str, str, str | None], object | None] = {}
        assert (
            service.resolve_delivery_point_id(db, distretto=distretto, punto_consegna="SOURCE-POINT", cache=cache)
            == point.id
        )
        assert cache[("24", "SOURCE-POINT", None)] == point.id


def test_resolve_delivery_point_id_supports_single_subdistrict_candidate() -> None:
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
            CatMeterReadingDeliveryPointMapping.__table__,
            CatMeterReading.__table__,
        ],
    )
    with Session(engine) as db:
        distretto = CatDistretto(num_distretto="28", nome_distretto="Distretto 28")
        db.add(distretto)
        db.flush()
        point = CatDeliveryPoint(
            distretto_code="28_1D_1L",
            punto_consegna_code="SINGLE",
            has_meter=True,
            is_active=True,
            source_dataset=service.SOURCE_DATASET_2026_DEF,
        )
        db.add(point)
        db.commit()

        assert service.resolve_delivery_point_id(db, distretto=distretto, punto_consegna="SINGLE", cache={}) == point.id
