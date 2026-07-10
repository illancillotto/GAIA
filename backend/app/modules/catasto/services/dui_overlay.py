from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
import json
import logging
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlparse
from pathlib import PurePosixPath
import re
import shlex
from typing import Any
from uuid import NAMESPACE_URL, uuid5

try:
    from osgeo import ogr, osr
except ModuleNotFoundError as exc:  # pragma: no cover - exercised through the runtime guard
    ogr = None
    osr = None
    _OSGEO_IMPORT_ERROR: ModuleNotFoundError | None = exc
else:  # pragma: no cover - depends on optional OSGeo being installed in the runtime
    _OSGEO_IMPORT_ERROR = None
try:
    import shapefile as pyshp
except ModuleNotFoundError as exc:  # pragma: no cover - exercised through the runtime guard
    pyshp = None
    _PYSHAPE_IMPORT_ERROR: ModuleNotFoundError | None = exc
else:
    _PYSHAPE_IMPORT_ERROR = None
try:
    from pyproj import CRS, Transformer
except ModuleNotFoundError as exc:  # pragma: no cover - exercised through the runtime guard
    CRS = None
    Transformer = None
    _PYPROJ_IMPORT_ERROR: ModuleNotFoundError | None = exc
else:  # pragma: no cover - depends on optional pyproj being installed in the runtime
    _PYPROJ_IMPORT_ERROR = None
from sqlalchemy import desc, func, or_, select, text
from sqlalchemy.orm import Session

from app.modules.catasto.schemas.gis_schemas import (
    DuiDomandaDetailResponse,
    DuiLayerResponse,
    DuiLayerStats,
    ParticellaPopupRuoloItem,
    ParticellaPopupRuoloSummary,
)
from app.modules.ruolo.models import RuoloAvviso, RuoloParticella, RuoloPartita
from app.modules.catasto.services.delivery_points_import import (
    _resolve_remote_directory_path_case_insensitive,
    _smb_uri_to_remote_path,
)
from app.services.nas_connector import NasConnectorError, get_nas_client


logger = logging.getLogger(__name__)

DUI_DEFAULT_YEAR = 2026
DUI_DEFAULT_FILE_GLOB = "Dui{year}-TOTALE-al_*.shp"
DUI_DEFAULT_FILE_FIND_PATTERN = "Dui{year}-TOTALE-al_*.shp"
DEFAULT_DUI_BACKUP_URI = (
    "smb://nas_cbo.local/settore catasto/"
    "DOMANDE UTENZA IRRIGUA/Dui2026/Shp_Dui2026/Backup"
)
DEFAULT_DUI_2026_BACKUP_URI = DEFAULT_DUI_BACKUP_URI
_SHAPEFILE_SIDECAR_EXTENSIONS = (".shp", ".dbf", ".shx", ".prj", ".cpg", ".qix", ".qmd")
SNAPSHOT_DATE_RE = re.compile(r"al_(\d{2})-(\d{2})-(\d{4})", re.IGNORECASE)
ROLE_MATCH_COLOR = "#0F766E"
ROLE_MISSING_COLOR = "#D97706"
DUI_TILE_LAYER = "cat_dui_2026_current"
DUI_2026_TILE_LAYER = DUI_TILE_LAYER


@dataclass(frozen=True)
class _CachedDataset:
    signature: tuple[str, int, int]
    payload: dict[str, Any]


_DATASET_CACHE: _CachedDataset | None = None


class DuiDependencyUnavailableError(RuntimeError):
    pass


Dui2026DependencyUnavailableError = DuiDependencyUnavailableError


def _supports_osgeo_reader() -> bool:
    return _OSGEO_IMPORT_ERROR is None and ogr is not None and osr is not None


def _supports_pyshp_reader() -> bool:
    return _PYSHAPE_IMPORT_ERROR is None and _PYPROJ_IMPORT_ERROR is None and pyshp is not None and CRS is not None and Transformer is not None


