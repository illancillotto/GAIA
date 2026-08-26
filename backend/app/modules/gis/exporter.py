from __future__ import annotations

import hashlib
import json
import re
import tempfile
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import chain
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

import shapefile
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.gis.artifact_storage import publish_artifact
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
        value = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value).encode("utf-8")[:254].decode("utf-8", errors="ignore")


def _row_feature(
    row: Any,
    geometry_column: str,
    geometry_alias: str | None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    geometry = _load_geometry(row.get(geometry_alias or geometry_column))
    attributes = {
        key: value
        for key, value in row.items()
        if key not in {geometry_column, "__geometry_geojson"} and not key.startswith("_sa_")
    }
    return attributes, geometry


def _feature_rows(db: Session, layer: GisLayer) -> Iterator[tuple[dict[str, Any], dict[str, Any] | None]]:
    dialect_name = db.get_bind().dialect.name
    query, geometry_column, geometry_alias = _source_query(layer, dialect_name)
    if dialect_name == "postgresql":
        db.execute(text("SET LOCAL max_parallel_workers_per_gather = 0"))
    result = db.execute(query, execution_options={"stream_results": True, "yield_per": 1000})
    try:
        yield from (_row_feature(row, geometry_column, geometry_alias) for row in result.mappings())
    finally:
        result.close()


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


def _write_features(
    writer: shapefile.Writer,
    field_mapping: dict[str, str],
    features: Iterator[tuple[dict[str, Any], dict[str, Any] | None]],
) -> int:
    row_count = 0
    for attributes, geometry in features:
        shape = _shape_from_geometry(geometry)
        writer.null() if shape is None else writer.shape(shape)
        writer.record(*[_record_value(attributes.get(name)) for name in field_mapping])
        row_count += 1
    return row_count


def export_layer_to_shapefile_zip(
    db: Session,
    layer: GisLayer,
    *,
    version_label: str,
    nas_path: str,
    metadata: dict[str, Any],
) -> GisExportArtifact:
    features = iter(_feature_rows(db, layer))
    first_feature = next(features, None)
    field_mapping: dict[str, str] = {}
    used_names: set[str] = set()
    if first_feature is not None:
        for key in first_feature[0]:
            field_mapping[key] = _field_name(key, used_names)
    if not field_mapping:
        field_mapping["_gaia_empty"] = "GAIA_EMPTY"

    with tempfile.TemporaryDirectory(prefix="gaia-gis-export-") as temp_dir:
        temp_root = Path(temp_dir)
        shapefile_base = temp_root / layer.name
        writer = shapefile.Writer(str(shapefile_base), shapeType=None, encoding="utf-8")
        for dbf_name in field_mapping.values():
            writer.field(dbf_name, "C", size=254)
        row_count = _write_features(
            writer,
            field_mapping,
            chain(() if first_feature is None else (first_feature,), features),
        )
        writer.close()
        shapefile_base.with_suffix(".cpg").write_text("UTF-8", encoding="ascii")
        manifest = _manifest(
            layer=layer,
            version_label=version_label,
            row_count=row_count,
            field_mapping=field_mapping,
            metadata=metadata,
        )
        manifest_path = temp_root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

        temp_zip = temp_root / f"{uuid.uuid4().hex}.zip"
        with ZipFile(temp_zip, "w", compression=ZIP_DEFLATED) as archive:
            for suffix in ("shp", "shx", "dbf", "cpg"):
                artifact = shapefile_base.with_suffix(f".{suffix}")
                archive.write(artifact, arcname=f"{layer.name}.{suffix}")
            archive.write(manifest_path, arcname="manifest.json")
        checksum = _sha256(temp_zip)
        publish_artifact(temp_zip, nas_path)

    return GisExportArtifact(path=Path(nas_path), checksum_sha256=checksum, row_count=row_count, manifest=manifest)
