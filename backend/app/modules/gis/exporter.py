from __future__ import annotations

import hashlib
import json
import re
import tempfile
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

import shapefile
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.gis.models import GisLayer


class GisExportError(RuntimeError):
    pass


@dataclass(frozen=True)
class GisExportArtifact:
    path: Path
    checksum_sha256: str
    row_count: int
    manifest: dict[str, Any]


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _source_query(layer: GisLayer, dialect_name: str) -> tuple[Any, str, str | None]:
    table_name = layer.postgis_table or layer.name
    geometry_column = layer.geometry_column or "geometry"
    if dialect_name == "sqlite":
        return text(f"SELECT * FROM {_quote_identifier(table_name)}"), geometry_column, None
    schema_name = layer.postgis_schema or "public"
    source_table = f"{_quote_identifier(schema_name)}.{_quote_identifier(table_name)}"
    geometry_identifier = _quote_identifier(geometry_column)
    return text(f"SELECT *, ST_AsGeoJSON({geometry_identifier}) AS __geometry_geojson FROM {source_table}"), geometry_column, "__geometry_geojson"


def _load_geometry(raw_value: Any) -> dict[str, Any] | None:
    if raw_value is None:
        return None
    if isinstance(raw_value, dict):
        return raw_value
    if isinstance(raw_value, str):
        return json.loads(raw_value)
    raise GisExportError("GIS export geometry must be GeoJSON")


def _field_name(original: str, used_names: set[str]) -> str:
    base_name = re.sub(r"[^A-Z0-9_]", "_", original.upper()).strip("_") or "FIELD"
    candidate = base_name[:10]
    counter = 1
    while candidate in used_names:
        suffix = f"_{counter}"
        candidate = f"{base_name[: 10 - len(suffix)]}{suffix}"
        counter += 1
    used_names.add(candidate)
    return candidate


def _record_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)[:254]
    return str(value)[:254]


def _feature_rows(db: Session, layer: GisLayer) -> list[tuple[dict[str, Any], dict[str, Any] | None]]:
    query, geometry_column, geometry_alias = _source_query(layer, db.get_bind().dialect.name)
    rows = db.execute(query).mappings().all()
    features: list[tuple[dict[str, Any], dict[str, Any] | None]] = []
    for row in rows:
        geometry = _load_geometry(row.get(geometry_alias or geometry_column))
        attributes = {
            key: value
            for key, value in row.items()
            if key not in {geometry_column, "__geometry_geojson"} and not key.startswith("_sa_")
        }
        features.append((attributes, geometry))
    return features


def _shape_from_geometry(geometry: dict[str, Any] | None) -> shapefile.Shape | None:
    if geometry is None:
        return None
    try:
        return shapefile.Shape._from_geojson(geometry)
    except Exception as exc:  # pragma: no cover - pyshp owns concrete geometry validation
        raise GisExportError(f"GIS export geometry not supported: {geometry.get('type')}") from exc


def _manifest(
    *,
    layer: GisLayer,
    version_label: str,
    row_count: int,
    field_mapping: dict[str, str],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    return {
        "format": "shapefile",
        "source": "postgis",
        "workspace": layer.workspace,
        "layer_name": layer.name,
        "version_label": version_label,
        "postgis_schema": layer.postgis_schema,
        "postgis_table": layer.postgis_table,
        "geometry_column": layer.geometry_column,
        "geometry_type": layer.geometry_type,
        "srid": layer.srid,
        "row_count": row_count,
        "field_mapping": field_mapping,
        "metadata": metadata,
        "generated_at": datetime.now(UTC).isoformat(),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def export_layer_to_shapefile_zip(
    db: Session,
    layer: GisLayer,
    *,
    version_label: str,
    nas_path: str,
    metadata: dict[str, Any],
) -> GisExportArtifact:
    features = _feature_rows(db, layer)
    shapes = [(attributes, _shape_from_geometry(geometry)) for attributes, geometry in features]
    shape_type = next((shape.shapeType for _, shape in shapes if shape is not None), shapefile.NULL)
    field_mapping: dict[str, str] = {}
    used_names: set[str] = set()
    for attributes, _ in shapes:
        for key in attributes:
            if key not in field_mapping:
                field_mapping[key] = _field_name(key, used_names)
    if not field_mapping:
        field_mapping["_gaia_empty"] = "GAIA_EMPTY"
    final_path = Path(nas_path)
    final_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = _manifest(
        layer=layer,
        version_label=version_label,
        row_count=len(shapes),
        field_mapping=field_mapping,
        metadata=metadata,
    )

    with tempfile.TemporaryDirectory(prefix="gaia-gis-export-") as temp_dir:
        temp_root = Path(temp_dir)
        shapefile_base = temp_root / layer.name
        writer = shapefile.Writer(str(shapefile_base), shapeType=shape_type, encoding="utf-8")
        for original_name, dbf_name in field_mapping.items():
            writer.field(dbf_name, "C", size=254)
        for attributes, shape in shapes:
            if shape is None:
                writer.null()
            else:
                writer.shape(shape)
            writer.record(*[_record_value(attributes.get(original_name)) for original_name in field_mapping])
        writer.close()
        shapefile_base.with_suffix(".cpg").write_text("UTF-8", encoding="ascii")
        manifest_path = temp_root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

        temp_zip = final_path.parent / f".{final_path.name}.{uuid.uuid4().hex}.tmp"
        with ZipFile(temp_zip, "w", compression=ZIP_DEFLATED) as archive:
            for suffix in ("shp", "shx", "dbf", "cpg"):
                artifact = shapefile_base.with_suffix(f".{suffix}")
                archive.write(artifact, arcname=f"{layer.name}.{suffix}")
            archive.write(manifest_path, arcname="manifest.json")
        checksum = _sha256(temp_zip)
        temp_zip.replace(final_path)

    return GisExportArtifact(path=final_path, checksum_sha256=checksum, row_count=len(shapes), manifest=manifest)