def _require_dui_reader_dependency() -> None:
    if _supports_osgeo_reader() or _supports_pyshp_reader():
        return
    raise DuiDependencyUnavailableError(
        f"Layer DUI {DUI_DEFAULT_YEAR} non disponibile: installare GDAL/OSGeo oppure pyshp+pyproj nel backend."
    ) from (_OSGEO_IMPORT_ERROR or _PYSHAPE_IMPORT_ERROR or _PYPROJ_IMPORT_ERROR)


def _norm_str(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized if normalized else None


def _norm_bool_label(value: Any, *, yes: str = "SI", no: str = "NO") -> str | None:
    normalized = _norm_str(value)
    if normalized is None:
        return None
    upper = normalized.upper()
    if upper in {"SI", "S", "Y", "YES", "TRUE", "1"}:
        return yes
    if upper in {"NO", "N", "FALSE", "0"}:
        return no
    return upper


def _normalize_domanda_irrigua(value: Any) -> str | None:
    normalized = _norm_str(value)
    if normalized is None:
        return None
    try:
        return str(int(float(normalized.replace(",", "."))))
    except Exception:
        return normalized


def _parse_snapshot_date(filename: str) -> date | None:
    match = SNAPSHOT_DATE_RE.search(filename)
    if match is None:
        return None
    day, month, year = (int(part) for part in match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _is_smb_uri(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme.lower() == "smb"


def _resolve_backup_source() -> str:
    configured = os.environ.get("CATASTO_DUI_BACKUP_PATH") or os.environ.get("CATASTO_DUI_2026_BACKUP_PATH")
    return configured.strip() if configured and configured.strip() else DEFAULT_DUI_BACKUP_URI


def _resolve_backup_dir() -> Path:
    return Path(_resolve_backup_source()).expanduser()


def _find_latest_shapefile_path(base_dir: Path) -> Path:
    if not base_dir.exists():
        raise FileNotFoundError(f"Directory shapefile DUI {DUI_DEFAULT_YEAR} non trovata: {base_dir}")

    candidates = [path for path in base_dir.glob(DUI_DEFAULT_FILE_GLOB.format(year=DUI_DEFAULT_YEAR)) if path.is_file()]
    if not candidates:
        raise FileNotFoundError(f"Nessuno shapefile DUI {DUI_DEFAULT_YEAR} trovato in: {base_dir}")

    def sort_key(path: Path) -> tuple[date, float, str]:
        snapshot_date = _parse_snapshot_date(path.name) or date.min
        stat = path.stat()
        return (snapshot_date, stat.st_mtime, path.name)

    return max(candidates, key=sort_key)


def _remote_file_stat(client: Any, remote_path: str) -> tuple[int, int]:
    output = client.run_command(f"stat -c '%Y %s' {shlex.quote(remote_path)}")
    first_line = next((line.strip() for line in output.splitlines() if line.strip()), "")
    mtime_raw, size_raw = first_line.split(maxsplit=1)
    return int(mtime_raw), int(size_raw)


def _find_latest_remote_shapefile(client: Any, remote_dir: str) -> tuple[str, int, int]:
    if not client.path_exists(remote_dir):
        raise FileNotFoundError(f"Directory shapefile DUI {DUI_DEFAULT_YEAR} non trovata: {remote_dir}")

    output = client.run_command(
        "find "
        f"{shlex.quote(remote_dir)} "
        f"-maxdepth 1 -type f -iname '{DUI_DEFAULT_FILE_FIND_PATTERN.format(year=DUI_DEFAULT_YEAR)}' -print"
    )
    candidates = [line.strip() for line in output.splitlines() if line.strip()]
    if not candidates:
        raise FileNotFoundError(f"Nessuno shapefile DUI {DUI_DEFAULT_YEAR} trovato in: {remote_dir}")

    def sort_key(remote_path: str) -> tuple[date, int, str]:
        name = PurePosixPath(remote_path).name
        mtime, _ = _remote_file_stat(client, remote_path)
        return (_parse_snapshot_date(name) or date.min, mtime, name)

    latest = max(candidates, key=sort_key)
    mtime, size = _remote_file_stat(client, latest)
    return latest, mtime, size


def _source_signature(path: Path) -> tuple[str, int, int]:
    stat = path.stat()
    return (str(path), int(stat.st_mtime_ns), int(stat.st_size))


def _remote_source_signature(remote_path: str, mtime: int, size: int) -> tuple[str, int, int]:
    return (remote_path, mtime, size)


@contextmanager
def _materialized_latest_shapefile():
    source = _resolve_backup_source()
    if not _is_smb_uri(source):
        source_path = _find_latest_shapefile_path(Path(source).expanduser())
        yield source_path, _source_signature(source_path), None
        return

    temp_dir = TemporaryDirectory(prefix=f"gaia-dui-{DUI_DEFAULT_YEAR}-")
    try:
        client = get_nas_client()
        remote_dir = _resolve_remote_directory_path_case_insensitive(client, _smb_uri_to_remote_path(source))
        remote_shp, remote_mtime, remote_size = _find_latest_remote_shapefile(client, remote_dir)
        remote_base = remote_shp.rsplit(".", 1)[0]
        local_shp = Path(temp_dir.name) / PurePosixPath(remote_shp).name
        for extension in _SHAPEFILE_SIDECAR_EXTENSIONS:
            remote_file = f"{remote_base}{extension}"
            if client.path_exists(remote_file):
                client.download_to_local(remote_file, str(local_shp.with_suffix(extension)))
        if not local_shp.exists():
            raise FileNotFoundError(f"Shapefile DUI {DUI_DEFAULT_YEAR} non scaricato dal NAS: {remote_shp}")
        yield local_shp, _remote_source_signature(remote_shp, remote_mtime, remote_size), remote_shp
    except NasConnectorError as exc:
        raise FileNotFoundError(f"Errore accesso NAS DUI {DUI_DEFAULT_YEAR}: {exc}") from exc
    finally:
        temp_dir.cleanup()


def _extract_feature_properties(feature: ogr.Feature) -> dict[str, Any]:
    return _extract_feature_properties_from_mapping(
        {
            "NUM_DOM": feature.GetField("NUM_DOM"),
            "CONTATORE": feature.GetField("CONTATORE"),
            "TELERILEV": feature.GetField("TELERILEV"),
            "DATA": feature.GetField("DATA"),
            "SUP_GRAFIC": feature.GetField("SUP_GRAFIC"),
            "CODICEFISC": feature.GetField("CODICEFISC"),
            "COGN_NOME": feature.GetField("COGN_NOME"),
            "TELEFONO": feature.GetField("TELEFONO"),
            "COLTURA": feature.GetField("COLTURA"),
            "TIPO_DOM": feature.GetField("TIPO_DOM"),
            "ID_OPERAT": feature.GetField("ID_OPERAT"),
            "X": feature.GetField("X"),
            "Y": feature.GetField("Y"),
        }
    )


def _extract_feature_properties_from_mapping(fields: dict[str, Any]) -> dict[str, Any]:
    domanda_irrigua = _normalize_domanda_irrigua(fields.get("NUM_DOM"))
    contatore = _norm_bool_label(fields.get("CONTATORE"))
    telerilev = _norm_bool_label(fields.get("TELERILEV"))
    submitted_at_raw = fields.get("DATA")
    if hasattr(submitted_at_raw, "strftime"):
        submitted_at = submitted_at_raw.strftime("%Y-%m-%d")
    else:
        submitted_at = _norm_str(submitted_at_raw)
    sup_grafic_raw = fields.get("SUP_GRAFIC")
    return {
        "domanda_irrigua": domanda_irrigua,
        "codice_fiscale": _norm_str(fields.get("CODICEFISC")),
        "intestatario": _norm_str(fields.get("COGN_NOME")),
        "telefono": _norm_str(fields.get("TELEFONO")),
        "sup_grafica_mq": int(sup_grafic_raw) if sup_grafic_raw is not None else None,
        "coltura": _norm_str(fields.get("COLTURA")),
        "tipo_domanda": _norm_str(fields.get("TIPO_DOM")),
        "data_domanda": submitted_at,
        "contatore": contatore,
        "telerilev": telerilev,
        "operatore": _norm_str(fields.get("ID_OPERAT")),
        "point_x": fields.get("X"),
        "point_y": fields.get("Y"),
    }


def _transform_geojson_coordinates(coordinates: Any, transformer: Any) -> Any:
    if not isinstance(coordinates, (list, tuple)):
        return coordinates
    if coordinates and all(isinstance(value, (int, float)) for value in coordinates[:2]):
        x, y = transformer.transform(coordinates[0], coordinates[1])
        remainder = list(coordinates[2:]) if len(coordinates) > 2 else []
        return [x, y, *remainder]
    return [_transform_geojson_coordinates(item, transformer) for item in coordinates]


def _transform_geojson_geometry(geometry: dict[str, Any], transformer: Any) -> dict[str, Any]:
    if transformer is None:
        return geometry
    return {
        **geometry,
        "coordinates": _transform_geojson_coordinates(geometry.get("coordinates"), transformer),
    }


def _resolve_fallback_source_crs(path: Path) -> Any:
    prj_path = path.with_suffix(".prj")
    if prj_path.exists():
        prj_wkt = prj_path.read_text(encoding="utf-8", errors="ignore").strip()
        if prj_wkt:
            return CRS.from_wkt(prj_wkt)

    logger.warning("PRJ DUI %s non trovato per %s, uso fallback EPSG:3003", DUI_DEFAULT_YEAR, path)
    return CRS.from_epsg(3003)


def _load_raw_dataset_from_pyshp(path: Path) -> dict[str, Any]:
    _require_dui_reader_dependency()

    reader = pyshp.Reader(str(path))
    try:
        field_names = [field[0] for field in reader.fields[1:]]
        source_crs = _resolve_fallback_source_crs(path)
        target_crs = CRS.from_epsg(4326)
        transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)

        features: list[dict[str, Any]] = []
        for shape_record in reader.iterShapeRecords():
            geometry = getattr(shape_record.shape, "__geo_interface__", None)
            if not geometry:
                continue
            geometry_json = _transform_geojson_geometry(dict(geometry), transformer)
            record_values = shape_record.record.as_dict() if hasattr(shape_record.record, "as_dict") else dict(
                zip(field_names, list(shape_record.record))
            )
            features.append(
                {
                    "type": "Feature",
                    "geometry": geometry_json,
                    "properties": _extract_feature_properties_from_mapping(record_values),
                }
            )
    finally:
        close = getattr(reader, "close", None)
        if callable(close):
            close()

    stat = path.stat()
    return {
        "source_path": str(path),
        "source_filename": path.name,
        "source_date": (_parse_snapshot_date(path.name) or date.fromtimestamp(stat.st_mtime)).isoformat(),
        "source_updated_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "feature_count": len(features),
        "geojson": {
            "type": "FeatureCollection",
            "features": features,
        },
    }


def _load_raw_dataset_from_shapefile(path: Path) -> dict[str, Any]:
    _require_dui_reader_dependency()

    if not _supports_osgeo_reader():
        return _load_raw_dataset_from_pyshp(path)

    datasource = ogr.Open(str(path))
    if datasource is None:
        raise ValueError(f"Impossibile aprire lo shapefile DUI {DUI_DEFAULT_YEAR}: {path}")

    layer = datasource.GetLayer(0)
    if layer is None:
        raise ValueError(f"Layer DUI {DUI_DEFAULT_YEAR} assente nello shapefile: {path}")

    source_srs = layer.GetSpatialRef()
    target_srs = osr.SpatialReference()
    target_srs.ImportFromEPSG(4326)
    transform = osr.CoordinateTransformation(source_srs, target_srs) if source_srs is not None else None

    features: list[dict[str, Any]] = []
    for feature in layer:
        geometry = feature.GetGeometryRef()
        if geometry is None:
            continue
        geometry_copy = geometry.Clone()
        if transform is not None:
            geometry_copy.Transform(transform)
        geometry_json = json.loads(geometry_copy.ExportToJson())
        features.append(
            {
                "type": "Feature",
                "geometry": geometry_json,
                "properties": _extract_feature_properties(feature),
            }
        )

    stat = path.stat()
    return {
        "source_path": str(path),
        "source_filename": path.name,
        "source_date": (_parse_snapshot_date(path.name) or date.fromtimestamp(stat.st_mtime)).isoformat(),
        "source_updated_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "feature_count": len(features),
        "geojson": {
            "type": "FeatureCollection",
            "features": features,
        },
    }


def _get_cached_dataset() -> dict[str, Any]:
    global _DATASET_CACHE

    with _materialized_latest_shapefile() as (source_path, signature, display_source_path):
        if _DATASET_CACHE is not None and _DATASET_CACHE.signature == signature:
            return _DATASET_CACHE.payload

        payload = _load_raw_dataset_from_shapefile(source_path)
        if display_source_path is not None:
            payload["source_path"] = display_source_path
        _DATASET_CACHE = _CachedDataset(signature=signature, payload=payload)
        logger.info("Caricato layer DUI %s da %s (%s feature)", DUI_DEFAULT_YEAR, payload["source_path"], payload["feature_count"])
        return payload


def _load_ruolo_2025_domande_counts(db: Session) -> Counter[str]:
    rows = db.execute(
        select(RuoloParticella.domanda_irrigua).where(
            RuoloParticella.anno_tributario == 2025,
            RuoloParticella.domanda_irrigua.is_not(None),
        )
    ).scalars()
    counts: Counter[str] = Counter()
    for value in rows:
        normalized = _normalize_domanda_irrigua(value)
        if normalized is not None:
            counts[normalized] += 1
    return counts


def _find_dui_features_by_domanda(domanda_irrigua: str) -> list[dict[str, Any]]:
    normalized_domanda = _normalize_domanda_irrigua(domanda_irrigua)
    if normalized_domanda is None:
        return []
    dataset = _get_cached_dataset()
    return [
        feature
        for feature in dataset["geojson"]["features"]
        if _normalize_domanda_irrigua(feature["properties"].get("domanda_irrigua")) == normalized_domanda
    ]


def _to_float(value: Any, digits: int) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), digits)
    except Exception:
        return None


