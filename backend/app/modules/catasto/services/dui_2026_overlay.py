from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
import json
import logging
import os
from pathlib import Path
import re
from typing import Any

try:
    from osgeo import ogr, osr
except ModuleNotFoundError as exc:  # pragma: no cover - exercised through the runtime guard
    ogr = None
    osr = None
    _OSGEO_IMPORT_ERROR: ModuleNotFoundError | None = exc
else:
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
else:
    _PYPROJ_IMPORT_ERROR = None
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from app.modules.catasto.schemas.gis_schemas import (
    Dui2026DomandaDetailResponse,
    Dui2026LayerResponse,
    Dui2026LayerStats,
    ParticellaPopupRuoloItem,
    ParticellaPopupRuoloSummary,
)
from app.modules.ruolo.models import RuoloAvviso, RuoloParticella, RuoloPartita


logger = logging.getLogger(__name__)

DEFAULT_DUI_2026_BACKUP_DIR = Path(
    f"/run/user/{os.getuid()}/gvfs/"
    "smb-share:server=nas_cbo.local,share=settore%20catasto/"
    "DOMANDE UTENZA IRRIGUA/Dui2026/Shp_Dui2026/Backup"
)
SNAPSHOT_DATE_RE = re.compile(r"al_(\d{2})-(\d{2})-(\d{4})", re.IGNORECASE)
ROLE_MATCH_COLOR = "#0F766E"
ROLE_MISSING_COLOR = "#D97706"


@dataclass(frozen=True)
class _CachedDataset:
    signature: tuple[str, int, int]
    payload: dict[str, Any]


_DATASET_CACHE: _CachedDataset | None = None


class Dui2026DependencyUnavailableError(RuntimeError):
    pass


def _supports_osgeo_reader() -> bool:
    return _OSGEO_IMPORT_ERROR is None and ogr is not None and osr is not None


def _supports_pyshp_reader() -> bool:
    return _PYSHAPE_IMPORT_ERROR is None and _PYPROJ_IMPORT_ERROR is None and pyshp is not None and CRS is not None and Transformer is not None


def _require_dui_reader_dependency() -> None:
    if _supports_osgeo_reader() or _supports_pyshp_reader():
        return
    raise Dui2026DependencyUnavailableError(
        "Layer DUI 2026 non disponibile: installare GDAL/OSGeo oppure pyshp+pyproj nel backend."
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


def _resolve_backup_dir() -> Path:
    configured = os.environ.get("CATASTO_DUI_2026_BACKUP_PATH")
    return Path(configured).expanduser() if configured else DEFAULT_DUI_2026_BACKUP_DIR


def _find_latest_shapefile_path(base_dir: Path) -> Path:
    if not base_dir.exists():
        raise FileNotFoundError(f"Directory shapefile DUI 2026 non trovata: {base_dir}")

    candidates = [path for path in base_dir.glob("Dui2026-TOTALE-al_*.shp") if path.is_file()]
    if not candidates:
        raise FileNotFoundError(f"Nessuno shapefile DUI 2026 trovato in: {base_dir}")

    def sort_key(path: Path) -> tuple[date, float, str]:
        snapshot_date = _parse_snapshot_date(path.name) or date.min
        stat = path.stat()
        return (snapshot_date, stat.st_mtime, path.name)

    return max(candidates, key=sort_key)


def _source_signature(path: Path) -> tuple[str, int, int]:
    stat = path.stat()
    return (str(path), int(stat.st_mtime_ns), int(stat.st_size))


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

    logger.warning("PRJ DUI 2026 non trovato per %s, uso fallback EPSG:3003", path)
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
        raise ValueError(f"Impossibile aprire lo shapefile DUI 2026: {path}")

    layer = datasource.GetLayer(0)
    if layer is None:
        raise ValueError(f"Layer DUI 2026 assente nello shapefile: {path}")

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

    source_path = _find_latest_shapefile_path(_resolve_backup_dir())
    signature = _source_signature(source_path)
    if _DATASET_CACHE is not None and _DATASET_CACHE.signature == signature:
        return _DATASET_CACHE.payload

    payload = _load_raw_dataset_from_shapefile(source_path)
    _DATASET_CACHE = _CachedDataset(signature=signature, payload=payload)
    logger.info("Caricato layer DUI 2026 da %s (%s feature)", source_path, payload["feature_count"])
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


def get_dui_2026_latest_layer(db: Session) -> Dui2026LayerResponse:
    _require_dui_reader_dependency()
    dataset = _get_cached_dataset()
    ruolo_2025_counts = _load_ruolo_2025_domande_counts(db)

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
    stats = Dui2026LayerStats(
        total_polygons=total,
        in_ruolo_2025=in_ruolo_2025,
        not_in_ruolo_2025=max(0, total - in_ruolo_2025),
        with_contatore=with_contatore,
        without_contatore=max(0, total - with_contatore),
        with_telerilev=with_telerilev,
    )
    return Dui2026LayerResponse(
        label="DUI 2026 live",
        source_path=dataset["source_path"],
        source_filename=dataset["source_filename"],
        source_date=dataset["source_date"],
        source_updated_at=dataset["source_updated_at"],
        stats=stats,
        geojson={"type": "FeatureCollection", "features": features},
    )


def get_dui_2026_domanda_detail(db: Session, domanda_irrigua: str) -> Dui2026DomandaDetailResponse:
    _require_dui_reader_dependency()
    normalized_domanda = _normalize_domanda_irrigua(domanda_irrigua)
    if normalized_domanda is None:
        raise ValueError("Domanda irrigua non valida")

    dataset = _get_cached_dataset()
    features = _find_dui_features_by_domanda(normalized_domanda)
    if not features:
        raise FileNotFoundError(f"Domanda irrigua {normalized_domanda} non trovata nello shapefile DUI 2026")

    first_properties = features[0]["properties"]
    total_sup_grafica = sum(float(feature["properties"].get("sup_grafica_mq") or 0) for feature in features)
    ruolo_summary = _load_ruolo_2025_summary_by_domanda(db, normalized_domanda)
    ruolo_match_count = ruolo_summary.n_righe if ruolo_summary is not None else 0

    return Dui2026DomandaDetailResponse(
        domanda_irrigua=normalized_domanda,
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