def _is_postgresql_session(db: Session) -> bool:
    bind = db.get_bind()
    return bool(bind is not None and bind.dialect.name == "postgresql")


def _stable_dui_feature_id(dataset: dict[str, Any], index: int, properties: dict[str, Any]) -> str:
    domanda = _normalize_domanda_irrigua(properties.get("domanda_irrigua")) or "senza-domanda"
    source = dataset.get("source_path") or dataset.get("source_filename") or f"dui-{DUI_DEFAULT_YEAR}"
    return str(uuid5(NAMESPACE_URL, f"gaia:catasto:dui:{DUI_DEFAULT_YEAR}:{source}:{domanda}:{index}"))


def _sync_dui_tile_table(db: Session, dataset: dict[str, Any], ruolo_2025_counts: Counter[str]) -> None:
    if not _is_postgresql_session(db):
        return

    db.execute(text("DELETE FROM cat_dui_2026_current"))
    insert_sql = text(
        """
        INSERT INTO cat_dui_2026_current (
          id,
          source_path,
          source_filename,
          source_date,
          source_updated_at,
          domanda_irrigua,
          codice_fiscale,
          intestatario,
          telefono,
          sup_grafica_mq,
          coltura,
          tipo_domanda,
          data_domanda,
          contatore,
          telerilev,
          operatore,
          point_x,
          point_y,
          in_ruolo_2025,
          ruolo_2025_match_count,
          source_payload_json,
          geometry,
          synced_at
        )
        VALUES (
          :id,
          :source_path,
          :source_filename,
          CAST(:source_date AS date),
          CAST(:source_updated_at AS timestamptz),
          :domanda_irrigua,
          :codice_fiscale,
          :intestatario,
          :telefono,
          :sup_grafica_mq,
          :coltura,
          :tipo_domanda,
          :data_domanda,
          :contatore,
          :telerilev,
          :operatore,
          :point_x,
          :point_y,
          :in_ruolo_2025,
          :ruolo_2025_match_count,
          CAST(:source_payload_json AS jsonb),
          ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geometry_geojson), 4326)))::geometry(MULTIPOLYGON, 4326),
          now()
        )
        """
    )

    rows: list[dict[str, Any]] = []
    for index, feature in enumerate(dataset["geojson"]["features"], start=1):
        geometry = feature.get("geometry")
        if not geometry:
            continue
        properties = dict(feature.get("properties") or {})
        domanda_irrigua = _normalize_domanda_irrigua(properties.get("domanda_irrigua"))
        ruolo_hits = int(ruolo_2025_counts.get(domanda_irrigua, 0)) if domanda_irrigua is not None else 0
        rows.append(
            {
                "id": _stable_dui_feature_id(dataset, index, properties),
                "source_path": dataset["source_path"],
                "source_filename": dataset["source_filename"],
                "source_date": dataset["source_date"],
                "source_updated_at": dataset["source_updated_at"],
                "domanda_irrigua": domanda_irrigua,
                "codice_fiscale": _norm_str(properties.get("codice_fiscale")),
                "intestatario": _norm_str(properties.get("intestatario")),
                "telefono": _norm_str(properties.get("telefono")),
                "sup_grafica_mq": _to_float(properties.get("sup_grafica_mq"), 2),
                "coltura": _norm_str(properties.get("coltura")),
                "tipo_domanda": _norm_str(properties.get("tipo_domanda")),
                "data_domanda": _norm_str(properties.get("data_domanda")),
                "contatore": _norm_str(properties.get("contatore")),
                "telerilev": _norm_str(properties.get("telerilev")),
                "operatore": _norm_str(properties.get("operatore")),
                "point_x": _to_float(properties.get("point_x"), 3),
                "point_y": _to_float(properties.get("point_y"), 3),
                "in_ruolo_2025": ruolo_hits > 0,
                "ruolo_2025_match_count": ruolo_hits,
                "source_payload_json": json.dumps(properties),
                "geometry_geojson": json.dumps(geometry),
            }
        )
    if rows:
        db.execute(insert_sql, rows)
    db.commit()


_sync_dui_2026_tile_table = _sync_dui_tile_table


def _load_ruolo_2025_summary_by_domanda(db: Session, domanda_irrigua: str) -> ParticellaPopupRuoloSummary | None:
    normalized_domanda = _normalize_domanda_irrigua(domanda_irrigua)
    if normalized_domanda is None:
        return None

    ltrim_key = normalized_domanda.lstrip("0") or "0"
    rows = db.execute(
        select(
            RuoloParticella,
            RuoloPartita.codice_partita,
            RuoloAvviso.codice_cnc,
        )
        .join(RuoloPartita, RuoloPartita.id == RuoloParticella.partita_id)
        .join(RuoloAvviso, RuoloAvviso.id == RuoloPartita.avviso_id)
        .where(
            RuoloParticella.anno_tributario == 2025,
            RuoloParticella.domanda_irrigua.is_not(None),
            or_(
                RuoloParticella.domanda_irrigua == normalized_domanda,
                func.ltrim(RuoloParticella.domanda_irrigua, "0") == ltrim_key,
            ),
        )
        .order_by(
            desc(RuoloParticella.anno_tributario),
            RuoloParticella.distretto,
            RuoloParticella.foglio,
            RuoloParticella.particella,
            RuoloParticella.subalterno,
        )
    ).all()
    if not rows:
        return None

    items: list[ParticellaPopupRuoloItem] = []
    subalterni: set[str] = set()
    total_sup_catastale = 0.0
    total_sup_irrigata = 0.0
    total_importo_manut = 0.0
    total_importo_irrig = 0.0
    total_importo_ist = 0.0
    total_importo = 0.0
    has_sup_catastale = False
    has_sup_irrigata = False
    has_importo_manut = False
    has_importo_irrig = False
    has_importo_ist = False
    has_importo = False

    for index, (ruolo_particella, codice_partita, codice_cnc) in enumerate(rows):
        if ruolo_particella.subalterno:
            subalterni.add(ruolo_particella.subalterno)

        sup_catastale_ha = _to_float(ruolo_particella.sup_catastale_ha, 4)
        sup_irrigata_ha = _to_float(ruolo_particella.sup_irrigata_ha, 4)
        importo_manut = _to_float(ruolo_particella.importo_manut, 2)
        importo_irrig = _to_float(ruolo_particella.importo_irrig, 2)
        importo_ist = _to_float(ruolo_particella.importo_ist, 2)
        importo_totale = _to_float((importo_manut or 0) + (importo_irrig or 0) + (importo_ist or 0), 2)

        if sup_catastale_ha is not None:
            has_sup_catastale = True
            total_sup_catastale += sup_catastale_ha
        if sup_irrigata_ha is not None:
            has_sup_irrigata = True
            total_sup_irrigata += sup_irrigata_ha
        if importo_manut is not None:
            has_importo_manut = True
            total_importo_manut += importo_manut
        if importo_irrig is not None:
            has_importo_irrig = True
            total_importo_irrig += importo_irrig
        if importo_ist is not None:
            has_importo_ist = True
            total_importo_ist += importo_ist
        if importo_totale is not None:
            has_importo = True
            total_importo += importo_totale

        if index < 12:
            items.append(
                ParticellaPopupRuoloItem(
                    anno_tributario=2025,
                    domanda_irrigua=ruolo_particella.domanda_irrigua,
                    subalterno=ruolo_particella.subalterno,
                    coltura=ruolo_particella.coltura,
                    sup_catastale_ha=sup_catastale_ha,
                    sup_irrigata_ha=sup_irrigata_ha,
                    importo_manut_euro=importo_manut,
                    importo_irrig_euro=importo_irrig,
                    importo_ist_euro=importo_ist,
                    importo_totale_euro=importo_totale,
                    codice_partita=codice_partita,
                    codice_cnc=codice_cnc,
                )
            )

    all_subalterni = {
        row[0].subalterno
        for row in rows
        if row[0].subalterno
    }
    return ParticellaPopupRuoloSummary(
        anno_tributario_latest=2025,
        anno_tributario_richiesto=2025,
        source_mode="dui_domanda",
        source_note="Dettaglio ruolo 2025 aggregato per domanda irrigua.",
        n_righe=len(rows),
        n_subalterni=len(all_subalterni),
        sup_catastale_ha_totale=round(total_sup_catastale, 4) if has_sup_catastale else None,
        sup_irrigata_ha_totale=round(total_sup_irrigata, 4) if has_sup_irrigata else None,
        importo_manut_euro_totale=round(total_importo_manut, 2) if has_importo_manut else None,
        importo_irrig_euro_totale=round(total_importo_irrig, 2) if has_importo_irrig else None,
        importo_ist_euro_totale=round(total_importo_ist, 2) if has_importo_ist else None,
        importo_totale_euro=round(total_importo, 2) if has_importo else None,
        items=items,
    )


def get_dui_latest_layer(db: Session) -> DuiLayerResponse:
    _require_dui_reader_dependency()
    dataset = _get_cached_dataset()
    ruolo_2025_counts = _load_ruolo_2025_domande_counts(db)
    _sync_dui_tile_table(db, dataset, ruolo_2025_counts)

    features: list[dict[str, Any]] = []
    in_ruolo_2025 = 0
    with_contatore = 0
    with_telerilev = 0

    for feature in dataset["geojson"]["features"]:
        properties = dict(feature["properties"])
        domanda_irrigua = properties.get("domanda_irrigua")
        ruolo_hits = int(ruolo_2025_counts.get(domanda_irrigua, 0)) if domanda_irrigua is not None else 0
        present_in_ruolo_2025 = ruolo_hits > 0
        if present_in_ruolo_2025:
            in_ruolo_2025 += 1
        if properties.get("contatore") == "SI":
            with_contatore += 1
        if properties.get("telerilev") == "SI":
            with_telerilev += 1

        properties["in_ruolo_2025"] = present_in_ruolo_2025
        properties["ruolo_2025_match_count"] = ruolo_hits
        properties["__overlayColor"] = ROLE_MATCH_COLOR if present_in_ruolo_2025 else ROLE_MISSING_COLOR
        properties["__overlayOutlineColor"] = properties["__overlayColor"]
        features.append(
            {
                "type": feature["type"],
                "geometry": feature["geometry"],
                "properties": properties,
            }
        )

    total = int(dataset["feature_count"])
    stats = DuiLayerStats(
        total_polygons=total,
        in_ruolo_2025=in_ruolo_2025,
        not_in_ruolo_2025=max(0, total - in_ruolo_2025),
        with_contatore=with_contatore,
        without_contatore=max(0, total - with_contatore),
        with_telerilev=with_telerilev,
    )
    return DuiLayerResponse(
        label=f"DUI {DUI_DEFAULT_YEAR} live",
        year=DUI_DEFAULT_YEAR,
        source_path=dataset["source_path"],
        source_filename=dataset["source_filename"],
        source_date=dataset["source_date"],
        source_updated_at=dataset["source_updated_at"],
        tile_layer=DUI_TILE_LAYER,
        rendering_mode="martin_tiles" if _is_postgresql_session(db) else "geojson_fallback",
        stats=stats,
        geojson={"type": "FeatureCollection", "features": [] if _is_postgresql_session(db) else features},
    )


def get_dui_domanda_detail(db: Session, domanda_irrigua: str) -> DuiDomandaDetailResponse:
    _require_dui_reader_dependency()
    normalized_domanda = _normalize_domanda_irrigua(domanda_irrigua)
    if normalized_domanda is None:
        raise ValueError("Domanda irrigua non valida")

    dataset = _get_cached_dataset()
    features = _find_dui_features_by_domanda(normalized_domanda)
    if not features:
        raise FileNotFoundError(f"Domanda irrigua {normalized_domanda} non trovata nello shapefile DUI {DUI_DEFAULT_YEAR}")

    first_properties = features[0]["properties"]
    total_sup_grafica = sum(float(feature["properties"].get("sup_grafica_mq") or 0) for feature in features)
    ruolo_summary = _load_ruolo_2025_summary_by_domanda(db, normalized_domanda)
    ruolo_match_count = ruolo_summary.n_righe if ruolo_summary is not None else 0

    return DuiDomandaDetailResponse(
        domanda_irrigua=normalized_domanda,
        year=DUI_DEFAULT_YEAR,
        codice_fiscale=_norm_str(first_properties.get("codice_fiscale")),
        intestatario=_norm_str(first_properties.get("intestatario")),
        telefono=_norm_str(first_properties.get("telefono")),
        coltura=_norm_str(first_properties.get("coltura")),
        tipo_domanda=_norm_str(first_properties.get("tipo_domanda")),
        data_domanda=_norm_str(first_properties.get("data_domanda")),
        contatore=_norm_str(first_properties.get("contatore")),
        telerilev=_norm_str(first_properties.get("telerilev")),
        operatore=_norm_str(first_properties.get("operatore")),
        sup_grafica_mq_totale=round(total_sup_grafica, 2) if total_sup_grafica > 0 else None,
        n_poligoni=len(features),
        x=_to_float(first_properties.get("point_x"), 3),
        y=_to_float(first_properties.get("point_y"), 3),
        in_ruolo_2025=ruolo_match_count > 0,
        ruolo_2025_match_count=ruolo_match_count,
        ruolo_summary=ruolo_summary,
        source_filename=dataset["source_filename"],
        source_date=dataset["source_date"],
    )


get_dui_2026_latest_layer = get_dui_latest_layer
get_dui_2026_domanda_detail = get_dui_domanda_detail
